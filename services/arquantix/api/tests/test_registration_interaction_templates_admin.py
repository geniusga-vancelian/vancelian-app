"""Admin interaction templates registry + screen validation."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import RegistrationFlow, RegistrationFlowStep, RegistrationJurisdiction, RegistrationStepScreen


def _seed_minimal_flow(db: Session) -> dict:
    j = RegistrationJurisdiction(
        id=uuid.uuid4(), code=f"Z{uuid.uuid4().hex[:6]}".upper(), name="T", is_active=True,
    )
    db.add(j)
    db.flush()
    flow = RegistrationFlow(
        id=uuid.uuid4(), jurisdiction_id=j.id, name="TF", version=1, status="draft",
    )
    db.add(flow)
    db.flush()
    step = RegistrationFlowStep(
        id=uuid.uuid4(), flow_id=flow.id, step_key="s1", title="S", position=0,
        is_blocking=True, is_optional=False,
    )
    db.add(step)
    db.flush()
    return {"jurisdiction": j, "flow": flow, "step": step}


def test_list_interaction_templates_includes_sms_and_email_skeleton(client: TestClient):
    r = client.get("/api/admin/registration/interaction-templates")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    keys = {t["template_key"] for t in data}
    assert "confirmation_code_sms" in keys
    assert "confirmation_code_email" in keys
    sms = next(t for t in data if t["template_key"] == "confirmation_code_sms")
    assert sms["selectable"] is True
    assert sms["interaction_type"] == "phone_verification_sms"
    assert sms["default_interaction_config"]["source_field_slug"] == "phone_number"
    email = next(t for t in data if t["template_key"] == "confirmation_code_email")
    assert email["selectable"] is False


def test_create_interaction_screen_with_full_config_ok(client: TestClient, db: Session):
    meta = _seed_minimal_flow(db)
    r = client.post(
        f"/api/admin/registration/steps/{meta['step'].id}/screens",
        json={
            "screen_key": "sms1",
            "title": "Confirm your mobile number",
            "subtitle": "Enter the code",
            "position": 0,
            "layout_type": "form",
            "button_label": "Continue",
            "screen_type": "interaction",
            "interaction_type": "phone_verification_sms",
            "interaction_config_json": {
                "source_field_slug": "phone_number",
                "verified_flag_slug": "phone_verified",
                "purpose": "verify_phone",
            },
        },
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["screen_type"] == "interaction"
    assert body["interaction_template_key"] == "confirmation_code_sms"
    assert body["interaction_template_display_name"] == "Confirmation code (SMS)"


def test_create_interaction_screen_missing_config_rejected(client: TestClient, db: Session):
    meta = _seed_minimal_flow(db)
    r = client.post(
        f"/api/admin/registration/steps/{meta['step'].id}/screens",
        json={
            "screen_key": "bad",
            "title": "X",
            "position": 0,
            "screen_type": "interaction",
            "interaction_type": "phone_verification_sms",
            "interaction_config_json": {"source_field_slug": "phone_number"},
        },
    )
    assert r.status_code == 422
    assert "verified_flag_slug" in r.json()["detail"].lower() or "purpose" in r.json()["detail"].lower()


def test_create_interaction_unsupported_type_rejected(client: TestClient, db: Session):
    meta = _seed_minimal_flow(db)
    r = client.post(
        f"/api/admin/registration/steps/{meta['step'].id}/screens",
        json={
            "screen_key": "em",
            "title": "Email",
            "position": 0,
            "screen_type": "interaction",
            "interaction_type": "email_verification_otp",
            "interaction_config_json": {
                "source_field_slug": "email",
                "verified_flag_slug": "email_verified",
                "purpose": "verify_email",
            },
        },
    )
    assert r.status_code == 422
    assert "unsupported" in r.json()["detail"].lower() or "only" in r.json()["detail"].lower()


def test_create_form_with_interaction_fields_rejected(client: TestClient, db: Session):
    meta = _seed_minimal_flow(db)
    r = client.post(
        f"/api/admin/registration/steps/{meta['step'].id}/screens",
        json={
            "screen_key": "bad2",
            "title": "X",
            "position": 0,
            "screen_type": "form",
            "interaction_type": "phone_verification_sms",
        },
    )
    assert r.status_code == 422


def test_legacy_screen_infer_template_without_stored_key(client: TestClient, db: Session):
    meta = _seed_minimal_flow(db)
    scr = RegistrationStepScreen(
        id=uuid.uuid4(),
        step_id=meta["step"].id,
        screen_key="legacy_ix",
        title="Legacy",
        position=0,
        layout_type="form",
        screen_type="interaction",
        interaction_type="phone_verification_sms",
        interaction_config_json={
            "source_field_slug": "phone_number",
            "verified_flag_slug": "phone_verified",
            "purpose": "verify_phone",
        },
    )
    db.add(scr)
    db.commit()
    r = client.get(f"/api/admin/registration/steps/{meta['step'].id}/screens")
    assert r.status_code == 200
    row = next(x for x in r.json() if x["screen_key"] == "legacy_ix")
    assert row["interaction_template_key"] == "confirmation_code_sms"


def test_patch_screen_to_form_clears_interaction(client: TestClient, db: Session):
    meta = _seed_minimal_flow(db)
    c = client.post(
        f"/api/admin/registration/steps/{meta['step'].id}/screens",
        json={
            "screen_key": "ix",
            "title": "T",
            "position": 0,
            "screen_type": "interaction",
            "interaction_type": "phone_verification_sms",
            "interaction_config_json": {
                "source_field_slug": "phone_number",
                "verified_flag_slug": "phone_verified",
                "purpose": "verify_phone",
            },
        },
    )
    sid = c.json()["id"]
    u = client.patch(
        f"/api/admin/registration/screens/{sid}",
        json={"screen_type": "form"},
    )
    assert u.status_code == 200
    assert u.json()["screen_type"] == "form"
    assert u.json()["interaction_type"] is None
    assert u.json()["interaction_config_json"] is None
