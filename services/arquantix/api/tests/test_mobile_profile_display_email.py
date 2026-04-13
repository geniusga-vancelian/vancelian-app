"""Profil mobile : pas d’e-mail affiché pour les placeholders d’inscription SMS."""
import uuid

from sqlalchemy.orm import Session

from conftest import make_linked_client
from database import AdminUser, Person
from services.portfolio_engine.clients.models import Client as PeClient
from services.test_clients.mobile_profile import build_mobile_profile_dict


def test_profile_email_empty_when_only_signup_placeholder(db: Session):
    """Sans e-mail collecté, ne pas exposer d’e-mail technique (PR4 : NULL en base)."""
    person = Person(
        id=uuid.uuid4(),
        status="active",
        jurisdiction="EU",
        profile_json={"collected": {}},
        kyc_status="not_started",
    )
    db.add(person)
    db.flush()
    u = AdminUser(
        email=None,
        hashed_password="x",
        person_id=person.id,
        mobile_e164="+33600000000",
    )
    db.add(u)
    db.flush()
    c = PeClient(
        id=uuid.uuid4(),
        person_id=person.id,
        email=None,
        status="active",
        kyc_status="not_started",
    )
    db.add(c)
    db.commit()
    db.refresh(c)

    d = build_mobile_profile_dict(db, c)
    assert d["email"] == ""
    contact = d.get("contact")
    if contact is not None:
        assert contact.get("email") in (None, "")


def test_profile_email_from_collected_when_real(db: Session):
    linked = make_linked_client(db)
    person = db.query(Person).filter(Person.id == linked.person_id).first()
    assert person is not None
    pj = dict(person.profile_json or {})
    col = dict(pj.get("collected") or {})
    col["email"] = "user.real@example.com"
    pj["collected"] = col
    person.profile_json = pj
    db.add(person)
    db.commit()

    c = db.query(PeClient).filter(PeClient.person_id == person.id).first()
    assert c is not None
    d = build_mobile_profile_dict(db, c)
    assert d["email"] == "user.real@example.com"
    assert d.get("contact", {}).get("email") == "user.real@example.com"
