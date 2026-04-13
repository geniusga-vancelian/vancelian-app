"""Tests for price alert crossing detection and cache logic.

Uses a FakeRedis-like dict-backed mock to test sorted set operations
without a real Redis instance.
"""
import pytest
from datetime import datetime, timezone

from services.price_alerts.cache import (
    add_alert_to_cache,
    remove_alert_from_cache,
    get_crossed_alert_ids_sorted,
    get_and_set_price,
)
from services.price_alerts.engine import PriceAlertEngine


class FakePipeline:
    """Minimal pipeline mock that buffers commands and executes them."""

    def __init__(self, redis):
        self._redis = redis
        self._ops = []

    def zadd(self, key, mapping):
        self._ops.append(("zadd", key, mapping))
        return self

    def zrem(self, key, member):
        self._ops.append(("zrem", key, member))
        return self

    def execute(self):
        results = []
        for op in self._ops:
            if op[0] == "zadd":
                self._redis.zadd(op[1], op[2])
                results.append(1)
            elif op[0] == "zrem":
                self._redis.zrem(op[1], op[2])
                results.append(1)
        self._ops.clear()
        return results


class FakeRedis:
    """Minimal Redis mock supporting sorted sets and string get/set."""

    def __init__(self):
        self._data = {}

    def zadd(self, key, mapping):
        if key not in self._data:
            self._data[key] = {}
        self._data[key].update(mapping)

    def zrem(self, key, member):
        if key in self._data:
            self._data[key].pop(member, None)

    def pipeline(self, transaction=True):
        return FakePipeline(self)

    def zrangebyscore(self, key, min, max, withscores=False):
        entries = self._data.get(key, {})
        result = [(m, s) for m, s in entries.items() if min <= s <= max]
        result.sort(key=lambda x: x[1])
        if withscores:
            return result
        return [m for m, _ in result]

    def getset(self, key, value):
        prev = self._data.get(key)
        self._data[key] = value
        return prev

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self._data:
            return None
        self._data[key] = value
        return True


class FakeAlert:
    def __init__(self, id, asset, direction, target_price):
        self.id = id
        self.asset = asset
        self.direction = direction
        self.target_price = target_price


class TestCrossingDetection:

    def test_cross_up_simple(self):
        r = FakeRedis()
        alert = FakeAlert("a1", "BTC", "up", 100000.0)
        add_alert_to_cache(r, alert)
        pairs = get_crossed_alert_ids_sorted(r, "BTC", "up", 99000.0, 101000.0)
        assert len(pairs) == 1
        assert pairs[0][0] == "a1"
        assert pairs[0][1] == 100000.0

    def test_cross_down_simple(self):
        r = FakeRedis()
        alert = FakeAlert("a1", "BTC", "down", 95000.0)
        add_alert_to_cache(r, alert)
        pairs = get_crossed_alert_ids_sorted(r, "BTC", "down", 94000.0, 96000.0)
        assert len(pairs) == 1
        assert pairs[0][0] == "a1"

    def test_no_trigger_outside_range(self):
        r = FakeRedis()
        alert = FakeAlert("a1", "BTC", "up", 100000.0)
        add_alert_to_cache(r, alert)
        pairs = get_crossed_alert_ids_sorted(r, "BTC", "up", 101000.0, 102000.0)
        assert len(pairs) == 0

    def test_gap_crossing_multiple_levels(self):
        r = FakeRedis()
        for i, price in enumerate([100000, 101000, 102000, 103000]):
            add_alert_to_cache(r, FakeAlert(f"a{i}", "BTC", "up", float(price)))
        pairs = get_crossed_alert_ids_sorted(r, "BTC", "up", 99000.0, 104000.0)
        assert len(pairs) == 4

    def test_cross_up_sorted_asc(self):
        r = FakeRedis()
        add_alert_to_cache(r, FakeAlert("high", "BTC", "up", 103000.0))
        add_alert_to_cache(r, FakeAlert("low", "BTC", "up", 100000.0))
        add_alert_to_cache(r, FakeAlert("mid", "BTC", "up", 101500.0))
        pairs = get_crossed_alert_ids_sorted(r, "BTC", "up", 99000.0, 104000.0)
        prices = [p for _, p in pairs]
        assert prices == sorted(prices), "CROSS UP must be sorted ASC"

    def test_cross_down_sorted_desc(self):
        r = FakeRedis()
        add_alert_to_cache(r, FakeAlert("low", "BTC", "down", 90000.0))
        add_alert_to_cache(r, FakeAlert("high", "BTC", "down", 95000.0))
        add_alert_to_cache(r, FakeAlert("mid", "BTC", "down", 92000.0))
        pairs = get_crossed_alert_ids_sorted(r, "BTC", "down", 89000.0, 96000.0)
        prices = [p for _, p in pairs]
        assert prices == sorted(prices, reverse=True), "CROSS DOWN must be sorted DESC"

    def test_remove_from_cache(self):
        r = FakeRedis()
        alert = FakeAlert("a1", "BTC", "up", 100000.0)
        add_alert_to_cache(r, alert)
        remove_alert_from_cache(r, "a1", "BTC", "up")
        pairs = get_crossed_alert_ids_sorted(r, "BTC", "up", 99000.0, 101000.0)
        assert len(pairs) == 0

    def test_redis_none_returns_empty(self):
        pairs = get_crossed_alert_ids_sorted(None, "BTC", "up", 0, 999999)
        assert pairs == []

    def test_add_to_cache_with_none_redis(self):
        add_alert_to_cache(None, FakeAlert("a1", "BTC", "up", 100000.0))

    def test_remove_from_cache_with_none_redis(self):
        remove_alert_from_cache(None, "a1", "BTC", "up")


