"""Tests for ClientIdentityService — create, link, sync, read, eligibility."""
import uuid

import pytest
from sqlalchemy.orm import Session

from database import Person
from services.portfolio_engine.clients.models import Client
from services.client_identity.service import (
    ClientIdentityService,
    PersonNotFoundError,
    ClientNotFoundError,
    AlreadyLinkedError,
    InvalidKycStatusError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def svc() -> ClientIdentityService:
    return ClientIdentityService()


@pytest.fixture
def standalone_person(db: Session) -> Person:
    """A person with no linked client."""
    p = Person(
        id=uuid.uuid4(),
        status="active",
        jurisdiction="EU",
        profile_json={},
        kyc_status="not_started",
    )
    db.add(p)
    db.flush()
    return p


def _make_unlinked_client_and_person(db: Session, *, kyc_status: str = "approved") -> tuple[Client, Person]:
    """Create a person+client pair linked at DB level but logically 'independent' for test purposes."""
    p = Person(
        id=uuid.uuid4(), status="active", profile_json={}, kyc_status=kyc_status,
    )
    db.add(p)
    db.flush()
    c = Client(
        id=uuid.uuid4(),
        email=f"standalone-{uuid.uuid4().hex[:8]}@test.com",
        status="active",
        kyc_status=kyc_status,
        person_id=p.id,
    )
    db.add(c)
    db.flush()
    return c, p


# ---------------------------------------------------------------------------
# create_person_and_client
# ---------------------------------------------------------------------------

class TestCreatePersonAndClient:

    def test_creates_both_and_links(self, db: Session, svc: ClientIdentityService):
        person, client = svc.create_person_and_client(
            db,
            email="test-create@example.com",
            jurisdiction="EU",
        )
        assert person.id is not None
        assert client.id is not None
        assert person.client_id == client.id
        assert client.person_id == person.id
        assert person.kyc_status == "not_started"
        assert client.kyc_status == "not_started"
        assert person.jurisdiction == "EU"

    def test_duplicate_email_raises(self, db: Session, svc: ClientIdentityService):
        svc.create_person_and_client(db, email="dup@test.com")
        db.flush()
        with pytest.raises(Exception):
            svc.create_person_and_client(db, email="dup@test.com")


# ---------------------------------------------------------------------------
# link_person_to_client
# ---------------------------------------------------------------------------

class TestLinkPersonToClient:

    def test_links_existing_pair(self, db: Session, svc: ClientIdentityService):
        """Link a standalone person to a client that already has a person (re-link scenario)."""
        # Create a person and a client that is already linked to a different person
        target_person = Person(
            id=uuid.uuid4(), status="active", profile_json={}, kyc_status="approved",
        )
        db.add(target_person)
        db.flush()

        # Create client via service (already linked to another person)
        _, client = svc.create_person_and_client(
            db, email=f"link-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()

        # This should raise because client is already linked
        with pytest.raises(AlreadyLinkedError):
            svc.link_person_to_client(db, person_id=target_person.id, client_id=client.id)

    def test_raises_if_person_not_found(self, db: Session, svc: ClientIdentityService):
        _, client = svc.create_person_and_client(
            db, email=f"pnf-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()

        with pytest.raises(PersonNotFoundError):
            svc.link_person_to_client(db, person_id=uuid.uuid4(), client_id=client.id)

    def test_raises_if_client_not_found(self, db: Session, svc: ClientIdentityService, standalone_person: Person):
        with pytest.raises(ClientNotFoundError):
            svc.link_person_to_client(db, person_id=standalone_person.id, client_id=uuid.uuid4())

    def test_idempotent_if_same_pair(self, db: Session, svc: ClientIdentityService):
        """Re-linking the same pair should not raise."""
        person, client = svc.create_person_and_client(
            db, email=f"idem-{uuid.uuid4().hex[:8]}@test.com",
        )
        db.flush()

        # Re-linking the same pair should succeed
        p2, c2 = svc.link_person_to_client(db, person_id=person.id, client_id=client.id)
        assert p2.client_id == client.id
        assert c2.person_id == person.id


# ---------------------------------------------------------------------------
# update_person_kyc_status + sync
# ---------------------------------------------------------------------------

class TestKycStatusSync:

    def test_update_and_sync(self, db: Session, svc: ClientIdentityService):
        person, client = svc.create_person_and_client(db, email="sync-test@test.com")
        db.flush()

        assert person.kyc_status == "not_started"
        assert client.kyc_status == "not_started"

        svc.update_person_kyc_status(db, person.id, "in_progress")
        assert person.kyc_status == "in_progress"
        assert client.kyc_status == "in_progress"

        svc.update_person_kyc_status(db, person.id, "approved")
        assert person.kyc_status == "approved"
        assert client.kyc_status == "approved"

    def test_pending_review_maps_to_pending_review(self, db: Session, svc: ClientIdentityService):
        person, client = svc.create_person_and_client(db, email="pr-test@test.com")
        db.flush()

        svc.update_person_kyc_status(db, person.id, "pending_review")
        assert person.kyc_status == "pending_review"
        assert client.kyc_status == "pending_review"

    def test_invalid_status_raises(self, db: Session, svc: ClientIdentityService):
        person, _ = svc.create_person_and_client(db, email="inv-test@test.com")
        db.flush()

        with pytest.raises(InvalidKycStatusError):
            svc.update_person_kyc_status(db, person.id, "INVALID")

    def test_sync_without_client(self, db: Session, svc: ClientIdentityService, standalone_person: Person):
        result = svc.sync_client_kyc_status_from_person(db, standalone_person)
        assert result is None  # no linked client, nothing to sync


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

class TestRead:

    def test_get_by_person_id(self, db: Session, svc: ClientIdentityService):
        person, client = svc.create_person_and_client(db, email="read-p@test.com", jurisdiction="UAE")
        db.flush()

        identity = svc.get_client_identity_by_person_id(db, person.id)
        assert identity["is_linked"] is True
        assert identity["jurisdiction"] == "UAE"
        assert identity["kyc_status"] == "not_started"
        assert identity["person"]["id"] == str(person.id)
        assert identity["client"]["id"] == str(client.id)

    def test_get_by_client_id(self, db: Session, svc: ClientIdentityService):
        person, client = svc.create_person_and_client(db, email="read-c@test.com")
        db.flush()

        identity = svc.get_client_identity_by_client_id(db, client.id)
        assert identity["is_linked"] is True
        assert identity["person"]["id"] == str(person.id)

    def test_get_by_person_id_not_found(self, db: Session, svc: ClientIdentityService):
        with pytest.raises(PersonNotFoundError):
            svc.get_client_identity_by_person_id(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------

class TestEligibility:

    def test_approved_is_eligible(self, db: Session, svc: ClientIdentityService):
        person, _ = svc.create_person_and_client(db, email="elig-ok@test.com")
        svc.update_person_kyc_status(db, person.id, "approved")
        db.flush()

        is_ok, reason = svc.is_client_eligible_for_products(db, person.id)
        assert is_ok is True
        assert reason == "eligible"

    def test_not_approved_is_ineligible(self, db: Session, svc: ClientIdentityService):
        person, _ = svc.create_person_and_client(db, email="elig-no@test.com")
        db.flush()

        is_ok, reason = svc.is_client_eligible_for_products(db, person.id)
        assert is_ok is False
        assert "not_started" in reason

    def test_high_risk_is_ineligible(self, db: Session, svc: ClientIdentityService):
        person, _ = svc.create_person_and_client(db, email="elig-risk@test.com")
        person.kyc_status = "approved"
        person.profile_json = {"risk-tier-current": {"value": "high"}}
        db.flush()

        is_ok, reason = svc.is_client_eligible_for_products(db, person.id)
        assert is_ok is False
        assert "high" in reason

    def test_person_not_found(self, db: Session, svc: ClientIdentityService):
        is_ok, reason = svc.is_client_eligible_for_products(db, uuid.uuid4())
        assert is_ok is False
        assert "not_found" in reason
