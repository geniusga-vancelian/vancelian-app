"""Tests bridge identité Privy / externes + wallets non-custodial.

Nécessite la migration ``156`` appliquée (tables ``person_external_identities``,
``person_crypto_wallets``). Sinon les tests sont ignorés.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
import sqlalchemy as sa
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt
from sqlalchemy.orm import Session

from auth import ALGORITHM, SECRET_KEY
from database import AdminUser, Person, PersonCryptoWallet, engine
from services.auth.person_identity_bridge import (
    PROVIDER_PRIVY,
    DuplicateExternalIdentityError,
    PersonIdentityBridgeError,
    get_or_create_login_account_for_person_if_needed,
    get_person_from_external_identity,
    get_pe_client_for_person,
    link_external_identity_to_person,
    upsert_person_crypto_wallet,
)
from tests.conftest import make_linked_client


def _migration_156_applied() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'person_external_identities'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_156_applied(),
    reason="Appliquer `alembic upgrade head` (révision 156) pour les tests identity bridge.",
)


def test_link_external_identity_and_resolve(db: Session):
    p = Person(
        id=uuid.uuid4(),
        status="active",
        profile_json={},
        kyc_status="not_started",
    )
    db.add(p)
    db.flush()

    ext_subj = f"did:privy:test-{uuid.uuid4().hex[:12]}"
    row = link_external_identity_to_person(
        db,
        person_id=p.id,
        provider=PROVIDER_PRIVY,
        external_subject=ext_subj,
        external_email="u@example.com",
    )
    db.commit()

    assert row.person_id == p.id
    resolved = get_person_from_external_identity(
        db, provider=PROVIDER_PRIVY, external_subject=ext_subj
    )
    assert resolved is not None
    assert resolved.id == p.id


def test_duplicate_external_identity_rejected(db: Session):
    p1 = Person(
        id=uuid.uuid4(),
        status="active",
        profile_json={},
        kyc_status="not_started",
    )
    p2 = Person(
        id=uuid.uuid4(),
        status="active",
        profile_json={},
        kyc_status="not_started",
    )
    db.add_all([p1, p2])
    db.flush()
    subj = f"sub-{uuid.uuid4().hex}"
    link_external_identity_to_person(
        db, person_id=p1.id, provider=PROVIDER_PRIVY, external_subject=subj
    )
    db.commit()

    with pytest.raises(DuplicateExternalIdentityError):
        link_external_identity_to_person(
            db, person_id=p2.id, provider=PROVIDER_PRIVY, external_subject=subj
        )


def test_wallet_uniqueness_provider_chain_address(db: Session):
    pe = make_linked_client(db)
    pid = pe.person_id

    addr = "0x" + "ab" * 20
    upsert_person_crypto_wallet(
        db,
        person_id=pid,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="evm",
        address=addr,
        chain_id=1,
    )
    db.commit()

    with pytest.raises(PersonIdentityBridgeError):
        upsert_person_crypto_wallet(
            db,
            person_id=uuid.uuid4(),
            provider=PROVIDER_PRIVY,
            wallet_type="embedded",
            chain_type="evm",
            address=addr,
            chain_id=1,
        )


def test_get_or_create_login_account_for_person(db: Session):
    p = Person(
        id=uuid.uuid4(),
        status="active",
        profile_json={},
        kyc_status="not_started",
    )
    db.add(p)
    db.flush()

    u1 = get_or_create_login_account_for_person_if_needed(db, person_id=p.id)
    u2 = get_or_create_login_account_for_person_if_needed(db, person_id=p.id)
    db.commit()
    assert u1.id == u2.id
    assert u1.person_id == p.id


def test_resolve_pe_client_from_person(db: Session):
    c = make_linked_client(db)
    got = get_pe_client_for_person(db, person_id=c.person_id)
    assert got is not None
    assert got.id == c.id


def test_privy_exchange_stub_jwt_format(client: TestClient, db: Session, monkeypatch):
    monkeypatch.setenv("PRIVY_EXCHANGE_VERIFICATION_MODE", "stub")
    c = make_linked_client(db)
    ext = f"privy-sub-{uuid.uuid4().hex[:10]}"
    link_external_identity_to_person(
        db,
        person_id=c.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=ext,
    )
    db.commit()

    res = client.post(
        "/auth/privy/exchange",
        json={"privy_access_token": f"stub:{ext}"},
        headers={"X-Device-ID": f"dev-{uuid.uuid4().hex[:8]}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body.get("access_token")
    assert body.get("refresh_token")
    assert body.get("person_id") == str(c.person_id)
    assert body.get("pe_client_id") == str(c.id)
    assert isinstance(body.get("wallets"), list)
    pl = jose_jwt.decode(
        body["access_token"], SECRET_KEY, algorithms=[ALGORITHM]
    )
    sub = str(pl.get("sub") or "")
    assert sub.startswith("au:")
    assert pl.get("person_id") == str(c.person_id)


def test_privy_exchange_503_when_verification_unconfigured(client: TestClient, monkeypatch):
    monkeypatch.delenv("PRIVY_EXCHANGE_VERIFICATION_MODE", raising=False)
    res = client.post(
        "/auth/privy/exchange",
        json={"privy_access_token": "stub:anything"},
    )
    assert res.status_code == 503
    assert res.json()["detail"]["code"] == "privy.verification_not_configured"


def test_privy_exchange_stub_forbidden_in_production(client: TestClient, monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setenv("PRIVY_EXCHANGE_VERIFICATION_MODE", "stub")
    res = client.post(
        "/auth/privy/exchange",
        json={"privy_access_token": "stub:any-subject"},
    )
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "privy.stub_forbidden_in_production"


def test_privy_exchange_token_missing(client: TestClient, monkeypatch):
    monkeypatch.setenv("PRIVY_EXCHANGE_VERIFICATION_MODE", "stub")
    res = client.post("/auth/privy/exchange", json={})
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "privy.token_missing"


def test_privy_exchange_token_invalid_stub(client: TestClient, monkeypatch):
    monkeypatch.setenv("PRIVY_EXCHANGE_VERIFICATION_MODE", "stub")
    res = client.post(
        "/auth/privy/exchange",
        json={"privy_access_token": "not-a-stub-token"},
    )
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "privy.token_invalid"


def test_privy_exchange_wallet_address_invalid(client: TestClient, db: Session, monkeypatch):
    monkeypatch.setenv("PRIVY_EXCHANGE_VERIFICATION_MODE", "stub")
    c = make_linked_client(db)
    ext = f"privy-sub-{uuid.uuid4().hex[:10]}"
    link_external_identity_to_person(
        db,
        person_id=c.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=ext,
    )
    db.commit()
    res = client.post(
        "/auth/privy/exchange",
        json={
            "privy_access_token": f"stub:{ext}",
            "wallets": [
                {
                    "address": "0xnotvalid",
                    "chain_type": "evm",
                    "wallet_type": "embedded",
                }
            ],
        },
        headers={"X-Device-ID": f"dev-{uuid.uuid4().hex[:8]}"},
    )
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "privy.wallet_address_invalid"


def test_privy_exchange_wallet_persisted(client: TestClient, db: Session, monkeypatch):
    monkeypatch.setenv("PRIVY_EXCHANGE_VERIFICATION_MODE", "stub")
    c = make_linked_client(db)
    ext = f"privy-sub-{uuid.uuid4().hex[:10]}"
    link_external_identity_to_person(
        db,
        person_id=c.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=ext,
    )
    db.commit()
    addr = "0x" + "cd" * 20
    res = client.post(
        "/auth/privy/exchange",
        json={
            "privy_access_token": f"stub:{ext}",
            "wallets": [
                {
                    "address": addr,
                    "chain_type": "evm",
                    "chain_id": 1,
                    "wallet_type": "embedded",
                }
            ],
        },
        headers={"X-Device-ID": f"dev-{uuid.uuid4().hex[:8]}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert any(w.get("address") == addr.lower() for w in body.get("wallets", []))
    row = (
        db.query(PersonCryptoWallet)
        .filter(
            PersonCryptoWallet.person_id == c.person_id,
            PersonCryptoWallet.address == addr.lower(),
        )
        .first()
    )
    assert row is not None


def test_privy_exchange_jwt_verified_roundtrip(client: TestClient, db: Session, monkeypatch):
    priv_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    priv_pem = priv_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    pub_pem = priv_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    app_id = f"privy-test-app-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("PRIVY_EXCHANGE_VERIFICATION_MODE", "jwt")
    monkeypatch.setenv("PRIVY_APP_ID", app_id)
    monkeypatch.setenv("PRIVY_JWT_VERIFICATION_KEY", pub_pem)

    c = make_linked_client(db)
    ext = f"jwt-privy-{uuid.uuid4().hex[:12]}"
    link_external_identity_to_person(
        db,
        person_id=c.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=ext,
    )
    db.commit()

    claims = {
        "sub": ext,
        "iss": "privy.io",
        "aud": app_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        "email": "jwt-privy@example.com",
    }
    bearer = jose_jwt.encode(claims, priv_pem, algorithm="ES256")

    res = client.post(
        "/auth/privy/exchange",
        json={"privy_access_token": bearer},
        headers={"X-Device-ID": f"dev-{uuid.uuid4().hex[:8]}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    pl = jose_jwt.decode(body["access_token"], SECRET_KEY, algorithms=[ALGORITHM])
    assert str(pl.get("sub") or "").startswith("au:")
    assert pl.get("person_id") == str(c.person_id)


def test_privy_exchange_jwt_login_email_body_fallback(client: TestClient, db: Session, monkeypatch):
    """Web prod : JWT access sans e-mail + adresse OTP dans le corps → rattachement AdminUser."""
    priv_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    priv_pem = priv_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    pub_pem = priv_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    app_id = f"privy-test-app-{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("PRIVY_EXCHANGE_VERIFICATION_MODE", "jwt")
    monkeypatch.setenv("PRIVY_APP_ID", app_id)
    monkeypatch.setenv("PRIVY_JWT_VERIFICATION_KEY", pub_pem)

    from tests.conftest import make_admin_user_with_pe_client

    login_email = f"web-login-{uuid.uuid4().hex[:8]}@example.com"
    make_admin_user_with_pe_client(db, email=login_email, password="test")
    db.commit()

    ext = f"jwt-privy-no-email-{uuid.uuid4().hex[:12]}"
    claims = {
        "sub": ext,
        "iss": "privy.io",
        "aud": app_id,
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
    }
    bearer = jose_jwt.encode(claims, priv_pem, algorithm="ES256")

    res = client.post(
        "/auth/privy/exchange",
        json={"privy_access_token": bearer, "email": login_email},
        headers={"X-Device-ID": f"dev-{uuid.uuid4().hex[:8]}"},
    )
    assert res.status_code == 200, res.text
    linked = get_person_from_external_identity(db, provider=PROVIDER_PRIVY, external_subject=ext)
    assert linked is not None


def test_privy_exchange_idempotent_single_admin_user(client: TestClient, db: Session, monkeypatch):
    monkeypatch.setenv("PRIVY_EXCHANGE_VERIFICATION_MODE", "stub")
    c = make_linked_client(db)
    ext = f"privy-sub-{uuid.uuid4().hex[:10]}"
    link_external_identity_to_person(
        db,
        person_id=c.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=ext,
    )
    db.commit()
    hdrs = {"X-Device-ID": f"dev-{uuid.uuid4().hex[:8]}"}
    payload = {"privy_access_token": f"stub:{ext}"}
    r1 = client.post("/auth/privy/exchange", json=payload, headers=hdrs)
    assert r1.status_code == 200
    n_mid = db.query(AdminUser).filter(AdminUser.person_id == c.person_id).count()
    r2 = client.post("/auth/privy/exchange", json=payload, headers=hdrs)
    assert r2.status_code == 200
    n_after = db.query(AdminUser).filter(AdminUser.person_id == c.person_id).count()
    assert n_mid == 1
    assert n_after == 1
