"""
Tests for purchase horizon flow: dont_know options + horizon inference.
"""
from services.chatbot_epargne.ai.agents import coach, extractor
from services.chatbot_epargne import orchestrator


def test_purchase_dont_know_proposes_options():
    profile = {
        "goal": {"type": "apport", "description": "sac Chanel", "target_amount": 5000},
        "initial_amount": 0,
    }
    reply = coach.run_coach(
        user_message="je ne sais pas aide moi",
        profile_partial=profile,
        suggested_questions=["horizon_bucket"],
        flow_stage="coach",
        next_question_id="q_time_or_budget",
        llm=None,
    )
    assert "6 mois" in reply
    assert "12 mois" in reply
    assert "24 mois" in reply
    assert "834" in reply
    assert "417" in reply
    assert "209" in reply
    assert "Laquelle te paraît la plus confortable" in reply
    banned = ["combien de temps", "dans quel délai", "à quelle échéance"]
    lowered = reply.lower()
    for phrase in banned:
        assert phrase not in lowered


def test_horizon_choice_extracts_months():
    last_turns = [{"role": "user", "content": "12 mois"}]
    out = extractor.run_extractor(last_turns, {}, [])
    extracted = {e["field"]: e["value"] for e in (out.get("extracted") or [])}
    assert extracted.get("horizon_months") == 12


def test_horizon_inferred_from_monthly_budget():
    profile = {
        "goal": {"target_amount": 5000},
        "initial_amount": 0,
        "monthly_contribution": 200,
    }
    orchestrator._infer_horizon_from_budget(profile)
    assert profile.get("horizon_months") == 25
    assert profile.get("horizon_bucket") == "short"
