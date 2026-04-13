"""
test_compliance_contradiction: horizon 3 months + illiquid product -> contradiction
"""
import pytest

from services.chatbot_epargne.ai.agents import compliance


def test_contradiction_horizon_short_plus_illiquid():
    profile = {
        "horizon_months": 3,
        "preferences": ["fonds 5 ans"],
    }
    out = compliance.run_compliance(profile, asked_questions=[])
    contradictions = out.get("contradictions") or []
    assert len(contradictions) >= 1
    types = [c.get("type") for c in contradictions]
    assert "horizon_liquidity" in types
    repair = [c for c in contradictions if c.get("repair_id") == "repair_horizon"]
    assert repair
