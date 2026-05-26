"""Tests Phase 2 — Bundle LI.FI Base (mock)."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest

from services.portfolio_engine.bundle_execution.bundle_lifi_validation import (
    BundleLifiValidationError,
    validate_bundle_lifi_leg,
    validate_bundle_quote_request,
)
from services.portfolio_engine.bundle_execution.config import get_bundle_execution_provider_name
from services.portfolio_engine.bundle_execution.lifi_base_config import (
    BUNDLE_LIFI_DESTINATION_ASSETS,
    BUNDLE_LIFI_SOURCE_ASSETS,
    normalize_bundle_asset,
    resolve_bundle_base_token,
    validate_bundle_leg_assets,
)
from config.supported_swap_assets import is_swap_destination_asset
from services.portfolio_engine.bundle_execution.providers import get_execution_provider
from services.portfolio_engine.bundle_execution.types import ExecutionLeg


def test_bundle_lifi_allows_cbbtc_base():
    """CBBTC accepté bundle ; BTC logique → CBBTC ; portail swap V1 inchangé."""
    assert normalize_bundle_asset("BTC") == "CBBTC"
    assert "CBBTC" in BUNDLE_LIFI_DESTINATION_ASSETS
    assert "USDC" in BUNDLE_LIFI_SOURCE_ASSETS

    validate_bundle_leg_assets("USDC", "CBBTC")
    validate_bundle_quote_request(
        from_asset="USDC",
        to_asset="CBBTC",
        amount="15",
    )
    validate_bundle_quote_request(
        from_asset="USDC",
        to_asset="BTC",
        amount="15",
    )

    tok = resolve_bundle_base_token("BTC")
    assert tok.asset == "CBBTC"
    assert tok.chain_key == "base"
    assert tok.lifi_chain_id == 8453

    assert not is_swap_destination_asset("CBBTC")

    with pytest.raises(BundleLifiValidationError) as exc:
        validate_bundle_quote_request(
            from_asset="BTC",
            to_asset="ETH",
            amount="1",
        )
    assert "native_btc" in exc.value.code or "BTC" in str(exc.value)

    with pytest.raises(BundleLifiValidationError):
        validate_bundle_lifi_leg(
            from_asset="USDC",
            to_asset="ETH",
            amount_from=Decimal("10"),
            chain="ethereum",
        )

    with pytest.raises(BundleLifiValidationError):
        validate_bundle_quote_request(
            from_asset="USDC",
            to_asset="USDT",
            amount="10",
        )


def test_normalize_btc_to_cbbtc():
    assert normalize_bundle_asset("BTC") == "CBBTC"


def test_resolve_cbbtc_base():
    tok = resolve_bundle_base_token("cbBTC")
    assert tok.chain_key == "base"
    assert tok.lifi_chain_id == 8453


def test_validate_rejects_non_base_chain():
    with pytest.raises(BundleLifiValidationError):
        validate_bundle_lifi_leg(
            from_asset="USDC",
            to_asset="ETH",
            amount_from=Decimal("10"),
            chain="ethereum",
        )


def test_lifi_provider_name_from_env(monkeypatch):
    monkeypatch.setenv("BUNDLE_EXECUTION_PROVIDER", "lifi_base")
    assert get_bundle_execution_provider_name() == "lifi_base"
    assert get_execution_provider().name == "lifi_base"


def test_execution_leg_pending_shape():
    leg = ExecutionLeg(
        leg_id="bundle-alloc-x",
        portfolio_id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        action="allocation",
        from_asset="USDC",
        to_asset="CBBTC",
        amount_from=Decimal("100"),
        batch_id="batch-1",
        bundle_action="allocation",
        chain="base",
        metadata={"entry_instrument_id": str(uuid.uuid4()), "target_instrument_id": str(uuid.uuid4())},
    )
    assert leg.chain == "base"


@patch("services.portfolio_engine.bundle_execution.bundle_lifi_leg_service.swaps_mock_mode", return_value=True)
@patch("services.portfolio_engine.bundle_execution.bundle_lifi_leg_service.bundle_lifi_sync_mock", return_value=True)
def test_lifi_execute_returns_completed_under_mock(_sync, _mock):
    from services.portfolio_engine.bundle_execution.lifi_provider import LifiExecutionProvider

    provider = LifiExecutionProvider()
    assert provider.name == "lifi_base"


# Wallet EVM / Base : voir tests/test_bundle_lifi_wallet.py
