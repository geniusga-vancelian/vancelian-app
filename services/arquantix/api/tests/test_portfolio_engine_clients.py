"""Tests for Portfolio Engine — Clients module."""
import uuid

import pytest
from sqlalchemy.orm import Session

from conftest import make_linked_client
from database import Person
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.clients.repository import ClientRepository, DuplicateEmailError
from services.portfolio_engine.clients.service import ClientNotFoundError, ClientService
from services.portfolio_engine.clients.schemas import ClientCreate, ClientUpdate


def _make_person(db: Session) -> Person:
    """Helper: create a minimal Person for linking to a Client."""
    p = Person(id=uuid.uuid4(), status="active", profile_json={}, kyc_status="not_started")
    db.add(p)
    db.flush()
    return p


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client_alice(db: Session) -> Client:
    return make_linked_client(db, email="alice@example.com", status="active", kyc_status="approved")


@pytest.fixture
def client_service() -> ClientService:
    return ClientService()


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestClientRepository:

    def test_create(self, db: Session):
        p = _make_person(db)
        c = ClientRepository.create(
            db,
            data={"email": "new@example.com", "person_id": p.id},
        )
        assert c.id is not None
        assert c.email == "new@example.com"
        assert c.status == "pending"
        assert c.kyc_status == "not_started"

    def test_create_duplicate_email(self, db: Session, client_alice: Client):
        with pytest.raises(DuplicateEmailError):
            ClientRepository.create(db, data={"email": "alice@example.com"})

    def test_get_by_id(self, db: Session, client_alice: Client):
        found = ClientRepository.get_by_id(db, client_alice.id)
        assert found is not None
        assert found.email == "alice@example.com"

    def test_get_by_id_not_found(self, db: Session):
        assert ClientRepository.get_by_id(db, uuid.uuid4()) is None

    def test_list_all(self, db: Session, client_alice: Client):
        p = _make_person(db)
        ClientRepository.create(db, data={"email": "bob@example.com", "person_id": p.id})
        items, total = ClientRepository.list(db)
        assert total >= 2

    def test_list_filter_by_status(self, db: Session, client_alice: Client):
        items, total = ClientRepository.list(db, status="active")
        assert total >= 1
        assert all(c.status == "active" for c in items)

    def test_update(self, db: Session, client_alice: Client):
        ClientRepository.update(db, client_alice, data={"status": "suspended"})
        db.flush()
        refreshed = ClientRepository.get_by_id(db, client_alice.id)
        assert refreshed.status == "suspended"

    def test_update_email_duplicate(self, db: Session, client_alice: Client):
        from sqlalchemy.exc import IntegrityError as SAIntegrityError
        p = _make_person(db)
        ClientRepository.create(db, data={"email": "bob@example.com", "person_id": p.id})
        with pytest.raises(SAIntegrityError):
            ClientRepository.update(db, client_alice, data={"email": "bob@example.com"})


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestClientService:

    def test_create_client(self, db: Session, client_service: ClientService):
        p = _make_person(db)
        payload = ClientCreate(email="svc@example.com", person_id=p.id)
        c = client_service.create_client(db, payload)
        assert c.email == "svc@example.com"
        assert c.status == "pending"
        assert c.kyc_status == "not_started"

    def test_get_client(self, db: Session, client_service: ClientService, client_alice: Client):
        found = client_service.get_client(db, client_alice.id)
        assert found.id == client_alice.id

    def test_get_client_not_found(self, db: Session, client_service: ClientService):
        with pytest.raises(ClientNotFoundError):
            client_service.get_client(db, uuid.uuid4())

    def test_list_clients(self, db: Session, client_service: ClientService, client_alice: Client):
        items, total = client_service.list_clients(db)
        assert total >= 1

    def test_update_client(self, db: Session, client_service: ClientService, client_alice: Client):
        payload = ClientUpdate(kyc_status="rejected")
        updated = client_service.update_client(db, client_alice.id, payload)
        assert updated.kyc_status == "rejected"
        assert updated.email == "alice@example.com"

    def test_update_client_partial(self, db: Session, client_service: ClientService, client_alice: Client):
        payload = ClientUpdate(status="closed")
        updated = client_service.update_client(db, client_alice.id, payload)
        assert updated.status == "closed"
        assert updated.kyc_status == "approved"


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class TestClientSchemas:

    def test_create_defaults(self):
        payload = ClientCreate(email="test@test.com")
        assert payload.status == "pending"
        assert payload.kyc_status == "not_started"

    def test_create_with_overrides(self):
        payload = ClientCreate(email="test@test.com", status="active", kyc_status="approved")
        assert payload.status == "active"
        assert payload.kyc_status == "approved"

    def test_update_partial(self):
        payload = ClientUpdate(status="suspended")
        dumped = payload.model_dump(exclude_unset=True)
        assert "status" in dumped
        assert "email" not in dumped
        assert "kyc_status" not in dumped
