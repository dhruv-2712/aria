# tests/test_agents.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from unittest.mock import patch, MagicMock
import pytest


# ── Researcher ────────────────────────────────────────────────────────────────

MOCK_FINDINGS = [
    {"query_index": 1, "content": "AI displaces routine jobs.", "source_url": "https://source1.com",
     "date": "2024", "confidence_score": 0.85, "angle": "economic"},
    {"query_index": 2, "content": "New AI roles emerge in tech.", "source_url": "https://source2.com",
     "date": "2024", "confidence_score": 0.80, "angle": "technical"},
    {"query_index": 3, "content": "Workers need reskilling.", "source_url": "https://source3.com",
     "date": "2024", "confidence_score": 0.75, "angle": "social"},
]


@patch("agents.researcher.call_groq", return_value=MOCK_FINDINGS)
def test_researcher_batches_into_one_call(mock_call):
    from agents.researcher import ResearcherAgent
    agent = ResearcherAgent()
    result = agent.run({
        "session_id": "test-session",
        "queries": ["AI jobs 2024", "AI economic impact", "AI reskilling"],
        "original_query": "Impact of AI on employment"
    })
    assert mock_call.call_count == 1, "Researcher should make exactly 1 API call for all queries"
    assert result["status"] == "success"
    assert len(result["findings"]) == 3


@patch("agents.researcher.call_groq", return_value={"error": "api failed", "raw": ""})
def test_researcher_handles_bad_response(mock_call):
    from agents.researcher import ResearcherAgent
    agent = ResearcherAgent()
    result = agent.run({
        "session_id": "test-session",
        "queries": ["some query"],
        "original_query": "test"
    })
    assert result["status"] == "success"
    assert result["findings"] == []


# ── Classifier ────────────────────────────────────────────────────────────────

MOCK_CLASSIFIED = {
    "scientific": [0], "economic": [1], "political": [],
    "social": [2], "technical": [0], "historical": [],
    "ethical": [], "cultural": []
}

MOCK_FOLLOW_UPS = [
    {"query": "AI political regulation", "target_domain": "political"},
    {"query": "AI history timeline", "target_domain": "historical"},
]


@patch("agents.classifier.call_groq", side_effect=[MOCK_CLASSIFIED, MOCK_FOLLOW_UPS])
def test_classifier_detects_gaps(mock_call):
    from agents.classifier import ClassifierAgent
    agent = ClassifierAgent()
    findings = [
        {"content": "science finding", "confidence_score": 0.9},
        {"content": "economic finding", "confidence_score": 0.8},
        {"content": "social finding", "confidence_score": 0.7},
    ]
    result = agent.run({
        "session_id": "test-session",
        "findings": findings,
        "original_query": "AI impact",
        "loop_count": 0
    })
    assert result["status"] == "success"
    assert "political" in result["gaps"]
    assert "historical" in result["gaps"]
    assert len(result["follow_ups"]) > 0


# ── Analyst ───────────────────────────────────────────────────────────────────

MOCK_INSIGHTS = {
    "insights": [
        {"id": "insight_1", "domain": "economic", "claim": "AI reduces low-skill jobs.",
         "evidence": "Multiple studies show 30% reduction.", "tag": "core", "confidence": 0.85},
        {"id": "insight_2", "domain": "social", "claim": "Reskilling programs are underfunded.",
         "evidence": "Government budgets lag demand.", "tag": "supporting", "confidence": 0.72},
    ]
}

MOCK_RELATIONSHIPS = [
    {"insight_a": "insight_1", "insight_b": "insight_2",
     "relationship_type": "causal", "description": "Job loss drives reskilling need.",
     "strength": 0.8}
]


@patch("agents.analyst.call_groq", side_effect=[MOCK_INSIGHTS, MOCK_RELATIONSHIPS])
def test_analyst_extracts_insights(mock_call):
    from agents.analyst import AnalystAgent
    agent = AnalystAgent()
    result = agent.run({
        "session_id": "test-session",
        "domains": {"economic": [{"content": "AI displaces jobs"}], "social": []},
        "original_query": "AI employment impact"
    })
    assert result["status"] == "success"
    assert result["insight_count"] == 2
    assert result["confidence"] > 0


@patch("agents.analyst.call_groq", return_value={"insights": []})
def test_analyst_returns_zero_insights_on_empty_data(mock_call):
    from agents.analyst import AnalystAgent
    agent = AnalystAgent()
    result = agent.run({
        "session_id": "test-session",
        "domains": {d: [] for d in ["scientific", "economic", "social", "technical",
                                     "political", "historical", "ethical", "cultural"]},
        "original_query": "obscure topic with no data"
    })
    assert result["insight_count"] == 0


# ── Writer ────────────────────────────────────────────────────────────────────

@patch("agents.writer.call_groq", return_value="Generated report text.")
@patch("agents.writer.save_report")
@patch("agents.writer.log_agent_call")
def test_writer_generates_all_formats(mock_log, mock_save, mock_call):
    from agents.writer import WriterAgent
    agent = WriterAgent()
    result = agent.run({
        "session_id": "test-session",
        "original_query": "AI employment impact",
        "insights": [{"id": "i1", "claim": "AI replaces jobs", "domain": "economic",
                       "tag": "core", "confidence": 0.8}],
        "relationships": [],
        "findings": [],
        "domains": {},
        "confidence": 0.8
    })
    assert result["status"] == "success"
    assert "executive" in result
    assert "standard" in result
    assert "technical" in result
