# core/state.py
from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass
class ARIAState:
    query: str
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    plan: dict = field(default_factory=dict)
    agent_outputs: dict = field(default_factory=lambda: {
        "researcher": {},
        "classifier": {},
        "analyst": {},
        "devil": {},
        "synthesizer": {},
        "visualizer": {},
        "writer": {}
    })
    loop_counts: dict = field(default_factory=lambda: {
        "classifier": 0,
        "devil": 0
    })
    status: str = "idle"   # idle/planning/researching/analyzing/critiquing/synthesizing/writing/done
    errors: list = field(default_factory=list)

    def update_status(self, new_status: str):
        self.status = new_status
        print(f"[ARIA] Status → {new_status}")

    def store_output(self, agent_name: str, output: dict):
        self.agent_outputs[agent_name] = output

    def log_error(self, agent_name: str, error: str):
        self.errors.append({"agent": agent_name, "error": error})
        print(f"[ERROR] {agent_name}: {error}")

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "session_id": self.session_id,
            "plan": self.plan,
            "agent_outputs": self.agent_outputs,
            "loop_counts": self.loop_counts,
            "status": self.status,
            "errors": self.errors
        }