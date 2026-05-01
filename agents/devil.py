# agents/devil.py
import time
from core.groq_client import build_model, call_groq
from core.memory import log_agent_call

MAX_REVISION_LOOPS = 2


class DevilsAdvocateAgent:
    def __init__(self):
        self.model = build_model(temperature=0.2, smart=False)
        self.agent_name = "devil"

    def run(self, input_data: dict) -> dict:
        """
        input_data = {
            "session_id": str,
            "insights": [...],        # from Analyst
            "relationships": [...],   # from Analyst
            "original_query": str,
            "revision_count": int
        }
        """
        self._validate_input(input_data)
        session_id = input_data["session_id"]
        insights = input_data["insights"]
        original_query = input_data["original_query"]
        revision_count = input_data.get("revision_count", 0)

        start = time.time()

        critiques = self._generate_critiques(insights, original_query)
        weak_claims = self._identify_weak_claims(critiques)
        missing_perspectives = self._find_missing_perspectives(insights, original_query)
        fallacies = self._detect_fallacies(insights, original_query)

        total_claims = len(insights)
        weak_ratio = len(weak_claims) / total_claims if total_claims > 0 else 0
        revision_needed = weak_ratio > 0.30 and revision_count < MAX_REVISION_LOOPS

        output = {
            "critiques": critiques,
            "weak_claims": weak_claims,
            "missing_perspectives": missing_perspectives,
            "fallacies": fallacies,
            "weak_ratio": round(weak_ratio, 3),
            "revision_needed": revision_needed,
            "revision_count": revision_count,
            "status": "success"
        }

        duration_ms = int((time.time() - start) * 1000)
        log_agent_call(session_id, self.agent_name, input_data, output, duration_ms)

        print(f"[Devil] Done. {len(critiques)} critiques, "
              f"{len(weak_claims)} weak claims ({weak_ratio:.0%}), "
              f"revision_needed={revision_needed}")
        return output

    def _generate_critiques(self, insights: list, original_query: str) -> list:
        insights_text = ""
        for ins in insights:
            insights_text += (f"\n[{ins.get('id', '?')}] "
                              f"({ins.get('tag', '?')} | {ins.get('domain', '?')}): "
                              f"{ins.get('claim', '')}")

        prompt = f"""
ROLE: You are a rigorous academic peer reviewer and devil's advocate.
Your job is to challenge every claim, find weaknesses, and strengthen the research.
You are not trying to destroy the research — you are making it bulletproof.

CONTEXT:
- Research question: {original_query}
- Claims to critique:
{insights_text}

TASK:
For EACH insight, generate at least one serious counterargument or challenge.
Rate the strength of the original claim after considering the counterargument.

OUTPUT FORMAT:
Return ONLY valid JSON. No markdown. No explanation.
{{
  "critiques": [
    {{
      "insight_id": "insight_1",
      "original_claim": "the claim being critiqued",
      "counterargument": "The strongest opposing argument or evidence (2-3 sentences)",
      "claim_strength": "strong",
      "weakness_type": "one of: evidence_gap/overgeneralization/false_causality/recency_bias/selection_bias/unverified/sound",
      "suggested_qualification": "How to make this claim more defensible"
    }}
  ]
}}

RULES:
- claim_strength must be: strong / moderate / weak / unverified
- Cover every insight — no skipping
- counterarguments must be substantive, not trivial
- suggested_qualification must be actionable
- Be harsh but fair — good claims should still get "strong"
"""
        result = call_groq(self.model, prompt, expect_json=True)
        if isinstance(result, dict) and "critiques" in result:
            return result["critiques"]
        return []

    def _identify_weak_claims(self, critiques: list) -> list:
        return [
            c for c in critiques
            if c.get("claim_strength") in ["weak", "unverified"]
        ]

    def _find_missing_perspectives(self, insights: list, original_query: str) -> list:
        covered_domains = list(set(i.get("domain", "") for i in insights))

        prompt = f"""
ROLE: You are a diversity-of-thought analyst ensuring research covers all
relevant stakeholder perspectives.

CONTEXT:
- Research question: {original_query}
- Domains currently covered: {covered_domains}
- Number of insights: {len(insights)}

TASK:
Identify important perspectives, stakeholder groups, or viewpoints that are
NOT represented in the current research but should be.

OUTPUT FORMAT:
Return ONLY valid JSON array. No markdown. No explanation.
[
  {{
    "missing_perspective": "Name of the missing viewpoint/group",
    "why_important": "Why this perspective matters for this research (1 sentence)",
    "example_question": "A specific question this perspective would raise"
  }}
]

RULES:
- Identify 2-4 missing perspectives maximum
- Be specific — not just 'developing countries' but 'informal economy workers in Southeast Asia'
- Focus on perspectives that would materially change conclusions if included
"""
        result = call_groq(self.model, prompt, expect_json=True)
        if isinstance(result, list):
            return result
        return []

    def _detect_fallacies(self, insights: list, original_query: str) -> list:
        claims_text = "\n".join([
            f"- {i.get('claim', '')}" for i in insights
        ])

        prompt = f"""
ROLE: You are a formal logic expert specializing in identifying reasoning errors.

CONTEXT:
- Research question: {original_query}
- Claims made:
{claims_text}

TASK:
Identify any logical fallacies present in these claims.

OUTPUT FORMAT:
Return ONLY valid JSON array. No markdown. No explanation.
[
  {{
    "claim": "the claim containing the fallacy",
    "fallacy_type": "hasty_generalization/false_causality/correlation_causation/
                     appeal_to_authority/false_dichotomy/slippery_slope/other",
    "explanation": "Why this is a fallacy in this context (1-2 sentences)"
  }}
]

RULES:
- Only flag genuine fallacies — do not invent problems
- Return empty array [] if no fallacies found
- Maximum 5 flagged fallacies
"""
        result = call_groq(self.model, prompt, expect_json=True)
        if isinstance(result, list):
            return result
        return []

    def _validate_input(self, data: dict):
        required = ["session_id", "insights", "original_query"]
        for field in required:
            if field not in data:
                raise ValueError(f"[Devil] Missing required field: {field}")