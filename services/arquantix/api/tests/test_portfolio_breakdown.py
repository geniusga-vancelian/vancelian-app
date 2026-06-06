"""Tests portfolio breakdown par actif (PR C + P1.1 — lecture seule, non additif)."""
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
    """total_holdings ≈ 176.74 — bundle non additif (pas 194.31)."""
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
    assert row["swappable_balance"] == "62.64"
    assert row["bundle_is_subset_of_wallet"] is True
    assert row["in_bundles_additive"] is False
    assert row["bundle_incremental_value"] == "0"
    assert Decimal(row["non_additive_overlap"]) == Decimal("17.57")
    naive_sum = Decimal("62.64") + Decimal("114.10") + Decimal("17.57")
    assert Decimal(row["total_holdings"]) < naive_sum


def test_link_bundle_only_total_includes_bundles():
    pe = CurrentPeScopeSnapshot(person_id=uuid.uuid4(), client_id=uuid.uuid4())
    pe.bundle_cash["LINK"] = Decimal("0.3146897938")
    row = build_asset_breakdown_row(
        "LINK",
        pe=pe,
        ledger={"LINK": Decimal("0.3146897938")},
        on_chain_base={"LINK": Decimal("0.3146897938")},
        pending_by_asset={},
    )
    assert Decimal(row["total_holdings"]) > 0
    assert row["total_holdings"] == row["in_bundles"]
    assert row["in_bundles_additive"] is True
    assert row["bundle_is_subset_of_wallet"] is False
    assert row["bundle_incremental_value"] == row["in_bundles"]
    assert Decimal(row["non_additive_overlap"]) == 0


def test_cbbtc_collateral_swappable_zero():
    pe = CurrentPeScopeSnapshot(person_id=uuid.uuid4(), client_id=uuid.uuid4())
    pe.trading_locked_collateral["CBBTC"] = Decimal("0.00031643")
    row = build_asset_breakdown_row(
        "CBBTC",
        pe=pe,
        ledger={"CBBTC": Decimal("0.00237")},
        on_chain_base={"CBBTC": Decimal("0.00205355")},
        pending_by_asset={},
    )
    assert row["available"] == "0"
    assert Decimal(row["locked_collateral"]) > 0
    assert Decimal(row["swappable_balance"]) == 0


def test_cbeth_collateral_swappable_zero():
    pe = CurrentPeScopeSnapshot(person_id=uuid.uuid4(), client_id=uuid.uuid4())
    pe.trading_locked_collateral["CBETH"] = Decimal("0.0047296265")
    row = build_asset_breakdown_row(
        "CBETH",
        pe=pe,
        ledger={"CBETH": Decimal("0.006542223")},
        on_chain_base={"CBETH": Decimal("0.0018125965")},
        pending_by_asset={},
    )
    assert row["available"] == "0"
    assert Decimal(row["locked_collateral"]) > 0
    assert Decimal(row["swappable_balance"]) == 0


def test_swappable_available_gt_on_chain_caps_at_on_chain():
    pe = CurrentPeScopeSnapshot(person_id=uuid.uuid4(), client_id=uuid.uuid4())
    pe.trading_available["USDC"] = Decimal("100")
    row = build_asset_breakdown_row(
        "USDC",
        pe=pe,
        ledger={"USDC": Decimal("100")},
        on_chain_base={"USDC": Decimal("38")},
        pending_by_asset={},
    )
    assert Decimal(row["swappable_balance"]) == Decimal("38")


def test_swappable_available_lt_on_chain_caps_at_available():
    pe = CurrentPeScopeSnapshot(person_id=uuid.uuid4(), client_id=uuid.uuid4())
    pe.trading_available["USDC"] = Decimal("10")
    row = build_asset_breakdown_row(
        "USDC",
        pe=pe,
        ledger={"USDC": Decimal("10")},
        on_chain_base={"USDC": Decimal("38")},
        pending_by_asset={},
    )
    assert Decimal(row["swappable_balance"]) == Decimal("10")


def test_gaelitier_prod_snapshot_p1_1():
    """Snapshot prod gaelitier (juin 2026) — critères review."""
    pe = CurrentPeScopeSnapshot(person_id=uuid.uuid4(), client_id=uuid.uuid4())
    pe.trading_available["USDC"] = Decimal("62.64")
    pe.vault_position["USDC"] = Decimal("114.10")
    pe.bundle_cash["USDC"] = Decimal("17.57")
    pe.liability["USDC"] = Decimal("69")
    pe.trading_available["EURC"] = Decimal("91.414272")
    pe.trading_locked_collateral["CBBTC"] = Decimal("0.00031643")
    pe.trading_locked_collateral["CBETH"] = Decimal("0.0047296265")
    pe.bundle_cash["LINK"] = Decimal("0.3146897938")

    usdc = build_asset_breakdown_row(
        "USDC",
        pe=pe,
        ledger={"USDC": Decimal("176.74")},
        on_chain_base={"USDC": Decimal("62.641746")},
        pending_by_asset={},
    )
    assert Decimal(usdc["total_holdings"]) == Decimal("176.74")
    assert Decimal(usdc["swappable_balance"]) == Decimal("62.64")
    assert usdc["in_bundles_additive"] is False
    assert usdc["bundle_is_subset_of_wallet"] is True

    eurc = build_asset_breakdown_row(
        "EURC",
        pe=pe,
        ledger={"EURC": Decimal("91.414272")},
        on_chain_base={"EURC": Decimal("91.414272")},
        pending_by_asset={},
    )
    assert eurc["available"] == eurc["total_holdings"]

    cbbtc = build_asset_breakdown_row(
        "CBBTC",
        pe=pe,
        ledger={"CBBTC": Decimal("0.00237")},
        on_chain_base={"CBBTC": Decimal("0.00205355")},
        pending_by_asset={},
    )
    assert Decimal(cbbtc["swappable_balance"]) == 0

    cbeth = build_asset_breakdown_row(
        "CBETH",
        pe=pe,
        ledger={"CBETH": Decimal("0.006542223")},
        on_chain_base={"CBETH": Decimal("0.0018125965")},
        pending_by_asset={},
    )
    assert Decimal(cbeth["swappable_balance"]) == 0

    link = build_asset_breakdown_row(
        "LINK",
        pe=pe,
        ledger={"LINK": Decimal("0.3146897938")},
        on_chain_base={"LINK": Decimal("0.3146897938")},
        pending_by_asset={},
    )
    assert Decimal(link["total_holdings"]) == Decimal("0.3146897938")
    assert link["in_bundles_additive"] is True


def test_build_portfolio_breakdown_doctrine_warnings(db: Session):
    pe = make_linked_client(db)
    with patch(
        "services.portfolio_engine.portfolio_breakdown.fetch_aggregated_on_chain_balances",
        return_value={},
    ):
        payload = build_portfolio_breakdown(db, pe.person_id)
    assert payload["breakdown_version"] == BREAKDOWN_VERSION
    assert payload["doctrine"]["swap_max_field"] == "swappable_balance"
    assert "min(on_chain_balance_base, available)" in payload["doctrine"]["swappable_formula"]
    assert "bundle_incremental_value" in payload["doctrine"]["total_holdings_formula"]
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
