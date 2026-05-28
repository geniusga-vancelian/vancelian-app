"""Tests GET /api/admin/customers/{person_id}/portfolio."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from services.auth.person_identity_bridge import upsert_person_crypto_wallet
from services.privy_wallet.admin_service import PrivyWalletAdminService
from services.privy_wallet.schemas import PrivySimulateDepositRequest
from tests.conftest import ensure_admin_for_linked_client, make_linked_client
from tests.test_person_identity_bridge import _migration_156_applied

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-admin@example.com",
    "X-Actor-Roles": "admin",
}

pytestmark = pytest.mark.skipif(
    not _migration_156_applied(),
    reason="Migration 156+ required for privy wallet tables.",
)


def test_portfolio_not_found(client: TestClient):
    res = client.get(f"/api/admin/customers/{uuid.uuid4()}/portfolio", headers=ADMIN_HEADERS)
    assert res.status_code == 404


def test_portfolio_includes_merged_privy_crypto(client: TestClient, db: Session):
    c = make_linked_client(db)
    ensure_admin_for_linked_client(db, c)
    addr = "0x" + "b" * 40
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

    svc = PrivyWalletAdminService()
    svc.simulate_deposit(
        db,
        PrivySimulateDepositRequest(
            person_id=c.person_id,
            amount="50",
            asset="USDC",
            chain_id=8453,
        ),
    )
    db.commit()

    res = client.get(
        f"/api/admin/customers/{c.person_id}/portfolio",
        headers=ADMIN_HEADERS,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["person_id"] == str(c.person_id)
    assert data["pe_client_id"] == str(c.id)
    assert isinstance(data["crypto"], list)
    usdc = next((row for row in data["crypto"] if row["asset"] == "USDC"), None)
    assert usdc is not None
    assert usdc["privy_balance"] == "50"
    assert usdc["network"] == "Base"
    assert usdc["chain_id"] == 8453
    assert usdc["source"] in ("privy", "merged")
    assert len(data["transactions"]) >= 1
    assert data["privy_admin"]["availability"] in ("available", "not_available")
