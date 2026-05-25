"""Tests métadonnées approval / status LI.FI."""
from __future__ import annotations

from services.lifi.lifi_approval_service import (
    build_token_approval_payload,
    read_chain_ids_from_lifi_quote,
    resolve_lifi_status_bridge,
)


def test_build_token_approval_payload_usdt():
    raw = {
        "action": {
            "fromAmount": "10000000",
            "fromToken": {
                "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
            },
        },
        "estimate": {
            "approvalAddress": "0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE",
        },
    }
    payload = build_token_approval_payload(raw)
    assert payload.required is True
    assert payload.token_address == "0xdAC17F958D2ee523a2206206994597C13D831ec7"
    assert payload.spender_address == "0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE"
    assert payload.amount_atomic == "10000000"


def test_build_token_approval_payload_native_eth_skipped():
    raw = {
        "action": {
            "fromAmount": "1000000000000000000",
            "fromToken": {"address": "0x0000000000000000000000000000000000000000"},
        },
        "estimate": {"approvalAddress": "0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE"},
    }
    payload = build_token_approval_payload(raw)
    assert payload.required is False


def test_resolve_lifi_status_bridge_same_chain_dex():
    assert (
        resolve_lifi_status_bridge(
            lifi_tool="sushiswap",
            from_chain_id=1,
            to_chain_id=1,
        )
        is None
    )


def test_resolve_lifi_status_bridge_cross_chain():
    assert (
        resolve_lifi_status_bridge(
            lifi_tool="stargateV2",
            from_chain_id=8453,
            to_chain_id=1,
        )
        == "stargateV2"
    )


def test_read_chain_ids_from_lifi_quote():
    from_id, to_id = read_chain_ids_from_lifi_quote(
        {"action": {"fromChainId": 1, "toChainId": 1}},
    )
    assert from_id == 1
    assert to_id == 1
