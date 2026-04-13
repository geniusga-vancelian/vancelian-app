"""Registration interaction screens: SMS phone verification (runtime + projection).

Requires DB migration ``098`` (columns ``screen_type``, ``interaction_type``,
``interaction_config_json`` on ``registration_step_screens``). Run::

    cd api && alembic upgrade head
"""
from __future__ import annotations

import uuid
from unittest import mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import (
    Person,
    RegistrationFlow,
    RegistrationFlowStep,
    RegistrationJurisdiction,
    RegistrationScreenComponent,
    RegistrationStepScreen,
    RegistrationSessionData,
    TwoFactorChallenge,
)
from services.registration.execution_events import RegistrationEventType


def _seed_interaction_only_flow(db: Session) -> dict:
    """Single interaction screen first — no phone collected (error payload)."""
    j = RegistrationJurisdiction(
        id=uuid.uuid4(), code="IX_ONLY", name="IX Only", is_active=True,
    )
    db.add(j)
    db.flush()
    flow = RegistrationFlow(
        id=uuid.uuid4(), jurisdiction_id=j.id,
        name="IX Only Flow", version=1, status="active",
    )
    db.add(flow)
    db.flush()
    step = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="s1", title="Step", position=0, is_blocking=True,
    )
    db.add(step)
    db.flush()
    scr_ix = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step.id,
        screen_key="confirm_sms", title="Confirm mobile", position=0,
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
    return {"jurisdiction": j, "flow": flow, "screen_ix": scr_ix}


