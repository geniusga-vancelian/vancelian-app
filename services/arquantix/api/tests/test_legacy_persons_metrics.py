"""Phase 4C.3 — compteurs agrégés legacy persons."""
from __future__ import annotations

from typing import Optional

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import Person
from services.persons.legacy_persons_metrics import (
    LEGACY_PERSONS_ENDPOINT_HIT_TOTAL,
    get_legacy_persons_metrics,
)
from tests.conftest import make_linked_client, make_admin_headers


@pytest.fixture(autouse=True)
def _reset_legacy_persons_metrics():
    m = get_legacy_persons_metrics()
    m.reset_for_tests()
    yield
    m.reset_for_tests()


def _find_series(snap: dict, **labels) -> Optional[int]:
    for s in snap.get("series", []):
        if s.get("labels") == labels:
            return s["value"]
    return None


class TestLegacyPersonsAggregatedMetrics:
    def test_get_increments_total_and_labels(self, client: TestClient, db: Session, monkeypatch):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()

        before = get_legacy_persons_metrics().snapshot()[LEGACY_PERSONS_ENDPOINT_HIT_TOTAL]
        r = client.get(f"/api/persons/{person.id}")
        assert r.status_code == 200
        snap = get_legacy_persons_metrics().snapshot()
        assert snap[LEGACY_PERSONS_ENDPOINT_HIT_TOTAL] == before + 1
        assert snap["metric"] == LEGACY_PERSONS_ENDPOINT_HIT_TOTAL
        v = _find_series(
            snap,
            endpoint_name="GET /api/persons/{person_id}",
            method="GET",
            authenticated="false",
            caller_category="unauthenticated",
            allow_legacy_unauthenticated_kyc="true",
        )
        assert v == 1
        # Aucun identifiant brut dans le snapshot
        dumped = str(snap)
        assert str(person.id) not in dumped

    def test_post_increments_total_and_labels(self, client: TestClient, db: Session, monkeypatch):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()

        before = get_legacy_persons_metrics().snapshot()[LEGACY_PERSONS_ENDPOINT_HIT_TOTAL]
        r = client.post(
            f"/api/persons/{person.id}/fields",
            json={"slug": "test-field", "value": "test-value"},
        )
        assert r.status_code != 401
        snap = get_legacy_persons_metrics().snapshot()
        assert snap[LEGACY_PERSONS_ENDPOINT_HIT_TOTAL] == before + 1
        v = _find_series(
            snap,
            endpoint_name="POST /api/persons/{person_id}/fields",
            method="POST",
            authenticated="false",
            caller_category="unauthenticated",
            allow_legacy_unauthenticated_kyc="true",
        )
        assert v == 1

    def test_get_as_admin_caller_category_admin(self, client: TestClient, db: Session, monkeypatch):
        monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "false")
        linked = make_linked_client(db)
        person = db.query(Person).filter(Person.client_id == linked.id).first()
        headers = make_admin_headers(db)

        client.get(f"/api/persons/{person.id}", headers=headers)
        snap = get_legacy_persons_metrics().snapshot()
        v = _find_series(
            snap,
            endpoint_name="GET /api/persons/{person_id}",
            method="GET",
            authenticated="true",
            caller_category="admin",
            allow_legacy_unauthenticated_kyc="false",
        )
        assert v == 1
