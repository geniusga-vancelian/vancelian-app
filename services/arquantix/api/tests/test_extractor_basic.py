"""
test_extractor_basic: « Je veux 50 000€ dans 5 ans » -> target_amount & horizon
"""
import pytest

from services.chatbot_epargne.ai.agents import extractor


def test_heuristic_extracts_target_amount_and_horizon():
    last_turns = [{"role": "user", "content": "Je veux 50 000€ dans 5 ans"}]
    profile = {}
    asked = []
    out = extractor.run_extractor(last_turns, profile, asked)
    extracted = {e["field"]: e["value"] for e in (out.get("extracted") or [])}
    assert extracted.get("goal.target_amount") == 50000
    assert extracted.get("horizon_months") == 60
    assert extracted.get("horizon_bucket") == "medium"
    # confidence
    for e in out.get("extracted") or []:
        if e.get("field") in ("goal.target_amount", "horizon_months"):
            assert float(e.get("confidence", 0)) >= 0.7


def test_extracts_one_year_as_12_months():
    last_turns = [{"role": "user", "content": "Sur 1 an"}]
    out = extractor.run_extractor(last_turns, {}, [])
    extracted = {e["field"]: e["value"] for e in (out.get("extracted") or [])}
    assert extracted.get("horizon_months") == 12


def test_extracts_monthly_budget_with_slash():
    last_turns = [{"role": "user", "content": "200/mois"}]
    out = extractor.run_extractor(last_turns, {}, [])
    extracted = {e["field"]: e["value"] for e in (out.get("extracted") or [])}
    assert extracted.get("monthly_contribution") == 200
