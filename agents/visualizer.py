# agents/visualizer.py
import time
from core.groq_client import build_model, call_groq
from core.memory import log_agent_call


class VisualizerAgent:
    def __init__(self):
        self.model = build_model(temperature=0.2, smart=False)
        self.agent_name = "visualizer"

    def run(self, input_data: dict) -> dict:
        """
        input_data = {
            "session_id": str,
            "headline": str,            # from Synthesizer
            "narrative": str,           # from Synthesizer
            "implications": [...],      # from Synthesizer
            "connections": [...],       # from Synthesizer
            "insights": [...],          # from Analyst
            "original_query": str
        }
        """
        self._validate_input(input_data)
        session_id = input_data["session_id"]

        start = time.time()

        sections = self._plan_sections(input_data)
        tables = self._generate_table_specs(input_data)
        executive_summary = self._write_executive_summary(input_data)

        output = {
            "sections": sections,
            "tables": tables,
            "executive_summary": executive_summary,
            "section_count": len(sections),
            "status": "success"
        }

        duration_ms = int((time.time() - start) * 1000)
        log_agent_call(session_id, self.agent_name, input_data, output, duration_ms)
        print(f"[Visualizer] Done. {len(sections)} sections planned, "
              f"{len(tables)} tables designed.")
        return output

    def _plan_sections(self, input_data: dict) -> list:
        implications = input_data.get("implications", [])
        connections = input_data.get("connections", [])
        insights = input_data.get("insights", [])

        domains_covered = list(set(
            i.get("domain", "") for i in insights if i.get("domain")
        ))

        prompt = f"""
ROLE: You are a research publication architect who designs the optimal
structure for complex, multi-domain research reports.

CONTEXT:
- Research question: {input_data['original_query']}
- Headline: {input_data.get('headline', '')}
- Domains covered: {domains_covered}
- Number of implications: {len(implications)}
- Number of cross-domain connections: {len(connections)}

TASK:
Design the section structure for a comprehensive research report.
Each section should have a clear purpose and the right format for its content.

OUTPUT FORMAT:
Return ONLY valid JSON array. No markdown. No explanation.
[
  {{
    "title": "Section Title",
    "purpose": "What this section achieves",
    "format": "paragraph/table/timeline/comparison/bullet_list/mixed",
    "content_ref": "which agent output feeds this section: insights/connections/implications/findings/narrative",
    "word_target": 200,
    "order": 1
  }}
]

RULES:
- format must be one of: paragraph/table/timeline/comparison/bullet_list/mixed
- Design 6-8 sections total
- word_target must be between 100-500
- Order from 1 (first) to N (last)
- First section is always Executive Overview
- Last section is always Conclusion & Implications
"""
        result = call_groq(self.model, prompt, expect_json=True)
        if isinstance(result, list):
            return sorted(result, key=lambda x: x.get("order", 99))
        return []

    def _generate_table_specs(self, input_data: dict) -> list:
        connections = input_data.get("connections", [])
        implications = input_data.get("implications", [])

        if not connections and not implications:
            return []

        prompt = f"""
ROLE: You are a data visualization designer specializing in research tables
and comparison matrices.

CONTEXT:
- Cross-domain connections available: {len(connections)}
- Implications available: {len(implications)}
- Research question: {input_data['original_query']}

TASK:
Design 1-2 tables that would best communicate the research findings.
These specs will be used to generate actual HTML tables in the report.

OUTPUT FORMAT:
Return ONLY valid JSON array. No markdown. No explanation.
[
  {{
    "table_id": "table_1",
    "title": "Table title",
    "type": "comparison/summary/matrix/timeline",
    "columns": ["Column 1", "Column 2", "Column 3"],
    "description": "What this table shows and why it's useful",
    "data_source": "connections/implications/insights/findings"
  }}
]

RULES:
- Maximum 2 tables
- columns must have 2-5 entries
- Make tables that would genuinely help a reader understand the research
"""
        result = call_groq(self.model, prompt, expect_json=True)
        if isinstance(result, list):
            return result
        return []

    def _write_executive_summary(self, input_data: dict) -> str:
        headline = input_data.get("headline", "")
        implications = input_data.get("implications", [])
        narrative = input_data.get("narrative", "")

        top_implications = [
            i.get("implication", "") for i in implications[:3]
        ]

        prompt = f"""
ROLE: You are writing the executive summary for a high-stakes research brief.
It will be the first thing decision-makers read.

CONTEXT:
- Research question: {input_data['original_query']}
- Headline finding: {headline}
- Narrative context: {narrative[:400] if narrative else 'Not available'}
- Key implications:
{chr(10).join(f'  {i+1}. {imp}' for i, imp in enumerate(top_implications))}

TASK:
Write a 120-150 word executive summary. It must:
1. Open with the headline finding
2. Provide essential context (2-3 sentences)
3. State the 2-3 most important implications
4. Close with a call to awareness or action

OUTPUT FORMAT:
Return ONLY the executive summary text. No JSON. No labels. Just the prose.

RULES:
- Exactly 120-150 words
- Zero technical jargon
- Every sentence must earn its place
- Confident, direct tone
"""
        result = call_groq(self.model, prompt, expect_json=False)
        return result.strip() if isinstance(result, str) else ""

    def _validate_input(self, data: dict):
        required = ["session_id", "original_query"]
        for field in required:
            if field not in data:
                raise ValueError(f"[Visualizer] Missing required field: {field}")