"""SIEM pipeline, corrélation, sinks, alertes, API admin sécurité."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from database import AuthSecurityEvent
from tests.conftest import make_admin_headers


def _event(
    *,
    user_id: int | None = 1,
    device_id: str = "dev1",
    event_type: str = "auth.login.failed",
    ip: str = "10.0.0.1",
    meta: dict | None = None,
    created_at: datetime | None = None,
) -> AuthSecurityEvent:
    return AuthSecurityEvent(
        id=uuid.uuid4(),
        user_id=user_id,
        device_id=device_id[:128],
        event_type=event_type[:128],
        ip_address=ip[:45],
        user_agent=None,
        metadata_payload=dict(meta or {}),
        created_at=created_at or datetime.now(timezone.utc),
    )


def test_retention_days_clamped(monkeypatch):
    from services.auth.security_events_retention import retention_days

    monkeypatch.setenv("AUTH_SECURITY_EVENTS_RETENTION_DAYS", "2")
    assert retention_days() == 7
    monkeypatch.setenv("AUTH_SECURITY_EVENTS_RETENTION_DAYS", "9000")
    assert retention_days() == 730


def test_purge_old_events_respects_ttl(db, monkeypatch):
    from services.auth.security_events_retention import purge_old_auth_security_events, retention_days

    monkeypatch.setenv("AUTH_SECURITY_EVENTS_RETENTION_DAYS", "90")
    days = retention_days()
    old_ts = datetime.now(timezone.utc) - timedelta(days=days + 10)
    fresh_ts = datetime.now(timezone.utc) - timedelta(days=1)
    e_old = _event(user_id=1, ip="10.0.0.2", created_at=old_ts)
    e_new = _event(user_id=1, ip="10.0.0.3", created_at=fresh_ts, event_type="auth.login.success")
    db.add_all([e_old, e_new])
    db.flush()
    n = purge_old_auth_security_events(db, do_commit=False)
    assert n >= 1
    assert db.get(AuthSecurityEvent, e_old.id) is None
    assert db.get(AuthSecurityEvent, e_new.id) is not None


def test_detect_bruteforce_pattern(db):
    from services.auth.security_correlation_service import detect_bruteforce_pattern

    ip = "192.168.55.55"
    for _ in range(26):
        db.add(_event(user_id=None, ip=ip, event_type="auth.login.failed"))
    db.flush()
    findings = detect_bruteforce_pattern(db, window_minutes=10, threshold=25)
    assert any(f.rule == "bruteforce_pattern" and f.severity in ("HIGH", "CRITICAL") for f in findings)


def test_detect_geo_jump(db):
    from services.auth.security_correlation_service import detect_geo_jump

    uid = 424242
    db.add(
        _event(
            user_id=uid,
            device_id="dgeo",
            event_type="auth.login.success",
            ip="10.1.1.1",
            meta={"country": "FR"},
        )
    )
    db.add(
        _event(
            user_id=uid,
            device_id="dgeo",
            event_type="auth.login.success",
            ip="10.1.1.2",
            meta={"geo_country": "US"},
        )
    )
    db.flush()
    findings = detect_geo_jump(db, window_hours=2)
    assert any(f.rule == "geo_jump" and f.detail.get("user_id") == uid for f in findings)


def test_correlation_engine_detect_bruteforce_ip(db):
    from services.security.security_correlation_engine import detect_bruteforce

    ip = "203.0.113.77"
    for _ in range(30):
        db.add(_event(user_id=None, ip=ip, event_type="auth.login.failed"))
    db.flush()
    sigs = detect_bruteforce(db, ip, threshold=25)
    assert sigs and sigs[0].rule == "bruteforce"


def test_security_event_sink_noop(monkeypatch):
    from services.security.security_event_sink import NoopSink, get_security_event_sink

    monkeypatch.setenv("SECURITY_EVENTS_SINK", "none")
    assert isinstance(get_security_event_sink(), NoopSink)


def test_security_events_retention_reexport():
    from services.security.security_events_retention import retention_days as rd2

    assert callable(rd2)


def test_forward_after_persist_datadog_sink(monkeypatch):
    monkeypatch.setenv("SECURITY_EVENTS_SINK", "datadog")
    monkeypatch.setenv("DATADOG_API_KEY", "test-key")
    captured: list[dict] = []

    def fake_push(payload: dict) -> bool:
        captured.append(payload)
        return True

    monkeypatch.setattr("services.auth.datadog_sink.push_datadog_log", fake_push)
    monkeypatch.setenv("SECURITY_CORRELATION_ON_EMIT", "false")

    from services.security.security_event_pipeline import forward_after_persist

    forward_after_persist(
        event_id=str(uuid.uuid4()),
        event_type="auth.test.event",
        user_id=1,
        device_id="device-abc",
        ip_address="203.0.113.10",
        user_agent="Mozilla/5.0",
        metadata={"x": 1, "risk_level": "LOW"},
        db=None,
    )
    assert len(captured) == 1
    assert captured[0]["event_type"] == "auth.test.event"
    assert captured[0]["schema"] == "arquantix.security.event.v2"


def test_forward_after_persist_opensearch_sink(monkeypatch):
    monkeypatch.setenv("SECURITY_EVENTS_SINK", "opensearch")
    monkeypatch.setenv("OPENSEARCH_URL", "https://search.example")
    captured: list[dict] = []

    monkeypatch.setattr("services.auth.opensearch_sink.push_opensearch_document", lambda p: captured.append(p) or True)
    monkeypatch.setenv("SECURITY_CORRELATION_ON_EMIT", "false")

    from services.security.security_event_pipeline import forward_after_persist

    forward_after_persist(
        event_id=str(uuid.uuid4()),
        event_type="auth.test.event",
        user_id=None,
        device_id="d",
        ip_address=None,
        user_agent=None,
        metadata={},
        db=None,
    )
    assert len(captured) == 1


def test_security_alert_webhook_only_on_critical(monkeypatch):
    monkeypatch.setenv("SECURITY_ALERT_WEBHOOK_URL", "https://hooks.example/here")
    mock_cm = MagicMock()
    mock_resp = MagicMock()
    mock_resp.__enter__.return_value.getcode.return_value = 204
    mock_resp.__exit__.return_value = None
    mock_cm.return_value = mock_resp
    monkeypatch.setattr("services.security.security_alert_service.urllib.request.urlopen", mock_cm)

    from services.auth.security_alerting import send_security_alert

    send_security_alert(severity="HIGH", title="h", body={"k": 1})
    mock_cm.assert_not_called()
    send_security_alert(severity="CRITICAL", title="c", body={"k": 2})
    mock_cm.assert_called_once()


def test_admin_security_anomalies_and_user_risk(client, db, monkeypatch):
    monkeypatch.setenv("AUTH_SECURITY_EVENTS_ENABLED", "true")
    ip = "198.51.100.9"
    for _ in range(26):
        db.add(_event(user_id=99, ip=ip, event_type="auth.login.failed", device_id="admintest"))
    db.flush()
    h = make_admin_headers(db)
    r = client.get("/admin/security/anomalies", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert "findings" in data and "legacy_flags" in data
    assert "global_risk_index" in data and "global_risk_level" in data
    assert any(f.get("rule") == "bruteforce_pattern" for f in data["findings"])

    r2 = client.get("/admin/security/user-risk/99", headers=h)
    assert r2.status_code == 200
    body = r2.json()
    assert body["user_id"] == 99
    assert body["recent_event_count"] >= 26
    assert isinstance(body["findings"], list)
    assert "risk_index" in body and isinstance(body["risk_index"], int)
    assert "engine_signals" in body
