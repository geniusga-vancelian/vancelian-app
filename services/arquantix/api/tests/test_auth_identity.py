"""Tests for auth layer on identity/KYC endpoints (Phase 1B)."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import create_access_token
from database import Person, AdminUser


def _admin_headers(db: Session) -> dict:
    """Create an admin user + JWT token and return auth headers."""
    user = db.query(AdminUser).filter(AdminUser.email == "admin-test@example.com").first()
    if user is None:
        from auth import get_password_hash
        user = AdminUser(email="admin-test@example.com", hashed_password=get_password_hash("test"))
        db.add(user)
        db.flush()
    from services.auth.jwt_user_claims import build_user_jwt_access_base_claims

    token = create_access_token(build_user_jwt_access_base_claims(user))
    return {"Authorization": f"Bearer {token}"}


def _bad_token_headers() -> dict:
    return {"Authorization": "Bearer invalid-token-12345"}


# ------------------------------------------------------------------
# POST /api/persons — admin only
# ------------------------------------------------------------------

class TestCreatePersonAuth:

    def test_no_token_returns_401(self, client: TestClient):
        resp = client.post("/api/persons", json={
            "email": "anon@test.com",
            "jurisdiction": "EU",
        })
        assert resp.status_code == 401

    def test_bad_token_returns_401(self, client: TestClient):
        resp = client.post(
            "/api/persons",
            json={"email": "anon@test.com", "jurisdiction": "EU"},
            headers=_bad_token_headers(),
        )
        assert resp.status_code == 401

    def test_valid_admin_creates_person(self, client: TestClient, db: Session):
        headers = _admin_headers(db)
        resp = client.post(
            "/api/persons",
            json={"email": f"new-{uuid.uuid4().hex[:6]}@test.com", "jurisdiction": "EU"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "person_id" in data
        assert "client_id" in data


# ------------------------------------------------------------------
# GET /api/persons/{id}/identity — owner or admin
# ------------------------------------------------------------------

class TestGetIdentityAuth:

    def test_no_token_returns_401(self, client: TestClient):
        resp = client.get(f"/api/persons/{uuid.uuid4()}/identity")
        assert resp.status_code == 401

    def test_bad_token_returns_401(self, client: TestClient):
        resp = client.get(
            f"/api/persons/{uuid.uuid4()}/identity",
            headers=_bad_token_headers(),
        )
        assert resp.status_code == 401

    def test_admin_can_access_any_person(self, client: TestClient, db: Session):
        from tests.conftest import make_linked_client
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()
        headers = _admin_headers(db)
        resp = client.get(f"/api/persons/{person.id}/identity", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["kyc_status"] is not None
        assert "eligibility" in data


# ------------------------------------------------------------------
# PATCH /api/persons/{id}/kyc-status — admin only
# ------------------------------------------------------------------

class TestPatchKycStatusAuth:

    def test_no_token_returns_401(self, client: TestClient):
        resp = client.patch(
            f"/api/persons/{uuid.uuid4()}/kyc-status",
            json={"kyc_status": "approved"},
        )
        assert resp.status_code == 401

    def test_admin_can_update(self, client: TestClient, db: Session):
        from tests.conftest import make_linked_client
        linked = make_linked_client(db, kyc_status="not_started")
        person = db.query(Person).filter(Person.client_id == linked.id).first()
        headers = _admin_headers(db)
        resp = client.patch(
            f"/api/persons/{person.id}/kyc-status",
            json={"kyc_status": "in_progress"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["kyc_status"] == "in_progress"


# ------------------------------------------------------------------
# POST /api/persons/{id}/link-client — admin only
# ------------------------------------------------------------------

class TestLinkClientAuth:

    def test_no_token_returns_401(self, client: TestClient):
        resp = client.post(
            f"/api/persons/{uuid.uuid4()}/link-client",
            json={"client_id": str(uuid.uuid4())},
        )
        assert resp.status_code == 401


# ------------------------------------------------------------------
# GET /api/portfolio-engine/clients/{id}/identity — owner or admin
# ------------------------------------------------------------------

class TestClientIdentityAuth:

    def test_no_token_returns_401(self, client: TestClient):
        resp = client.get(f"/api/portfolio-engine/clients/{uuid.uuid4()}/identity")
        assert resp.status_code == 401

    def test_admin_can_access(self, client: TestClient, db: Session):
        from tests.conftest import make_linked_client
        linked = make_linked_client(db)
        headers = _admin_headers(db)
        resp = client.get(
            f"/api/portfolio-engine/clients/{linked.id}/identity",
            headers=headers,
        )
        assert resp.status_code == 200
