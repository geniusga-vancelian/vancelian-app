"""Customer 360 : éligibilité et mobile lorsque seul admin_users porte le numéro."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import get_password_hash
from database import AdminUser, Person

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


def test_customer_detail_visible_when_only_auth_mobile_no_collected(
    client: TestClient,
    db: Session,
):
    """Ancien écart : mobile sur AdminUser mais pas dans collected → fiche doit exister + mobile affiché."""
    phone = "+33651700042"
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
    db.commit()

    res = client.get(f"/api/admin/customers/{pid}", headers=ADMIN_HEADERS)
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["identity"]["mobile"] == phone


def test_customers_list_includes_person_with_auth_mobile_only(
    client: TestClient,
    db: Session,
):
    phone = "+33650000001"
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
    db.commit()

    res = client.get("/api/admin/customers?page=1&page_size=100", headers=ADMIN_HEADERS)
    assert res.status_code == 200, res.text
    ids = {str(x["person_id"]) for x in res.json()["items"]}
    assert str(pid) in ids
