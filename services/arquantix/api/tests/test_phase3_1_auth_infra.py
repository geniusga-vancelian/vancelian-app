"""Phase 3.1 — rate limit Redis INCR, bootstrap prod, fingerprint, événements, corrélation."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from auth import get_password_hash
from database import AdminUser, AuthSecurityEvent, AuthSession, engine, get_db
from services.auth.auth_bootstrap import enforce_auth_infrastructure_bootstrap
from services.auth.auth_rate_limit import RedisIncrAuthRateLimiter, reset_auth_rate_limiter_for_tests
from services.auth.auth_redis import reset_auth_redis_pool_for_tests
from services.auth.device_fingerprint import parse_device_fingerprint_header
from services.auth.security_signal_service import SecuritySignalService


class _MiniRedis:
    """Sous-ensemble Redis pour valider INCR + expire côté limiteur (concurrence threads)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._n: dict[str, int] = {}

    def incr(self, key: str) -> int:
        with self._lock:
            self._n[key] = int(self._n.get(key, 0)) + 1
            return self._n[key]

    def expire(self, key: str, _sec: int) -> None:
        _ = key, _sec

    def ttl(self, key: str) -> int:
        _ = key
        return 60


def test_redis_incr_limiter_threads_exceed_quota(monkeypatch):
    monkeypatch.setenv("AUTH_RL_LOGIN_MAX", "5")
    monkeypatch.setenv("AUTH_RL_LOGIN_WINDOW_SEC", "60")
    r = _MiniRedis()
    lim = RedisIncrAuthRateLimiter(r)
    errors = []

    def hit():
        try:
            lim.check_login("1.2.3.4")
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=hit) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(errors) >= 1


