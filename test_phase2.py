# test_phase2.py
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from core.state import ARIAState
from core.memory import init_db, create_session
from agents.researcher import ResearcherAgent
from agents.classifier import ClassifierAgent
from agents.analyst import AnalystAgent
from agents.writer import WriterAgent

print("=" * 60)
print("ARIA Phase 2 — Pipeline Test")
print("Researcher → Classifier → Analyst → Writer")
print("=" * 60)

# Setup
init_db()
state = ARIAState(query="Impact of artificial intelligence on employment")
create_session(state.session_id, state.query)
print(f"\nSession: {state.session_id}")
print(f"Query: {state.query}\n")

# --- Agent 2: Researcher ---
print("[STEP 1/4] Running Researcher Agent...")
researcher = ResearcherAgent()
research_output = researcher.run({
    "session_id": state.session_id,
    "queries": [
        "AI automation impact on jobs and employment 2024",
        "economic effects of artificial intelligence on labor market",
        "new jobs created by AI technology industries"
    ],
    "original_query": state.query
})
state.store_output("researcher", research_output)
print(f"  → Findings: {len(research_output.get('findings', []))}")
print(f"  → High quality: {research_output.get('high_quality_count', 0)}")

# --- Agent 3: Classifier ---
print("\n[STEP 2/4] Running Classifier Agent...")
classifier = ClassifierAgent()
classifier_output = classifier.run({
    "session_id": state.session_id,
    "findings": research_output.get("findings", []),
    "original_query": state.query,
    "loop_count": 0
})
state.store_output("classifier", classifier_output)

# If classifier found gaps, run researcher again with follow-ups
if classifier_output.get("follow_ups") and classifier_output["loop_count"] < 2:
    print(f"  → Running follow-up research for gaps: {classifier_output['gaps'][:3]}")
    follow_up_output = researcher.run({
        "session_id": state.session_id,
        "queries": classifier_output["follow_ups"][:3],
        "original_query": state.query
    })
    # Merge findings
    all_findings = research_output["findings"] + follow_up_output["findings"]
    # Re-classify with merged findings
    classifier_output = classifier.run({
        "session_id": state.session_id,
        "findings": all_findings,
        "original_query": state.query,
        "loop_count": 1
    })
    state.store_output("classifier", classifier_output)
else:
    all_findings = research_output["findings"]

domains_with_data = {k: v for k, v in classifier_output["domains"].items() if v}
print(f"  → Domains covered: {list(domains_with_data.keys())}")
print(f"  → Gaps: {classifier_output.get('gaps', [])}")

# --- Agent 4: Analyst ---
print("\n[STEP 3/4] Running Analyst Agent...")
analyst = AnalystAgent()
analyst_output = analyst.run({
    "session_id": state.session_id,
    "domains": classifier_output["domains"],
    "original_query": state.query
})
state.store_output("analyst", analyst_output)
print(f"  → Insights: {analyst_output.get('insight_count', 0)}")
print(f"  → Relationships: {len(analyst_output.get('relationships', []))}")
print(f"  → Pipeline confidence: {analyst_output.get('confidence', 0):.2f}")

# --- Agent 8: Writer ---
print("\n[STEP 4/4] Running Writer Agent...")
writer = WriterAgent()
writer_output = writer.run({
    "session_id": state.session_id,
    "original_query": state.query,
    "insights": analyst_output.get("insights", []),
    "relationships": analyst_output.get("relationships", []),
    "findings": all_findings,
    "domains": classifier_output["domains"],
    "confidence": analyst_output.get("confidence", 0.0)
})
state.store_output("writer", writer_output)
state.update_status("done")

# --- Print Results ---
print("\n" + "=" * 60)
print("PIPELINE COMPLETE")
print("=" * 60)

print("\n--- EXECUTIVE REPORT (preview) ---")
executive = writer_output.get("executive", "")
print(executive[:500] + "..." if len(executive) > 500 else executive)

print("\n--- STANDARD REPORT (first 300 chars) ---")
standard = writer_output.get("standard", "")
print(standard[:300] + "...")

print(f"\n--- CITATIONS: {len(writer_output.get('citations', []))} sources ---")

print("\n✓ All agents completed successfully")
print(f"✓ Report saved to database for session: {state.session_id}")
print("\nReady for Phase 3 — Intelligence Layer (Devil, Synthesizer, Visualizer, Orchestrator)")