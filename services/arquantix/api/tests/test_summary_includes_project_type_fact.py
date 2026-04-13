"""
Tests for summarizer project_type fact inclusion.
"""
from services.chatbot_epargne.ai.agents import summarizer


def test_summary_includes_project_type_fact():
    profile = {
        "project_type": "prepare_future",
        "project_type_confidence": 0.9,
    }
    out = summarizer.run_summarizer(
        previous_summary=None,
        last_turns=[{"role": "user", "content": "Je prépare ma retraite"}],
        current_profile=profile,
        llm=None,
    )
    facts = out.get("facts") or []
    assert any("Catégorie projet" in f for f in facts)
