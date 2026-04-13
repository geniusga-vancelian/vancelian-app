"""Tests for Registration Runtime Settings — current jurisdiction endpoints."""
import uuid

import pytest
from sqlalchemy import text

from database import (
    SessionLocal,
    RegistrationRuntimeSetting,
    RegistrationJurisdiction,
    RegistrationFlow,
)


@pytest.fixture()
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client():
    from main import app
    from fastapi.testclient import TestClient

    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/registration/runtime/current-jurisdiction
# ---------------------------------------------------------------------------

class TestGetCurrentJurisdiction:

    def test_returns_eu_by_default(self, client, db):
        """The seed sets EU as the current jurisdiction."""
        resp = client.get("/api/registration/runtime/current-jurisdiction")
        assert resp.status_code == 200
        data = resp.json()
        assert data["jurisdiction_code"] == "EU"
        assert data["jurisdiction_name"] is not None
        assert data["active_flow_name"] is not None
        assert data["active_flow_version"] >= 1

    def test_resolves_active_flow(self, client, db):
        """Should return the active individual flow for the current jurisdiction."""
        resp = client.get("/api/registration/runtime/current-jurisdiction")
        assert resp.status_code == 200
        data = resp.json()
        assert data["active_flow_id"] is not None
        assert "Individual" in data["active_flow_name"] or "Onboarding" in data["active_flow_name"]

    def test_returns_404_when_no_setting(self, client, db):
        """If runtime settings table is empty, return 404."""
        settings = db.query(RegistrationRuntimeSetting).all()
        codes = []
        for s in settings:
            codes.append(s.current_jurisdiction_code)
            db.delete(s)
        db.commit()

        try:
            resp = client.get("/api/registration/runtime/current-jurisdiction")
            assert resp.status_code == 404
        finally:
            for code in codes:
                db.add(RegistrationRuntimeSetting(current_jurisdiction_code=code))
            db.commit()


# ---------------------------------------------------------------------------
# PATCH /api/admin/registration/runtime/current-jurisdiction
# ---------------------------------------------------------------------------

class TestPatchCurrentJurisdiction:

    def test_patch_valid_jurisdiction(self, client, db):
        """Switching to a valid active jurisdiction should succeed."""
        eu_j = db.query(RegistrationJurisdiction).filter(
            RegistrationJurisdiction.code == "EU"
        ).first()
        if not eu_j:
            pytest.skip("EU jurisdiction not seeded")

        resp = client.patch(
            "/api/admin/registration/runtime/current-jurisdiction",
            json={"jurisdiction_code": "EU"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["current_jurisdiction_code"] == "EU"
        assert data["jurisdiction_name"] is not None

    def test_patch_unknown_jurisdiction_rejected(self, client, db):
        """Unknown jurisdiction code should return 404."""
        resp = client.patch(
            "/api/admin/registration/runtime/current-jurisdiction",
            json={"jurisdiction_code": "MARS"},
        )
        assert resp.status_code == 404

    def test_patch_empty_code_rejected(self, client, db):
        """Empty jurisdiction_code should be rejected (422)."""
        resp = client.patch(
            "/api/admin/registration/runtime/current-jurisdiction",
            json={"jurisdiction_code": ""},
        )
        assert resp.status_code == 422

    def test_patch_persists(self, client, db):
        """After patch, GET should return the new value."""
        uae_j = db.query(RegistrationJurisdiction).filter(
            RegistrationJurisdiction.code == "UAE",
            RegistrationJurisdiction.is_active.is_(True),
        ).first()
        if not uae_j:
            pytest.skip("UAE jurisdiction not seeded or not active")

        client.patch(
            "/api/admin/registration/runtime/current-jurisdiction",
            json={"jurisdiction_code": "UAE"},
        )

        resp = client.get("/api/registration/runtime/current-jurisdiction")
        assert resp.status_code == 200
        assert resp.json()["jurisdiction_code"] == "UAE"

        # Restore EU
        client.patch(
            "/api/admin/registration/runtime/current-jurisdiction",
            json={"jurisdiction_code": "EU"},
        )


# ---------------------------------------------------------------------------
# Admin GET
# ---------------------------------------------------------------------------

class TestAdminGetCurrentJurisdiction:

    def test_admin_get(self, client, db):
        """Admin endpoint returns current_jurisdiction_code."""
        resp = client.get("/api/admin/registration/runtime/current-jurisdiction")
        assert resp.status_code == 200
        data = resp.json()
        assert "current_jurisdiction_code" in data
