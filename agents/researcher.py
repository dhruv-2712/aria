# agents/researcher.py
import time
from core.gemini_client import build_model, call_gemini
from core.memory import log_agent_call


class ResearcherAgent:
    def __init__(self):
        # use_search=True gives this agent Google Search grounding
        self.model = build_model(temperature=0.2, use_search=False)
        self.agent_name = "researcher"

    def run(self, input_data: dict) -> dict:
        """
        input_data = {
            "session_id": str,
            "queries": [str],        # list of search queries
            "original_query": str    # the user's original question
        }
        """
        self._validate_input(input_data)
        session_id = input_data["session_id"]
        queries = input_data["queries"]
        original_query = input_data["original_query"]

        start = time.time()
        all_findings = []

        for query in queries:
            print(f"[Researcher] Searching: {query}")
            findings = self._research_query(query, original_query)
            all_findings.extend(findings)

        # Deduplicate by content similarity (simple URL-based dedup)
        seen_urls = set()
        unique_findings = []
        for f in all_findings:
            url = f.get("source_url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique_findings.append(f)

        # Flag low-confidence findings
        flagged = [f for f in unique_findings if f.get("confidence_score", 0) < 0.5]
        high_quality = [f for f in unique_findings if f.get("confidence_score", 0) >= 0.5]

        output = {
            "findings": unique_findings,
            "high_quality_count": len(high_quality),
            "flagged_count": len(flagged),
            "total_queries_run": len(queries),
            "status": "success"
        }

        duration_ms = int((time.time() - start) * 1000)
        log_agent_call(session_id, self.agent_name, input_data, output, duration_ms)
        print(f"[Researcher] Done. {len(unique_findings)} findings, {len(flagged)} flagged.")
        return output

    def _research_query(self, query: str, original_query: str) -> list:
        prompt = f"""
ROLE: You are an expert research agent with access to Google Search.
Your job is to find accurate, high-quality information on a topic.

CONTEXT:
- Original research question: {original_query}
- Current search query: {query}

TASK:
Search for information about "{query}" and return structured findings.
Find at least 3 distinct pieces of information from different angles.
For each finding, honestly score your confidence based on:
- Source quality (academic/news/official = high, blog/forum = low)
- Information recency
- Corroboration from multiple sources

OUTPUT FORMAT:
Return ONLY a valid JSON array. No explanation. No markdown. Just the array.
[
  {{
    "content": "The specific finding or fact (2-4 sentences, be detailed)",
    "source_url": "URL of the source or 'web_search' if grounded",
    "date": "Publication date or 'recent' if unknown",
    "confidence_score": 0.0,
    "angle": "What perspective this covers (economic/technical/social/etc)"
  }}
]

RULES:
- Return minimum 3 findings per query
- confidence_score must be between 0.0 and 1.0
- Never fabricate sources — use 'web_search' as source_url if uncertain
- Each finding must cover a different angle
- content must be factual and specific, not vague
"""
        result = call_gemini(self.model, prompt, expect_json=True)

        # call_gemini returns a dict on error, list on success
        if isinstance(result, list):
            return result
        elif isinstance(result, dict) and "error" not in result:
            # Sometimes Gemini wraps the array in an object
            for key in result:
                if isinstance(result[key], list):
                    return result[key]
        
        print(f"[Researcher] Warning: bad response for query '{query}'")
        return []

    def _validate_input(self, data: dict):
        required = ["session_id", "queries", "original_query"]
        for field in required:
            if field not in data:
                raise ValueError(f"[Researcher] Missing required field: {field}")
        if not isinstance(data["queries"], list) or len(data["queries"]) == 0:
            raise ValueError("[Researcher] 'queries' must be a non-empty list")