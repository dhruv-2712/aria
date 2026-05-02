# agents/classifier.py
import time
from core.groq_client import build_model, call_groq
from core.memory import log_agent_call
from core.config import MAX_RESEARCH_LOOPS

VALID_DOMAINS = [
    "scientific", "economic", "political", "social",
    "technical", "historical", "ethical", "cultural"
]


class ClassifierAgent:
    def __init__(self):
        self.model = build_model(temperature=0.2, smart=False)
        self.agent_name = "classifier"

    def run(self, input_data: dict) -> dict:
        self._validate_input(input_data)
        session_id = input_data["session_id"]
        findings = input_data["findings"]
        original_query = input_data["original_query"]
        loop_count = input_data.get("loop_count", 0)

        start = time.time()

        classified = self._classify_findings(findings, original_query)
        gaps = self._identify_gaps(classified)

        # Only generate follow-up queries if the research loop will actually use them
        follow_ups = []
        if gaps and loop_count < MAX_RESEARCH_LOOPS:
            follow_ups = self._generate_follow_up_queries(gaps, original_query)
            print(f"[Classifier] Gaps found in: {gaps}. Generating {len(follow_ups)} follow-up queries.")
        else:
            print(f"[Classifier] Skipping follow-up generation (loop disabled or limit reached).")

        output = {
            "domains": classified,
            "gaps": gaps,
            "follow_ups": follow_ups,
            "loop_count": loop_count,
            "total_findings_classified": len(findings),
            "status": "success"
        }

        duration_ms = int((time.time() - start) * 1000)
        log_agent_call(session_id, self.agent_name, input_data, output, duration_ms)
        print(f"[Classifier] Done. Domains covered: {list(classified.keys())}")
        return output

    def _classify_findings(self, findings: list, original_query: str) -> dict:
        findings_text = ""
        for i, f in enumerate(findings[:12]):  # cap to avoid token bloat
            findings_text += f"\n[{i}] {f.get('content', '')[:150]}"

        prompt = f"""
ROLE: You are a domain classification expert for research intelligence.

CONTEXT:
- Research topic: {original_query}
- Findings to classify:
{findings_text}

TASK:
Classify each finding (by its index number) into one or more of these domains:
{VALID_DOMAINS}

OUTPUT FORMAT:
Return ONLY valid JSON. No markdown. No explanation.
{{
  "scientific": [0, 3, 5],
  "economic": [1, 4],
  "political": [],
  "social": [2],
  "technical": [3],
  "historical": [],
  "ethical": [6],
  "cultural": []
}}

RULES:
- Use the finding's index number (0-based) as the value
- A finding can appear in multiple domains if it spans topics
- Every domain key must be present in output, even if empty list
- Only use the 8 specified domain names
"""
        result = call_groq(self.model, prompt, expect_json=True)

        if isinstance(result, dict) and "error" not in result:
            # Convert index lists to actual finding objects
            domain_findings = {}
            for domain in VALID_DOMAINS:
                indices = result.get(domain, [])
                domain_findings[domain] = [
                    findings[i] for i in indices
                    if isinstance(i, int) and i < len(findings)
                ]
            return domain_findings

        # Fallback: put everything in "social"
        return {d: [] for d in VALID_DOMAINS} | {"social": findings}

    def _identify_gaps(self, classified: dict) -> list:
        # A gap = domain with zero findings
        return [domain for domain, items in classified.items() if len(items) == 0]

    def _generate_follow_up_queries(self, gaps: list, original_query: str) -> list:
        prompt = f"""
ROLE: You are a research gap analyst.

CONTEXT:
- Research topic: {original_query}
- Domains with insufficient coverage (< 2 findings): {gaps}

TASK:
Generate targeted search queries to fill the gaps in these specific domains.

OUTPUT FORMAT:
Return ONLY valid JSON array. No markdown. No explanation.
[
  {{
    "query": "specific search query to fill the gap",
    "target_domain": "the domain this query addresses"
  }}
]

RULES:
- Generate exactly 1 query per gap domain
- Queries must be specific to both the topic AND the domain
- Make queries web-search-friendly (concise, keyword-rich)
"""
        result = call_groq(self.model, prompt, expect_json=True)

        if isinstance(result, list):
            return [item.get("query", "") for item in result if "query" in item]
        return []

    def _validate_input(self, data: dict):
        required = ["session_id", "findings", "original_query"]
        for field in required:
            if field not in data:
                raise ValueError(f"[Classifier] Missing required field: {field}")