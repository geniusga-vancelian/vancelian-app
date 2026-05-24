"""Tests parsing des frais réseau LI.FI (unités atomiques vs USD)."""
from __future__ import annotations

from decimal import Decimal

from services.lifi.lifi_quote_service import _parse_network_fees


def test_parse_network_fees_prefers_usd_over_atomic_fee_cost():
    fees = _parse_network_fees(
        estimate={
            "feeCosts": [
                {
                    "name": "Gas",
                    "amount": "25000000",
                    "amountUSD": "0.025",
                    "included": False,
                    "token": {"symbol": "USDC", "decimals": 6},
                }
            ],
            "gasCosts": [],
        },
        default_asset="USDC",
        amount_in=Decimal("10"),
    )
    assert fees["network_fee"] == Decimal("0.025")
    assert fees["network_fee_asset"] == "USD"
    assert fees["network_fee_usd"] == Decimal("0.025")


def test_parse_network_fees_sums_gas_costs_usd():
    fees = _parse_network_fees(
        estimate={
            "feeCosts": [],
            "gasCosts": [
                {
                    "type": "SEND",
                    "amount": "1764000000000000",
                    "amountUSD": "0.04",
                    "token": {"symbol": "ETH", "decimals": 18},
                },
                {
                    "type": "APPROVE",
                    "amount": "50000000000000",
                    "amountUSD": "0.01",
                    "token": {"symbol": "ETH", "decimals": 18},
                },
            ],
        },
        default_asset="USDC",
        amount_in=Decimal("10"),
    )
    assert fees["network_fee"] == Decimal("0.05")
    assert fees["network_fee_asset"] == "USD"
    assert fees["network_fee_usd"] == Decimal("0.05")


def test_parse_network_fees_skips_included_fee_costs():
    fees = _parse_network_fees(
        estimate={
            "feeCosts": [
                {
                    "amount": "25000000",
                    "amountUSD": "25",
                    "included": True,
                    "token": {"symbol": "USDC", "decimals": 6},
                }
            ],
            "gasCosts": [{"amount": "176400", "amountUSD": "0.03", "token": {"symbol": "ETH", "decimals": 18}}],
        },
        default_asset="USDC",
        amount_in=Decimal("10"),
    )
    assert fees["network_fee"] == Decimal("0.03")
    assert fees["network_fee_usd"] == Decimal("0.03")


def test_parse_network_fees_rejects_absurd_usd_values():
    fees = _parse_network_fees(
        estimate={
            "feeCosts": [
                {
                    "amount": "25000000",
                    "amountUSD": "25",
                    "included": False,
                    "token": {"symbol": "USDC", "decimals": 6},
                }
            ],
            "gasCosts": [],
        },
        default_asset="USDC",
        amount_in=Decimal("10"),
    )
    assert fees["network_fee"] == Decimal("0")
    assert fees["network_fee_usd"] is None


def test_parse_network_fees_falls_back_to_gas_human_when_no_usd():
    fees = _parse_network_fees(
        estimate={
            "feeCosts": [],
            "gasCosts": [
                {
                    "type": "SEND",
                    "amount": "1000000000000000",
                    "token": {"symbol": "ETH", "decimals": 18},
                }
            ],
        },
        default_asset="USDC",
        amount_in=Decimal("10"),
    )
    assert fees["network_fee"] == Decimal("0.001")
    assert fees["network_fee_asset"] == "ETH"
    assert fees["network_fee_usd"] is None