def test_bootstrap_prod_requires_redis_backend(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ARQUANTIX_ENV", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("TWO_FACTOR_DEV_FIXED_CODE", raising=False)
    monkeypatch.delenv("TWO_FACTOR_DEV_EXPOSE_CODE", raising=False)
    monkeypatch.delenv("FAKE_SMS_PROVIDER", raising=False)
    monkeypatch.setenv("AUTH_RL_BACKEND", "memory")
    with pytest.raises(RuntimeError, match="AUTH_RL_BACKEND must be redis"):
        enforce_auth_infrastructure_bootstrap(testing=False)


def test_bootstrap_normalized_app_env_production_requires_redis_without_environment(monkeypatch):
    """AUTH_REDIS_ENV_STRATEGY=normalized : APP_ENV=production suffit (pas de ENVIRONMENT)."""
    monkeypatch.setenv("AUTH_REDIS_ENV_STRATEGY", "normalized")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("TWO_FACTOR_DEV_FIXED_CODE", raising=False)
    monkeypatch.delenv("TWO_FACTOR_DEV_EXPOSE_CODE", raising=False)
    monkeypatch.delenv("FAKE_SMS_PROVIDER", raising=False)
    monkeypatch.setenv("AUTH_RL_BACKEND", "memory")
    with pytest.raises(RuntimeError, match="AUTH_RL_BACKEND must be redis"):
        enforce_auth_infrastructure_bootstrap(testing=False)


def test_bootstrap_prod_requires_reachable_redis(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.delenv("ARQUANTIX_ENV", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("TWO_FACTOR_DEV_FIXED_CODE", raising=False)
    monkeypatch.delenv("TWO_FACTOR_DEV_EXPOSE_CODE", raising=False)
    monkeypatch.delenv("FAKE_SMS_PROVIDER", raising=False)
    monkeypatch.setenv("AUTH_RL_BACKEND", "redis")
    monkeypatch.setenv("AUTH_REDIS_URL", "redis://127.0.0.1:63979/0")
    reset_auth_redis_pool_for_tests()
    try:
        with pytest.raises(RuntimeError, match="reachable Redis"):
            enforce_auth_infrastructure_bootstrap(testing=False)
    finally:
        reset_auth_redis_pool_for_tests()


def test_parse_device_fingerprint_header_normalizes():
    raw = json.dumps(
        {
            "device_id": "d1",
            "install_id": str(uuid.uuid4()),
            "platform": "ios",
            "os_version": "17.0",
            "app_version": "1.0.0",
            "device_model": "iPhone",
        }
    )
    meta, h = parse_device_fingerprint_header(raw)
    assert meta is not None and h is not None and len(h) == 64
    assert meta["platform"] == "ios"


@pytest.fixture
def client_main_app_db(db):
    from main import app

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def _has_fingerprint_columns() -> bool:
    try:
        insp = inspect(engine)
        cols = {c["name"] for c in insp.get_columns("auth_sessions", schema="public")}
    except Exception:  # noqa: BLE001 — table absente / schéma partiel
        return False
    return "fingerprint_hash" in cols


def test_login_stores_fingerprint_when_migrated(client_main_app_db, db, monkeypatch):
    monkeypatch.setenv("AUTH_DEVICE_FINGERPRINT_ENABLED", "true")
    if not _has_fingerprint_columns():
        pytest.skip("Migration 109 non appliquée (colonnes fingerprint absentes).")

    email = "fp_store@example.com"
    db.add(AdminUser(email=email, hashed_password=get_password_hash("p")))
    db.commit()
    fp = {
        "device_id": "dev-fp-1",
        "install_id": str(uuid.uuid4()),
        "platform": "android",
        "os_version": "14",
        "app_version": "1.0.0+1",
    }
    r = client_main_app_db.post(
        "/auth/login",
        json={"email": email, "password": "p"},
        headers={
            "X-Device-ID": "dev-fp-1",
            "X-Device-Fingerprint": json.dumps(fp),
        },
    )
    assert r.status_code == 200
    user = db.query(AdminUser).filter(AdminUser.email == email).first()
    row = db.query(AuthSession).filter(AuthSession.user_id == user.id).first()
    assert row is not None
    assert row.fingerprint_hash is not None
    assert row.fingerprint_metadata is not None


def test_security_events_persist_in_transaction_when_enabled(client_main_app_db, db, monkeypatch):
    monkeypatch.setenv("AUTH_SECURITY_EVENTS_ENABLED", "true")
    if not _has_security_events_table():
        pytest.skip("Table auth_security_events absente (migration 109).")

    email = "sec_evt@example.com"
    db.add(AdminUser(email=email, hashed_password=get_password_hash("p")))
    db.commit()
    r = client_main_app_db.post("/auth/login", json={"email": email, "password": "p"})
    assert r.status_code == 200
    n = db.query(AuthSecurityEvent).filter(AuthSecurityEvent.event_type == "auth.login.succeeded").count()
    assert n >= 1


def _has_security_events_table() -> bool:
    try:
        return bool(inspect(engine).has_table("auth_security_events", schema="public"))
    except Exception:  # noqa: BLE001
        return False


def test_correlation_detects_refresh_reject_burst(db, monkeypatch):
    monkeypatch.setenv("AUTH_SECURITY_EVENTS_ENABLED", "true")
    if not _has_security_events_table():
        pytest.skip("Table auth_security_events absente (migration 109).")

    now = datetime.now(timezone.utc)
    for i in range(12):
        db.add(
            AuthSecurityEvent(
                id=uuid.uuid4(),
                user_id=None,
                device_id="",
                event_type="auth.refresh.rejected",
                ip_address="10.0.0.1",
                user_agent=None,
                metadata_payload={"i": i},
                created_at=now - timedelta(seconds=i),
            )
        )
        db.flush()
    flags = SecuritySignalService.detect_anomalies(db)
    assert flags.get("suspicious_ip") is True


@pytest.fixture(autouse=True)
def _reset_rl():
    reset_auth_rate_limiter_for_tests()
    yield
    reset_auth_rate_limiter_for_tests()
