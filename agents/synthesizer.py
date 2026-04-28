# agents/synthesizer.py
import time
from core.groq_client import build_model, call_groq
from core.memory import log_agent_call


class SynthesizerAgent:
    def __init__(self):
        self.model = build_model(temperature=0.2, smart=True)
        self.agent_name = "synthesizer"

    def run(self, input_data: dict) -> dict:
        """
        input_data = {
            "session_id": str,
            "insights": [...],              # from Analyst (possibly revised)
            "relationships": [...],         # from Analyst
            "critiques": [...],             # from Devil
            "missing_perspectives": [...],  # from Devil
            "original_query": str
        }
        """
        self._validate_input(input_data)
        session_id = input_data["session_id"]
        original_query = input_data["original_query"]

        start = time.time()

        connections = self._find_cross_domain_connections(input_data)
        implications = self._generate_implications(input_data)
        headline = self._find_headline_insight(input_data)
        narrative = self._build_narrative_arc(input_data, headline)

        output = {
            "connections": connections,
            "implications": implications,
            "headline": headline,
            "narrative": narrative,
            "connection_count": len(connections),
            "status": "success"
        }

        duration_ms = int((time.time() - start) * 1000)
        log_agent_call(session_id, self.agent_name, input_data, output, duration_ms)
        print(f"[Synthesizer] Done. {len(connections)} connections, "
              f"{len(implications)} implications.")
        print(f"[Synthesizer] Headline: {headline[:80]}...")
        return output

    def _build_context_summary(self, input_data: dict) -> str:
        insights = input_data.get("insights", [])
        critiques = input_data.get("critiques", [])

        # Build a map of claim strength from devil's output
        strength_map = {}
        for c in critiques:
            strength_map[c.get("insight_id", "")] = c.get("claim_strength", "moderate")

        summary = "INSIGHTS (with critique strength):\n"
        for ins in insights:
            strength = strength_map.get(ins.get("id", ""), "moderate")
            summary += (f"  [{ins.get('domain', '?')} | {strength}] "
                        f"{ins.get('claim', '')}\n")

        relationships = input_data.get("relationships", [])
        if relationships:
            summary += "\nESTABLISHED RELATIONSHIPS:\n"
            for rel in relationships[:6]:
                summary += f"  {rel.get('description', '')}\n"

        return summary

    def _find_cross_domain_connections(self, input_data: dict) -> list:
        context = self._build_context_summary(input_data)

        prompt = f"""
ROLE: You are a synthesis expert who finds non-obvious, cross-domain connections
that individual domain experts would miss. You excel at seeing the bigger picture.

CONTEXT:
- Research question: {input_data['original_query']}
{context}

TASK:
Find 3-5 connections that cross DIFFERENT domains (e.g., economic insight
connecting to social insight). These should be genuinely non-obvious — not just
restating what's already in the relationships list.

OUTPUT FORMAT:
Return ONLY valid JSON array. No markdown. No explanation.
[
  {{
    "domain_a": "first domain",
    "insight_a": "the insight from domain A",
    "domain_b": "second domain",
    "insight_b": "the insight from domain B",
    "connection": "The non-obvious link between them (2-3 sentences)",
    "novelty": "low/medium/high",
    "implication": "What this connection means for the research question"
  }}
]

RULES:
- Must connect insights from DIFFERENT domains
- novelty=high means this connection is genuinely surprising
- Each connection must add new understanding, not just repeat known links
- Minimum 3 connections, maximum 5
"""
        result = call_groq(self.model, prompt, expect_json=True)
        if isinstance(result, list):
            return result
        return []

    def _generate_implications(self, input_data: dict) -> list:
        context = self._build_context_summary(input_data)
        missing = input_data.get("missing_perspectives", [])
        missing_text = "\n".join([
            f"  - {m.get('missing_perspective', '')}: {m.get('why_important', '')}"
            for m in missing
        ])

        prompt = f"""
ROLE: You are a strategic foresight analyst answering the "so what?" question
for decision-makers, researchers, and policymakers.

CONTEXT:
- Research question: {input_data['original_query']}
{context}
- Known gaps in research: {missing_text if missing_text else "None identified"}

TASK:
Generate 3-5 key implications — what does all this research actually MEAN?
What should someone DO or THINK DIFFERENTLY as a result of this research?

OUTPUT FORMAT:
Return ONLY valid JSON array. No markdown. No explanation.
[
  {{
    "implication": "The key implication statement (1-2 sentences, specific and actionable)",
    "audience": "Who this most affects: policymakers/businesses/workers/researchers/society",
    "urgency": "immediate/near_term/long_term",
    "confidence": 0.0
  }}
]

RULES:
- confidence between 0.0 and 1.0 based on how well evidence supports this implication
- Be specific — avoid vague statements like 'more research is needed'
- Each implication must be distinct and non-overlapping
- Acknowledge uncertainty where it exists
"""
        result = call_groq(self.model, prompt, expect_json=True)
        if isinstance(result, list):
            return result
        return []

    def _find_headline_insight(self, input_data: dict) -> str:
        insights = input_data.get("insights", [])
        critiques = input_data.get("critiques", [])

        strong_insights = []
        strong_ids = {c.get("insight_id") for c in critiques
                      if c.get("claim_strength") == "strong"}

        for ins in insights:
            if ins.get("id") in strong_ids or ins.get("tag") == "core":
                strong_insights.append(ins.get("claim", ""))

        if not strong_insights:
            strong_insights = [i.get("claim", "") for i in insights[:3]]

        prompt = f"""
ROLE: You are a headline writer for a top-tier research journal.

CONTEXT:
- Research question: {input_data['original_query']}
- Strongest findings:
{chr(10).join(f'  - {s}' for s in strong_insights)}

TASK:
Write the single most important insight from this research as one crisp,
declarative sentence. This is the headline finding — the one thing a reader
must remember. It should be specific, surprising if possible, and falsifiable.

OUTPUT FORMAT:
Return ONLY the headline sentence. No JSON. No explanation. No quotes.
Just the sentence itself.

RULES:
- Maximum 25 words
- Must be a complete declarative statement
- Must be grounded in the actual research findings
- Avoid hedging words like "may", "might", "could" — be bold but accurate
"""
        result = call_groq(self.model, prompt, expect_json=False)
        return result.strip() if isinstance(result, str) else "Headline generation failed."

    def _build_narrative_arc(self, input_data: dict, headline: str) -> str:
        connections = self._find_cross_domain_connections.__doc__  # just for reference
        implications_preview = input_data.get("original_query", "")

        prompt = f"""
ROLE: You are a narrative strategist who connects complex research into a
coherent story that a general audience can follow.

CONTEXT:
- Research question: {input_data['original_query']}
- Headline finding: {headline}
- Domains covered: {list(set(i.get('domain','') for i in input_data.get('insights',[])))}

TASK:
Write a narrative arc — a 150-200 word connecting story that ties all domains
together into a coherent explanation. This is NOT a summary. It is a logical
progression: setup → tension → resolution → implication.

OUTPUT FORMAT:
Return ONLY the narrative text. No JSON. No headers. Just flowing prose.

RULES:
- Start with the most provocative or surprising aspect of the research
- Build tension by showing competing forces or contradictions
- Resolve by showing what the synthesis reveals
- End with the "so what" — why this matters
- Write for an intelligent non-specialist audience
"""
        result = call_groq(self.model, prompt, expect_json=False)
        return result.strip() if isinstance(result, str) else ""

    def _validate_input(self, data: dict):
        required = ["session_id", "insights", "original_query"]
        for field in required:
            if field not in data:
                raise ValueError(f"[Synthesizer] Missing required field: {field}")