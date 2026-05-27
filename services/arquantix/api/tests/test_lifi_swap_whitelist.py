"""Tests whitelist swap assets."""
import pytest

from config.base_allowed_assets import BASE_SWAP_SYMBOLS
from config.supported_swap_assets import (
    asset_available_on_chain,
    human_amount_to_atomic,
    is_supported_asset,
    is_swap_destination_asset,
    is_swap_source_asset,
    list_supported_assets_public,
    list_supported_chains_public,
    list_supported_destination_assets_public,
    resolve_swap_token,
)
from services.lifi.lifi_validation_service import SwapValidationError, validate_quote_request


def test_whitelist_base_assets_only():
    assert is_supported_asset("USDC")
    assert is_supported_asset("ETH")
    assert is_supported_asset("CBBTC")
    assert is_supported_asset("CBETH")
    assert is_supported_asset("LINK")
    assert not is_supported_asset("USDT")
    assert not is_supported_asset("SOL")


def test_source_and_destination_sets():
    assert is_swap_source_asset("USDC")
    assert is_swap_destination_asset("ETH")
    assert is_swap_destination_asset("CBBTC")
    assert is_swap_destination_asset("CBETH")
    assert BASE_SWAP_SYMBOLS == frozenset(
        {"ETH", "CBETH", "USDC", "EURC", "CBBTC", "LINK", "AAVE", "UNI"}
    )


def test_usdc_on_base():
    assert asset_available_on_chain("USDC", "base")
    token = resolve_swap_token("USDC", "base")
    assert token.token_address.startswith("0x")


def test_ethereum_alias_resolves_to_base():
    token = resolve_swap_token("ETH", "ethereum")
    assert token.chain_key == "base"


def test_solana_chain_not_supported():
    with pytest.raises(SwapValidationError) as exc:
        validate_quote_request(
            from_asset="USDC",
            to_asset="ETH",
            amount="100",
            from_chain="solana",
            to_chain="base",
        )
    assert exc.value.code == "swap.chain_not_supported"


def test_reject_unknown_asset():
    with pytest.raises(SwapValidationError) as exc:
        validate_quote_request(
            from_asset="SCAM",
            to_asset="USDC",
            amount="100",
            from_chain="base",
            to_chain="base",
        )
    assert exc.value.code == "swap.asset_not_whitelisted"


def test_reject_btc_as_destination():
    with pytest.raises(SwapValidationError) as exc:
        validate_quote_request(
            from_asset="USDC",
            to_asset="BTC",
            amount="100",
            from_chain="base",
            to_chain="base",
        )
    assert exc.value.code == "swap.asset_not_whitelisted"


def test_reject_unknown_chain():
    with pytest.raises(SwapValidationError) as exc:
        validate_quote_request(
            from_asset="USDC",
            to_asset="ETH",
            amount="100",
            from_chain="bsc",
            to_chain="base",
        )
    assert exc.value.code == "swap.chain_not_supported"


def test_reject_same_asset_same_chain():
    with pytest.raises(SwapValidationError) as exc:
        validate_quote_request(
            from_asset="USDC",
            to_asset="USDC",
            amount="100",
            from_chain="base",
            to_chain="base",
        )
    assert exc.value.code == "swap.same_asset"


def test_reject_amount_below_min():
    with pytest.raises(SwapValidationError) as exc:
        validate_quote_request(
            from_asset="USDC",
            to_asset="ETH",
            amount="0.01",
            from_chain="base",
            to_chain="base",
        )
    assert exc.value.code == "swap.amount_below_min"


def test_human_amount_to_atomic_usdc():
    from decimal import Decimal

    assert human_amount_to_atomic(Decimal("1000"), 6) == "1000000000"


def test_public_assets_payload_has_no_addresses():
    assets = list_supported_assets_public()
    assert len(assets) == len(BASE_SWAP_SYMBOLS)
    for item in assets:
        assert "addresses" not in item
        assert "symbol" in item
        assert item["chains"] == ["base"]


def test_wallet_chain_type_matches_evm_aliases():
    from services.lifi.lifi_quote_service import _wallet_chain_type_matches

    assert _wallet_chain_type_matches("evm", "base") is True
    assert _wallet_chain_type_matches("ethereum", "evm") is True
    assert _wallet_chain_type_matches("solana", "base") is False


def test_reject_cross_chain_when_pilot():
    with pytest.raises(SwapValidationError) as exc:
        validate_quote_request(
            from_asset="USDC",
            to_asset="ETH",
            amount="100",
            from_chain="base",
            to_chain="ethereum",
        )
    assert exc.value.code == "swap.chain_not_supported"


def test_public_chains_base_only():
    from config.supported_swap_assets import effective_swap_v1_chain_keys

    chains = list_supported_chains_public()
    keys = {c["key"] for c in chains}
    assert keys == {"base"}
    assert keys == set(effective_swap_v1_chain_keys())
    assert all(c["evm"] is True for c in chains)


def test_destination_assets_payload():
    dest = list_supported_destination_assets_public()
    assert {d["symbol"] for d in dest} == BASE_SWAP_SYMBOLS
