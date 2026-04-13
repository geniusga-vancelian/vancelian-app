"""E2E registration: phone form → SMS interaction → 2FA verify → complete → next → project.

Uses **no** mock on OTP generation. Requires explicit test env (see fixture):
- TWO_FACTOR_RELAXED=true
- TWO_FACTOR_DEV_FIXED_CODE=111111
- FAKE_SMS_PROVIDER=true
- TWO_FACTOR_DEV_EXPOSE_CODE=true (optional; asserts dev_code in prepare response)

No real SMS / no Twilio HTTP (fake provider + httpx guard).
"""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import (
    Person,
    RegistrationFlow,
    RegistrationFlowStep,
    RegistrationJurisdiction,
    RegistrationScreenComponent,
    RegistrationSessionData,
    RegistrationStepScreen,
    TwoFactorChallenge,
)
from services.registration.execution_events import RegistrationEventType
from services.security.two_factor_service import get_two_factor_service


@pytest.fixture
def _registration_phone_e2e_env(monkeypatch):
    """Explicit guardrails for this suite (dev/test only).

    Applied *before* ``create_app`` so ``load_dotenv`` during import cannot
    leave ``APP_ENV=production`` from ``.env`` and disable the fixed OTP.
    """
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("ARQUANTIX_ENV", raising=False)
    monkeypatch.setenv("TWO_FACTOR_RELAXED", "true")
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "111111")
    monkeypatch.setenv("TWO_FACTOR_DEV_EXPOSE_CODE", "true")
    monkeypatch.setenv("FAKE_SMS_PROVIDER", "true")
    monkeypatch.setenv("TWO_FACTOR_REQUIRE_AUTH", "false")
    monkeypatch.delenv("TWILIO_ACCOUNT_SID", raising=False)
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)


@pytest.fixture
def test_app(_registration_phone_e2e_env):
    """Override conftest ``test_app``: env must be set before app import."""
    from main import create_app

    return create_app(testing=True)


def _seed_phone_sms_then_done_flow(db: Session) -> dict:
    """One step: phone (form) → SMS interaction → optional trailing form (so next() succeeds)."""
    j = RegistrationJurisdiction(
        id=uuid.uuid4(),
        code="E2E_SMS01",
        name="E2E SMS Registration",
        is_active=True,
    )
    db.add(j)
    db.flush()
    flow = RegistrationFlow(
        id=uuid.uuid4(),
        jurisdiction_id=j.id,
        name="E2E SMS Flow",
        version=1,
        status="active",
    )
    db.add(flow)
    db.flush()
    step = RegistrationFlowStep(
        id=uuid.uuid4(),
        flow_id=flow.id,
        step_key="onboarding",
        title="Onboarding",
        position=0,
        is_blocking=True,
    )
    db.add(step)
    db.flush()
    scr_phone = RegistrationStepScreen(
        id=uuid.uuid4(),
        step_id=step.id,
        screen_key="phone_entry",
        title="Your phone",
        position=0,
    )
    db.add(scr_phone)
    db.flush()
    comp_phone = RegistrationScreenComponent(
        id=uuid.uuid4(),
        screen_id=scr_phone.id,
        component_type="phone_input",
        component_key="ph",
        position=0,
        binding_slug="phone_number",
        props_json={"label": "Mobile", "required": True},
    )
    db.add(comp_phone)
    db.flush()
    scr_ix = RegistrationStepScreen(
        id=uuid.uuid4(),
        step_id=step.id,
        screen_key="phone_verification_sms",
        title="Confirm mobile",
        position=1,
        screen_type="interaction",
        interaction_type="phone_verification_sms",
        interaction_config_json={
            "source_field_slug": "phone_number",
            "verified_flag_slug": "phone_verified",
            "purpose": "verify_phone",
        },
    )
    db.add(scr_ix)
    db.flush()
    scr_done = RegistrationStepScreen(
        id=uuid.uuid4(),
        step_id=step.id,
        screen_key="post_sms_done",
        title="Almost there",
        position=2,
    )
    db.add(scr_done)
    db.flush()
    comp_note = RegistrationScreenComponent(
        id=uuid.uuid4(),
        screen_id=scr_done.id,
        component_type="text_input",
        component_key="note",
        position=0,
        binding_slug="e2e_optional_note",
        props_json={"label": "Note (optional)", "required": False},
    )
    db.add(comp_note)
    db.flush()
    return {
        "jurisdiction": j,
        "flow": flow,
        "screen_phone": scr_phone,
        "screen_ix": scr_ix,
        "screen_done": scr_done,
    }


