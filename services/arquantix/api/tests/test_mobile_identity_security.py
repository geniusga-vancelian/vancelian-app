"""Garde-fous identité mobile : JWT obligatoire si pas de mode dev explicite ; pas de fuite inter-clients."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import create_access_token, get_password_hash
from conftest import ensure_admin_for_linked_client, make_linked_client
from database import AdminUser, Person
from services.auth.jwt_user_claims import build_user_jwt_access_base_claims
from services.portfolio_engine.clients.models import Client as PeClient


def test_bootstrap_401_without_bearer(client: TestClient):
    res = client.get("/api/app/bootstrap")
    assert res.status_code == 401
    assert res.json().get("detail")


def test_bootstrap_401_invalid_bearer_token(client: TestClient):
    res = client.get(
        "/api/app/bootstrap",
        headers={"Authorization": "Bearer not-a-valid-jwt"},
    )
    assert res.status_code == 401


def test_bootstrap_200_bearer_resolves_linked_client(client: TestClient, db: Session):
    c = make_linked_client(db)
    u = ensure_admin_for_linked_client(db, c)
    token = create_access_token(build_user_jwt_access_base_claims(u))
    res = client.get(
        "/api/app/bootstrap",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["client"]["id"] == str(c.id)
    assert body["client"]["email"] == c.email


def test_bootstrap_403_when_client_id_claim_mismatches_resolved_client(
    client: TestClient, db: Session,
):
    c = make_linked_client(db)
    u = ensure_admin_for_linked_client(db, c)
    token = create_access_token(
        {**build_user_jwt_access_base_claims(u), "client_id": str(uuid.uuid4())},
    )
    res = client.get(
        "/api/app/bootstrap",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_bootstrap_bearer_user_a_never_returns_user_b(client: TestClient, db: Session):
    c_a = make_linked_client(db)
    c_b = make_linked_client(db)
    u_a = ensure_admin_for_linked_client(db, c_a)
    ensure_admin_for_linked_client(db, c_b)
    token_a = create_access_token(build_user_jwt_access_base_claims(u_a))
    res = client.get(
        "/api/app/bootstrap",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res.status_code == 200
    assert res.json()["client"]["id"] == str(c_a.id)
    assert res.json()["client"]["id"] != str(c_b.id)


def test_bootstrap_200_partial_session_sec_inc_lazy_provisions_pe_client(
    client: TestClient, db: Session,
):
    """JWT partiel (sec_inc, sans ACK passcode) : bootstrap OK + PeClient lazy pour suivi inscription."""
    person = Person(
        id=uuid.uuid4(),
        status="active",
        jurisdiction="EU",
        profile_json={},
        kyc_status="not_started",
    )
    db.add(person)
    db.flush()
    au = AdminUser(
        email=None,
        hashed_password=get_password_hash("secret"),
        person_id=person.id,
    )
    db.add(au)
    db.flush()
    assert db.query(PeClient).filter(PeClient.person_id == person.id).count() == 0

    token = create_access_token(
        {"sub": str(au.id), "person_id": str(person.id)},
        security_incomplete=True,
    )
    res = client.get(
        "/api/app/bootstrap",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["client"]["email"] is None
    assert db.query(PeClient).filter(PeClient.person_id == person.id).count() == 1


def test_bootstrap_404_valid_token_unknown_person_id(client: TestClient, db: Session):
    """JWT valide mais aucun PeClient : 404, pas de fallback test client."""
    token = create_access_token(
        {
            "sub": "ghost@example.com",
            "person_id": str(uuid.uuid4()),
        },
    )
    res = client.get(
        "/api/app/bootstrap",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 404


def test_bootstrap_200_lazy_provisions_pe_client_when_missing(client: TestClient, db: Session):
    """JWT valide + AdminUser + Person mais sans pe_clients → auto-provision puis 200."""
    person = Person(
        id=uuid.uuid4(),
        status="active",
        jurisdiction="EU",
        profile_json={
            "security": {"local_passcode_registered_at": "2026-01-01T00:00:00Z"},
        },
        kyc_status="not_started",
    )
    db.add(person)
    db.flush()
    au = AdminUser(
        email=None,
        hashed_password=get_password_hash("secret"),
        person_id=person.id,
    )
    db.add(au)
    db.flush()
    assert db.query(PeClient).filter(PeClient.person_id == person.id).count() == 0

    token = create_access_token({"sub": str(au.id), "pid": str(person.id)})
    res = client.get(
        "/api/app/bootstrap",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    cid = res.json()["client"]["id"]
    assert db.query(PeClient).filter(PeClient.person_id == person.id).count() == 1

    res2 = client.get(
        "/api/app/bootstrap",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res2.status_code == 200
    assert res2.json()["client"]["id"] == cid


def test_profile_200_lazy_provisions_pe_client_when_missing(client: TestClient, db: Session):
    """GET /api/app/profile même résolution que bootstrap."""
    person = Person(
        id=uuid.uuid4(),
        status="active",
        jurisdiction="EU",
        profile_json={
            "security": {"local_passcode_registered_at": "2026-01-01T00:00:00Z"},
        },
        kyc_status="not_started",
    )
    db.add(person)
    db.flush()
    au = AdminUser(
        email=None,
        hashed_password=get_password_hash("secret"),
        person_id=person.id,
    )
    db.add(au)
    db.flush()

    token = create_access_token({"sub": str(au.id), "person_id": str(person.id)})
    res = client.get(
        "/api/app/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    assert "initials" in res.json()

    res_flutter = client.get(
        "/api/mobile/flutter/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_flutter.status_code == 200, res_flutter.text
    assert res_flutter.json() == res.json()
