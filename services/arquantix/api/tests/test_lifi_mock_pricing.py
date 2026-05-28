"""Tests estimation mock LI.FI via quotes Binance (ExchangeService.preview_swap)."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock, patch

from services.lifi.lifi_mock_client import LifiMockClient
from services.lifi.lifi_mock_pricing import estimate_mock_swap_output


def test_estimate_mock_swap_output_uses_exchange_preview():
    with patch("services.lifi.lifi_mock_pricing.ExchangeService") as mock_svc_cls:
        mock_svc_cls.return_value.preview_swap.return_value = {
            "estimated_to_amount": 0.00234567,
        }
        out = estimate_mock_swap_output(
            from_asset="USDC",
            to_asset="ETH",
            amount_in=Decimal("10"),
        )
    assert out == Decimal("0.00234567")
    mock_svc_cls.return_value.preview_swap.assert_called_once()


def test_estimate_mock_swap_output_fallback_when_exchange_fails():
    from services.exchange.service import ExchangeError

    with patch("services.lifi.lifi_mock_pricing.ExchangeService") as mock_svc_cls:
        mock_svc_cls.return_value.preview_swap.side_effect = ExchangeError("no_quote")
        out = estimate_mock_swap_output(
            from_asset="USDC",
            to_asset="CBBTC",
            amount_in=Decimal("10"),
        )
    assert out > 0


def test_lifi_mock_client_quote_uses_binance_pricing():
    client = LifiMockClient()
    with patch(
        "services.lifi.lifi_mock_client.estimate_mock_swap_output",
        return_value=Decimal("0.003"),
    ) as mock_price:
        quote = client.get_quote(
            from_chain=8453,
            to_chain=8453,
            from_token="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
            to_token="0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
            from_amount="10000000",
            from_address="0xabc",
        )
    mock_price.assert_called_once()
    assert int(quote["estimate"]["toAmount"]) > 0
