"""Tests mapping actifs Privy multi-chain."""
from __future__ import annotations

from services.privy_wallet.asset_mapping import (
    contract_for_asset,
    resolve_asset_symbol,
    supported_assets_for_chain,
)


def test_base_usdc_contract_mapping():
    contract = contract_for_asset(8453, "USDC")
    assert contract == "0x833589fCD6eDb6E08Ab4aB98b4690795417555"


def test_resolve_base_usdc_from_contract():
    asset = resolve_asset_symbol(
        chain_id=8453,
        asset_payload={"type": "erc20", "symbol": "USDC"},
        contract_address="0x833589fCD6eDb6E08Ab4aB98b4690795417555",
    )
    assert asset == "USDC"


def test_supported_assets_include_base_usdc_and_eth():
    assets = supported_assets_for_chain(8453)
    assert "USDC" in assets
    assert "ETH" in assets
