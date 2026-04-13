"""Alignement téléphone customer (profile_json) ↔ auth."""
import uuid

from database import AdminUser, Person
from services.customer_identity.profile_phone import ensure_person_collected_phone_e164


def test_ensure_collected_phone_skips_when_already_set(db):
    p = Person(
        id=uuid.uuid4(),
        status="active",
        jurisdiction="EU",
        profile_json={
            "collected": {"phone_e164": "+33611111111"},
            "computed": {},
            "compliance": {},
        },
        kyc_status="not_started",
    )
    db.add(p)
    db.flush()
    assert ensure_person_collected_phone_e164(p, "+33699999999") is False


def test_ensure_collected_phone_fills_when_empty(db):
    p = Person(
        id=uuid.uuid4(),
        status="active",
        jurisdiction="EU",
        profile_json={"collected": {}, "computed": {}, "compliance": {}},
        kyc_status="not_started",
    )
    db.add(p)
    db.flush()
    phone = "+33651624864"
    assert ensure_person_collected_phone_e164(p, phone) is True
    assert (p.profile_json or {}).get("collected", {}).get("phone_e164") == phone
