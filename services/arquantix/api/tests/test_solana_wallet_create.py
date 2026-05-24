"""Tests wallet Solana Privy — get_or_create idempotent."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import create_access_token
from services.auth.jwt_user_claims import build_user_jwt_access_base_claims
from services.auth.person_identity_bridge import (
    PROVIDER_PRIVY,
    link_external_identity_to_person,
    upsert_person_crypto_wallet,
)
from tests.conftest import ensure_admin_for_linked_client, make_linked_client
from tests.test_person_identity_bridge import _migration_156_applied

pytestmark = pytest.mark.skipif(
    not _migration_156_applied(),
    reason="Appliquer `alembic upgrade head` (156) pour les tests wallet Solana.",
)

SOL_ADDR = "9wtGmqMamnKfz49XBwnJASbjcVnnKnT78qKopCL54TAk"
PRIVY_USER = "did:privy:testsolwalletuser01"


def _auth_headers(db: Session, client_id):
    user = ensure_admin_for_linked_client(db, client_id)
    token = create_access_token(build_user_jwt_access_base_claims(user))
    return {"Authorization": f"Bearer {token}"}


def _link_privy(db: Session, person_id):
    link_external_identity_to_person(
        db,
        person_id=person_id,
        provider=PROVIDER_PRIVY,
        external_subject=PRIVY_USER,
        external_email="sol-wallet@test.local",
    )


def test_solana_get_status_linked(client: TestClient, db: Session):
    pe = make_linked_client(db)
    _link_privy(db, pe.person_id)
    upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="solana",
        address=SOL_ADDR,
        metadata_json={"privy_wallet_id": "existing-privy-id"},
    )
    db.commit()

    res = client.get(
        "/api/wallets/solana",
        headers=_auth_headers(db, pe),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "linked"
    assert body["address"] == SOL_ADDR


def test_solana_get_status_unlinked(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _link_privy(db, pe.person_id)
    db.commit()

    def _fake_fetch(_uid: str):
        return {
            "linked_accounts": [
                {
                    "type": "wallet",
                    "chain_type": "solana",
                    "address": SOL_ADDR,
                    "id": "linked-sol-wallet",
                    "wallet_client_type": "privy",
                }
            ]
        }

    monkeypatch.setattr(
        "services.privy.privy_wallet_service.fetch_privy_user",
        _fake_fetch,
    )
    monkeypatch.setattr(
        "services.privy.privy_wallet_service.privy_server_api_configured",
        lambda: True,
    )

    res = client.get(
        "/api/wallets/solana",
        headers=_auth_headers(db, pe),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "unlinked"
    assert body["address"] == SOL_ADDR
    assert body["wallet_id"] == "linked-sol-wallet"


def test_solana_get_status_missing(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _link_privy(db, pe.person_id)
    db.commit()

    monkeypatch.setattr(
        "services.privy.privy_wallet_service.fetch_privy_user",
        lambda _uid: {"linked_accounts": []},
    )
    monkeypatch.setattr(
        "services.privy.privy_wallet_service.privy_server_api_configured",
        lambda: True,
    )

    res = client.get(
        "/api/wallets/solana",
        headers=_auth_headers(db, pe),
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "missing"


def test_solana_create_requires_session(client: TestClient):
    res = client.post("/api/wallets/solana/create")
    assert res.status_code == 401


def test_solana_create_without_privy_link(client: TestClient, db: Session):
    pe = make_linked_client(db)
    db.commit()
    res = client.post(
        "/api/wallets/solana/create",
        headers=_auth_headers(db, pe),
    )
    assert res.status_code == 400
    assert res.json()["detail"]["code"] == "privy.solana_wallet.privy_not_linked"


def test_solana_create_new_wallet(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _link_privy(db, pe.person_id)
    db.commit()

    def _fake_create(*, privy_user_id: str, chain_type: str = "solana", idempotency_key=None):
        assert privy_user_id == PRIVY_USER
        assert chain_type == "solana"
        return {"id": "privy-wallet-sol-1", "address": SOL_ADDR, "chain_type": "solana"}

    def _fake_fetch(_uid: str):
        return {"linked_accounts": []}

    monkeypatch.setattr(
        "services.privy.privy_wallet_service.create_privy_wallet",
        _fake_create,
    )
    monkeypatch.setattr(
        "services.privy.privy_wallet_service.fetch_privy_user",
        _fake_fetch,
    )
    monkeypatch.setattr(
        "services.privy.privy_wallet_service.privy_server_api_configured",
        lambda: True,
    )

    res = client.post(
        "/api/wallets/solana/create",
        headers=_auth_headers(db, pe),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["address"] == SOL_ADDR
    assert body["chain_type"] == "solana"
    assert body["created"] is True
    assert body["wallet_id"] == "privy-wallet-sol-1"
    uuid.UUID(body["person_wallet_id"])


def test_solana_create_returns_existing_db_wallet(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _link_privy(db, pe.person_id)
    upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="solana",
        address=SOL_ADDR,
        metadata_json={"privy_wallet_id": "existing-privy-id"},
    )
    db.commit()

    def _fail_create(**kwargs):
        raise AssertionError("create_privy_wallet must not be called when wallet exists")

    monkeypatch.setattr(
        "services.privy.privy_wallet_service.create_privy_wallet",
        _fail_create,
    )

    res = client.post(
        "/api/wallets/solana/create",
        headers=_auth_headers(db, pe),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["address"] == SOL_ADDR
    assert body["created"] is False
    assert body["wallet_id"] == "existing-privy-id"


def test_solana_create_syncs_from_privy_linked_accounts(
    client: TestClient, db: Session, monkeypatch
):
    pe = make_linked_client(db)
    _link_privy(db, pe.person_id)
    db.commit()

    def _fake_fetch(_uid: str):
        return {
            "linked_accounts": [
                {
                    "type": "wallet",
                    "chain_type": "solana",
                    "address": SOL_ADDR,
                    "id": "linked-sol-wallet",
                    "wallet_client_type": "privy",
                }
            ]
        }

    def _fail_create(**kwargs):
        raise AssertionError("create_privy_wallet must not be called when linked account exists")

    monkeypatch.setattr(
        "services.privy.privy_wallet_service.fetch_privy_user",
        _fake_fetch,
    )
    monkeypatch.setattr(
        "services.privy.privy_wallet_service.create_privy_wallet",
        _fail_create,
    )
    monkeypatch.setattr(
        "services.privy.privy_wallet_service.privy_server_api_configured",
        lambda: True,
    )

    res = client.post(
        "/api/wallets/solana/create",
        headers=_auth_headers(db, pe),
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["address"] == SOL_ADDR
    assert body["created"] is False
    assert body["wallet_id"] == "linked-sol-wallet"
