"""Tests for KYC status synchronization — persons.kyc_status -> pe_clients.kyc_status."""
import uuid

import pytest
from sqlalchemy.orm import Session

from database import Person, AuditEvent
from services.portfolio_engine.clients.models import Client
from services.client_identity.service import ClientIdentityService


@pytest.fixture
def svc() -> ClientIdentityService:
    return ClientIdentityService()


@pytest.fixture
def linked_pair(db: Session, svc: ClientIdentityService) -> tuple[Person, Client]:
    """A person+client pair already linked."""
    person, client = svc.create_person_and_client(
        db,
        email=f"sync-{uuid.uuid4().hex[:8]}@test.com",
        jurisdiction="EU",
    )
    db.flush()
    return person, client


class TestKycStatusSyncFlow:
    """Tests the full lifecycle of KYC status changes and their sync."""

    def test_full_kyc_lifecycle(self, db: Session, svc: ClientIdentityService, linked_pair):
        person, client = linked_pair

        transitions = [
            ("in_progress", "in_progress"),
            ("pending_review", "pending_review"),
            ("approved", "approved"),
            ("rejected", "rejected"),
            ("not_started", "not_started"),
        ]
        for person_status, expected_client_status in transitions:
            svc.update_person_kyc_status(db, person.id, person_status)
            db.refresh(client)
            assert person.kyc_status == person_status
            assert client.kyc_status == expected_client_status, (
                f"After setting person to '{person_status}', "
                f"client should be '{expected_client_status}' but got '{client.kyc_status}'"
            )

    def test_sync_creates_audit_events(self, db: Session, svc: ClientIdentityService, linked_pair):
        person, _ = linked_pair

        svc.update_person_kyc_status(db, person.id, "approved")

        events = (
            db.query(AuditEvent)
            .filter(
                AuditEvent.person_id == person.id,
                AuditEvent.event_type == "KYC_STATUS_SYNCED",
            )
            .all()
        )
        assert len(events) >= 1
        latest = events[-1]
        assert latest.payload["new_client_kyc_status"] == "approved"

    def test_no_sync_when_status_unchanged(self, db: Session, svc: ClientIdentityService, linked_pair):
        person, client = linked_pair

        svc.update_person_kyc_status(db, person.id, "approved")
        # Count sync events
        count_before = (
            db.query(AuditEvent)
            .filter(AuditEvent.person_id == person.id, AuditEvent.event_type == "KYC_STATUS_SYNCED")
            .count()
        )

        # Set to same status again
        svc.update_person_kyc_status(db, person.id, "approved")
        count_after = (
            db.query(AuditEvent)
            .filter(AuditEvent.person_id == person.id, AuditEvent.event_type == "KYC_STATUS_SYNCED")
            .count()
        )
        # No new sync event should be created
        assert count_after == count_before

    def test_sync_standalone_person_no_error(self, db: Session, svc: ClientIdentityService):
        """A person without a linked client should not fail during sync."""
        person = Person(
            id=uuid.uuid4(),
            status="active",
            profile_json={},
            kyc_status="not_started",
        )
        db.add(person)
        db.flush()

        result = svc.sync_client_kyc_status_from_person(db, person)
        assert result is None
