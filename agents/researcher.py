# agents/researcher.py
import time
from core.groq_client import build_model, call_groq
from core.memory import log_agent_call


class ResearcherAgent:
    def __init__(self):
        self.model = build_model(temperature=0.2)
        self.agent_name = "researcher"

    def run(self, input_data: dict) -> dict:
        self._validate_input(input_data)
        session_id = input_data["session_id"]
        queries = input_data["queries"]
        original_query = input_data["original_query"]

        start = time.time()
        print(f"[Researcher] Researching {len(queries)} queries in one call...")
        all_findings = self._research_all(queries, original_query)

        seen_urls = set()
        unique_findings = []
        for f in all_findings:
            url = f.get("source_url", "")
            if url not in seen_urls:
                seen_urls.add(url)
                unique_findings.append(f)

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

    def _research_all(self, queries: list, original_query: str) -> list:
        queries_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(queries))

        prompt = f"""
ROLE: You are an expert research agent. Your job is to find accurate,
high-quality information across multiple search queries in one pass.

CONTEXT:
- Original research question: {original_query}

QUERIES TO RESEARCH:
{queries_text}

TASK:
For EACH query above, find at least 3 distinct findings from different angles.
Score each finding's confidence honestly based on source quality, recency,
and corroboration.

OUTPUT FORMAT:
Return ONLY a valid JSON array. No explanation. No markdown. Just the array.
[
  {{
    "query_index": 1,
    "content": "The specific finding or fact (2-4 sentences, be detailed)",
    "source_url": "URL of the source or 'web_search' if uncertain",
    "date": "Publication date or 'recent' if unknown",
    "confidence_score": 0.85,
    "angle": "economic/technical/social/scientific/political/etc"
  }}
]

RULES:
- query_index must match the number of the query above (1-based)
- Return minimum 3 findings per query
- confidence_score between 0.0 and 1.0
- Never fabricate sources — use 'web_search' as source_url if uncertain
- Each finding must cover a different angle
- content must be factual and specific, not vague
"""
        result = call_groq(self.model, prompt, expect_json=True)

        if isinstance(result, list):
            return result
        if isinstance(result, dict) and "error" not in result:
            for val in result.values():
                if isinstance(val, list):
                    return val

        print("[Researcher] Warning: unexpected response format, returning empty.")
        return []

    def _validate_input(self, data: dict):
        required = ["session_id", "queries", "original_query"]
        for field in required:
            if field not in data:
                raise ValueError(f"[Researcher] Missing required field: {field}")
        if not isinstance(data["queries"], list) or len(data["queries"]) == 0:
            raise ValueError("[Researcher] 'queries' must be a non-empty list")