def _seed_phone_then_interaction_flow(db: Session) -> dict:
    j = RegistrationJurisdiction(
        id=uuid.uuid4(), code="IX_PHONE", name="IX Phone", is_active=True,
    )
    db.add(j)
    db.flush()
    flow = RegistrationFlow(
        id=uuid.uuid4(), jurisdiction_id=j.id,
        name="IX Phone Flow", version=1, status="active",
    )
    db.add(flow)
    db.flush()
    step = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id,
        step_key="s1", title="Step", position=0, is_blocking=True,
    )
    db.add(step)
    db.flush()
    scr_phone = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step.id,
        screen_key="phone", title="Phone", position=0,
    )
    db.add(scr_phone)
    db.flush()
    comp = RegistrationScreenComponent(
        id=uuid.uuid4(), screen_id=scr_phone.id,
        component_type="phone_input", component_key="ph",
        position=0, binding_slug="phone_number",
        props_json={"label": "Phone", "required": True},
    )
    db.add(comp)
    db.flush()
    scr_ix = RegistrationStepScreen(
        id=uuid.uuid4(), step_id=step.id,
        screen_key="confirm_sms", title="Confirm mobile", position=1,
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
    return {
        "jurisdiction": j,
        "flow": flow,
        "screen_phone": scr_phone,
        "screen_ix": scr_ix,
    }


class TestRegistrationInteractionSms:
    def test_screen_payload_error_without_phone(self, client: TestClient, db: Session):
        _seed_interaction_only_flow(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "IX_ONLY"})
        assert start.status_code == 201
        sid = start.json()["session_id"]
        scr = client.get(f"/api/registration/sessions/{sid}/screen")
        assert scr.status_code == 200
        pay = scr.json()["screen"]["interaction_payload"]
        assert pay["error_code"] == "phone_number_required"
        assert pay["challenge_ready"] is False

    def test_prepare_fails_without_phone(self, client: TestClient, db: Session):
        _seed_interaction_only_flow(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "IX_ONLY"})
        sid = start.json()["session_id"]
        prep = client.post(f"/api/registration/sessions/{sid}/interaction/prepare")
        assert prep.status_code == 422
        body = prep.json()
        assert body["detail"]["code"] == "phone_number_required"
        assert body["detail"]["message"] == "Please enter your phone number"

    def test_prepare_fails_invalid_phone(self, client: TestClient, db: Session):
        _seed_phone_then_interaction_flow(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "IX_PHONE"})
        assert start.status_code == 201
        sid = uuid.UUID(start.json()["session_id"])
        sub = client.post(
            f"/api/registration/sessions/{sid}/submit",
            json={"answers": {"phone_number": "+33612345678"}},
        )
        assert sub.status_code == 200
        row = (
            db.query(RegistrationSessionData)
            .filter(
                RegistrationSessionData.session_id == sid,
                RegistrationSessionData.field_slug == "phone_number",
            )
            .first()
        )
        assert row is not None
        row.value_json = "+12345"
        db.commit()
        prep = client.post(f"/api/registration/sessions/{sid}/interaction/prepare")
        assert prep.status_code == 422
        assert prep.json()["detail"]["code"] == "invalid_phone_number"
        assert prep.json()["detail"]["message"] == (
            "Please enter a valid mobile number."
        )

    def test_prepare_accepts_french_national_number(self, client: TestClient, db: Session):
        _seed_phone_then_interaction_flow(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "IX_PHONE"})
        sid = start.json()["session_id"]
        client.post(
            f"/api/registration/sessions/{sid}/submit",
            json={
                "answers": {
                    "phone_number_raw": "06 12 34 56 78",
                    "phone_number_country_code": "FR",
                    "phone_number_country_iso2": "FR",
                }
            },
        )
        with mock.patch(
            "services.security.two_factor_service.new_plaintext_sms_otp",
            return_value="123456",
        ):
            p1 = client.post(f"/api/registration/sessions/{sid}/interaction/prepare")
            assert p1.status_code == 200
            assert p1.json().get("challenge_id")

    def test_submit_rejected_on_interaction_screen(self, client: TestClient, db: Session):
        meta = _seed_phone_then_interaction_flow(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "IX_PHONE"})
        sid = start.json()["session_id"]
        client.post(
            f"/api/registration/sessions/{sid}/submit",
            json={"answers": {"phone_number": "+33612345678"}},
        )
        sub = client.post(
            f"/api/registration/sessions/{sid}/submit",
            json={"answers": {}},
        )
        assert sub.status_code == 422
        assert "interaction" in sub.json()["detail"].lower()

    def test_prepare_reuses_pending_challenge(self, client: TestClient, db: Session):
        meta = _seed_phone_then_interaction_flow(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "IX_PHONE"})
        sid = start.json()["session_id"]
        client.post(
            f"/api/registration/sessions/{sid}/submit",
            json={"answers": {"phone_number": "+33612345678"}},
        )
        with mock.patch(
            "services.security.two_factor_service.new_plaintext_sms_otp",
            return_value="123456",
        ):
            p1 = client.post(f"/api/registration/sessions/{sid}/interaction/prepare")
            assert p1.status_code == 200
            c1 = p1.json()["challenge_id"]
            assert p1.json()["reused"] is False
            p2 = client.post(f"/api/registration/sessions/{sid}/interaction/prepare")
            assert p2.status_code == 200
            assert p2.json()["challenge_id"] == c1
            assert p2.json()["reused"] is True
            assert p1.json()["sent"] is True
            assert p2.json()["sent"] is False
            assert p1.json().get("resend_after_seconds") == 30
            assert p2.json().get("resend_after_seconds") == 30

    def test_resend_supersedes_pending_and_sends_new_challenge(self, client: TestClient, db: Session):
        meta = _seed_phone_then_interaction_flow(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "IX_PHONE"})
        sid = start.json()["session_id"]
        client.post(
            f"/api/registration/sessions/{sid}/submit",
            json={"answers": {"phone_number": "+33612345678"}},
        )
        with mock.patch(
            "services.security.two_factor_service.new_plaintext_sms_otp",
            side_effect=["111111", "222222"],
        ):
            p1 = client.post(f"/api/registration/sessions/{sid}/interaction/prepare")
            assert p1.status_code == 200
            c_old = p1.json()["challenge_id"]
            rs = client.post(
                f"/api/registration/sessions/{sid}/interaction/resend",
                json={
                    "screen_id": str(meta["screen_ix"].id),
                    "interaction_type": "phone_verification_sms",
                },
            )
            assert rs.status_code == 200
            body = rs.json()
            assert body["sent"] is True
            assert body["challenge_id"] != c_old
            assert body.get("resend_after_seconds") == 30
            row_old = db.query(TwoFactorChallenge).filter(
                TwoFactorChallenge.id == uuid.UUID(c_old),
            ).first()
            assert row_old is not None
            assert row_old.status == "superseded"

    def test_verify_rejects_superseded_challenge(self, client: TestClient, db: Session):
        meta = _seed_phone_then_interaction_flow(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "IX_PHONE"})
        sid = start.json()["session_id"]
        client.post(
            f"/api/registration/sessions/{sid}/submit",
            json={"answers": {"phone_number": "+33612345678"}},
        )
        with mock.patch(
            "services.security.two_factor_service.new_plaintext_sms_otp",
            side_effect=["111111", "222222"],
        ):
            p1 = client.post(f"/api/registration/sessions/{sid}/interaction/prepare")
            token1 = p1.json()["otp_token"]
            c_old = p1.json()["challenge_id"]
            rs = client.post(
                f"/api/registration/sessions/{sid}/interaction/resend",
                json={
                    "screen_id": str(meta["screen_ix"].id),
                    "interaction_type": "phone_verification_sms",
                },
            )
            assert rs.status_code == 200
            rs_body = rs.json()
            token2 = rs_body["otp_token"]
            c_new = rs_body["challenge_id"]
        bad = client.post(
            "/api/2fa/verify",
            json={"challenge_id": c_old, "code": "111111"},
            headers={"Authorization": f"Bearer {token1}"},
        )
        assert bad.status_code == 410
        ok = client.post(
            "/api/2fa/verify",
            json={"challenge_id": c_new, "code": "222222"},
            headers={"Authorization": f"Bearer {token2}"},
        )
        assert ok.status_code == 200

    def test_resend_second_within_cooldown_429(self, client: TestClient, db: Session):
        meta = _seed_phone_then_interaction_flow(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "IX_PHONE"})
        sid = start.json()["session_id"]
        client.post(
            f"/api/registration/sessions/{sid}/submit",
            json={"answers": {"phone_number": "+33612345678"}},
        )
        with mock.patch(
            "services.security.two_factor_service.new_plaintext_sms_otp",
            side_effect=["111111", "222222", "333333"],
        ):
            client.post(f"/api/registration/sessions/{sid}/interaction/prepare")
            rs1 = client.post(
                f"/api/registration/sessions/{sid}/interaction/resend",
                json={
                    "screen_id": str(meta["screen_ix"].id),
                    "interaction_type": "phone_verification_sms",
                },
            )
            assert rs1.status_code == 200
            rs2 = client.post(
                f"/api/registration/sessions/{sid}/interaction/resend",
                json={
                    "screen_id": str(meta["screen_ix"].id),
                    "interaction_type": "phone_verification_sms",
                },
            )
            assert rs2.status_code == 429

    def test_resend_rejects_when_challenge_already_verified(self, client: TestClient, db: Session):
        meta = _seed_phone_then_interaction_flow(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "IX_PHONE"})
        sid = start.json()["session_id"]
        client.post(
            f"/api/registration/sessions/{sid}/submit",
            json={"answers": {"phone_number": "+33612345678"}},
        )
        with mock.patch(
            "services.security.two_factor_service.new_plaintext_sms_otp",
            return_value="123456",
        ):
            p1 = client.post(f"/api/registration/sessions/{sid}/interaction/prepare")
        token = p1.json()["otp_token"]
        cid = p1.json()["challenge_id"]
        client.post(
            "/api/2fa/verify",
            json={"challenge_id": cid, "code": "123456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        rs = client.post(
            f"/api/registration/sessions/{sid}/interaction/resend",
            json={
                "screen_id": str(meta["screen_ix"].id),
                "interaction_type": "phone_verification_sms",
            },
        )
        assert rs.status_code == 422

    def test_next_blocked_until_interaction_complete(self, client: TestClient, db: Session):
        meta = _seed_phone_then_interaction_flow(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "IX_PHONE"})
        sid = start.json()["session_id"]
        client.post(
            f"/api/registration/sessions/{sid}/submit",
            json={"answers": {"phone_number": "+33612345678"}},
        )
        nx = client.post(f"/api/registration/sessions/{sid}/next")
        assert nx.status_code == 409

    def test_complete_rejects_unverified_challenge(self, client: TestClient, db: Session):
        meta = _seed_phone_then_interaction_flow(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "IX_PHONE"})
        sid = start.json()["session_id"]
        client.post(
            f"/api/registration/sessions/{sid}/submit",
            json={"answers": {"phone_number": "+33612345678"}},
        )
        with mock.patch(
            "services.security.two_factor_service.new_plaintext_sms_otp",
            return_value="654321",
        ):
            p1 = client.post(f"/api/registration/sessions/{sid}/interaction/prepare")
        cid = p1.json()["challenge_id"]
        bad = client.post(
            f"/api/registration/sessions/{sid}/interaction/complete",
            json={
                "screen_id": str(meta["screen_ix"].id),
                "interaction_type": "phone_verification_sms",
                "challenge_id": cid,
                "verified": True,
            },
        )
        assert bad.status_code == 422

    def test_full_flow_verify_complete_next_projection(self, client: TestClient, db: Session):
        meta = _seed_phone_then_interaction_flow(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "IX_PHONE"})
        sid = start.json()["session_id"]
        client.post(
            f"/api/registration/sessions/{sid}/submit",
            json={"answers": {"phone_number": "+33612345678"}},
        )
        with mock.patch(
            "services.security.two_factor_service.new_plaintext_sms_otp",
            return_value="123456",
        ):
            p1 = client.post(f"/api/registration/sessions/{sid}/interaction/prepare")
        assert p1.status_code == 200
        token = p1.json()["otp_token"]
        cid = p1.json()["challenge_id"]
        vr = client.post(
            "/api/2fa/verify",
            json={"challenge_id": cid, "code": "123456"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert vr.status_code == 200
        done = client.post(
            f"/api/registration/sessions/{sid}/interaction/complete",
            json={
                "screen_id": str(meta["screen_ix"].id),
                "interaction_type": "phone_verification_sms",
                "challenge_id": cid,
                "verified": True,
            },
        )
        assert done.status_code == 200
        nx = client.post(f"/api/registration/sessions/{sid}/next")
        assert nx.status_code == 409  # no third screen

        session_row = client.get(f"/api/registration/sessions/{sid}/screen")
        # session may 404 if at end — check session data via DB
        rows = db.query(RegistrationSessionData).filter(
            RegistrationSessionData.session_id == uuid.UUID(sid),
            RegistrationSessionData.field_slug == "phone_verified",
        ).all()
        assert len(rows) == 1
        assert rows[0].value_json is True

        comp = client.post(f"/api/registration/sessions/{sid}/complete")
        assert comp.status_code == 200
        pid = comp.json()["person_id"]
        person = db.query(Person).filter(Person.id == uuid.UUID(pid)).first()
        assert person is not None
        pj = person.profile_json or {}
        assert pj.get("compliance", {}).get("phone_verified") is True
        assert pj.get("collected", {}).get("phone_number") == "+33612345678"

    def test_execution_events_include_interaction(self, client: TestClient, db: Session):
        meta = _seed_phone_then_interaction_flow(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "IX_PHONE"})
        sid = start.json()["session_id"]
        client.post(
            f"/api/registration/sessions/{sid}/submit",
            json={"answers": {"phone_number": "+33612345678"}},
        )
        with mock.patch(
            "services.security.two_factor_service.new_plaintext_sms_otp",
            return_value="123456",
        ):
            client.post(f"/api/registration/sessions/{sid}/interaction/prepare")
        ev = client.get(f"/api/admin/registration/sessions/{sid}/execution-events")
        types = [e["event_type"] for e in ev.json()["events"]]
        assert RegistrationEventType.INTERACTION_PREPARED in types

    def test_execution_events_include_resend(self, client: TestClient, db: Session):
        meta = _seed_phone_then_interaction_flow(db)
        start = client.post("/api/registration/sessions/start", json={"jurisdiction": "IX_PHONE"})
        sid = start.json()["session_id"]
        client.post(
            f"/api/registration/sessions/{sid}/submit",
            json={"answers": {"phone_number": "+33612345678"}},
        )
        with mock.patch(
            "services.security.two_factor_service.new_plaintext_sms_otp",
            side_effect=["111111", "222222"],
        ):
            client.post(f"/api/registration/sessions/{sid}/interaction/prepare")
            client.post(
                f"/api/registration/sessions/{sid}/interaction/resend",
                json={
                    "screen_id": str(meta["screen_ix"].id),
                    "interaction_type": "phone_verification_sms",
                },
            )
        ev = client.get(f"/api/admin/registration/sessions/{sid}/execution-events")
        types = [e["event_type"] for e in ev.json()["events"]]
        assert RegistrationEventType.INTERACTION_RESEND_REQUESTED in types
