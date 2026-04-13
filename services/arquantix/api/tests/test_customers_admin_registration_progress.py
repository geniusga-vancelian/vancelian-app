"""Tests progression canonique Customer 360."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.orm import Session

from database import (
    Person,
    RegistrationJurisdiction,
    RegistrationFlow,
    RegistrationFlowStep,
    RegistrationSession,
    TwoFactorChallenge,
)
from services.customers_admin.registration_progress import compute_canonical_registration_progress
from services.customers_admin.schemas import RegistrationMacroStage
from services.portfolio_engine.clients.models import Client as PeClient


def _person(db: Session, **kwargs) -> Person:
    p = Person(
        id=uuid.uuid4(),
        status="active",
        jurisdiction=kwargs.get("jurisdiction", "EU"),
        profile_json=kwargs.get("profile_json", {}),
        kyc_status=kwargs.get("kyc_status", "not_started"),
    )
    db.add(p)
    db.flush()
    return p


def _pe_client(db: Session, person_id, **kwargs) -> PeClient:
    c = PeClient(
        id=uuid.uuid4(),
        email=kwargs.get("email", f"c_{uuid.uuid4().hex[:6]}@t.com"),
        status=kwargs.get("status", "active"),
        kyc_status=kwargs.get("kyc_status", "approved"),
        person_id=person_id,
    )
    db.add(c)
    db.flush()
    return c


@pytest.fixture()
def reg_flow_minimal(db: Session):
    """Flow + step identity pour session en cours."""
    j = RegistrationJurisdiction(
        id=uuid.uuid4(),
        code="ZZ_TEST_REG",
        name="Test",
        entity_name="T",
        default_language="en",
        is_active=True,
    )
    db.add(j)
    db.flush()
    flow = RegistrationFlow(
        id=uuid.uuid4(),
        jurisdiction_id=j.id,
        name="Test flow",
        version=1,
        status="active",
        entrypoint_type="individual",
        published_at=datetime.now(timezone.utc),
        published_by="test",
    )
    db.add(flow)
    db.flush()
    step = RegistrationFlowStep(
        id=uuid.uuid4(),
        flow_id=flow.id,
        step_key="identity",
        title="Identity",
        position=0,
        is_optional=False,
        is_blocking=True,
    )
    db.add(step)
    db.flush()
    return flow, step


def test_phone_only_person(db: Session):
    p = _person(
        db,
        profile_json={"collected": {"phone_e164": "+33123456789"}},
    )
    r = compute_canonical_registration_progress(db, p, None)
    assert r.stage == RegistrationMacroStage.PHONE_STARTED
    assert r.foundation.mobile_collected is True
    assert r.registration.registration_completed is False


def test_mobile_otp_verified(db: Session):
    p = _person(
        db,
        profile_json={"collected": {"phone_e164": "+33123456789"}},
    )
    db.add(
        TwoFactorChallenge(
            id=uuid.uuid4(),
            person_id=p.id,
            channel="sms",
            target="+33123456789",
            code_hash="x",
            expires_at=datetime.now(timezone.utc),
            attempts=0,
            status="verified",
            purpose="login",
        )
    )
    db.flush()
    r = compute_canonical_registration_progress(db, p, None)
    assert r.foundation.mobile_verified is True
    assert r.stage == RegistrationMacroStage.ACCOUNT_SECURED
    assert r.foundation.passcode_created is None


def test_registration_in_progress(db: Session, reg_flow_minimal):
    flow, step = reg_flow_minimal
    p = _person(
        db,
        profile_json={"collected": {"phone_e164": "+33123456789"}},
    )
    j = db.query(RegistrationJurisdiction).filter(RegistrationJurisdiction.id == flow.jurisdiction_id).first()
    sess = RegistrationSession(
        id=uuid.uuid4(),
        jurisdiction_id=j.id,
        flow_id=flow.id,
        flow_version=1,
        person_id=p.id,
        status="in_progress",
        current_step_id=step.id,
        progress_percent=10,
    )
    db.add(sess)
    db.flush()
    r = compute_canonical_registration_progress(db, p, None)
    assert r.stage == RegistrationMacroStage.REGISTRATION_IN_PROGRESS
    assert r.session_snapshot is not None
    assert r.session_snapshot.flow_version == 1


def test_registration_completed_triggers_kyc_bucket(db: Session, reg_flow_minimal):
    """Session registration terminée + KYC non validé → macro KYC_PENDING (pas un stade « completed » séparé)."""
    flow, step = reg_flow_minimal
    p = _person(
        db,
        profile_json={"collected": {"phone_e164": "+33"}},
    )
    j = db.query(RegistrationJurisdiction).filter(RegistrationJurisdiction.id == flow.jurisdiction_id).first()
    sess = RegistrationSession(
        id=uuid.uuid4(),
        jurisdiction_id=j.id,
        flow_id=flow.id,
        flow_version=1,
        person_id=p.id,
        status="completed",
        current_step_id=step.id,
        progress_percent=100,
    )
    db.add(sess)
    db.flush()
    r = compute_canonical_registration_progress(db, p, None)
    assert r.registration.registration_completed is True
    assert r.lifecycle.kyc_pending is True
    assert r.stage == RegistrationMacroStage.KYC_PENDING


def test_kyc_pending_requires_registration_completed(db: Session, reg_flow_minimal):
    p = _person(db, kyc_status="in_progress", profile_json={"collected": {}})
    r = compute_canonical_registration_progress(db, p, None)
    assert r.lifecycle.kyc_pending is False

    flow, step = reg_flow_minimal
    j = db.query(RegistrationJurisdiction).filter(RegistrationJurisdiction.id == flow.jurisdiction_id).first()
    sess = RegistrationSession(
        id=uuid.uuid4(),
        jurisdiction_id=j.id,
        flow_id=flow.id,
        flow_version=1,
        person_id=p.id,
        status="completed",
        current_step_id=step.id,
        progress_percent=100,
    )
    db.add(sess)
    db.flush()
    r2 = compute_canonical_registration_progress(db, p, None)
    assert r2.lifecycle.kyc_pending is True
    assert r2.stage == RegistrationMacroStage.KYC_PENDING


def test_passcode_server_ack_optional(db: Session):
    p = _person(
        db,
        profile_json={
            "collected": {"phone_e164": "+33"},
            "security": {"local_passcode_registered_at": "2026-01-01T00:00:00Z"},
        },
    )
    r = compute_canonical_registration_progress(db, p, None)
    assert r.foundation.passcode_created is True


def test_kyc_completed(db: Session):
    p = _person(db, kyc_status="approved", profile_json={"collected": {}})
    r = compute_canonical_registration_progress(db, p, None)
    assert r.lifecycle.kyc_completed is True
    assert r.stage == RegistrationMacroStage.KYC_COMPLETED


def test_active_client(db: Session):
    p = _person(db, kyc_status="approved", profile_json={"collected": {}})
    _pe_client(db, p.id, status="active")
    db.flush()
    p2 = db.query(Person).filter(Person.id == p.id).first()
    pe = db.query(PeClient).filter(PeClient.person_id == p.id).first()
    r = compute_canonical_registration_progress(db, p2, pe)
    assert r.lifecycle.active_client is True
    assert r.stage == RegistrationMacroStage.ACTIVE_CLIENT


def test_no_session_snapshot(db: Session):
    p = _person(db, profile_json={"collected": {}})
    r = compute_canonical_registration_progress(db, p, None)
    assert r.session_snapshot is None


def test_legacy_partial_profile_fields(db: Session):
    p = _person(
        db,
        profile_json={
            "collected": {
                "first_name": "A",
                "last_name": "B",
                "phone_e164": "+1",
            }
        },
    )
    r = compute_canonical_registration_progress(db, p, None)
    assert "registration:identity" in r.completed_steps or r.registration.identity_completed


def test_multi_session_old_completed_new_in_progress(db: Session, reg_flow_minimal):
    """Une session completed historique + nouvelle session in_progress : registration_completed reste vrai."""
    flow, step = reg_flow_minimal
    p = _person(db, profile_json={"collected": {"phone_e164": "+33"}})
    j = db.query(RegistrationJurisdiction).filter(RegistrationJurisdiction.id == flow.jurisdiction_id).first()
    t_old = datetime.now(timezone.utc) - timedelta(hours=3)
    t_new = datetime.now(timezone.utc)
    s_done = RegistrationSession(
        id=uuid.uuid4(),
        jurisdiction_id=j.id,
        flow_id=flow.id,
        flow_version=1,
        person_id=p.id,
        status="completed",
        current_step_id=step.id,
        progress_percent=100,
        updated_at=t_old,
    )
    s_new = RegistrationSession(
        id=uuid.uuid4(),
        jurisdiction_id=j.id,
        flow_id=flow.id,
        flow_version=1,
        person_id=p.id,
        status="in_progress",
        current_step_id=step.id,
        progress_percent=5,
        updated_at=t_new,
    )
    db.add(s_done)
    db.add(s_new)
    db.flush()
    r = compute_canonical_registration_progress(db, p, None)
    assert r.registration.registration_completed is True
    assert r.registration.identity_completed is True
    assert r.session_snapshot is not None
    assert r.session_snapshot.status == "in_progress"
    assert r.session_snapshot.has_older_completed_session is True
    assert "has_older_completed_vs_latest_runtime=True" in r.source_notes


def test_profile_fills_step_when_session_not_marked(db: Session, reg_flow_minimal):
    """Sans session completed : le profil persisté complète le jalon si les données sont présentes."""
    flow, step = reg_flow_minimal
    p = _person(
        db,
        profile_json={
            "collected": {
                "phone_e164": "+1",
                "first_name": "Jane",
                "last_name": "Doe",
            }
        },
    )
    j = db.query(RegistrationJurisdiction).filter(RegistrationJurisdiction.id == flow.jurisdiction_id).first()
    sess = RegistrationSession(
        id=uuid.uuid4(),
        jurisdiction_id=j.id,
        flow_id=flow.id,
        flow_version=1,
        person_id=p.id,
        status="in_progress",
        current_step_id=step.id,
        progress_percent=5,
    )
    db.add(sess)
    db.flush()
    r = compute_canonical_registration_progress(db, p, None)
    assert r.registration.identity_completed is True
    assert r.stage == RegistrationMacroStage.REGISTRATION_IN_PROGRESS
