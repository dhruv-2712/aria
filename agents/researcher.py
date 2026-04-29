# agents/researcher.py
import time
import concurrent.futures
from core.groq_client import build_model, call_groq
from core.memory import log_agent_call
from core.search import search, fetch_page


class ResearcherAgent:
    def __init__(self):
        self.model = build_model(temperature=0.2)
        self.agent_name = "researcher"

    def run(self, input_data: dict) -> dict:
        self._validate_input(input_data)
        session_id    = input_data["session_id"]
        queries       = input_data["queries"]
        original_query = input_data["original_query"]

        start = time.time()
        print(f"[Researcher] Running {len(queries)} web searches in parallel...")

        # Search all queries concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(queries)) as ex:
            raw_batches = list(ex.map(lambda q: search(q, max_results=5), queries))

        # Flatten + tag with query index
        all_results = []
        for idx, batch in enumerate(raw_batches):
            for r in batch:
                r["query_index"] = idx + 1
                all_results.append(r)

        print(f"[Researcher] {len(all_results)} raw results — fetching page content...")

        # Fetch full page text concurrently (best-effort, failures return "")
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            pages = list(ex.map(lambda r: fetch_page(r["url"]), all_results))

        for r, page_text in zip(all_results, pages):
            if page_text:
                r["content"] = page_text   # replace snippet with full text

        # LLM extraction: turn raw results into structured findings
        all_findings = self._extract_findings(all_results, original_query)

        # URL-level dedup
        seen_urls, unique = set(), []
        for f in all_findings:
            url = f.get("source_url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique.append(f)

        high_q  = [f for f in unique if f.get("confidence_score", 0) >= 0.5]
        flagged = [f for f in unique if f.get("confidence_score", 0) < 0.5]

        output = {
            "findings":           unique,
            "high_quality_count": len(high_q),
            "flagged_count":      len(flagged),
            "total_queries_run":  len(queries),
            "status":             "success",
        }

        duration_ms = int((time.time() - start) * 1000)
        log_agent_call(session_id, self.agent_name, input_data, output, duration_ms)
        print(f"[Researcher] Done in {duration_ms}ms — {len(unique)} findings "
              f"({len(high_q)} high-quality).")
        return output

    def _extract_findings(self, results: list, original_query: str) -> list:
        if not results:
            return []

        results_text = ""
        for i, r in enumerate(results[:20]):  # cap to avoid token overflow
            snippet = r.get("content") or r.get("snippet", "")
            results_text += (
                f"\n[{i+1}] URL: {r.get('url', 'unknown')}\n"
                f"Title: {r.get('title', '')}\n"
                f"Content: {snippet[:600]}\n"
            )

        prompt = f"""
ROLE: You are an expert research analyst extracting structured intelligence
from live web search results.

RESEARCH QUESTION: {original_query}

SEARCH RESULTS:
{results_text}

TASK:
For each search result that contains information relevant to the research question,
extract one structured finding. Skip results that are irrelevant or contain no
substantive information.

OUTPUT FORMAT:
Return ONLY a valid JSON array. No explanation. No markdown. Just the array.
[
  {{
    "content": "The key finding from this source (2-4 sentences, specific and informative)",
    "source_url": "the exact URL from the result",
    "date": "publication date if visible in content, otherwise 'recent'",
    "confidence_score": 0.85,
    "domain": "scientific/economic/political/social/technical/historical/ethical/cultural"
  }}
]

RULES:
- Only include findings directly relevant to the research question
- confidence_score: 0.9+ for peer-reviewed/government sources, 0.7-0.89 for reputable outlets,
  0.5-0.69 for uncertain provenance, below 0.5 for speculative content
- content must be specific and informative — not vague summaries
- Use the exact source URL from the result (never 'web_search')
- Skip results with no useful content
"""
        result = call_groq(self.model, prompt, expect_json=True)

        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "error" not in result:
            for val in result.values():
                if isinstance(val, list):
                    return val

        print("[Researcher] Warning: unexpected extraction response — returning empty.")
        return []

    def _validate_input(self, data: dict):
        required = ["session_id", "queries", "original_query"]
        for field in required:
            if field not in data:
                raise ValueError(f"[Researcher] Missing required field: {field}")
        if not isinstance(data["queries"], list) or not data["queries"]:
            raise ValueError("[Researcher] 'queries' must be a non-empty list")
