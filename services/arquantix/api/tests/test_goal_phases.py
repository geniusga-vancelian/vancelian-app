"""
Tests for GOAL phases (goal_free / goal_clarify / goal_force_pick).
"""
from services.chatbot_epargne.ai.agents import decide
from services.chatbot_epargne import orchestrator


def test_goal_phase_free_when_low_conf_first_attempt():
    profile = {"goal_confidence": 0.4, "goal_attempts": 0}
    out = decide.run_decide(profile, "", [], 0.0, turn_index=1)
    assert out.get("goal_phase") == "goal_free"
    assert out.get("next_question_id") == "Q_GOAL_FREE"


def test_goal_phase_clarify_after_one_unclear():
    profile = {"goal_confidence": 0.4, "goal_attempts": 1}
    out = decide.run_decide(profile, "", [], 0.0, turn_index=1)
    assert out.get("goal_phase") == "goal_clarify"
    assert out.get("next_question_id") == "Q_GOAL_CLARIFY"


def test_goal_phase_force_pick_after_two_unclear():
    profile = {"goal_confidence": 0.4, "goal_attempts": 2}
    out = decide.run_decide(profile, "", [], 0.0, turn_index=1)
    assert out.get("goal_phase") == "goal_force_pick"
    assert out.get("next_question_id") == "Q_GOAL_FORCE_PICK"


def test_goal_locked_after_chip_selection():
    profile = {"goal_confidence": 0.95, "goal_locked": True}
    out = decide.run_decide(profile, "", [], 0.0, turn_index=1)
    assert out.get("goal_phase") is None
    assert out.get("next_question_id") not in ("Q_GOAL_FREE", "Q_GOAL_CLARIFY", "Q_GOAL_FORCE_PICK")


def test_gibberish_progression_to_force_pick():
    profile = {"goal_confidence": 0.1, "goal_locked": False, "goal_attempts": 0}
    orchestrator._update_goal_attempts(profile, 1)
    out1 = decide.run_decide(profile, "", [], 0.0, turn_index=1)
    assert profile["goal_attempts"] == 1
    assert out1.get("goal_phase") == "goal_clarify"
    assert out1.get("next_question_id") == "Q_GOAL_CLARIFY"

    profile["goal_confidence"] = 0.1
    orchestrator._update_goal_attempts(profile, 2)
    out2 = decide.run_decide(profile, "", [], 0.0, turn_index=2)
    assert profile["goal_attempts"] == 2
    assert out2.get("goal_phase") == "goal_force_pick"
    assert out2.get("next_question_id") == "Q_GOAL_FORCE_PICK"
