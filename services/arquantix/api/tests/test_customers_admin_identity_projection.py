"""Projection identité Customer 360 : sources collected vs auth vs PE (documentées dans _extract_identity_fields)."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import get_password_hash
from database import AdminUser, Person
from services.portfolio_engine.clients.models import Client

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-admin@example.com",
    "X-Actor-Roles": "admin",
}


@pytest.fixture(autouse=True)
def _require_admin_mobile_and_person(db: Session):
    from sqlalchemy import inspect

    insp = inspect(db.bind)
    cols = {c["name"] for c in insp.get_columns("admin_users", schema="public")}
    if "mobile_e164" not in cols or "person_id" not in cols:
        pytest.skip("Schéma sans admin_users.mobile_e164 / person_id")


def _eligible_person_with_mobile(
    db: Session,
    *,
    pid: uuid.UUID,
    phone: str,
    profile_json: dict,
    jurisdiction: str = "EU",
    person_status: str = "active",
) -> None:
    person = Person(
        id=pid,
        status=person_status,
        jurisdiction=jurisdiction,
        profile_json=profile_json,
        kyc_status="not_started",
    )
    db.add(person)
    db.flush()
    db.add(
        AdminUser(
            email=None,
            hashed_password=get_password_hash("x"),
            mobile_e164=phone,
            person_id=pid,
        )
    )
    db.commit()


def test_identity_email_collected_wins_over_pe_email(client: TestClient, db: Session):
    """collected.email prime ; PE sert de repli seulement si collected absent."""
    phone = "+33651700099"
    pid = uuid.uuid4()
    pe_email = f"pe-{uuid.uuid4().hex[:8]}@wallet.example.com"
    collected_email = "user.real@example.com"

    person = Person(
        id=pid,
        status="active",
        jurisdiction="EU",
        profile_json={
            "collected": {"email": collected_email, "phone_e164": phone},
            "computed": {},
            "compliance": {},
        },
        kyc_status="not_started",
    )
    db.add(person)
    db.flush()
    db.add(
        AdminUser(
            email=None,
            hashed_password=get_password_hash("x"),
            mobile_e164=phone,
            person_id=pid,
        )
    )
    db.add(
        Client(
            id=uuid.uuid4(),
            email=pe_email,
            status="active",
            kyc_status="approved",
            person_id=pid,
        )
    )
    db.commit()

    res = client.get(f"/api/admin/customers/{pid}", headers=ADMIN_HEADERS)
    assert res.status_code == 200, res.text
    idy = res.json()["identity"]
    assert idy["email"] == collected_email
    assert res.json()["wallet"]["email"] == pe_email


def test_identity_email_fallback_pe_when_collected_missing(client: TestClient, db: Session):
    """Sans collected.email, la liste / fiche utilisent pe_clients.email comme repli affichage."""
    phone = "+33651700098"
    pid = uuid.uuid4()
    pe_email = "fallback.pe@example.com"
    person = Person(
        id=pid,
        status="active",
        jurisdiction="EU",
        profile_json={"collected": {"phone_e164": phone}, "computed": {}, "compliance": {}},
        kyc_status="not_started",
    )
    db.add(person)
    db.flush()
    pe_id = uuid.uuid4()
    db.add(
        Client(
            id=pe_id,
            email=pe_email,
            status="active",
            kyc_status="approved",
            person_id=pid,
        )
    )
    db.flush()
    person.client_id = pe_id
    db.add(person)
    db.flush()
    db.add(
        AdminUser(
            email=None,
            hashed_password=get_password_hash("x"),
            mobile_e164=phone,
            person_id=pid,
        )
    )
    db.commit()

    res = client.get(f"/api/admin/customers/{pid}", headers=ADMIN_HEADERS)
    assert res.status_code == 200, res.text
    assert res.json()["identity"]["email"] == pe_email


def test_identity_jurisdiction_and_person_status_from_person_row(
    client: TestClient, db: Session,
):
    phone = "+33651700097"
    pid = uuid.uuid4()
    _eligible_person_with_mobile(
        db,
        pid=pid,
        phone=phone,
        profile_json={"collected": {}, "computed": {}, "compliance": {}},
        jurisdiction="EU",
        person_status="active",
    )

    res = client.get(f"/api/admin/customers/{pid}", headers=ADMIN_HEADERS)
    assert res.status_code == 200, res.text
    idy = res.json()["identity"]
    assert idy["jurisdiction"] == "EU"
    assert idy["person_status"] == "active"


def test_wallet_client_status_distinct_from_person_status(client: TestClient, db: Session):
    """Statut PE (wallet) distinct du statut Person (identité)."""
    phone = "+33651700096"
    pid = uuid.uuid4()
    person = Person(
        id=pid,
        status="active",
        jurisdiction="EU",
        profile_json={"collected": {}, "computed": {}, "compliance": {}},
        kyc_status="not_started",
    )
    db.add(person)
    db.flush()
    db.add(
        AdminUser(
            email=None,
            hashed_password=get_password_hash("x"),
            mobile_e164=phone,
            person_id=pid,
        )
    )
    db.add(
        Client(
            id=uuid.uuid4(),
            email=f"c-{uuid.uuid4().hex[:8]}@example.com",
            status="suspended",
            kyc_status="pending",
            person_id=pid,
        )
    )
    db.commit()

    res = client.get(f"/api/admin/customers/{pid}", headers=ADMIN_HEADERS)
    assert res.status_code == 200, res.text
    assert res.json()["identity"]["person_status"] == "active"
    assert res.json()["wallet"]["client_status"] == "suspended"
