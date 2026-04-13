"""Login + refresh + revoke (JWT) — routes enregistrées sur l’instance globale ``main.app``."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from auth import ALGORITHM, SECRET_KEY, get_password_hash
from database import AdminUser, AuthRefreshToken, AuthSession, get_db
from conftest import make_admin_user_with_pe_client

# Aligné sur `legacy-unknown` quand le login est sans en-tête device.
_HDR_LEGACY = {"X-Device-ID": "legacy-unknown"}


@pytest.fixture(autouse=True)
def _reset_auth_rate_limiter_each_test(monkeypatch):
    """Évite 429 entre tests (IP partagée ``testclient``) et isole le backend mémoire."""
    from services.auth.auth_rate_limit import reset_auth_rate_limiter_for_tests

    monkeypatch.setenv("AUTH_RL_BACKEND", "memory")
    monkeypatch.setenv("AUTH_RL_LOGIN_MAX", "10000")
    monkeypatch.setenv("AUTH_RL_REFRESH_MAX", "10000")
    monkeypatch.setenv("AUTH_RL_REVOKE_MAX", "10000")
    # Évite step_up_otp dans le JWT (sinon 403 sur /auth/revoke-all via enforce_access_security).
    monkeypatch.setenv("LOGIN_FRAUD_ML_EVALUATION_ENABLED", "false")
    monkeypatch.setenv("DEVICE_REPUTATION_ENABLED", "false")
    monkeypatch.setenv("LOGIN_AUTH_STRATEGY_ENABLED", "false")
    monkeypatch.setenv("LOGIN_DEVICE_TRUST_ENABLED", "false")
    reset_auth_rate_limiter_for_tests()
    yield
    reset_auth_rate_limiter_for_tests()


@pytest.fixture
def client_main_app_db(db):
    """TestClient sur ``main.app`` avec la même session DB transactionnelle que [db]."""
    from main import app

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


def test_login_rejects_admin_without_portfolio_customer(client_main_app_db, db):
    """Compte admin sans Person + pe_clients : pas de JWT (connexion web Next.js hors scope)."""
    email = "admin_only_jwt@example.com"
    db.add(AdminUser(email=email, hashed_password=get_password_hash("p")))
    db.commit()
    r = client_main_app_db.post("/auth/login", json={"email": email, "password": "p"})
    assert r.status_code == 403
    assert r.json()["detail"]["code"] == "APP_JWT_REQUIRES_CUSTOMER"


def test_login_returns_access_and_refresh(client_main_app_db, db):
    email = "refresh_flow_test@example.com"
    make_admin_user_with_pe_client(db, email=email, password="Correct-Horse-99!")
    db.commit()

    r = client_main_app_db.post(
        "/auth/login",
        json={"email": email, "password": "Correct-Horse-99!"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body.get("access_token")
    assert body.get("refresh_token")
    assert body.get("token_type") == "bearer"
    did = body.get("device_id")
    assert did and str(did).startswith("srvtmp-")


def test_refresh_rotates_tokens(client_main_app_db, db):
    email = "refresh_rotate@example.com"
    make_admin_user_with_pe_client(db, email=email, password="x")
    db.commit()
    login = client_main_app_db.post(
        "/auth/login",
        json={"email": email, "password": "x"},
    )
    rt = login.json()["refresh_token"]
    r2 = client_main_app_db.post("/auth/refresh", json={"refresh_token": rt})
    assert r2.status_code == 200
    d2 = r2.json()
    assert d2["access_token"]
    assert d2.get("refresh_token")
    assert d2["refresh_token"] != rt


def test_refresh_rejects_access_token(client_main_app_db, db):
    email = "refresh_reject@example.com"
    make_admin_user_with_pe_client(db, email=email, password="y")
    db.commit()
    login = client_main_app_db.post(
        "/auth/login",
        json={"email": email, "password": "y"},
    )
    at = login.json()["access_token"]
    r = client_main_app_db.post("/auth/refresh", json={"refresh_token": at})
    assert r.status_code == 401


def test_revoke_returns_204(client_main_app_db, db):
    email = "revoke_test@example.com"
    make_admin_user_with_pe_client(db, email=email, password="z")
    db.commit()
    login = client_main_app_db.post(
        "/auth/login",
        json={"email": email, "password": "z"},
    )
    rt = login.json()["refresh_token"]
    r = client_main_app_db.post(
        "/auth/revoke",
        json={"refresh_token": rt},
        headers=_HDR_LEGACY,
    )
    assert r.status_code == 204


def test_login_creates_auth_session_row(client_main_app_db, db):
    email = "session_row@example.com"
    make_admin_user_with_pe_client(db, email=email, password="pw")
    db.commit()
    user = db.query(AdminUser).filter(AdminUser.email == email).first()
    assert db.query(AuthSession).filter(AuthSession.user_id == user.id).count() == 0

    r = client_main_app_db.post(
        "/auth/login",
        json={"email": email, "password": "pw"},
        headers={"X-Device-ID": "unit-test-device"},
    )
    assert r.status_code == 200
    row = db.query(AuthSession).filter(AuthSession.user_id == user.id).one()
    assert row.device_id == "unit-test-device"
    assert row.revoked_at is None


def test_refresh_rejects_reused_refresh_token(client_main_app_db, db):
    email = "reuse@example.com"
    make_admin_user_with_pe_client(db, email=email, password="p")
    db.commit()
    login = client_main_app_db.post("/auth/login", json={"email": email, "password": "p"})
    rt1 = login.json()["refresh_token"]
    r2 = client_main_app_db.post("/auth/refresh", json={"refresh_token": rt1})
    assert r2.status_code == 200
    r3 = client_main_app_db.post("/auth/refresh", json={"refresh_token": rt1})
    assert r3.status_code == 401
    pl1 = jwt.decode(rt1, SECRET_KEY, algorithms=[ALGORITHM])
    sess = db.query(AuthSession).filter(AuthSession.id == pl1["sid"]).first()
    assert sess is not None
    assert sess.revoke_reason == "refresh_token_reuse_detected"
    assert sess.revoked_at is not None


def test_refresh_jwt_contains_sid_and_did(client_main_app_db, db):
    email = "sid-claim@example.com"
    make_admin_user_with_pe_client(db, email=email, password="p")
    db.commit()
    login = client_main_app_db.post("/auth/login", json={"email": email, "password": "p"})
    rt = login.json()["refresh_token"]
    pl = jwt.decode(rt, SECRET_KEY, algorithms=[ALGORITHM])
    assert pl.get("typ") == "refresh"
    assert pl.get("sid")
    assert pl.get("did") == pl.get("device_id")
    row = db.query(AuthSession).filter(AuthSession.id == pl["sid"]).one()
    assert row.refresh_jti == pl["jti"]


def test_chain_rotation_second_rt_works_first_rt_rejected(client_main_app_db, db):
    """Après rotation, seul le dernier refresh est valide ; l’ancien révoque la session si rejoué."""
    email = "chain-rot@example.com"
    make_admin_user_with_pe_client(db, email=email, password="p")
    db.commit()
    login = client_main_app_db.post("/auth/login", json={"email": email, "password": "p"})
    rt_a = login.json()["refresh_token"]
    r_b = client_main_app_db.post("/auth/refresh", json={"refresh_token": rt_a})
    assert r_b.status_code == 200
    rt_b = r_b.json()["refresh_token"]
    assert rt_a != rt_b
    r_c = client_main_app_db.post("/auth/refresh", json={"refresh_token": rt_b})
    assert r_c.status_code == 200
    stale = client_main_app_db.post("/auth/refresh", json={"refresh_token": rt_a})
    assert stale.status_code == 401
    pl_b = jwt.decode(rt_b, SECRET_KEY, algorithms=[ALGORITHM])
    sess = db.query(AuthSession).filter(AuthSession.id == pl_b["sid"]).first()
    assert sess is not None
    assert sess.revoked_at is not None


def test_stale_refresh_without_auth_refresh_row_revokes_via_sid(client_main_app_db, db):
    """Sans ligne ``auth_refresh_tokens`` pour l’ancien jti, le chemin ``sid`` + jti incohérent révoque."""
    email = "sid-gap@example.com"
    make_admin_user_with_pe_client(db, email=email, password="p")
    db.commit()
    login = client_main_app_db.post("/auth/login", json={"email": email, "password": "p"})
    rt_a = login.json()["refresh_token"]
    pl_a = jwt.decode(rt_a, SECRET_KEY, algorithms=[ALGORITHM])
    jti_a = pl_a["jti"]
    r_b = client_main_app_db.post("/auth/refresh", json={"refresh_token": rt_a})
    assert r_b.status_code == 200
    db.query(AuthRefreshToken).filter(AuthRefreshToken.jti == str(jti_a)[:64]).delete(
        synchronize_session=False
    )
    db.commit()
    stale = client_main_app_db.post("/auth/refresh", json={"refresh_token": rt_a})
    assert stale.status_code == 401
    sess = db.query(AuthSession).filter(AuthSession.id == pl_a["sid"]).first()
    assert sess is not None
    assert sess.revoked_at is not None
    assert sess.revoke_reason == "refresh_sid_jti_mismatch_or_stale"


def test_refresh_rejects_device_mismatch(client_main_app_db, db):
    email = "devmis@example.com"
    make_admin_user_with_pe_client(db, email=email, password="p")
    db.commit()
    login = client_main_app_db.post(
        "/auth/login",
        json={"email": email, "password": "p"},
        headers={"X-Device-ID": "phone-a"},
    )
    rt = login.json()["refresh_token"]
    pl = jwt.decode(rt, SECRET_KEY, algorithms=[ALGORITHM])
    bad = client_main_app_db.post(
        "/auth/refresh",
        json={"refresh_token": rt},
        headers={"X-Device-ID": "phone-b"},
    )
    assert bad.status_code == 401
    sess = db.query(AuthSession).filter(AuthSession.id == pl["sid"]).one()
    assert sess.revoked_at is not None
    assert sess.revoke_reason == "device_jwt_header_conflict"


def test_device_binding_migrates_legacy_unknown_session(client_main_app_db, db):
    """Session créée avec ``legacy-unknown`` explicite → premier refresh avec un vrai device migre la ligne."""
    email = "bind-migrate@example.com"
    make_admin_user_with_pe_client(db, email=email, password="p")
    db.commit()
    login = client_main_app_db.post(
        "/auth/login",
        json={"email": email, "password": "p"},
        headers={"X-Device-ID": "legacy-unknown"},
    )
    assert login.status_code == 200
    rt = login.json()["refresh_token"]
    pl = jwt.decode(rt, SECRET_KEY, algorithms=[ALGORITHM])
    sid = pl["sid"]
    row = db.query(AuthSession).filter(AuthSession.id == sid).one()
    assert row.device_id == "legacy-unknown"
    r2 = client_main_app_db.post(
        "/auth/refresh",
        json={"refresh_token": rt},
        headers={"X-Device-ID": "migrated-handset-1"},
    )
    assert r2.status_code == 200
    db.refresh(row)
    assert row.device_id == "migrated-handset-1"


def test_srvtmp_session_promotes_to_client_device_once(client_main_app_db, db):
    """``srvtmp-*`` = bootstrap serveur ; un seul passage vers un ID client stable, puis binding strict."""
    email = "srvtmp-promo@example.com"
    make_admin_user_with_pe_client(db, email=email, password="p")
    db.commit()
    login = client_main_app_db.post("/auth/login", json={"email": email, "password": "p"})
    assert login.status_code == 200
    body = login.json()
    assert body.get("device_id", "").startswith("srvtmp-")
    rt = body["refresh_token"]
    pl = jwt.decode(rt, SECRET_KEY, algorithms=[ALGORITHM])
    assert str(pl.get("device_id", "")).startswith("srvtmp-")
    sid = pl["sid"]
    row = db.query(AuthSession).filter(AuthSession.id == sid).one()
    assert row.device_id.startswith("srvtmp-")
    r2 = client_main_app_db.post(
        "/auth/refresh",
        json={"refresh_token": rt},
        headers={"X-Device-ID": "flutter-stable-device-99"},
    )
    assert r2.status_code == 200
    db.refresh(row)
    assert row.device_id == "flutter-stable-device-99"
    rt2 = r2.json()["refresh_token"]
    pl2 = jwt.decode(rt2, SECRET_KEY, algorithms=[ALGORITHM])
    assert pl2["device_id"] == "flutter-stable-device-99"
    r3 = client_main_app_db.post(
        "/auth/refresh",
        json={"refresh_token": rt2},
        headers={"X-Device-ID": "other-handset"},
    )
    assert r3.status_code == 401


def test_revoke_then_refresh_rejected(client_main_app_db, db):
    email = "rvk@example.com"
    make_admin_user_with_pe_client(db, email=email, password="p")
    db.commit()
    login = client_main_app_db.post("/auth/login", json={"email": email, "password": "p"})
    rt = login.json()["refresh_token"]
    assert (
        client_main_app_db.post(
            "/auth/revoke",
            json={"refresh_token": rt},
            headers=_HDR_LEGACY,
        ).status_code
        == 204
    )
    assert client_main_app_db.post("/auth/refresh", json={"refresh_token": rt}).status_code == 401


def test_revoke_all_invalidates_refresh(client_main_app_db, db):
    email = "all@example.com"
    make_admin_user_with_pe_client(db, email=email, password="p")
    db.commit()
    login = client_main_app_db.post("/auth/login", json={"email": email, "password": "p"})
    at = login.json()["access_token"]
    rt = login.json()["refresh_token"]
    ra = client_main_app_db.post(
        "/auth/revoke-all",
        headers={"Authorization": f"Bearer {at}"},
    )
    assert ra.status_code == 204
    assert client_main_app_db.post("/auth/refresh", json={"refresh_token": rt}).status_code == 401
