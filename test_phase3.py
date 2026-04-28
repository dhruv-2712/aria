# test_phase3.py — Full 8-agent pipeline test via Orchestrator
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from orchestrator import Orchestrator

print("=" * 60)
print("ARIA Phase 3 — Full Pipeline Test (All 8 Agents)")
print("=" * 60)

orchestrator = Orchestrator()
result = orchestrator.run("Impact of artificial intelligence on employment")

print("\n--- METADATA ---")
meta = result.get("metadata", {})
for k, v in meta.items():
    print(f"  {k}: {v}")

print("\n--- HEADLINE FINDING ---")
report = result.get("report", {})
# Headline comes through writer now via synthesizer
print(f"  Status: {result.get('status')}")
print(f"  Session: {result.get('session_id')}")

print("\n--- EXECUTIVE (preview) ---")
executive = report.get("executive", "")
print(executive[:600] + "..." if len(executive) > 600 else executive)

print(f"\n✓ Full pipeline complete. Citations: {len(report.get('citations', []))}")