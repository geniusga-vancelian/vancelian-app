"""
Tests for GOAL force pick progression after gibberish.
"""
from services.chatbot_epargne import orchestrator
from services.chatbot_epargne.ai.agents import decide


def test_force_pick_after_two_gibberish_messages():
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
