"""Tests trading_available sur GET /api/app/crypto-positions/direct (vault invest UI)."""
from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom
from services.portfolio_engine.vault_execution.vault_funding import fund_vault_from_self_trading

from conftest import make_linked_client
from tests.test_bundle_lifi_funding import _instrument_usdc
from tests.test_privy_wallet_deposits import mobile_auth_headers


def test_direct_crypto_positions_exposes_trading_available_separate_from_merged_balance(
    client: TestClient,
    db: Session,
):
    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    sync_direct_atom(db, ensure_direct_portfolio(db, pe.id).id, usdc.id, Decimal("100"), Decimal("86"))
    fund_vault_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        asset="USDC",
        instrument_id=usdc.id,
        amount=Decimal("90"),
        linked_reference_id=f"cl{uuid.uuid4().hex[:22]}",
    )
    db.commit()

    headers = mobile_auth_headers(db, pe)
    res = client.get("/api/app/crypto-positions/direct", headers=headers)
    assert res.status_code == 200, res.text
    usdc_row = next((p for p in res.json()["positions"] if p["asset"] == "USDC"), None)
    assert usdc_row is not None
    assert Decimal(str(usdc_row["trading_available"])) == Decimal("10")
    assert Decimal(str(usdc_row["platform_balance"])) == Decimal("10")
    assert Decimal(str(usdc_row["balance"])) >= Decimal("10")
