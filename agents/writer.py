# agents/writer.py
import asyncio
import time
from core.groq_client import build_model, call_groq
from core.memory import log_agent_call, save_report


class WriterAgent:
    def __init__(self):
        # temperature=0.7 for creative, publication-quality writing
        self.model = build_model(temperature=0.2, smart=True)
        self.agent_name = "writer"

    def run(self, input_data: dict) -> dict:
        self._validate_input(input_data)
        session_id = input_data["session_id"]

        start = time.time()
        print("[Writer] Generating all 3 report formats in parallel...")

        async def _gather():
            return await asyncio.gather(
                asyncio.to_thread(self._write_executive, input_data),
                asyncio.to_thread(self._write_standard, input_data),
                asyncio.to_thread(self._write_technical, input_data),
            )

        executive, standard, technical = asyncio.run(_gather())

        citations = self._compile_citations(input_data.get("findings", []))

        output = {
            "executive": executive,
            "standard": standard,
            "technical": technical,
            "citations": citations,
            "status": "success"
        }

        save_report(session_id, executive, standard, technical, citations)
        duration_ms = int((time.time() - start) * 1000)
        log_agent_call(session_id, self.agent_name, input_data, output, duration_ms)
        print(f"[Writer] Done in {duration_ms}ms. Report saved.")
        return output

    def _build_context(self, input_data: dict) -> str:
        insights = input_data.get("insights", [])
        relationships = input_data.get("relationships", [])

        context = "KEY INSIGHTS:\n"
        for ins in insights:
            tag = ins.get("tag", "supporting")
            claim = ins.get("claim", "")
            domain = ins.get("domain", "")
            context += f"  [{tag.upper()} | {domain}] {claim}\n"

        if relationships:
            context += "\nKEY RELATIONSHIPS:\n"
            for rel in relationships[:5]:
                context += f"  {rel.get('description', '')}\n"

        return context

    def _write_executive(self, input_data: dict) -> str:
        context = self._build_context(input_data)
        prompt = f"""
ROLE: You are a senior analyst writing for C-suite executives who have
30 seconds to understand a complex topic.

CONTEXT:
- Research question: {input_data['original_query']}
{context}

TASK:
Write an executive summary. It must be:
- 300-400 words exactly
- Zero jargon — plain business language
- Start with the single most important finding
- Include 2-3 actionable implications
- End with a "bottom line" sentence

OUTPUT FORMAT:
Return ONLY the report text. No JSON. No headers. Just the prose.

RULES:
- No bullet points — flowing paragraphs only
- Every claim must be grounded in the research context provided
- Confident, authoritative tone
"""
        return call_groq(self.model, prompt, expect_json=False)

    def _write_standard(self, input_data: dict) -> str:
        context = self._build_context(input_data)
        domains = input_data.get("domains", {})

        domain_coverage = ", ".join([
            d for d, items in domains.items() if items
        ])

        prompt = f"""
ROLE: You are a professional research analyst writing a structured report
for an informed, educated audience.

CONTEXT:
- Research question: {input_data['original_query']}
- Domains covered: {domain_coverage}
{context}

TASK:
Write a complete, structured research report of 1500-2000 words.

Structure it with these sections:
1. Executive Overview (150 words)
2. Background & Context (250 words)
3. Key Findings by Domain (600-700 words — cover each relevant domain)
4. Cross-Domain Analysis (300 words — connections between domains)
5. Implications & Outlook (200 words)
6. Conclusion (150 words)

OUTPUT FORMAT:
Return ONLY the report text with markdown headers (## for sections).
No JSON wrapper.

RULES:
- Use ## for section headers
- Use **bold** for key terms on first use
- Cite claims with [Source] placeholders where appropriate
- Maintain analytical, objective tone throughout
- Every section must directly address the research question
"""
        return call_groq(self.model, prompt, expect_json=False)

    def _write_technical(self, input_data: dict) -> str:
        findings = input_data.get("findings", [])
        insights = input_data.get("insights", [])

        findings_text = ""
        for i, f in enumerate(findings[:20]):  # cap at 20
            findings_text += f"""
[F{i+1}] Confidence: {f.get('confidence_score', 'N/A')}
  Content: {f.get('content', '')[:300]}
  Source: {f.get('source_url', 'N/A')}
  Date: {f.get('date', 'N/A')}
"""

        insights_text = ""
        for ins in insights:
            insights_text += f"""
  - [{ins.get('tag', '').upper()}] {ins.get('claim', '')}
    Confidence: {ins.get('confidence', 'N/A')} | Domain: {ins.get('domain', 'N/A')}
"""

        return f"""# ARIA Technical Appendix
## Research Query
{input_data['original_query']}

## Methodology
- System: ARIA Autonomous Research & Intelligence Architecture
- Pipeline: Researcher → Classifier → Analyst → Writer
- Total findings processed: {len(findings)}
- Insights extracted: {len(insights)}

## Raw Findings
{findings_text}

## Insight Inventory
{insights_text}

## Pipeline Confidence Score
Analyst confidence: {input_data.get('confidence', 'N/A')}
"""

    def _compile_citations(self, findings: list) -> list:
        citations = []
        seen = set()
        for f in findings:
            url = f.get("source_url", "")
            if url and url not in seen and url != "web_search":
                seen.add(url)
                citations.append({
                    "url": url,
                    "date": f.get("date", "N/A"),
                    "confidence": f.get("confidence_score", 0.0)
                })
        return citations

    def _validate_input(self, data: dict):
        required = ["session_id", "original_query", "insights"]
        for field in required:
            if field not in data:
                raise ValueError(f"[Writer] Missing required field: {field}")