"""Adaptive Auth Orchestrator — arbre de décision et intégration légère."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from database import AdminUser


@pytest.fixture
def orch_user(db):
    u = AdminUser(
        email=f"adapt_{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="x",
        mobile_e164="+33612345678",
    )
    db.add(u)
    db.flush()
    return u


def _minimal_risk(
    *,
    hint: str = "otp_only",
    dtl: str = "HIGH",
    login_risk: int = 20,
    signals=None,
    has_pk: bool = True,
):
    return {
        "decision_hint": hint,
        "device_trust_level": dtl,
        "login_risk_score": login_risk,
        "signals": signals or [],
        "user_has_passkeys": has_pk,
        "global_risk_level": "LOW",
        "global_risk_score": 5,
    }


def test_orchestrate_passkey_auto_high_trust(monkeypatch, db, orch_user):
    monkeypatch.setenv("ADAPTIVE_AUTH_ENABLED", "true")
    from services.auth.adaptive_auth_orchestrator import orchestrate_login_strategy

    risk = _minimal_risk(hint="passkey_preferred", dtl="HIGH", login_risk=25)
    pk_ctx = {"eligible": True, "recommended": True, "reason_codes": ["passkey_auto_recommended"]}
    d = orchestrate_login_strategy(
        db,
        orch_user,
        {"kind": "phone_e164", "value": orch_user.mobile_e164},
        device_context={"device_hash": "ab" * 32},
        risk_context=risk,
        fraud_context={"skipped": True},
        passkey_context=pk_ctx,
        attestation_context={"trusted": False},
        user_login_context={"has_mobile": True, "has_email": True},
        login_channel="sms_start",
    )
    assert d.primary_method == "passkey"
    assert d.auto_trigger_passkey is True
    assert d.ui_variant == "fast_lane"


def test_orchestrate_suspect_step_up(monkeypatch, db, orch_user):
    monkeypatch.setenv("ADAPTIVE_AUTH_ENABLED", "true")
    from services.auth.adaptive_auth_orchestrator import orchestrate_login_strategy

    risk = _minimal_risk(hint="otp_step_up", dtl="LOW", login_risk=60, has_pk=True)
    pk_ctx = {"eligible": True, "recommended": False, "reason_codes": []}
    d = orchestrate_login_strategy(
        db,
        orch_user,
        {"kind": "phone_e164", "value": orch_user.mobile_e164},
        device_context={},
        risk_context=risk,
        fraud_context={"skipped": True},
        passkey_context=pk_ctx,
        attestation_context={},
        user_login_context={"has_mobile": True, "has_email": True},
        login_channel="sms_start",
    )
    assert d.primary_method == "otp_sms"
    assert d.step_up_required is True
    assert d.auto_trigger_passkey is False
    assert d.ui_variant == "cautious"


def test_orchestrate_account_locked(monkeypatch, db, orch_user):
    monkeypatch.setenv("ADAPTIVE_AUTH_ENABLED", "true")
    from services.auth.adaptive_auth_orchestrator import orchestrate_login_strategy

    orch_user.security_account_locked_until = datetime.now(timezone.utc) + timedelta(hours=1)
    db.flush()
    risk = _minimal_risk()
    d = orchestrate_login_strategy(
        db,
        orch_user,
        {"kind": "phone_e164", "value": orch_user.mobile_e164},
        device_context={},
        risk_context=risk,
        fraud_context={},
        passkey_context={},
        attestation_context={},
        user_login_context={"has_mobile": True, "has_email": True},
        login_channel="sms_start",
    )
    assert d.blocked is True
    assert d.primary_method == "blocked"


def test_orchestrate_email_channel(monkeypatch, db, orch_user):
    monkeypatch.setenv("ADAPTIVE_AUTH_ENABLED", "true")
    from services.auth.adaptive_auth_orchestrator import orchestrate_login_strategy

    risk = _minimal_risk(dtl="MEDIUM", login_risk=30)
    d = orchestrate_login_strategy(
        db,
        orch_user,
        {"kind": "email", "value": orch_user.email},
        device_context={},
        risk_context=risk,
        fraud_context={"skipped": True},
        passkey_context={"eligible": True, "recommended": False},
        attestation_context={},
        user_login_context={"has_mobile": True, "has_email": True},
        login_channel="email_otp_start",
    )
    assert d.primary_method == "otp_email"


def test_decide_falls_back_when_adaptive_off(db, orch_user, monkeypatch):
    monkeypatch.setenv("ADAPTIVE_AUTH_ENABLED", "false")
    monkeypatch.setenv("LOGIN_AUTH_STRATEGY_ENABLED", "true")
    from services.security.login_auth_strategy_service import decide_login_auth_strategy

    req = MagicMock()
    req.headers = {"x-device-id": "dev-orch-test"}
    req.client = MagicMock()
    req.client.host = "10.0.0.1"
    out = decide_login_auth_strategy(
        db,
        req,
        orch_user,
        device_header="dev-orch-test",
        login_channel="sms_start",
    )
    assert out.blocked in (True, False)
    assert out.primary_method in ("otp", "passkey")
