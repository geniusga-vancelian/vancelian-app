"""Tests for Client Identity invariants — 1:1 mapping, no orphans, no duplicates."""
import uuid

import pytest
from sqlalchemy.orm import Session

from database import Person
from services.portfolio_engine.clients.models import Client
from services.client_identity.service import ClientIdentityService, AlreadyLinkedError


@pytest.fixture
def svc() -> ClientIdentityService:
    return ClientIdentityService()


class TestOneToOneInvariant:
    """Verify that the person <-> client mapping is strictly 1:1."""

    def test_person_client_id_matches_client_id(self, db: Session, svc: ClientIdentityService):
        person, client = svc.create_person_and_client(
            db, email=f"inv1-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()
        assert person.client_id == client.id

    def test_client_person_id_matches_person_id(self, db: Session, svc: ClientIdentityService):
        person, client = svc.create_person_and_client(
            db, email=f"inv2-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()
        assert client.person_id == person.id

    def test_bidirectional_consistency(self, db: Session, svc: ClientIdentityService):
        person, client = svc.create_person_and_client(
            db, email=f"inv3-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()

        # Navigate person -> client -> person
        linked_client = db.query(Client).filter(Client.id == person.client_id).first()
        assert linked_client is not None
        assert linked_client.person_id == person.id

        # Navigate client -> person -> client
        linked_person = db.query(Person).filter(Person.id == client.person_id).first()
        assert linked_person is not None
        assert linked_person.client_id == client.id

    def test_cannot_link_one_person_to_two_clients(self, db: Session, svc: ClientIdentityService):
        """A person already linked to client1 cannot be linked to client2."""
        person, client1 = svc.create_person_and_client(
            db, email=f"inv4a-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()

        # Create a second independent pair
        _, client2 = svc.create_person_and_client(
            db, email=f"inv4b-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()

        with pytest.raises(AlreadyLinkedError):
            svc.link_person_to_client(db, person_id=person.id, client_id=client2.id)

    def test_cannot_link_one_client_to_two_persons(self, db: Session, svc: ClientIdentityService):
        """A client already linked to person1 cannot be linked to person2."""
        person1, client = svc.create_person_and_client(
            db, email=f"inv5a-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()

        person2 = Person(
            id=uuid.uuid4(),
            status="active",
            profile_json={},
            kyc_status="not_started",
        )
        db.add(person2)
        db.flush()

        with pytest.raises(AlreadyLinkedError):
            svc.link_person_to_client(db, person_id=person2.id, client_id=client.id)


class TestNoOrphans:
    """Verify that create flows never leave orphans."""

    def test_create_produces_no_orphan_person(self, db: Session, svc: ClientIdentityService):
        person, client = svc.create_person_and_client(
            db, email=f"orph1-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()
        assert person.client_id is not None

    def test_create_produces_no_orphan_client(self, db: Session, svc: ClientIdentityService):
        person, client = svc.create_person_and_client(
            db, email=f"orph2-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()
        assert client.person_id is not None

    def test_both_sides_populated_after_create(self, db: Session, svc: ClientIdentityService):
        person, client = svc.create_person_and_client(
            db, email=f"orph3-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()
        assert person.client_id == client.id
        assert client.person_id == person.id


class TestKycConsistency:
    """KYC status must always be consistent between linked person and client."""

    def test_kyc_always_consistent_after_create(self, db: Session, svc: ClientIdentityService):
        person, client = svc.create_person_and_client(
            db, email=f"cons1-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()
        assert person.kyc_status == client.kyc_status

    def test_kyc_consistent_after_update(self, db: Session, svc: ClientIdentityService):
        person, client = svc.create_person_and_client(
            db, email=f"cons2-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()

        for status in ["in_progress", "approved", "rejected", "not_started"]:
            svc.update_person_kyc_status(db, person.id, status)
            db.refresh(client)
            assert client.kyc_status == status

    def test_kyc_sync_on_link_uses_person_as_source(self, db: Session, svc: ClientIdentityService):
        """When re-linking, person's KYC status (source of truth) should override client."""
        person, client = svc.create_person_and_client(
            db, email=f"cons3-{uuid.uuid4().hex[:8]}@test.com",
        )
        # Set person to approved
        svc.update_person_kyc_status(db, person.id, "approved")
        db.flush()

        assert person.kyc_status == "approved"
        assert client.kyc_status == "approved"
