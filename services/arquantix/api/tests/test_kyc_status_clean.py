"""Tests for KYC status cleanup — pending_review stays pending_review (Phase 1B)."""
import uuid

import pytest
from sqlalchemy.orm import Session

from database import Person
from services.client_identity.service import ClientIdentityService
from tests.conftest import make_linked_client


class TestPendingReviewMapping:
    """Verify the 1:1 mapping: pending_review on person → pending_review on client."""

    def test_sync_pending_review_stays_pending_review(self, db: Session):
        linked = make_linked_client(db, kyc_status="not_started")
        person = db.query(Person).filter(Person.client_id == linked.id).first()

        person, client = ClientIdentityService.update_person_kyc_status(
            db, person.id, "pending_review",
        )
        db.flush()

        assert person.kyc_status == "pending_review"
        assert client.kyc_status == "pending_review"

    def test_full_kyc_lifecycle_preserves_pending_review(self, db: Session):
        linked = make_linked_client(db, kyc_status="not_started")
        person = db.query(Person).filter(Person.client_id == linked.id).first()

        for status in ["in_progress", "pending_review", "approved"]:
            person, client = ClientIdentityService.update_person_kyc_status(
                db, person.id, status,
            )
            db.flush()
            assert person.kyc_status == status
            assert client.kyc_status == status

    def test_create_person_with_pending_review_syncs(self, db: Session):
        """If a person is created and then moved to pending_review, client mirrors it."""
        person, client = ClientIdentityService.create_person_and_client(
            db,
            email=f"kyc-{uuid.uuid4().hex[:6]}@test.com",
        )
        db.flush()

        person, client = ClientIdentityService.update_person_kyc_status(
            db, person.id, "pending_review",
        )
        db.flush()

        assert client.kyc_status == "pending_review"

    def test_link_syncs_pending_review(self, db: Session):
        """Creating a person+client then updating to pending_review preserves status."""
        person, client = ClientIdentityService.create_person_and_client(
            db,
            email=f"link-{uuid.uuid4().hex[:6]}@test.com",
        )
        db.flush()

        person, client = ClientIdentityService.update_person_kyc_status(
            db, person.id, "pending_review",
        )
        db.flush()

        assert person.kyc_status == "pending_review"
        assert client.kyc_status == "pending_review"


class TestAllKycStatuses:
    """Every valid status maps 1:1 without surprises."""

    @pytest.mark.parametrize("status", [
        "not_started", "in_progress", "pending_review", "approved", "rejected",
    ])
    def test_status_maps_directly(self, db: Session, status: str):
        linked = make_linked_client(db, kyc_status="not_started")
        person = db.query(Person).filter(Person.client_id == linked.id).first()

        person, client = ClientIdentityService.update_person_kyc_status(
            db, person.id, status,
        )
        db.flush()

        assert person.kyc_status == status
        assert client.kyc_status == status
