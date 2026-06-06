"""Tests portfolio breakdown par actif (PR C — lecture seule, non additif)."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from services.portfolio_engine.internal_scope_movements.types import CurrentPeScopeSnapshot
from services.portfolio_engine.portfolio_breakdown import (
    BREAKDOWN_VERSION,
    build_asset_breakdown_row,
    build_portfolio_breakdown,
)
from tests.conftest import make_linked_client, mobile_auth_headers


def _gaelitier_usdc_pe() -> CurrentPeScopeSnapshot:
    pe = CurrentPeScopeSnapshot(person_id=uuid.uuid4(), client_id=uuid.uuid4())
    pe.trading_available["USDC"] = Decimal("62.64")
    pe.vault_position["USDC"] = Decimal("114.10")
    pe.bundle_cash["USDC"] = Decimal("17.57")
    pe.liability["USDC"] = Decimal("69")
    return pe


def test_usdc_breakdown_non_additive_total_holdings():
    """total_holdings = available + vault (+ collateral), pas la somme avec bundles."""
    pe = _gaelitier_usdc_pe()
    row = build_asset_breakdown_row(
        "USDC",
        pe=pe,
        ledger={"USDC": Decimal("176.74")},
        on_chain_base={"USDC": Decimal("62.641746")},
        pending_by_asset={},
    )
    assert row["total_holdings"] == "176.74"
    assert row["available"] == "62.64"
    assert row["in_vaults"] == "114.1"
    assert row["in_bundles"] == "17.57"
    assert row["swappable_balance"] == "62.641746"
    assert row["bundle_is_subset_of_wallet"] is True
    assert Decimal(row["non_additive_overlap"]) > 0
    assert row["components"]["in_bundles"]["bundle_is_subset_of_wallet"] is True
    assert row["components"]["in_bundles"]["additive"] is False


def test_swappable_respects_collateral_lock():
    pe = CurrentPeScopeSnapshot(person_id=uuid.uuid4(), client_id=uuid.uuid4())
    pe.trading_locked_collateral["CBBTC"] = Decimal("0.00031643")
    row = build_asset_breakdown_row(
        "CBBTC",
        pe=pe,
        ledger={"CBBTC": Decimal("0.00237")},
        on_chain_base={"CBBTC": Decimal("0.00237")},
        pending_by_asset={},
    )
    assert Decimal(row["swappable_balance"]) == Decimal("0.00237") - Decimal("0.00031643")


def test_build_portfolio_breakdown_doctrine_warnings(db: Session):
    pe = make_linked_client(db)
    with patch(
        "services.portfolio_engine.portfolio_breakdown.fetch_aggregated_on_chain_balances",
        return_value={},
    ):
        payload = build_portfolio_breakdown(db, pe.person_id)
    assert payload["breakdown_version"] == BREAKDOWN_VERSION
    assert payload["doctrine"]["swap_max_field"] == "swappable_balance"
    assert "bundle" in payload["warnings"][1].lower() or "sous-scopes" in payload["warnings"][1]
    assert "in_bundles" in payload["non_additive_components"]


def test_portfolio_breakdown_endpoint(client: TestClient, db: Session):
    pe = make_linked_client(db, email=f"bd-{uuid.uuid4().hex[:8]}@example.com")
    headers = mobile_auth_headers(db, pe)
    with patch(
        "services.portfolio_engine.portfolio_breakdown.fetch_aggregated_on_chain_balances",
        return_value={},
    ):
        res = client.get("/api/app/portfolio/breakdown", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["breakdown_version"] == BREAKDOWN_VERSION
    assert body["doctrine"]["hierarchy"][0] == "privy_ledger"
    assert isinstance(body["assets"], list)
