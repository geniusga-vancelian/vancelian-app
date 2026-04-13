"""Tests for Client Identity API endpoints."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import Person
from services.portfolio_engine.clients.models import Client
from tests.conftest import make_admin_headers


# ---------------------------------------------------------------------------
# POST /api/persons — Create person + client
# ---------------------------------------------------------------------------

class TestCreatePersonEndpoint:

    def test_create_success(self, client: TestClient, db: Session):
        headers = make_admin_headers(db)
        resp = client.post("/api/persons", json={
            "email": f"api-create-{uuid.uuid4().hex[:8]}@test.com",
            "jurisdiction": "EU",
        }, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert "person_id" in data
        assert "client_id" in data
        assert data["kyc_status"] == "not_started"
        assert data["jurisdiction"] == "EU"

    def test_create_duplicate_email(self, client: TestClient, db: Session):
        headers = make_admin_headers(db)
        email = f"api-dup-{uuid.uuid4().hex[:8]}@test.com"
        resp1 = client.post("/api/persons", json={"email": email}, headers=headers)
        assert resp1.status_code == 201

        resp2 = client.post("/api/persons", json={"email": email}, headers=headers)
        assert resp2.status_code == 409

    def test_create_with_custom_currency(self, client: TestClient, db: Session):
        headers = make_admin_headers(db)
        resp = client.post("/api/persons", json={
            "email": f"api-usd-{uuid.uuid4().hex[:8]}@test.com",
            "reference_currency": "USD",
        }, headers=headers)
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# GET /api/persons/{id}/identity — Consolidated identity view
# ---------------------------------------------------------------------------

class TestGetIdentityEndpoint:

    def test_get_identity(self, client: TestClient, db: Session):
        headers = make_admin_headers(db)
        create_resp = client.post("/api/persons", json={
            "email": f"api-id-{uuid.uuid4().hex[:8]}@test.com",
            "jurisdiction": "UAE",
        }, headers=headers)
        person_id = create_resp.json()["person_id"]

        resp = client.get(f"/api/persons/{person_id}/identity", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_linked"] is True
        assert data["jurisdiction"] == "UAE"
        assert data["kyc_status"] == "not_started"
        assert data["person"] is not None
        assert data["client"] is not None

    def test_get_identity_not_found(self, client: TestClient, db: Session):
        headers = make_admin_headers(db)
        resp = client.get(f"/api/persons/{uuid.uuid4()}/identity", headers=headers)
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/persons/{id}/kyc-status — Update KYC status
# ---------------------------------------------------------------------------

class TestUpdateKycStatusEndpoint:

    def test_update_kyc_status(self, client: TestClient, db: Session):
        headers = make_admin_headers(db)
        create_resp = client.post("/api/persons", json={
            "email": f"api-kyc-{uuid.uuid4().hex[:8]}@test.com",
        }, headers=headers)
        person_id = create_resp.json()["person_id"]

        resp = client.patch(f"/api/persons/{person_id}/kyc-status", json={
            "kyc_status": "approved",
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["kyc_status"] == "approved"
        assert data["client_kyc_status"] == "approved"
        assert data["synced"] is True

    def test_invalid_kyc_status(self, client: TestClient, db: Session):
        headers = make_admin_headers(db)
        create_resp = client.post("/api/persons", json={
            "email": f"api-inv-{uuid.uuid4().hex[:8]}@test.com",
        }, headers=headers)
        person_id = create_resp.json()["person_id"]

        resp = client.patch(f"/api/persons/{person_id}/kyc-status", json={
            "kyc_status": "INVALID",
        }, headers=headers)
        assert resp.status_code == 400

    def test_pending_review_maps_on_client(self, client: TestClient, db: Session):
        headers = make_admin_headers(db)
        create_resp = client.post("/api/persons", json={
            "email": f"api-pr-{uuid.uuid4().hex[:8]}@test.com",
        }, headers=headers)
        person_id = create_resp.json()["person_id"]

        resp = client.patch(f"/api/persons/{person_id}/kyc-status", json={
            "kyc_status": "pending_review",
        }, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["kyc_status"] == "pending_review"
        assert data["client_kyc_status"] == "pending_review"


# ---------------------------------------------------------------------------
# POST /api/persons/{id}/link-client — Link person to client
# ---------------------------------------------------------------------------

class TestLinkPersonToClientEndpoint:

    def test_link_idempotent(self, client: TestClient, db: Session):
        """Re-linking an already linked pair should succeed."""
        headers = make_admin_headers(db)
        create_resp = client.post("/api/persons", json={
            "email": f"link-{uuid.uuid4().hex[:8]}@test.com",
        }, headers=headers)
        assert create_resp.status_code == 201
        data = create_resp.json()

        resp = client.post(f"/api/persons/{data['person_id']}/link-client", json={
            "client_id": data["client_id"],
        }, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["is_linked"] is True

    def test_link_not_found(self, client: TestClient, db: Session):
        headers = make_admin_headers(db)
        resp = client.post(f"/api/persons/{uuid.uuid4()}/link-client", json={
            "client_id": str(uuid.uuid4()),
        }, headers=headers)
        assert resp.status_code == 404

    def test_link_conflict_when_already_linked(self, client: TestClient, db: Session):
        """Linking a person already linked to another client should return 409."""
        headers = make_admin_headers(db)
        resp1 = client.post("/api/persons", json={
            "email": f"lk1-{uuid.uuid4().hex[:8]}@test.com",
        }, headers=headers)
        resp2 = client.post("/api/persons", json={
            "email": f"lk2-{uuid.uuid4().hex[:8]}@test.com",
        }, headers=headers)
        person_id = resp1.json()["person_id"]
        other_client_id = resp2.json()["client_id"]

        resp = client.post(f"/api/persons/{person_id}/link-client", json={
            "client_id": other_client_id,
        }, headers=headers)
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# GET /api/persons/{id} — Backward-compatible endpoint
# ---------------------------------------------------------------------------

class TestBackwardCompatibleGetPerson:

    def test_get_person_returns_new_fields(self, client: TestClient, db: Session):
        headers = make_admin_headers(db)
        create_resp = client.post("/api/persons", json={
            "email": f"api-compat-{uuid.uuid4().hex[:8]}@test.com",
        }, headers=headers)
        person_id = create_resp.json()["person_id"]

        resp = client.get(f"/api/persons/{person_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert "kyc_status" in data
        assert "client_id" in data
