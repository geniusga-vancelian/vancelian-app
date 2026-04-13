"""Tests for legacy endpoint security — progressive auth with feature flag."""
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import Person
from services.persons.routes import _LEGACY_WARNING_POST_FIELDS, _legacy_warning_get_identity
from tests.conftest import make_linked_client, make_admin_headers


class TestGetPersonLegacyAuth:

    def test_unauthenticated_allowed_when_flag_on(self, client: TestClient, db: Session, monkeypatch):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()

        resp = client.get(f"/api/persons/{person.id}")
        assert resp.status_code == 200
        assert resp.headers.get("Deprecation") == "true"
        assert "/identity" in (resp.headers.get("Link") or "")
        assert resp.headers.get("Warning") == _legacy_warning_get_identity(person.id)

    def test_unauthenticated_blocked_when_flag_off(self, client: TestClient, db: Session, monkeypatch):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "false")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()

        resp = client.get(f"/api/persons/{person.id}")
        assert resp.status_code == 401

    def test_admin_always_allowed(self, client: TestClient, db: Session, monkeypatch):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "false")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()
        headers = make_admin_headers(db)

        resp = client.get(f"/api/persons/{person.id}", headers=headers)
        assert resp.status_code == 200
        assert resp.headers.get("Deprecation") == "true"
        assert resp.headers.get("Warning") == _legacy_warning_get_identity(person.id)

    def test_get_person_deprecation_link_points_to_identity(self, client: TestClient, db: Session, monkeypatch):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()
        resp = client.get(f"/api/persons/{person.id}")
        link = resp.headers.get("Link") or ""
        assert f"/api/persons/{person.id}/identity" in link
        assert "successor-version" in link
        assert resp.headers.get("Warning") == _legacy_warning_get_identity(person.id)


class TestSetFieldLegacyAuth:

    def test_unauthenticated_allowed_when_flag_on(self, client: TestClient, db: Session, monkeypatch):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()

        resp = client.post(f"/api/persons/{person.id}/fields", json={
            "slug": "test-field",
            "value": "test-value",
        })
        # May fail with 400/500 if field doesn't exist, but NOT 401
        assert resp.status_code != 401
        if resp.status_code == 200:
            assert resp.headers.get("Deprecation") == "true"
            assert resp.headers.get("Warning") == _LEGACY_WARNING_POST_FIELDS
            assert resp.headers.get("Link") is None

    def test_unauthenticated_blocked_when_flag_off(self, client: TestClient, db: Session, monkeypatch):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "false")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()

        resp = client.post(f"/api/persons/{person.id}/fields", json={
            "slug": "test-field",
            "value": "test-value",
        })
        assert resp.status_code == 401

    def test_admin_always_allowed(self, client: TestClient, db: Session, monkeypatch):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "false")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()
        headers = make_admin_headers(db)

        resp = client.post(f"/api/persons/{person.id}/fields", json={
            "slug": "test-field",
            "value": "test-value",
        }, headers=headers)
        # Not 401 — may be 400/500 if field doesn't exist, that's fine
        assert resp.status_code != 401
        if resp.status_code == 200:
            assert resp.headers.get("Deprecation") == "true"
            assert resp.headers.get("Warning") == _LEGACY_WARNING_POST_FIELDS
