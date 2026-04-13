"""PR F.6 — Intent Engine (séquences + escalade step-up)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request

from database import AuthUserIntentEvent
from services.auth.device_intent_engine import (
    evaluate_intent_engine,
    match_intent_patterns,
)
from services.auth.device_risk_engine_pr_f import RiskEvaluationContext, RiskEvaluationResult


def _req(path: str) -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": [],
    }
    return Request(scope)


def test_match_beneficiary_then_withdrawal_block():
    m = match_intent_patterns(
        prior_action_types=["beneficiary_add"],
        current_action="withdrawal",
        prior_step_up_count=0,
    )
    assert m is not None
    assert m[0] == "block"
    assert "intent_beneficiary_then_withdrawal" in m[1]


def test_match_login_then_withdrawal_step_up():
    m = match_intent_patterns(
        prior_action_types=["login"],
        current_action="withdrawal",
        prior_step_up_count=0,
    )
    assert m is not None
    assert m[0] == "step_up"
    assert "intent_login_then_withdrawal" in m[1]


def test_match_repeated_step_up_block():
    m = match_intent_patterns(
        prior_action_types=[],
        current_action="wallet_transfer",
        prior_step_up_count=3,
    )
    assert m is not None
    assert m[0] == "block"
    assert "intent_repeated_step_up_window" in m[1]


@pytest.fixture
def _intent_on(monkeypatch):
    monkeypatch.setenv("DEVICE_INTENT_ENGINE_ENABLED", "true")


@pytest.fixture
def intent_admin(db):
    from tests.conftest import make_admin_user_with_pe_client

    return make_admin_user_with_pe_client(db, email="intent-pr6@test.local", password="test")


def test_evaluate_intent_block_overrides_allow(db, intent_admin, _intent_on):
    """Table requise : auth_user_intent_events (migration 140)."""
    uid = intent_admin.id
    # historique : bénéficiaire puis retrait courant
    db.add(
        AuthUserIntentEvent(
            id=uuid.uuid4(),
            user_id=uid,
            device_id="dev",
            action_type="beneficiary_add",
            metadata_payload={},
        )
    )
    db.flush()

    ctx = RiskEvaluationContext(
        device_trust_level="HIGH",
        attestation_absent=False,
        attestation_stale=False,
        last_ip="1.1.1.1",
        current_ip="1.1.1.1",
        last_country="FR",
        current_country="FR",
        velocity_count=0,
        signature_failure_count=0,
        device_churn_distinct_24h=0,
        session_is_new=False,
        login_failures_recent=0,
        refresh_failures_recent=0,
    )
    base = RiskEvaluationResult(score=10, decision="allow", context=ctx, risk_reasons=[])

    req = _req("/api/v1/custody/simulate-withdrawal/test")
    out = evaluate_intent_engine(
        db,
        request=req,
        user_id=uid,
        device_id="dev",
        result=base,
    )
    assert out.decision == "block"
    assert any("intent_beneficiary_then_withdrawal" in r for r in out.risk_reasons)


def test_evaluate_three_prior_step_ups_block(db, intent_admin, _intent_on):
    uid = intent_admin.id
    for _ in range(3):
        db.add(
            AuthUserIntentEvent(
                id=uuid.uuid4(),
                user_id=uid,
                device_id="d",
                action_type="wallet_transfer",
                metadata_payload={"risk_decision": "step_up"},
                created_at=datetime.now(timezone.utc),
            )
        )
    db.flush()

    ctx = MagicMock(spec=RiskEvaluationContext)
    base = RiskEvaluationResult(score=5, decision="allow", context=ctx, risk_reasons=[])

    out = evaluate_intent_engine(
        db,
        request=_req("/api/internal-transfer/foo"),
        user_id=uid,
        device_id="d",
        result=base,
    )
    assert out.decision == "block"
    assert "intent_repeated_step_up_window" in " ".join(out.risk_reasons)
