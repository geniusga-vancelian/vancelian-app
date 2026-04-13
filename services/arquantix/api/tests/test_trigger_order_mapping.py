"""Tests for trigger order type mapping — business invariants.

Ensures that the mapping from (side, order_type) → (direction, price_source)
is correct and stable. These are core trading invariants.
"""
import pytest
from services.price_alerts.orders_router import ORDER_TYPE_MAP, CreateOrderRequest
from pydantic import ValidationError


class TestOrderTypeMapping:
    """Verify each order type maps to the correct direction and price source."""

    def test_buy_limit_maps_to_down_ask(self):
        m = ORDER_TYPE_MAP[("buy", "limit")]
        assert m["direction"] == "down"
        assert m["price_source"] == "ask"

    def test_buy_stop_maps_to_up_ask(self):
        m = ORDER_TYPE_MAP[("buy", "stop")]
        assert m["direction"] == "up"
        assert m["price_source"] == "ask"

    def test_sell_limit_maps_to_up_bid(self):
        m = ORDER_TYPE_MAP[("sell", "limit")]
        assert m["direction"] == "up"
        assert m["price_source"] == "bid"

    def test_sell_stop_maps_to_down_bid(self):
        m = ORDER_TYPE_MAP[("sell", "stop")]
        assert m["direction"] == "down"
        assert m["price_source"] == "bid"

    def test_all_buy_orders_use_ask(self):
        for key, val in ORDER_TYPE_MAP.items():
            if key[0] == "buy":
                assert val["price_source"] == "ask", f"{key} should use ask"

    def test_all_sell_orders_use_bid(self):
        for key, val in ORDER_TYPE_MAP.items():
            if key[0] == "sell":
                assert val["price_source"] == "bid", f"{key} should use bid"

    def test_exactly_four_mappings(self):
        assert len(ORDER_TYPE_MAP) == 4

    def test_no_duplicate_direction_source_pairs(self):
        pairs = [(v["direction"], v["price_source"]) for v in ORDER_TYPE_MAP.values()]
        assert len(pairs) == len(set(pairs))


class TestCreateOrderRequestValidation:
    """Validate pydantic schema constraints."""

    def test_valid_buy_limit(self):
        req = CreateOrderRequest(
            asset="BTC", side="buy", order_type="limit",
            trigger_price=65000.0, amount=100.0,
        )
        assert req.side == "buy"
        assert req.slippage_bps is None

    def test_valid_with_slippage(self):
        req = CreateOrderRequest(
            asset="ETH", side="sell", order_type="stop",
            trigger_price=3000.0, amount=1.5, slippage_bps=50,
        )
        assert req.slippage_bps == 50

    def test_invalid_side_rejected(self):
        with pytest.raises(ValidationError):
            CreateOrderRequest(
                asset="BTC", side="short", order_type="limit",
                trigger_price=65000.0, amount=100.0,
            )

    def test_invalid_order_type_rejected(self):
        with pytest.raises(ValidationError):
            CreateOrderRequest(
                asset="BTC", side="buy", order_type="market",
                trigger_price=65000.0, amount=100.0,
            )

    def test_negative_price_rejected(self):
        with pytest.raises(ValidationError):
            CreateOrderRequest(
                asset="BTC", side="buy", order_type="limit",
                trigger_price=-100.0, amount=100.0,
            )

    def test_zero_amount_rejected(self):
        with pytest.raises(ValidationError):
            CreateOrderRequest(
                asset="BTC", side="buy", order_type="limit",
                trigger_price=65000.0, amount=0,
            )

    def test_slippage_over_500_rejected(self):
        with pytest.raises(ValidationError):
            CreateOrderRequest(
                asset="BTC", side="buy", order_type="limit",
                trigger_price=65000.0, amount=100.0, slippage_bps=501,
            )

    def test_empty_asset_rejected(self):
        with pytest.raises(ValidationError):
            CreateOrderRequest(
                asset="", side="buy", order_type="limit",
                trigger_price=65000.0, amount=100.0,
            )
