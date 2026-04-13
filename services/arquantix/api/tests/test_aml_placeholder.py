"""Tests for AML placeholder — explicit aml_status + ENABLE_AML_BLOCKING flag."""
import uuid

import pytest
from sqlalchemy.orm import Session

from database import Person
from services.compliance.eligibility_service import (
    EligibilityService,
    EligibilityResult,
    AML_STATUS_NOT_CHECKED,
    AML_STATUS_VERIFIED,
)
from services.portfolio_engine.provisioning.errors import ClientNotEligibleError
from tests.conftest import make_linked_client


def _make_person(db: Session, *, kyc_status: str = "approved") -> Person:
    person = Person(
        id=uuid.uuid4(),
        status="active",
        profile_json={},
        kyc_status=kyc_status,
    )
    db.add(person)
    db.flush()
    return person


class TestAmlStatusExplicit:

    def test_aml_status_is_not_checked_by_default(self, db: Session):
        person = _make_person(db)
        result = EligibilityService.evaluate_client_eligibility(db, person)

        assert result.aml_status == AML_STATUS_NOT_CHECKED
        assert result.aml_ok is False

    def test_eligible_when_aml_blocking_off(self, db: Session, monkeypatch):
        monkeypatch.setenv("ENABLE_AML_BLOCKING", "false")
        person = _make_person(db, kyc_status="approved")
        result = EligibilityService.evaluate_client_eligibility(db, person)

        assert result.eligible is True
        assert result.aml_ok is False
        assert result.aml_status == AML_STATUS_NOT_CHECKED

    def test_not_eligible_when_aml_blocking_on(self, db: Session, monkeypatch):
        monkeypatch.setenv("ENABLE_AML_BLOCKING", "true")
        person = _make_person(db, kyc_status="approved")
        result = EligibilityService.evaluate_client_eligibility(db, person)

        assert result.eligible is False
        assert result.aml_ok is False
        assert any("aml_status" in r for r in result.reasons)


class TestAmlWithProductGating:

    def test_require_eligible_passes_when_aml_non_blocking(self, db: Session, monkeypatch):
        monkeypatch.setenv("ENABLE_AML_BLOCKING", "false")
        linked = make_linked_client(db, kyc_status="approved")

        result = EligibilityService.require_eligible_by_client_id(db, linked.id)
        assert result.eligible is True

    def test_require_eligible_fails_when_aml_blocking(self, db: Session, monkeypatch):
        monkeypatch.setenv("ENABLE_AML_BLOCKING", "true")
        linked = make_linked_client(db, kyc_status="approved")

        with pytest.raises(ClientNotEligibleError):
            EligibilityService.require_eligible_by_client_id(db, linked.id)


class TestAmlApiResponse:

    def test_identity_endpoint_includes_aml_status(self, client, db: Session):
        from tests.conftest import make_admin_headers
        headers = make_admin_headers(db)
        linked = make_linked_client(db, kyc_status="approved")
        person = db.query(Person).filter(Person.client_id == linked.id).first()

        resp = client.get(f"/api/persons/{person.id}/identity", headers=headers)
        assert resp.status_code == 200
        data = resp.json()

        assert "eligibility" in data
        elig = data["eligibility"]
        assert "aml_status" in elig
        assert elig["aml_status"] == "not_checked"
        assert elig["aml_ok"] is False
