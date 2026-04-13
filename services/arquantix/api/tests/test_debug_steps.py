"""
Tests for debug steps status.
"""
from services.chatbot_epargne import orchestrator


def _get_status(steps, step_id):
    return next((s["status"] for s in steps if s["id"] == step_id), None)


def test_steps_initial_opening_in_progress():
    steps = orchestrator.build_steps({}, "coach", 0)
    assert _get_status(steps, "opening") == "in_progress"
    assert _get_status(steps, "goal_category") is None


def test_steps_after_first_user_message():
    steps = orchestrator.build_steps({}, "coach", 1)
    assert _get_status(steps, "opening") == "success"
    assert _get_status(steps, "goal_category") == "in_progress"


def test_steps_goal_locked_advances():
    profile = {
        "project_type": "buy_something",
        "project_type_confidence": 0.9,
        "project_type_attempts": 1,
    }
    steps = orchestrator.build_steps(profile, "coach", 1)
    assert _get_status(steps, "goal_category") == "success"
    assert _get_status(steps, "project_details") == "in_progress"


def test_steps_horizon_success_when_horizon_months_set():
    profile = {"horizon_months": 60}
    steps = orchestrator.build_steps(profile, "coach", 1)
    assert _get_status(steps, "horizon") == "success"