class TestPriceTracking:

    def test_get_and_set_returns_previous(self):
        r = FakeRedis()
        prev = get_and_set_price(r, "BTC", "bid", 84000.0)
        assert prev is None
        prev = get_and_set_price(r, "BTC", "bid", 84100.0)
        assert prev == 84000.0

    def test_get_and_set_none_redis(self):
        prev = get_and_set_price(None, "BTC", "bid", 84000.0)
        assert prev is None


class TestSymbolToAsset:

    @pytest.mark.parametrize("symbol,expected", [
        ("BTCUSDT", "BTC"),
        ("ETHUSDT", "ETH"),
        ("SOLUSDT", "SOL"),
        ("BTCBUSD", "BTC"),
        ("BTCUSD", "BTC"),
        ("BTCEUR", "BTC"),
        ("btcusdt", "BTC"),
    ])
    def test_valid_symbols(self, symbol, expected):
        assert PriceAlertEngine._symbol_to_asset(symbol) == expected

    @pytest.mark.parametrize("symbol", ["USDT", "", "RANDOM"])
    def test_invalid_symbols(self, symbol):
        assert PriceAlertEngine._symbol_to_asset(symbol) is None


class TestExtractPrice:

    def test_extracts_bid_price(self):
        assert PriceAlertEngine._extract_price({"bid_price": "84000.5"}, "bid") == 84000.5

    def test_extracts_bid_fallback(self):
        assert PriceAlertEngine._extract_price({"bid": 84000}, "bid") == 84000.0

    def test_returns_none_if_missing(self):
        assert PriceAlertEngine._extract_price({}, "bid") is None

    def test_returns_none_for_invalid(self):
        assert PriceAlertEngine._extract_price({"bid_price": "invalid"}, "bid") is None


class TestCheckSourceLogic:

    def setup_method(self):
        self.redis = FakeRedis()
        self.engine = PriceAlertEngine(self.redis)

    def test_no_trigger_when_prev_is_none(self):
        result = self.engine._check_source("BTC", "mid", None, 84000.0, datetime.now(timezone.utc), lambda: None)
        assert result == 0

    def test_no_trigger_when_price_unchanged(self):
        result = self.engine._check_source("BTC", "mid", 84000.0, 84000.0, datetime.now(timezone.utc), lambda: None)
        assert result == 0
