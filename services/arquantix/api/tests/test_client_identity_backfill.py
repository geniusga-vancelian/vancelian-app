"""Tests for the backfill logic — verifying migration 082 behavior.

Since pe_clients.person_id is now NOT NULL, these tests verify the
service-level creation logic that ensures no orphans exist, and that
the backfill invariants hold for newly created records.
"""
import uuid

import pytest
from sqlalchemy.orm import Session

from database import Person
from services.portfolio_engine.clients.models import Client
from services.client_identity.service import ClientIdentityService


@pytest.fixture
def svc() -> ClientIdentityService:
    return ClientIdentityService()


class TestBackfillInvariants:
    """Validates the invariants that the backfill migration established."""

    def test_every_client_has_a_linked_person(self, db: Session, svc: ClientIdentityService):
        """After creation via service, every client must have a person_id."""
        person, client = svc.create_person_and_client(
            db, email=f"bf-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()

        assert client.person_id is not None
        assert client.person_id == person.id

    def test_person_without_client_is_valid(self, db: Session):
        """A standalone person (compliance-only) is allowed."""
        standalone = Person(
            id=uuid.uuid4(),
            status="active",
            profile_json={},
            kyc_status="not_started",
        )
        db.add(standalone)
        db.flush()

        assert standalone.client_id is None

    def test_multiple_pairs_have_unique_links(self, db: Session, svc: ClientIdentityService):
        """Creating multiple person+client pairs produces unique 1:1 mappings."""
        pairs = []
        for i in range(3):
            p, c = svc.create_person_and_client(
                db, email=f"batch-{i}-{uuid.uuid4().hex[:8]}@test.com",
            )
            pairs.append((p, c))
        db.flush()

        person_ids = {p.id for p, _ in pairs}
        client_ids = {c.id for _, c in pairs}
        assert len(person_ids) == 3
        assert len(client_ids) == 3

        for person, client in pairs:
            assert person.client_id == client.id
            assert client.person_id == person.id

    def test_kyc_status_preserved_during_creation(self, db: Session, svc: ClientIdentityService):
        """Person and client start with the same KYC status after creation."""
        person, client = svc.create_person_and_client(
            db, email=f"kyc-pres-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()

        assert person.kyc_status == "not_started"
        assert client.kyc_status == "not_started"

    def test_kyc_status_sync_after_update(self, db: Session, svc: ClientIdentityService):
        """After KYC update on person, client mirrors the status."""
        person, client = svc.create_person_and_client(
            db, email=f"kyc-sync-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()

        for status in ["in_progress", "approved", "rejected", "not_started"]:
            svc.update_person_kyc_status(db, person.id, status)
            db.refresh(client)
            assert client.kyc_status == status

    def test_backfill_migration_result_integrity(self, db: Session):
        """Verify that all existing pe_clients in the DB have a valid person_id
        (this tests the result of migration 082 on real data)."""
        from sqlalchemy import text
        result = db.execute(
            text("SELECT COUNT(*) FROM public.pe_clients WHERE person_id IS NULL")
        ).scalar()
        assert result == 0, f"Found {result} pe_clients without person_id"

    def test_all_linked_persons_have_matching_client(self, db: Session):
        """Every person with a client_id should point to an existing pe_client."""
        from sqlalchemy import text
        result = db.execute(
            text("""
                SELECT COUNT(*) FROM public.persons p
                WHERE p.client_id IS NOT NULL
                AND NOT EXISTS (SELECT 1 FROM public.pe_clients c WHERE c.id = p.client_id)
            """)
        ).scalar()
        assert result == 0, f"Found {result} persons referencing non-existent clients"
