"""Réputation device : multi-comptes, scoring, blacklist, findings, risk engine."""
from __future__ import annotations

import pytest

from auth import get_password_hash
from database import AdminUser, AuthDeviceGraphFinding
from services.security.device_reputation.device_graph_analysis import find_shared_devices
from services.security.device_reputation.device_identity import build_device_hash
from services.security.device_reputation.device_reputation_service import (
    blacklist_device,
    compute_device_reputation,
    evaluate_auth_impact,
    persist_graph_finding,
    record_device_usage,
    unblacklist_device,
)
from services.security.security_response_engine import _device_reputation_user_boost


def test_build_device_hash_stable_with_fingerprint():
    h1 = build_device_hash("dev-1", "ab" * 32, None)
    h2 = build_device_hash("dev-1", "ab" * 32, None)
    assert h1 == h2
    assert len(h1) == 64


def test_multi_user_increases_reputation(db, monkeypatch):
    monkeypatch.setenv("DEVICE_REPUTATION_ENABLED", "true")
    u1 = AdminUser(email="dr1@test.dev", hashed_password=get_password_hash("x"))
    u2 = AdminUser(email="dr2@test.dev", hashed_password=get_password_hash("x"))
    db.add_all([u1, u2])
    db.flush()
    dh = "f" * 64
    record_device_usage(
        db,
        device_hash=dh,
        user_id=u1.id,
        event_type="auth.session.opened",
        ip_address="10.0.0.1",
        session_id=None,
    )
    record_device_usage(
        db,
        device_hash=dh,
        user_id=u2.id,
        event_type="auth.session.opened",
        ip_address="10.0.0.2",
        session_id=None,
    )
    rep = compute_device_reputation(db, dh)
    assert rep.unique_user_count == 2
    assert rep.global_risk_score >= 18


def test_progressive_finding_shared_device(db, monkeypatch):
    monkeypatch.setenv("DEVICE_REPUTATION_ENABLED", "true")
    monkeypatch.setenv("DEVICE_REPUTATION_SHARED_USER_FINDING_MIN", "2")
    u1 = AdminUser(email="df1@test.dev", hashed_password=get_password_hash("x"))
    u2 = AdminUser(email="df2@test.dev", hashed_password=get_password_hash("x"))
    db.add_all([u1, u2])
    db.flush()
    dh = "c" * 64
    record_device_usage(db, device_hash=dh, user_id=u1.id, event_type="auth.session.opened", ip_address="1.1.1.1")
    record_device_usage(db, device_hash=dh, user_id=u2.id, event_type="auth.session.opened", ip_address="1.1.1.2")
    compute_device_reputation(db, dh)
    n = db.query(AuthDeviceGraphFinding).filter(AuthDeviceGraphFinding.device_hash == dh).count()
    assert n >= 1


def test_blacklist_blocks_evaluate(db, monkeypatch):
    monkeypatch.setenv("DEVICE_REPUTATION_ENABLED", "true")
    dh = "b" * 64
    record_device_usage(db, device_hash=dh, user_id=None, event_type="auth.login.failed", ip_address="9.9.9.9")
    compute_device_reputation(db, dh)
    blacklist_device(db, dh, reason="test_block", blocked_until=None, created_by=None)
    db.commit()
    blocked, _, meta = evaluate_auth_impact(db, dh, user_id=1)
    assert blocked is True
    assert meta.get("device_reputation_level") == "BLOCKED"
    unblacklist_device(db, dh)
    db.commit()
    blocked2, _, _ = evaluate_auth_impact(db, dh, user_id=1)
    assert blocked2 is False


def test_persist_graph_finding_dedupe(db):
    dh = "d" * 64
    assert persist_graph_finding(db, finding_type="unit.test", severity="LOW", device_hash=dh, metadata={"x": 1})
    assert not persist_graph_finding(db, finding_type="unit.test", severity="LOW", device_hash=dh, metadata={"x": 2})
    db.commit()


def test_find_shared_devices_graph(db, monkeypatch):
    monkeypatch.setenv("DEVICE_REPUTATION_ENABLED", "true")
    u1 = AdminUser(email="g1@test.dev", hashed_password=get_password_hash("x"))
    u2 = AdminUser(email="g2@test.dev", hashed_password=get_password_hash("x"))
    db.add_all([u1, u2])
    db.flush()
    dh = "e" * 64
    record_device_usage(db, device_hash=dh, user_id=u1.id, event_type="x", ip_address="1.1.1.1")
    record_device_usage(db, device_hash=dh, user_id=u2.id, event_type="x", ip_address="1.1.1.2")
    out = find_shared_devices(db, min_user_count=2, window_days=30, persist=False)
    assert any(x["device_hash"] == dh for x in out)


def test_device_reputation_risk_engine_boost(db, monkeypatch):
    monkeypatch.setenv("DEVICE_REPUTATION_ENABLED", "true")
    monkeypatch.setenv("DEVICE_REPUTATION_RISK_ENGINE_INTEGRATION", "true")
    u1 = AdminUser(email="rb@test.dev", hashed_password=get_password_hash("x"))
    db.add(u1)
    db.flush()
    dh = "a" * 64
    for _ in range(5):
        record_device_usage(
            db,
            device_hash=dh,
            user_id=u1.id,
            event_type="auth.session.opened",
            ip_address="2.2.2.2",
            session_id=None,
        )
    rep = compute_device_reputation(db, dh)
    rep.global_risk_score = 80
    rep.reputation_level = "HIGH"
    db.flush()
    b = _device_reputation_user_boost(db, u1.id)
    assert b >= 10
