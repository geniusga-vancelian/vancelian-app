"""Provisioning PeClient au login — évite 404 /api/app/profile sans pe_clients."""
import uuid

from sqlalchemy.orm import Session

from auth import get_password_hash
from conftest import make_linked_client
from database import AdminUser, Person
from services.client_identity.service import ClientIdentityService
from services.portfolio_engine.clients.models import Client as PeClient


def test_ensure_pe_client_creates_row_when_only_person_exists(db: Session):
    person = Person(
        id=uuid.uuid4(),
        status="active",
        jurisdiction="EU",
        profile_json={},
        kyc_status="not_started",
    )
    db.add(person)
    db.flush()
    db.add(
        AdminUser(
            email=None,
            hashed_password=get_password_hash("secret"),
            person_id=person.id,
        )
    )
    db.flush()

    assert db.query(PeClient).filter(PeClient.person_id == person.id).first() is None

    c = ClientIdentityService.ensure_pe_client_for_login_user(
        db,
        person_id=person.id,
        client_email=None,
    )
    db.commit()

    db.refresh(person)
    assert c.person_id == person.id
    assert c.email is None
    assert person.client_id == c.id


def test_ensure_pe_client_idempotent_when_already_linked(db: Session):
    c0 = make_linked_client(db)
    c1 = ClientIdentityService.ensure_pe_client_for_login_user(
        db,
        person_id=c0.person_id,
        client_email=c0.email,
    )
    assert c1.id == c0.id

