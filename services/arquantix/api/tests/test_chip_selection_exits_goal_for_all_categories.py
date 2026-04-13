"""
Chip selection should exit GOAL for all categories.
"""
import os

from services.chatbot_epargne.ai.agents import decide, extractor
from services.chatbot_epargne import orchestrator


LABELS = {
    "Acheter quelque chose": "buy_something",
    "Mieux vivre au quotidien": "live_better",
    "Préparer mon avenir": "prepare_future",
    "Protéger mes proches": "protect_family",
    "Vivre des expériences": "experiences",
    "Faire fructifier mon argent": "grow_money",
}


def test_chip_selection_exits_goal_for_all_categories():
    os.environ.pop("OPENAI_API_KEY", None)
    for label, expected in LABELS.items():
        last_turns = [{"role": "user", "content": label}]
        ext = extractor.run_extractor(last_turns, {}, [], llm=None)
        profile, _ = orchestrator._apply_extracted({}, ext.get("extracted") or [])
        assert profile.get("project_type") == expected
        conf = profile.get("goal_confidence")
        if conf is None:
            conf = profile.get("project_type_confidence")
        try:
            conf_val = float(conf) if conf is not None else 0.0
        except (TypeError, ValueError):
            conf_val = 0.0
        assert conf_val >= 0.7
        profile["goal_confidence"] = conf_val
        profile["goal_locked"] = orchestrator._goal_locked(profile)
        assert profile.get("goal_locked") is True

        out = decide.run_decide(profile, "", [], 0.0, turn_index=1)
        assert out.get("goal_phase") is None
        assert out.get("next_question_id") == "Q_PROJECT_DETAILS"
