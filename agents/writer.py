# agents/writer.py
import asyncio
import time
from core.groq_client import build_model, call_groq
from core.memory import log_agent_call, save_report


class WriterAgent:
    def __init__(self):
        self.model = build_model(temperature=0.3, smart=True)
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
        insights    = input_data.get("insights", [])
        relationships = input_data.get("relationships", [])
        implications  = input_data.get("implications", [])
        connections   = input_data.get("connections", [])
        critiques     = input_data.get("critiques", [])
        headline      = input_data.get("headline", "")
        narrative     = input_data.get("narrative", "")

        ctx = ""

        if headline:
            ctx += f"HEADLINE FINDING:\n  {headline}\n\n"
        if narrative:
            ctx += f"CORE NARRATIVE:\n  {narrative}\n\n"

        if insights:
            ctx += "KEY INSIGHTS:\n"
            for ins in insights:
                tag    = ins.get("tag", "supporting")
                claim  = ins.get("claim", "")
                domain = ins.get("domain", "")
                conf   = ins.get("confidence", "")
                ctx += f"  [{tag.upper()} | {domain}] {claim}"
                if conf:
                    ctx += f"  (confidence: {conf})"
                ctx += "\n"
            ctx += "\n"

        if relationships:
            ctx += "RELATIONSHIPS & MECHANISMS:\n"
            for rel in relationships[:10]:
                ctx += f"  • {rel.get('description', '')}\n"
            ctx += "\n"

        if connections:
            ctx += "CROSS-DOMAIN CONNECTIONS:\n"
            for c in connections[:8]:
                ctx += f"  • {c.get('description', c) if isinstance(c, dict) else c}\n"
            ctx += "\n"

        if implications:
            ctx += "IMPLICATIONS:\n"
            for imp in implications[:8]:
                ctx += f"  • {imp.get('description', imp) if isinstance(imp, dict) else imp}\n"
            ctx += "\n"

        if critiques:
            ctx += "DEVIL'S ADVOCATE CRITIQUES (address these):\n"
            for crit in critiques[:5]:
                ctx += f"  ⚠ {crit.get('critique', crit) if isinstance(crit, dict) else crit}\n"
            ctx += "\n"

        return ctx

    def _write_executive(self, input_data: dict) -> str:
        from core.groq_client import stream_groq
        context = self._build_context(input_data)
        callback = input_data.get("_on_executive_token")
        prompt = f"""
ROLE: You are a senior intelligence analyst writing a classified executive briefing
for senior decision-makers who need depth, not just a summary.

RESEARCH QUESTION: {input_data['original_query']}

INTELLIGENCE CONTEXT:
{context}

TASK:
Write a comprehensive executive intelligence briefing of 700-900 words.

Structure it as follows:
1. **SITUATION ASSESSMENT** (~150 words)
   Open with the single most critical finding. State the stakes clearly.

2. **KEY INTELLIGENCE FINDINGS** (~250 words)
   3-4 substantive paragraphs covering the most important insights.
   Each paragraph should make a distinct, evidence-grounded point.

3. **RISK FACTORS & COUNTERVAILING FORCES** (~150 words)
   Address the critiques and weaknesses honestly. What could be wrong?
   What are the key uncertainties?

4. **STRATEGIC IMPLICATIONS** (~200 words)
   What does this mean for decision-makers? 3-4 concrete implications.
   Be specific — avoid generic platitudes.

5. **BOTTOM LINE** (~100 words)
   One tight paragraph. The most important thing to understand and act on.

OUTPUT FORMAT:
Return ONLY the report text with markdown headers (## for section names).
No JSON. No preamble. Start directly with ## SITUATION ASSESSMENT.

RULES:
- Authoritative, precise intelligence-analyst tone
- Every claim grounded in the research context provided
- Specific over generic — name domains, mechanisms, actors where relevant
- Bold key terms and critical findings with **asterisks**
- No filler phrases ("it is important to note", "in conclusion", etc.)
"""
        if callback:
            return stream_groq(self.model, prompt, callback=callback)
        return call_groq(self.model, prompt, expect_json=False)

    def _write_standard(self, input_data: dict) -> str:
        context  = self._build_context(input_data)
        domains  = input_data.get("domains", {})
        findings = input_data.get("findings", [])

        domain_list = [d for d, items in domains.items() if items]
        domain_coverage = ", ".join(domain_list) if domain_list else "multiple domains"

        finding_highlights = ""
        high_conf = [f for f in findings if f.get("confidence_score", 0) >= 0.7][:12]
        for i, f in enumerate(high_conf):
            finding_highlights += f"  [{i+1}] {f.get('content', '')[:200]}\n"

        prompt = f"""
ROLE: You are a professional research analyst producing a comprehensive intelligence
report for an expert audience. This is a FULL, DETAILED, LONG-FORM report — not a summary.

RESEARCH QUESTION: {input_data['original_query']}
DOMAINS COVERED: {domain_coverage}
TOTAL FINDINGS PROCESSED: {len(findings)}

INTELLIGENCE CONTEXT:
{context}

HIGH-CONFIDENCE SOURCE FINDINGS:
{finding_highlights}

TASK:
Write a complete, deeply analytical research report of 3500-4500 words.
This must be a thorough, publication-quality document — not a brief overview.

Structure it with these sections:

## 1. Executive Overview (200-250 words)
High-level summary of the most critical findings and their significance.

## 2. Background & Context (350-400 words)
Historical context, why this question matters now, the landscape before
this research was conducted. Set the stage for the analysis.

## 3. Methodology & Data Sources (150-200 words)
How the research was conducted: multi-domain intelligence gathering,
number of findings, confidence scoring, cross-domain synthesis.

## 4. Domain-by-Domain Analysis (1200-1500 words)
A dedicated subsection for EACH domain covered (use ### for subsections).
Each subsection: 200-300 words minimum. Cover the key findings,
mechanisms, actors, and dynamics within that domain specifically.

## 5. Cross-Domain Synthesis (400-500 words)
How the domains interact and reinforce each other. The emergent patterns
that only become visible when you look across all domains simultaneously.
What connections were unexpected or counterintuitive?

## 6. Contested Claims & Uncertainty Analysis (300-350 words)
Where is the evidence weak? What do critics argue? What are the key
unknowns and uncertainties? Be intellectually honest about limitations.

## 7. Forward Implications & Strategic Outlook (400-450 words)
What happens next? What are the 2nd and 3rd-order effects? What should
different stakeholders (policymakers, businesses, researchers) do?
Include specific, concrete recommendations — not generic advice.

## 8. Conclusion (200-250 words)
Synthesise the single most important insight. What does this research
tell us that we didn't know before? What remains unknown?

OUTPUT FORMAT:
Return ONLY the report text with markdown headers.
Use ## for main sections, ### for subsections.
Use **bold** for key terms, findings, and critical points.
Use bullet points within sections where listing aids clarity.
No JSON wrapper. Start directly with ## 1. Executive Overview.

RULES:
- MINIMUM 3500 words — this is a detailed professional report, not a brief
- Each section must substantively address the research question
- Cite specific insights and findings from the context provided
- Analytical, evidence-grounded, expert tone throughout
- No padding or filler — every sentence must add information
- Specific names, mechanisms, data points where available
"""
        return call_groq(self.model, prompt, expect_json=False)

    def _write_technical(self, input_data: dict) -> str:
        findings = input_data.get("findings", [])
        insights = input_data.get("insights", [])
        critiques = input_data.get("critiques", [])
        connections = input_data.get("connections", [])

        findings_text = ""
        for i, f in enumerate(findings[:30]):
            findings_text += f"""
[F{str(i+1).zfill(2)}] confidence={f.get('confidence_score', 'N/A')} | domain={f.get('domain', 'N/A')}
     {f.get('content', '')[:400]}
     source: {f.get('source_url', 'N/A')}
"""

        insights_text = ""
        for ins in insights:
            insights_text += (
                f"  [{ins.get('tag','').upper()}] {ins.get('claim','')}\n"
                f"    confidence={ins.get('confidence','N/A')} | domain={ins.get('domain','N/A')}\n\n"
            )

        critiques_text = ""
        for c in critiques:
            if isinstance(c, dict):
                critiques_text += f"  ⚠ {c.get('critique', '')}\n    weak_score={c.get('confidence_impact', 'N/A')}\n\n"
            else:
                critiques_text += f"  ⚠ {c}\n\n"

        connections_text = ""
        for c in connections:
            desc = c.get('description', c) if isinstance(c, dict) else c
            connections_text += f"  ↔ {desc}\n"

        return f"""# ARIA Technical Appendix
## Research Query
{input_data['original_query']}

## Pipeline Metadata
- System: ARIA Autonomous Research & Intelligence Architecture v2.1
- Pipeline: Researcher → Classifier → Analyst → Devil's Advocate → Synthesizer → Structurer → Writer
- Total findings processed: {len(findings)}
- High-confidence findings (≥0.7): {len([f for f in findings if f.get('confidence_score',0) >= 0.7])}
- Insights extracted: {len(insights)}
- Pipeline confidence score: {input_data.get('confidence', 'N/A')}
- Headline: {input_data.get('headline', 'N/A')}

## Cross-Domain Connections ({len(connections)} identified)
{connections_text if connections_text else '  None recorded.'}

## Devil\'s Advocate Critiques ({len(critiques)} identified)
{critiques_text if critiques_text else '  No significant weaknesses flagged.'}

## Full Insight Inventory ({len(insights)} insights)
{insights_text if insights_text else '  No insights recorded.'}

## Raw Findings (top 30 by confidence)
{findings_text if findings_text else '  No findings recorded.'}
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
