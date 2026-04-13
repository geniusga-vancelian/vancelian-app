"""Phase 4C.8 — export durable (admin + helper) des métriques legacy persons."""
from __future__ import annotations

import re
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import Person
from services.persons.legacy_persons_metrics import (
    LEGACY_PERSONS_METRICS_EXPORT_KIND,
    build_legacy_persons_metrics_export,
    get_legacy_persons_metrics,
)
from tests.conftest import make_admin_headers, make_linked_client

_UUID_RE = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.I,
)


@pytest.fixture(autouse=True)
def _reset_metrics():
    get_legacy_persons_metrics().reset_for_tests()
    yield
    get_legacy_persons_metrics().reset_for_tests()


class TestBuildLegacyPersonsMetricsExport:
    def test_export_structure(self):
        exp = build_legacy_persons_metrics_export()
        assert exp["export_kind"] == LEGACY_PERSONS_METRICS_EXPORT_KIND
        assert "exported_at_utc" in exp and exp["exported_at_utc"].endswith("Z")
        m = exp["metrics"]
        assert "legacy_persons_endpoint_hit_total" in m
        assert "last_24h_hits" in m
        assert "last_7d_hits" in m
        assert "series" in m
        assert isinstance(m["series"], list)

    def test_export_matches_snapshot_after_hit(self, client: TestClient, db: Session, monkeypatch):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()
        client.get(f"/api/persons/{person.id}")
        exp = build_legacy_persons_metrics_export()
        snap = get_legacy_persons_metrics().snapshot()
        assert exp["metrics"] == snap

    def test_payload_no_raw_uuid(self, client: TestClient, db: Session, monkeypatch):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()
        client.get(f"/api/persons/{person.id}")
        raw = str(build_legacy_persons_metrics_export())
        assert str(person.id) not in raw
        assert _UUID_RE.search(raw) is None


class TestLegacyPersonsMetricsExportHttp:
    def test_requires_auth(self, client: TestClient):
        r = client.get("/admin/security/legacy-persons/metrics-export")
        assert r.status_code == 401

    def test_returns_export_with_admin(self, client: TestClient, db: Session):
        h = make_admin_headers(db)
        r = client.get("/admin/security/legacy-persons/metrics-export", headers=h)
        assert r.status_code == 200
        body = r.json()
        assert body["export_kind"] == LEGACY_PERSONS_METRICS_EXPORT_KIND
        assert "metrics" in body
        assert "legacy_persons_endpoint_hit_total" in body["metrics"]