def test_registration_phone_verification_e2e_fake_sms_fixed_code(
    client: TestClient,
    db: Session,
):
    meta = _seed_phone_sms_then_done_flow(db)
    test_phone = "+33701999888"

    with patch("services.security.providers.sms_provider.httpx.Client") as httpx_client:
        start = client.post(
            "/api/registration/sessions/start",
            json={"jurisdiction": "E2E_SMS01"},
        )
        assert start.status_code == 201, start.text
        sid = start.json()["session_id"]
        sid_uuid = uuid.UUID(sid)

        scr0 = client.get(f"/api/registration/sessions/{sid}/screen")
        assert scr0.status_code == 200
        assert scr0.json()["screen"]["screen_key"] == "phone_entry"

        sub = client.post(
            f"/api/registration/sessions/{sid}/submit",
            json={"answers": {"phone_number": test_phone}},
        )
        assert sub.status_code == 200, sub.text

        scr1 = client.get(f"/api/registration/sessions/{sid}/screen")
        assert scr1.status_code == 200
        assert scr1.json()["screen"]["screen_type"] == "interaction"
        assert scr1.json()["screen"]["interaction_type"] == "phone_verification_sms"

        prep = client.post(f"/api/registration/sessions/{sid}/interaction/prepare")
        assert prep.status_code == 200, prep.text
        body = prep.json()
        cid = body["challenge_id"]
        token = body["otp_token"]
        assert cid
        assert token
        assert body.get("dev_code") == "111111"
        assert body.get("reused") is False

        ch = db.query(TwoFactorChallenge).filter(TwoFactorChallenge.id == uuid.UUID(cid)).first()
        assert ch is not None
        assert ch.status == "pending"
        assert ch.channel == "sms"
        assert (ch.target or "").strip() == test_phone
        db.refresh(ch)
        tfs = get_two_factor_service()
        assert tfs._verify_otp_hash(
            "111111",
            ch.code_hash,
        ), "challenge hash must match TWO_FACTOR_DEV_FIXED_CODE (no mock on OTP)"

        httpx_client.assert_not_called()

        vr = client.post(
            "/api/2fa/verify",
            json={"challenge_id": cid, "code": "111111"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert vr.status_code == 200, vr.text

        db.expire_all()
        ch2 = db.query(TwoFactorChallenge).filter(TwoFactorChallenge.id == uuid.UUID(cid)).first()
        assert ch2 is not None
        assert ch2.status == "verified"

        done = client.post(
            f"/api/registration/sessions/{sid}/interaction/complete",
            json={
                "screen_id": str(meta["screen_ix"].id),
                "interaction_type": "phone_verification_sms",
                "challenge_id": cid,
                "verified": True,
            },
        )
        assert done.status_code == 200, done.text

        def _session_value(slug: str):
            row = (
                db.query(RegistrationSessionData)
                .filter(
                    RegistrationSessionData.session_id == sid_uuid,
                    RegistrationSessionData.field_slug == slug,
                )
                .first()
            )
            return None if row is None else row.value_json

        assert _session_value("phone_verified") is True
        assert _session_value("phone_verification_channel") == "sms"
        assert _session_value("phone_verified_at")

        nx = client.post(f"/api/registration/sessions/{sid}/next")
        assert nx.status_code == 200, nx.text
        assert nx.json()["screen"]["screen_key"] == "post_sms_done"

        fin = client.post(f"/api/registration/sessions/{sid}/complete")
        assert fin.status_code == 200, fin.text
        pid = fin.json()["person_id"]
        person = db.query(Person).filter(Person.id == uuid.UUID(pid)).first()
        assert person is not None
        pj = person.profile_json or {}
        assert pj.get("compliance", {}).get("phone_verified") is True
        assert pj.get("compliance", {}).get("phone_verification_channel") == "sms"
        assert pj.get("compliance", {}).get("phone_verified_at")
        assert pj.get("collected", {}).get("phone_number") == test_phone

        ev = client.get(f"/api/admin/registration/sessions/{sid}/execution-events")
        assert ev.status_code == 200
        types = [e["event_type"] for e in ev.json()["events"]]
        assert RegistrationEventType.INTERACTION_PREPARED in types
        assert RegistrationEventType.INTERACTION_COMPLETED in types
        assert RegistrationEventType.NAVIGATION_NEXT in types
