"""Changement d’e-mail profil mobile : pending → confirmed."""
from conftest import make_linked_client
from database import Person
from services.portfolio_engine.clients.models import Client as PeClient
from services.registration.service import get_person_collected_value
from services.test_clients.mobile_contact_email import (
    STATUS_CONFIRMED,
    STATUS_PENDING,
    confirm_contact_email_change,
    request_contact_email_change,
)


def test_request_then_confirm_persists_collected_email(db):
    linked = make_linked_client(db)
    person = db.query(Person).filter(Person.id == linked.person_id).first()
    client = db.query(PeClient).filter(PeClient.person_id == person.id).first()
    assert person is not None and client is not None

    request_contact_email_change(person, "new.user@example.com")
    db.add(person)
    db.commit()
    db.refresh(person)

    pj = person.profile_json or {}
    change = pj.get("contact_email_change") or {}
    assert change.get("status") == STATUS_PENDING
    assert change.get("pending_email") == "new.user@example.com"
    assert get_person_collected_value(person, "email") != "new.user@example.com"

    confirm_contact_email_change(
        db,
        person=person,
        client=client,
        new_email="new.user@example.com",
        verified_privy_email="new.user@example.com",
    )
    db.commit()
    db.refresh(person)
    db.refresh(client)

    assert get_person_collected_value(person, "email") == "new.user@example.com"
    assert get_person_collected_value(person, "contact_email") == "new.user@example.com"
    change2 = (person.profile_json or {}).get("contact_email_change") or {}
    assert change2.get("status") == STATUS_CONFIRMED
    assert client.email == "new.user@example.com"
