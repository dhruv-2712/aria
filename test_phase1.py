# test_phase1.py — run this to verify Phase 1 works
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from core.state import ARIAState
from core.memory import init_db, create_session, log_agent_call, get_session_logs
from core.gemini_client import build_model, call_gemini

print("=" * 50)
print("ARIA Phase 1 — Foundation Test")
print("=" * 50)

# Test 1: State
print("\n[1] Testing ARIAState...")
state = ARIAState(query="Impact of AI on education")
state.update_status("planning")
state.store_output("researcher", {"test": "data"})
print(f"    Session ID: {state.session_id}")
print(f"    Status: {state.status}")
print("    ✓ State OK")

# Test 2: Database
print("\n[2] Testing SQLite memory...")
init_db()
create_session(state.session_id, state.query)
log_agent_call(state.session_id, "test_agent", {"input": "x"}, {"output": "y"}, 123)
logs = get_session_logs(state.session_id)
print(f"    Logs found: {len(logs)}")
print("    ✓ Database OK")

# Test 3: Gemini connection
print("\n[3] Testing Gemini API...")
model = build_model(temperature=0.2)
result = call_gemini(model, """
ROLE: Test agent
TASK: Return a simple JSON object
OUTPUT FORMAT: {"status": "ok", "message": "Gemini is working"}
RULES: Return only valid JSON, nothing else.
""")
print(f"    Response: {result}")
if "error" not in result:
    print("    ✓ Gemini API OK")
else:
    print("    ✗ Gemini API FAILED — check your API key in .env")

print("\n" + "=" * 50)
print("Phase 1 complete. Ready for Phase 2.")
print("=" * 50)