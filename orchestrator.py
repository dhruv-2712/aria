# orchestrator.py
import time
from concurrent.futures import ThreadPoolExecutor
from core.state import ARIAState
from core.config import MAX_RESEARCH_LOOPS, MAX_CRITIQUE_LOOPS
from core.memory import init_db, create_session, update_session_status, log_agent_call, update_report_follow_ups
from core.dedup import deduplicate_findings
from agents.researcher import ResearcherAgent
from agents.classifier import ClassifierAgent
from agents.analyst import AnalystAgent
from agents.devil import DevilsAdvocateAgent
from agents.synthesizer import SynthesizerAgent
from agents.visualizer import VisualizerAgent
from agents.writer import WriterAgent

MAX_RETRIES = 3


class Orchestrator:
    def __init__(self):
        init_db()
        self.researcher = ResearcherAgent()
        self.classifier = ClassifierAgent()
        self.analyst = AnalystAgent()
        self.devil = DevilsAdvocateAgent()
        self.synthesizer = SynthesizerAgent()
        self.visualizer = VisualizerAgent()
        self.writer = WriterAgent()

    def run(self, query: str, on_status=None, on_executive_token=None, on_standard_token=None, on_session_id=None) -> dict:
        """
        Master entry point. Takes raw user query, runs all 8 agents,
        returns final report dict.
        """
        state = ARIAState(query=query)
        create_session(state.session_id, query)
        if on_session_id:
            on_session_id(state.session_id)

        # Wrap state.update_status so main.py gets live updates
        _orig_update = state.update_status
        def _update(status):
            _orig_update(status)
            if on_status:
                on_status(status)
        state.update_status = _update

        print(f"\n{'='*60}")
        print(f"ARIA — Starting Research Pipeline")
        print(f"Query: {query}")
        print(f"Session: {state.session_id}")
        print(f"{'='*60}\n")

        try:
            # === PHASE 1: RESEARCH ===
            state.update_status("researching")
            update_session_status(state.session_id, "researching")
            research_output = self._run_with_retry(
                "researcher",
                self.researcher,
                {
                    "session_id": state.session_id,
                    "queries": self._generate_search_queries(query),
                    "original_query": query
                },
                state
            )
            state.store_output("researcher", research_output)

            # === PHASE 2: CLASSIFY (instant — pass findings straight through) ===
            state.update_status("classifying")
            update_session_status(state.session_id, "classifying")
            all_findings = deduplicate_findings(research_output["findings"])

            # === PHASE 3: ANALYZE ===
            state.update_status("analyzing")
            update_session_status(state.session_id, "analyzing")
            analyst_output = self._run_with_retry(
                "analyst",
                self.analyst,
                {
                    "session_id":     state.session_id,
                    "findings":       all_findings,
                    "original_query": query
                },
                state
            )
            state.store_output("analyst", analyst_output)
            insights = analyst_output.get("insights", [])

            # === PHASE 4: CRITIQUE (instant — skipped for speed) ===
            state.update_status("critiquing")
            update_session_status(state.session_id, "critiquing")

            # === PHASE 5: SYNTHESIZE ===
            state.update_status("synthesizing")
            update_session_status(state.session_id, "synthesizing")
            synthesizer_output = self._run_with_retry(
                "synthesizer",
                self.synthesizer,
                {
                    "session_id":           state.session_id,
                    "insights":             insights,
                    "relationships":        analyst_output.get("relationships", []),
                    "critiques":            [],
                    "missing_perspectives": [],
                    "original_query":       query
                },
                state
            )
            state.store_output("synthesizer", synthesizer_output)

            # === PHASE 6: STRUCTURE (instant — skipped for speed) ===
            state.update_status("structuring")
            update_session_status(state.session_id, "structuring")

            # === PHASE 7: WRITE ===
            state.update_status("writing")
            update_session_status(state.session_id, "writing")

            writer_base_input = {
                "session_id":        state.session_id,
                "original_query":    query,
                "insights":          insights,
                "relationships":     analyst_output.get("relationships", []),
                "findings":          all_findings,
                "domains":           {},
                "confidence":        analyst_output.get("confidence", 0.0),
                "headline":          synthesizer_output.get("headline", ""),
                "narrative":         synthesizer_output.get("narrative", ""),
                "implications":      synthesizer_output.get("implications", []),
                "connections":       synthesizer_output.get("connections", []),
                "sections":          [],
                "executive_summary": "",
                "critiques":         [],
            }

            writer_output = self._run_with_retry(
                "writer",
                self.writer,
                {**writer_base_input,
                 "_on_executive_token": on_executive_token,
                 "_on_standard_token":  on_standard_token},
                state
            )
            state.store_output("writer", writer_output)

            state.update_status("done")
            update_session_status(state.session_id, "done")

            # === FOLLOW-UP SUGGESTIONS (non-blocking — status already "done") ===
            follow_ups = self._generate_follow_ups(query, synthesizer_output.get("headline", ""))
            if follow_ups:
                update_report_follow_ups(state.session_id, follow_ups)

            print(f"\n{'='*60}")
            print("ARIA — Pipeline Complete")
            print(f"{'='*60}")

            return {
                "session_id":   state.session_id,
                "status":       "done",
                "report":       writer_output,
                "follow_ups":   follow_ups,
                "writer_input": writer_base_input,
                "metadata": {
                    "total_findings": len(all_findings),
                    "insights_generated": len(insights),
                    "pipeline_confidence": analyst_output.get("confidence", 0.0),
                    "weak_claims_ratio": 0.0,
                    "cross_domain_connections": synthesizer_output.get("connection_count", 0)
                }
            }

        except Exception as e:
            state.log_error("orchestrator", str(e))
            state.update_status("failed")
            update_session_status(state.session_id, "failed")
            print(f"[Orchestrator] FATAL ERROR: {e}")
            return {
                "session_id": state.session_id,
                "status": "failed",
                "error": str(e),
                "partial_outputs": state.agent_outputs
            }

    def _generate_follow_ups(self, query: str, headline: str) -> list:
        """Generate 3 follow-up research questions after the pipeline completes."""
        from core.groq_client import build_model, call_groq
        model = build_model(temperature=0.5)
        prompt = f"""Research just completed on: "{query}"
Key headline finding: {headline}

Generate exactly 3 follow-up research questions that would deepen understanding of this topic.
Each must explore a different angle not fully addressed above.

Return ONLY a JSON array of 3 question strings. No explanation.
["question 1", "question 2", "question 3"]"""
        try:
            result = call_groq(model, prompt, expect_json=True)
            if isinstance(result, list):
                return [str(q) for q in result[:3]]
        except Exception as e:
            print(f"[Orchestrator] Follow-up generation failed: {e}")
        return []

    def _generate_search_queries(self, query: str) -> list:
        """Generate 3 targeted search queries using templates (no LLM call)."""
        return [
            f"{query} latest research analysis 2024 2025",
            f"{query} statistics data evidence impact",
            f"{query} expert opinion criticism challenges",
        ]

    def _run_with_retry(self, agent_name: str, agent, input_data: dict,
                        state: ARIAState) -> dict:
        """Run an agent with up to MAX_RETRIES attempts on failure."""
        retry_count = state.retry_count if hasattr(state, 'retry_count') else {}
        attempts = 0

        while attempts < MAX_RETRIES:
            try:
                output = agent.run(input_data)
                if output.get("status") == "success":
                    return output
                raise ValueError(f"Agent returned non-success status: {output.get('status')}")
            except Exception as e:
                attempts += 1
                print(f"[Orchestrator] {agent_name} failed (attempt {attempts}/{MAX_RETRIES}): {e}")
                if attempts >= MAX_RETRIES:
                    state.log_error(agent_name, str(e))
                    raise
                time.sleep(2)

    def _run_research_loop(self, query: str, state: ARIAState,
                           initial_findings: list) -> tuple:
        """Classifier → Researcher loop for gap filling. Max 2 iterations."""
        all_findings = list(initial_findings)
        loop_count = 0

        while loop_count <= MAX_RESEARCH_LOOPS:
            classifier_output = self._run_with_retry(
                "classifier",
                self.classifier,
                {
                    "session_id": state.session_id,
                    "findings": all_findings,
                    "original_query": query,
                    "loop_count": loop_count
                },
                state
            )

            follow_ups = classifier_output.get("follow_ups", [])
            if not follow_ups or loop_count >= MAX_RESEARCH_LOOPS:
                break

            print(f"[Orchestrator] Research loop {loop_count + 1}: "
                  f"filling {len(classifier_output.get('gaps', []))} gaps")

            follow_up_output = self._run_with_retry(
                "researcher",
                self.researcher,
                {
                    "session_id": state.session_id,
                    "queries": follow_ups[:3],
                    "original_query": query
                },
                state
            )
            all_findings.extend(follow_up_output.get("findings", []))
            loop_count += 1

        return all_findings, classifier_output

    def _run_critique_loop(self, query: str, state: ARIAState,
                           analyst_output: dict) -> tuple:
        """Devil → Analyst revision loop. Max 2 iterations."""
        insights = analyst_output.get("insights", [])
        revision_count = 0

        while revision_count <= MAX_CRITIQUE_LOOPS:
            devil_output = self._run_with_retry(
                "devil",
                self.devil,
                {
                    "session_id": state.session_id,
                    "insights": insights,
                    "relationships": analyst_output.get("relationships", []),
                    "original_query": query,
                    "revision_count": revision_count
                },
                state
            )

            if not devil_output.get("revision_needed") or revision_count >= MAX_CRITIQUE_LOOPS:
                break

            print(f"[Orchestrator] Critique loop {revision_count + 1}: "
                  f"weak ratio={devil_output.get('weak_ratio', 0):.0%}, "
                  f"requesting analyst revision")

            # Re-run analyst with critique context
            weak_claims = [c.get("original_claim", "") for c in devil_output.get("weak_claims", [])]
            revised_analyst = self._run_with_retry(
                "analyst",
                self.analyst,
                {
                    "session_id": state.session_id,
                    "domains": analyst_output.get("domains",
                                state.agent_outputs.get("classifier", {}).get("domains", {})),
                    "original_query": query,
                    "revision_note": f"Please strengthen or remove these weak claims: {weak_claims}"
                },
                state
            )
            insights = revised_analyst.get("insights", insights)
            revision_count += 1

        return insights, devil_output