# agents/analyst.py
import time
from core.groq_client import build_model, call_groq
from core.memory import log_agent_call


class AnalystAgent:
    def __init__(self):
        self.model       = build_model(temperature=0.2, smart=False)
        self.model_fast  = build_model(temperature=0.2, smart=False)
        self.agent_name = "analyst"

    def run(self, input_data: dict) -> dict:
        """
        input_data = {
            "session_id": str,
            "domains": {domain: [findings]},   # from Classifier
            "original_query": str
        }
        """
        self._validate_input(input_data)
        session_id = input_data["session_id"]
        domains = input_data["domains"]
        original_query = input_data["original_query"]

        start = time.time()

        insights = self._extract_insights(domains, original_query)
        relationships = self._find_relationships(insights, original_query)
        confidence = self._score_confidence(insights, relationships)

        output = {
            "insights": insights,
            "relationships": relationships,
            "confidence": confidence,
            "insight_count": len(insights),
            "status": "success"
        }

        duration_ms = int((time.time() - start) * 1000)
        log_agent_call(session_id, self.agent_name, input_data, output, duration_ms)
        print(f"[Analyst] Done. {len(insights)} insights, confidence: {confidence:.2f}")
        return output

    def _extract_insights(self, domains: dict, original_query: str) -> list:
        # Build a compact summary of all findings
        domain_summary = ""
        for domain, findings in domains.items():
            if findings:
                domain_summary += f"\n\n[{domain.upper()}]\n"
                for f in findings[:3]:  # cap at 3 per domain to stay within token limits
                    domain_summary += f"- {f.get('content', '')[:200]}\n"

        prompt = f"""
ROLE: You are a senior intelligence analyst specializing in pattern recognition
and insight extraction from multi-domain research data.

CONTEXT:
- Research question: {original_query}
- Research findings by domain:
{domain_summary}

TASK:
Extract the most important insights from this research. Go beyond summarizing —
identify what the data actually means, what patterns exist, and what is significant.

OUTPUT FORMAT:
Return ONLY valid JSON. No markdown. No explanation.
{{
  "insights": [
    {{
      "id": "insight_1",
      "domain": "the primary domain",
      "claim": "The core insight statement (1-2 sentences, precise)",
      "evidence": "What specific findings support this",
      "tag": "core",
      "confidence": 0.0
    }}
  ]
}}

RULES:
- tag must be one of: core / supporting / peripheral
- core insights = most important to answering the research question
- confidence between 0.0 and 1.0 based on evidence strength
- Generate 5-10 insights total
- Each insight must be a distinct, non-overlapping claim
- Write claims as declarative statements of fact or finding
"""
        result = call_groq(self.model, prompt, expect_json=True)
        if isinstance(result, dict) and "insights" in result:
            return result["insights"]

        # Smart model failed — retry with fast model
        print("[Analyst] Smart model extraction failed, retrying with fast model...")
        result = call_groq(self.model_fast, prompt, expect_json=True)
        if isinstance(result, dict) and "insights" in result:
            return result["insights"]
        return []

    def _find_relationships(self, insights: list, original_query: str) -> list:
        if len(insights) < 2:
            return []

        insights_text = ""
        for ins in insights:
            insights_text += f"\n- [{ins.get('id')}] {ins.get('claim', '')}"

        prompt = f"""
ROLE: You are an expert at finding non-obvious connections between ideas
across different domains of knowledge.

CONTEXT:
- Research question: {original_query}
- Insights identified:
{insights_text}

TASK:
Identify meaningful relationships between these insights.
Look for: causation, correlation, contradiction, reinforcement, trade-offs.

OUTPUT FORMAT:
Return ONLY valid JSON array. No markdown. No explanation.
[
  {{
    "insight_a": "insight_id",
    "insight_b": "insight_id",
    "relationship_type": "one of: causal/correlational/contradictory/reinforcing/tradeoff",
    "description": "Explain the relationship in 1 sentence",
    "strength": 0.0
  }}
]

RULES:
- strength between 0.0 (weak) and 1.0 (strong)
- Only include relationships with strength > 0.4
- Maximum 8 relationships
- Never repeat the same pair
"""
        result = call_groq(self.model_fast, prompt, expect_json=True)

        if isinstance(result, list):
            return result
        return []

    def _score_confidence(self, insights: list, relationships: list) -> float:
        if not insights:
            return 0.0
        avg_confidence = sum(i.get("confidence", 0.5) for i in insights) / len(insights)
        relationship_bonus = min(len(relationships) * 0.02, 0.1)
        return round(min(avg_confidence + relationship_bonus, 1.0), 3)

    def _validate_input(self, data: dict):
        required = ["session_id", "domains", "original_query"]
        for field in required:
            if field not in data:
                raise ValueError(f"[Analyst] Missing required field: {field}")