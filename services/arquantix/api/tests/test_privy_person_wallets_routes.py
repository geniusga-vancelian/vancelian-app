"""Tests ``GET /auth/privy/person-wallets``."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import create_access_token
from services.auth.jwt_user_claims import build_user_jwt_access_base_claims
from services.auth.person_identity_bridge import upsert_person_crypto_wallet
from tests.conftest import ensure_admin_for_linked_client, make_linked_client
from tests.test_person_identity_bridge import _migration_156_applied


pytestmark = pytest.mark.skipif(
    not _migration_156_applied(),
    reason="Appliquer `alembic upgrade head` (156) pour les tests person wallets.",
)


def test_person_wallets_requires_session(client: TestClient):
    res = client.get("/auth/privy/person-wallets")
    assert res.status_code == 401
    assert res.json()["detail"]["code"] == "privy.person_wallets_requires_session"


def test_person_wallets_empty(client: TestClient, db: Session):
    c = make_linked_client(db)
    u = ensure_admin_for_linked_client(db, c)
    db.commit()
    token = create_access_token(build_user_jwt_access_base_claims(u))
    res = client.get(
        "/auth/privy/person-wallets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    assert res.json().get("wallets") == []


def test_person_wallets_returns_row(client: TestClient, db: Session):
    c = make_linked_client(db)
    u = ensure_admin_for_linked_client(db, c)
    db.commit()
    addr = "0x" + "a" * 40
    upsert_person_crypto_wallet(
        db,
        person_id=c.person_id,
        pe_client_id=c.id,
        provider="privy",
        wallet_type="embedded",
        chain_type="evm",
        address=addr.lower(),
        chain_id=1,
        is_primary=True,
        metadata_json=None,
    )
    db.commit()

    token = create_access_token(build_user_jwt_access_base_claims(u))
    res = client.get(
        "/auth/privy/person-wallets",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    wallets = res.json().get("wallets") or []
    assert len(wallets) == 1
    assert wallets[0]["address"] == addr.lower()
    assert wallets[0]["chain_type"] == "evm"
    uuid.UUID(str(wallets[0]["id"]))
