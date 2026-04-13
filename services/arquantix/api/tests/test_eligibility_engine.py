"""Tests for the centralized EligibilityService (Phase 1B)."""
import uuid
from typing import Optional, Dict, Any

import pytest
from sqlalchemy.orm import Session

from database import Person, AuditEvent
from services.compliance.eligibility_service import EligibilityService, EligibilityResult


def _make_person(db: Session, *, kyc_status: str = "approved", profile_json: Optional[dict] = None) -> Person:
    person = Person(
        id=uuid.uuid4(),
        status="active",
        profile_json=profile_json or {},
        kyc_status=kyc_status,
    )
    db.add(person)
    db.flush()
    return person


class TestEligibilityBasic:

    def test_approved_person_is_eligible(self, db: Session):
        person = _make_person(db, kyc_status="approved")
        result = EligibilityService.evaluate_client_eligibility(db, person)

        assert result.eligible is True
        assert result.kyc_ok is True
        assert result.aml_ok is False  # not_checked — non-blocking by default
        assert result.aml_status == "not_checked"
        assert result.risk_ok is True
        assert result.reasons == []

    def test_not_started_person_is_not_eligible(self, db: Session):
        person = _make_person(db, kyc_status="not_started")
        result = EligibilityService.evaluate_client_eligibility(db, person)

        assert result.eligible is False
        assert result.kyc_ok is False
        assert "kyc_status" in result.reasons[0]

    def test_in_progress_person_is_not_eligible(self, db: Session):
        person = _make_person(db, kyc_status="in_progress")
        result = EligibilityService.evaluate_client_eligibility(db, person)

        assert result.eligible is False
        assert result.kyc_ok is False

    def test_pending_review_person_is_not_eligible(self, db: Session):
        person = _make_person(db, kyc_status="pending_review")
        result = EligibilityService.evaluate_client_eligibility(db, person)

        assert result.eligible is False
        assert result.kyc_ok is False

    def test_rejected_person_is_not_eligible(self, db: Session):
        person = _make_person(db, kyc_status="rejected")
        result = EligibilityService.evaluate_client_eligibility(db, person)

        assert result.eligible is False
        assert result.kyc_ok is False


class TestEligibilityRisk:

    def test_high_risk_tier_blocks_eligibility(self, db: Session):
        person = _make_person(
            db,
            kyc_status="approved",
            profile_json={"risk-tier-current": {"value": "high"}},
        )
        result = EligibilityService.evaluate_client_eligibility(db, person)

        assert result.eligible is False
        assert result.kyc_ok is True
        assert result.risk_ok is False
        assert any("risk_tier" in r for r in result.reasons)

    def test_medium_risk_tier_is_ok(self, db: Session):
        person = _make_person(
            db,
            kyc_status="approved",
            profile_json={"risk-tier-current": {"value": "medium"}},
        )
        result = EligibilityService.evaluate_client_eligibility(db, person)

        assert result.eligible is True
        assert result.risk_ok is True

    def test_no_risk_tier_is_ok(self, db: Session):
        person = _make_person(db, kyc_status="approved", profile_json={})
        result = EligibilityService.evaluate_client_eligibility(db, person)

        assert result.eligible is True
        assert result.risk_ok is True

    def test_risk_tier_string_format(self, db: Session):
        person = _make_person(
            db,
            kyc_status="approved",
            profile_json={"risk-tier-current": "high"},
        )
        result = EligibilityService.evaluate_client_eligibility(db, person)

        assert result.eligible is False
        assert result.risk_ok is False


class TestEligibilityCombined:

    def test_kyc_not_approved_and_high_risk(self, db: Session):
        person = _make_person(
            db,
            kyc_status="in_progress",
            profile_json={"risk-tier-current": {"value": "high"}},
        )
        result = EligibilityService.evaluate_client_eligibility(db, person)

        assert result.eligible is False
        assert result.kyc_ok is False
        assert result.risk_ok is False
        assert len(result.reasons) == 2


class TestEligibilityByPersonId:

    def test_person_not_found(self, db: Session):
        result = EligibilityService.evaluate_by_person_id(db, uuid.uuid4())

        assert result.eligible is False
        assert "person_not_found" in result.reasons

    def test_person_found_and_eligible(self, db: Session):
        person = _make_person(db, kyc_status="approved")
        result = EligibilityService.evaluate_by_person_id(db, person.id)

        assert result.eligible is True


class TestEligibilityAudit:

    def test_audit_event_created(self, db: Session):
        person = _make_person(db, kyc_status="approved")

        count_before = db.query(AuditEvent).filter(
            AuditEvent.event_type == "CLIENT_ELIGIBILITY_EVALUATED",
            AuditEvent.person_id == person.id,
        ).count()

        EligibilityService.evaluate_client_eligibility(db, person)

        count_after = db.query(AuditEvent).filter(
            AuditEvent.event_type == "CLIENT_ELIGIBILITY_EVALUATED",
            AuditEvent.person_id == person.id,
        ).count()

        assert count_after == count_before + 1

    def test_audit_event_payload_contains_result(self, db: Session):
        person = _make_person(db, kyc_status="approved")
        EligibilityService.evaluate_client_eligibility(db, person)

        event = db.query(AuditEvent).filter(
            AuditEvent.event_type == "CLIENT_ELIGIBILITY_EVALUATED",
            AuditEvent.person_id == person.id,
        ).order_by(AuditEvent.created_at.desc()).first()

        assert event is not None
        assert event.payload["eligible"] is True
        assert event.payload["kyc_ok"] is True
