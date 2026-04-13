"""Phase 4C.1 — observabilité runtime des endpoints persons legacy."""
from __future__ import annotations

import hashlib
import json
import logging
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from database import AuthSecurityEvent, Person, engine
from services.persons.legacy_observability import LEGACY_PERSONS_ENDPOINT_HIT
from services.persons.routes import _legacy_warning_get_identity
from tests.conftest import make_linked_client, make_admin_headers


def _fingerprint(person_id: uuid.UUID) -> str:
    return hashlib.sha256(f"person:{person_id}".encode()).hexdigest()[:16]


def _has_security_events_table() -> bool:
    try:
        return bool(inspect(engine).has_table("auth_security_events", schema="public"))
    except Exception:  # noqa: BLE001
        return False


def _legacy_log_records(caplog) -> list:
    return [r for r in caplog.records if r.name == "arquantix.persons.legacy"]


@pytest.mark.usefixtures("client", "db")
class TestLegacyPersonsRuntimeObservability:
    def test_get_legacy_emits_structured_signal(self, client: TestClient, db: Session, monkeypatch, caplog):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")
        caplog.set_level(logging.INFO, logger="arquantix.persons.legacy")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()

        resp = client.get(f"/api/persons/{person.id}")
        assert resp.status_code == 200
        assert resp.headers.get("Deprecation") == "true"
        assert resp.headers.get("Warning") == _legacy_warning_get_identity(person.id)

        recs = _legacy_log_records(caplog)
        assert recs, "expected structured log from arquantix.persons.legacy"
        payload = json.loads(recs[-1].message.split(LEGACY_PERSONS_ENDPOINT_HIT, 1)[1].strip())
        assert payload["legacy_persons_event"] == LEGACY_PERSONS_ENDPOINT_HIT
        assert payload["legacy"] is True
        assert payload["endpoint_name"] == "GET /api/persons/{person_id}"
        assert payload["method"] == "GET"
        assert payload["authenticated"] is False
        assert payload["allow_legacy_unauthenticated_kyc"] is True
        assert payload["caller_category"] == "unauthenticated"
        assert payload["person_id_fingerprint"] == _fingerprint(person.id)
        assert payload["successor_endpoint"] == "/api/persons/{person_id}/identity"

    def test_post_legacy_emits_structured_signal(self, client: TestClient, db: Session, monkeypatch, caplog):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")
        caplog.set_level(logging.INFO, logger="arquantix.persons.legacy")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()

        resp = client.post(
            f"/api/persons/{person.id}/fields",
            json={"slug": "test-field", "value": "test-value"},
        )
        assert resp.status_code != 401

        recs = _legacy_log_records(caplog)
        assert recs
        payload = json.loads(recs[-1].message.split(LEGACY_PERSONS_ENDPOINT_HIT, 1)[1].strip())
        assert payload["legacy_persons_event"] == LEGACY_PERSONS_ENDPOINT_HIT
        assert payload["endpoint_name"] == "POST /api/persons/{person_id}/fields"
        assert payload["method"] == "POST"
        assert payload["successor_endpoint"] is None
        assert payload["person_id_fingerprint"] == _fingerprint(person.id)

    def test_observability_log_has_no_raw_person_uuid(self, client: TestClient, db: Session, monkeypatch, caplog):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")
        caplog.set_level(logging.INFO, logger="arquantix.persons.legacy")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()

        client.get(f"/api/persons/{person.id}")

        for r in _legacy_log_records(caplog):
            assert str(person.id) not in r.getMessage()

    def test_auth_security_event_persisted_when_siem_enabled(
        self, client: TestClient, db: Session, monkeypatch
    ):
        if not _has_security_events_table():
            pytest.skip("Table auth_security_events absente.")
        monkeypatch.setenv("AUTH_SECURITY_EVENTS_ENABLED", "true")
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()

        before = (
            db.query(AuthSecurityEvent)
            .filter(AuthSecurityEvent.event_type == LEGACY_PERSONS_ENDPOINT_HIT)
            .count()
        )
        resp = client.get(f"/api/persons/{person.id}")
        assert resp.status_code == 200
        after = (
            db.query(AuthSecurityEvent)
            .filter(AuthSecurityEvent.event_type == LEGACY_PERSONS_ENDPOINT_HIT)
            .count()
        )
        assert after == before + 1
        row = (
            db.query(AuthSecurityEvent)
            .filter(AuthSecurityEvent.event_type == LEGACY_PERSONS_ENDPOINT_HIT)
            .order_by(AuthSecurityEvent.created_at.desc())
            .first()
        )
        assert row.metadata_payload.get("person_id_fingerprint") == _fingerprint(person.id)
        assert str(person.id) not in json.dumps(row.metadata_payload)

    def test_get_legacy_behavior_unchanged_401_when_flag_off(self, client: TestClient, db: Session, monkeypatch):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "false")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()

        resp = client.get(f"/api/persons/{person.id}")
        assert resp.status_code == 401

    def test_get_legacy_admin_still_200_and_caller_category(self, client: TestClient, db: Session, monkeypatch, caplog):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "false")
        caplog.set_level(logging.INFO, logger="arquantix.persons.legacy")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()
        headers = make_admin_headers(db)

        resp = client.get(f"/api/persons/{person.id}", headers=headers)
        assert resp.status_code == 200

        recs = _legacy_log_records(caplog)
        payload = json.loads(recs[-1].message.split(LEGACY_PERSONS_ENDPOINT_HIT, 1)[1].strip())
        assert payload["authenticated"] is True
        assert payload["caller_category"] == "admin"
