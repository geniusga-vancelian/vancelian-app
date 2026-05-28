"""Tests bundle invest preview — allocations CBBTC/CBETH + montants USDC par jambe."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

from services.portfolio_engine.bundle_execution.bundle_lifi_validation import (
    BundleLifiValidationError,
)
from services.portfolio_engine.bundle_execution.lifi_base_config import (
    BUNDLE_LIFI_DESTINATION_ASSETS,
    display_bundle_asset,
    normalize_bundle_asset,
)
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.portfolio_engine.bundles.preview_warnings import parse_preview_warning


def test_normalize_and_display_bundle_assets():
    assert normalize_bundle_asset("BTC") == "CBBTC"
    assert normalize_bundle_asset("ETH") == "CBETH"
    assert display_bundle_asset("BTC") == "cbBTC"
    assert display_bundle_asset("CBETH") == "cbETH"
    assert "LINK" in BUNDLE_LIFI_DESTINATION_ASSETS
    assert "AAVE" in BUNDLE_LIFI_DESTINATION_ASSETS
    assert "UNI" in BUNDLE_LIFI_DESTINATION_ASSETS


def test_preview_allocation_leg_exchange_fallback():
    orch = BundleOrchestrator()
    db = MagicMock()
    orch._exchange = MagicMock()
    orch._exchange.preview_swap.return_value = {"estimated_to_amount": 0.00012}

    result = orch._preview_allocation_leg(
        db,
        entry_asset="USDC",
        lifi_target="CBBTC",
        display_asset="cbBTC",
        alloc_input=Decimal("25"),
        target_weight=Decimal("0.5"),
        reference_currency="EUR",
        use_lifi_preview=False,
        person_id=None,
    )

    assert result["status"] == "ok"
    row = result["row"]
    assert row["asset"] == "CBBTC"
    assert row["asset_display"] == "cbBTC"
    assert row["estimated_input_amount"] == "25"
    assert row["estimated_output_quantity"] == "0.00012"
    assert row["status"] == "ok"


@patch(
    "services.portfolio_engine.bundle_execution.bundle_lifi_quote_service.BundleLifiQuoteService.preview_bundle_quote"
)
def test_preview_allocation_leg_lifi_success(mock_preview_quote):
    mock_preview_quote.return_value = Decimal("0.00031")
    orch = BundleOrchestrator()
    orch._exchange = MagicMock()
    person_id = uuid.uuid4()

    result = orch._preview_allocation_leg(
        MagicMock(),
        entry_asset="USDC",
        lifi_target="CBBTC",
        display_asset="cbBTC",
        alloc_input=Decimal("21"),
        target_weight=Decimal("0.7"),
        reference_currency="EUR",
        use_lifi_preview=True,
        person_id=person_id,
    )

    assert result["status"] == "ok"
    assert result["row"]["estimated_output_quantity"] == "0.00031"
    orch._exchange.preview_swap.assert_not_called()
    mock_preview_quote.assert_called_once()


@patch(
    "services.portfolio_engine.bundle_execution.bundle_lifi_quote_service.BundleLifiQuoteService.preview_bundle_quote"
)
def test_preview_allocation_leg_lifi_failure_does_not_fallback_to_exchange(mock_preview_quote):
    mock_preview_quote.side_effect = BundleLifiValidationError(
        "bundle.lifi.quote_failed",
        "LI.FI route unavailable",
    )
    orch = BundleOrchestrator()
    orch._exchange = MagicMock()

    result = orch._preview_allocation_leg(
        MagicMock(),
        entry_asset="USDC",
        lifi_target="CBBTC",
        display_asset="cbBTC",
        alloc_input=Decimal("21"),
        target_weight=Decimal("0.7"),
        reference_currency="EUR",
        use_lifi_preview=True,
        person_id=uuid.uuid4(),
    )

    assert result["status"] == "unavailable"
    parsed = parse_preview_warning(result["warning"])
    assert parsed["kind"] == "lifi_preview_failed"
    assert parsed["code"] == "bundle.lifi.quote_failed"
    assert parsed["detail"] == "LI.FI route unavailable"
    orch._exchange.preview_swap.assert_not_called()


def test_preview_allocation_leg_lifi_requires_person_id():
    orch = BundleOrchestrator()
    orch._exchange = MagicMock()

    result = orch._preview_allocation_leg(
        MagicMock(),
        entry_asset="USDC",
        lifi_target="CBETH",
        display_asset="cbETH",
        alloc_input=Decimal("9"),
        target_weight=Decimal("0.3"),
        reference_currency="EUR",
        use_lifi_preview=True,
        person_id=None,
    )

    assert result["status"] == "unavailable"
    parsed = parse_preview_warning(result["warning"])
    assert parsed["code"] == "bundle.lifi.no_person_id"
    orch._exchange.preview_swap.assert_not_called()


@patch(
    "services.portfolio_engine.bundles.orchestrator.BundleOrchestrator._preview_allocation_leg"
)
@patch("services.portfolio_engine.bundles.orchestrator.BundleOrchestrator._load_target_allocations")
@patch("services.portfolio_engine.bundles.orchestrator.BundleOrchestrator._load_product")
@patch("services.portfolio_engine.bundles.orchestrator.BundleOrchestrator._load_and_validate_portfolio")
def test_preview_invest_direct_usdc_returns_input_amounts(
    mock_load_portfolio,
    mock_load_product,
    mock_load_allocs,
    mock_preview_leg,
):
    portfolio_id = uuid.uuid4()
    client_id = uuid.uuid4()

    mock_load_portfolio.return_value = MagicMock(
        id=portfolio_id, name="Crypto Majors", origin_product_id=uuid.uuid4(),
    )
    mock_load_product.return_value = MagicMock(
        metadata_={"entry_asset_default": "USDC", "entry_assets_allowed": ["USDC"]},
    )

    inst = MagicMock()
    inst.asset_id = uuid.uuid4()
    alloc = MagicMock()
    alloc.instrument = inst
    alloc.instrument_id = uuid.uuid4()
    alloc.target_weight = Decimal("0.5")
    mock_load_allocs.return_value = [alloc]

    asset_obj = MagicMock()
    asset_obj.symbol = "BTC"

    db = MagicMock()
    db.query.return_value.filter.return_value.first.side_effect = [
        inst,
        asset_obj,
    ]

    mock_preview_leg.return_value = {
        "status": "ok",
        "row": {
            "asset": "CBBTC",
            "asset_display": "cbBTC",
            "target_weight": "0.5",
            "estimated_input_amount": "25",
            "estimated_output_quantity": "0.00011",
            "status": "ok",
        },
    }

    orch = BundleOrchestrator()
    orch._execution = MagicMock(provider_name="lifi_base")
    orch._resolve_person_id = MagicMock(return_value=uuid.uuid4())

    result = orch.preview_invest(
        db,
        client_id=client_id,
        portfolio_id=portfolio_id,
        funding_asset="USDC",
        funding_amount=Decimal("50"),
    )

    assert result["preview_status"] == "ok"
    assert result["estimated_entry_asset_amount"] == "50"
    assert len(result["allocations"]) == 1
    assert result["allocations"][0]["estimated_input_amount"] == "25"
    assert result["allocations"][0]["asset_display"] == "cbBTC"
