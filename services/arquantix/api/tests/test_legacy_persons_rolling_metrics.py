"""Phase 4C.5 — fenêtres glissantes 24h / 7j pour les métriques legacy persons."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from database import Person
from services.persons.legacy_persons_metrics import (
    LAST_24H_HITS,
    LAST_7D_HITS,
    LEGACY_PERSONS_ENDPOINT_HIT_TOTAL,
    _MAX_ROLLING_TIMESTAMPS,
    get_legacy_persons_metrics,
)
from tests.conftest import make_linked_client


@pytest.fixture(autouse=True)
def _reset_legacy_persons_metrics():
    m = get_legacy_persons_metrics()
    m.reset_for_tests()
    yield
    m.reset_for_tests()


def test_snapshot_includes_rolling_keys_after_http_hit(client: TestClient, db: Session, monkeypatch):
    monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")
    linked = make_linked_client(db)
    person = db.query(Person).filter(Person.client_id == linked.id).first()
    client.get(f"/api/persons/{person.id}")
    snap = get_legacy_persons_metrics().snapshot()
    assert LAST_24H_HITS in snap and LAST_7D_HITS in snap
    assert snap[LAST_24H_HITS] == 1
    assert snap[LAST_7D_HITS] == 1
    assert snap[LEGACY_PERSONS_ENDPOINT_HIT_TOTAL] == 1


def test_last_24h_excludes_hits_older_than_24h(client: TestClient, db: Session, monkeypatch):
    monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")
    t = {"v": 1_000_000_000.0}

    def fake_now():
        return t["v"]

    monkeypatch.setattr("services.persons.legacy_persons_metrics._utc_now_ts", fake_now)
    linked = make_linked_client(db)
    person = db.query(Person).filter(Person.client_id == linked.id).first()
    client.get(f"/api/persons/{person.id}")
    t["v"] = 1_000_000_000.0 + 25 * 3600
    snap = get_legacy_persons_metrics().snapshot()
    assert snap[LAST_24H_HITS] == 0
    assert snap[LAST_7D_HITS] == 1
    assert snap[LEGACY_PERSONS_ENDPOINT_HIT_TOTAL] == 1


def test_last_7d_excludes_hits_older_than_7d(client: TestClient, db: Session, monkeypatch):
    monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")
    t = {"v": 1_000_000_000.0}

    def fake_now():
        return t["v"]

    monkeypatch.setattr("services.persons.legacy_persons_metrics._utc_now_ts", fake_now)
    linked = make_linked_client(db)
    person = db.query(Person).filter(Person.client_id == linked.id).first()
    client.get(f"/api/persons/{person.id}")
    t["v"] = 1_000_000_000.0 + 8 * 24 * 3600
    snap = get_legacy_persons_metrics().snapshot()
    assert snap[LAST_7D_HITS] == 0
    assert snap[LAST_24H_HITS] == 0
    assert snap[LEGACY_PERSONS_ENDPOINT_HIT_TOTAL] == 1


def test_cumulative_total_unaffected_by_rolling_prune(client: TestClient, db: Session, monkeypatch):
    monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")
    t = {"v": 1_000_000_000.0}

    def fake_now():
        return t["v"]

    monkeypatch.setattr("services.persons.legacy_persons_metrics._utc_now_ts", fake_now)
    linked = make_linked_client(db)
    person = db.query(Person).filter(Person.client_id == linked.id).first()
    client.get(f"/api/persons/{person.id}")
    t["v"] = 1_000_000_000.0 + 8 * 24 * 3600
    snap = get_legacy_persons_metrics().snapshot()
    assert snap[LEGACY_PERSONS_ENDPOINT_HIT_TOTAL] == 1


def test_timestamp_deque_bounded(monkeypatch):
    monkeypatch.setattr("services.persons.legacy_persons_metrics._utc_now_ts", lambda: 5000.0)
    m = get_legacy_persons_metrics()
    m.reset_for_tests()
    kw = dict(
        endpoint_name="GET /api/persons/{person_id}",
        method="GET",
        authenticated=False,
        caller_category="unauthenticated",
        allow_legacy_unauthenticated_kyc=True,
    )
    for _ in range(_MAX_ROLLING_TIMESTAMPS + 5_000):
        m.record_hit(**kw)
    snap = m.snapshot()
    assert snap[LAST_7D_HITS] == _MAX_ROLLING_TIMESTAMPS
    assert snap[LEGACY_PERSONS_ENDPOINT_HIT_TOTAL] == _MAX_ROLLING_TIMESTAMPS + 5_000


def test_snapshot_string_has_no_uuid_from_rolling_data(client: TestClient, db: Session, monkeypatch):
    monkeypatch.setenv("ALLOW_LEGACY_UNAUTHENTICATED_KYC", "true")
    linked = make_linked_client(db)
    person = db.query(Person).filter(Person.client_id == linked.id).first()
    client.get(f"/api/persons/{person.id}")
    snap = get_legacy_persons_metrics().snapshot()
    assert str(person.id) not in str(snap)
