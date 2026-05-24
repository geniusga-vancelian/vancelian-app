"""Tests placeholders wallet dédiés (Solana, …) à solde 0."""
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
from services.privy_wallet.dedicated_wallet_assets import native_asset_for_dedicated_wallet
from services.privy_wallet.service import PrivyWalletLedgerService
from tests.conftest import ensure_admin_for_linked_client, make_linked_client
from tests.test_person_identity_bridge import _migration_156_applied

pytestmark = pytest.mark.skipif(
    not _migration_156_applied(),
    reason="Appliquer `alembic upgrade head` (156) pour les tests wallet dédiés.",
)

SOL_ADDR = "9wtGmqMamnKfz49XBwnJASbjcVnnKnT78qKopCL54TAk"


def test_native_asset_for_dedicated_wallet():
    assert native_asset_for_dedicated_wallet("solana") == "SOL"
    assert native_asset_for_dedicated_wallet("evm") is None
    assert native_asset_for_dedicated_wallet("ethereum") is None


def test_get_balances_includes_zero_sol_for_dedicated_wallet(db: Session):
    pe = make_linked_client(db)
    upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="solana",
        address=SOL_ADDR,
    )
    db.commit()

    response = PrivyWalletLedgerService().get_balances(db, person_id=pe.person_id)
    assert response.summary.positions_count == 1
    assert response.balances[0].asset == "SOL"
    assert response.balances[0].balance == "0"
    assert response.balances[0].dedicated_wallet is True


def test_get_balances_skips_evm_zero_eth_placeholder(db: Session):
    pe = make_linked_client(db)
    upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="evm",
        chain_id=1,
        address=f"0x{uuid.uuid4().hex[:40]}",
    )
    db.commit()

    response = PrivyWalletLedgerService().get_balances(db, person_id=pe.person_id)
    assert response.summary.positions_count == 0


def test_crypto_positions_includes_zero_sol(client: TestClient, db: Session):
    pe = make_linked_client(db)
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject="did:privy:dedicatedsoltest01",
        external_email="dedicated-sol@test.local",
    )
    upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="solana",
        address=SOL_ADDR,
    )
    db.commit()

    user = ensure_admin_for_linked_client(db, pe)
    token = create_access_token(build_user_jwt_access_base_claims(user))
    res = client.get(
        "/api/app/crypto-positions",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text
    assets = {row["asset"] for row in res.json().get("positions", [])}
    assert "SOL" in assets
    sol = next(row for row in res.json()["positions"] if row["asset"] == "SOL")
    assert sol["balance"] == "0"
    assert sol.get("dedicated_wallet") is True
