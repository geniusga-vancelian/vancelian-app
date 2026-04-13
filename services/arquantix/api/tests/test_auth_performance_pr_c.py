"""PR C — métriques auth, cache identité, niveaux jwt_only / strict_db (sans régression sécurité)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from auth import create_access_token
from conftest import make_admin_user_with_pe_client
from database import get_db
from services.auth.auth_performance_metrics import (
    get_auth_performance_metrics,
    reset_auth_performance_metrics,
)
from services.auth.auth_resolution import (
    resolve_auth_context_jwt_only,
    resolve_auth_context_strict_db,
    resolve_identity_for_auth_context_fast_with_client,
)
from services.auth.identity_cache import (
    clear_identity_cache_for_tests,
    get_client_id_for_person_cached,
    get_person_id_cached,
    PERSON_ID_CACHE_MISS,
)
from services.auth.jwt_user_claims import build_user_jwt_access_base_claims


@pytest.fixture(autouse=True)
def _reset_pr_c_metrics_and_cache():
    reset_auth_performance_metrics()
    clear_identity_cache_for_tests()
    yield
    reset_auth_performance_metrics()
    clear_identity_cache_for_tests()


@pytest.fixture(autouse=True)
def _auth_flow_rate_limit_isolation(monkeypatch):
    """Même garde-fous que test_auth_refresh (429 / ML login)."""
    from services.auth.auth_rate_limit import reset_auth_rate_limiter_for_tests

    monkeypatch.setenv("AUTH_RL_BACKEND", "memory")
    monkeypatch.setenv("AUTH_RL_LOGIN_MAX", "10000")
    monkeypatch.setenv("AUTH_RL_REFRESH_MAX", "10000")
    monkeypatch.setenv("AUTH_RL_REVOKE_MAX", "10000")
    monkeypatch.setenv("LOGIN_FRAUD_ML_EVALUATION_ENABLED", "false")
    monkeypatch.setenv("DEVICE_REPUTATION_ENABLED", "false")
    monkeypatch.setenv("LOGIN_AUTH_STRATEGY_ENABLED", "false")
    monkeypatch.setenv("LOGIN_DEVICE_TRUST_ENABLED", "false")
    reset_auth_rate_limiter_for_tests()
    yield
    reset_auth_rate_limiter_for_tests()


@pytest.fixture
def client_main_app_db(db):
    """TestClient sur ``main.app`` avec session DB transactionnelle (cf. test_auth_refresh)."""
    from main import app

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def test_jwt_only_increments_metric_without_db_path(db):
    """Niveau 1 : resolve_auth_context_jwt_only ne passe pas par strict_db (0 bump db pour ce module)."""
    u = make_admin_user_with_pe_client(db, email="jwt_only_metrics@example.com", password="p")
    db.commit()
    token = create_access_token(build_user_jwt_access_base_claims(u))

    m0 = get_auth_performance_metrics()
    ctx = resolve_auth_context_jwt_only(token)
    m1 = get_auth_performance_metrics()

    assert ctx.admin_user_id == u.id
    assert m1["auth_jwt_only_count"] == m0["auth_jwt_only_count"] + 1
    assert m1["auth_db_hits_count"] == m0["auth_db_hits_count"]


def test_strict_db_increments_db_metric(db):
    u = make_admin_user_with_pe_client(db, email="strict_db_metrics@example.com", password="p")
    db.commit()
    token = create_access_token(build_user_jwt_access_base_claims(u))

    m0 = get_auth_performance_metrics()
    user, _st = resolve_auth_context_strict_db(token, db)
    m1 = get_auth_performance_metrics()

    assert user.id == u.id
    assert m1["auth_db_hits_count"] == m0["auth_db_hits_count"] + 1
    assert m1["auth_resolution_mode_db"] == m0["auth_resolution_mode_db"] + 1


def test_fast_identity_jwt_only_no_admin_lookup(db):
    """Cache froid + ``person_id`` dans le JWT → mode jwt_only (pas de ``_get_current_user_internal``)."""
    u = make_admin_user_with_pe_client(db, email="fast_jwt_only@example.com", password="p")
    db.commit()
    token = create_access_token(build_user_jwt_access_base_claims(u))

    m0 = get_auth_performance_metrics()
    r = resolve_identity_for_auth_context_fast_with_client(token, db)
    m1 = get_auth_performance_metrics()

    assert r.resolution_mode == "jwt_only"
    assert r.user_id == u.id
    assert r.person_id == u.person_id
    assert m1["auth_db_hits_count"] == m0["auth_db_hits_count"]
    assert m1["auth_resolution_mode_jwt_only"] == m0["auth_resolution_mode_jwt_only"] + 1


def test_fast_identity_cache_hit_after_strict_warm(db):
    """Après ``strict_db`` le bundle est chaud : le fast path suivant est ``cache`` (0 nouveau hit DB résolution)."""
    u = make_admin_user_with_pe_client(db, email="fast_cache_after_warm@example.com", password="p")
    db.commit()
    token = create_access_token(build_user_jwt_access_base_claims(u))

    resolve_auth_context_strict_db(token, db)
    m0 = get_auth_performance_metrics()
    r = resolve_identity_for_auth_context_fast_with_client(token, db)
    m1 = get_auth_performance_metrics()

    assert r.resolution_mode == "cache"
    assert r.person_id == u.person_id
    assert m1["auth_db_hits_count"] == m0["auth_db_hits_count"]
    assert m1["auth_resolution_mode_cache"] == m0["auth_resolution_mode_cache"] + 1


def test_client_cache_second_call_is_cache_hit(db):
    u = make_admin_user_with_pe_client(db, email="cache_client@example.com", password="p")
    db.commit()
    assert u.person_id is not None

    m0 = get_auth_performance_metrics()
    c1 = get_client_id_for_person_cached(db, u.person_id)
    m1 = get_auth_performance_metrics()
    c2 = get_client_id_for_person_cached(db, u.person_id)
    m2 = get_auth_performance_metrics()

    assert c1 == c2
    assert m2["auth_cache_hits_count"] == m1["auth_cache_hits_count"] + 1
    assert m1["auth_cache_hits_count"] == m0["auth_cache_hits_count"]


def test_person_id_cache_ttl_expires(monkeypatch, db):
    """Après expiration TTL, lecture = miss (pas de hit cache)."""
    import services.auth.identity_cache as ic

    t = [1000.0]

    def fake_now():
        return t[0]

    monkeypatch.setattr(ic, "_now", fake_now)
    monkeypatch.setattr(ic, "get_ttl_seconds", lambda: 10)

    u = make_admin_user_with_pe_client(db, email="ttl_expire@example.com", password="p")
    db.commit()
    # exp = 1000 + 10 = 1010
    ic.set_person_id_cache(u.id, u.person_id)

    assert get_person_id_cached(u.id) == u.person_id
    m_hit = get_auth_performance_metrics()["auth_cache_hits_count"]

    t[0] = 1020.0  # > 1010 → entrée expirée
    assert get_person_id_cached(u.id) is PERSON_ID_CACHE_MISS
    assert get_auth_performance_metrics()["auth_cache_hits_count"] == m_hit


def test_coherence_jwt_only_vs_strict_db(db):
    u = make_admin_user_with_pe_client(db, email="cohere@example.com", password="p")
    db.commit()
    token = create_access_token(build_user_jwt_access_base_claims(u))

    j = resolve_auth_context_jwt_only(token)
    user, _ = resolve_auth_context_strict_db(token, db)

    assert j.admin_user_id == user.id
    assert j.person_id == user.person_id


def test_refresh_rotation_succeeds_not_jwt_only_path(client_main_app_db, db):
    """``/auth/refresh`` utilise ``perform_refresh`` (sessions / rotation PR A) — hors compteur ``auth_db_hits`` PR C résolution Bearer."""
    email = "refresh_db_pr_c@example.com"
    make_admin_user_with_pe_client(db, email=email, password="x")
    db.commit()
    login = client_main_app_db.post(
        "/auth/login",
        json={"email": email, "password": "x"},
        headers={"X-Device-ID": "legacy-unknown"},
    )
    assert login.status_code == 200
    rt = login.json()["refresh_token"]

    r = client_main_app_db.post("/auth/refresh", json={"refresh_token": rt})
    assert r.status_code == 200
    body = r.json()
    assert body.get("access_token")
    assert body.get("refresh_token")
    assert body["refresh_token"] != rt
