"""Tests for resilience and edge cases in the auto execution engine.

Covers: Redis unavailability, stale quotes, unsupported assets,
load scenarios, precision/rounding.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from services.price_alerts.engine import PriceAlertEngine
from services.price_alerts.cache import (
    add_alert_to_cache,
    get_crossed_alert_ids_sorted,
    get_and_set_price,
    check_notif_dedup,
)
from services.price_alerts.metrics import AlertMetrics


class FakePipeline:
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
    def __init__(self):
        self._data = {}

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self._data:
            return None
        self._data[key] = value
        return True

    def zadd(self, key, mapping):
        if key not in self._data:
            self._data[key] = {}
        self._data[key].update(mapping)

    def zrem(self, key, member):
        if key in self._data:
            self._data[key].pop(member, None)

    def pipeline(self, transaction=True):
        return FakePipeline(self)

    def getset(self, key, value):
        prev = self._data.get(key)
        self._data[key] = value
        return prev

    def zrangebyscore(self, key, min, max, withscores=False):
        entries = self._data.get(key, {})
        result = [(m, s) for m, s in entries.items() if min <= s <= max]
        result.sort(key=lambda x: x[1])
        return result if withscores else [m for m, _ in result]


class FakeAlert:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid.uuid4())
        self.client_id = kwargs.get("client_id", uuid.uuid4())
        self.asset = kwargs.get("asset", "BTC")
        self.target_price = Decimal(str(kwargs.get("target_price", 85000)))
        self.direction = kwargs.get("direction", "down")
        self.price_source = kwargs.get("price_source", "ask")
        self.status = kwargs.get("status", "active")
        self.action_type = kwargs.get("action_type", "order")
        self.trigger_mode = "once"
        self.trigger_count = 0
        self.order_payload = kwargs.get("order_payload", {"side": "buy", "order_type": "limit", "amount": 100.0})
        self.cooldown_seconds = 0
        self.created_at = datetime.now(timezone.utc)
        self.triggered_at = None
        self.last_triggered_at = None
        self.triggered_price = None
        self.execution_status = kwargs.get("execution_status", "pending")
        self.metadata_ = {}


@pytest.fixture(autouse=True)
def reset_metrics():
    from services.price_alerts import metrics as m
    m._metrics = AlertMetrics()
    yield
    m._metrics = AlertMetrics()


class TestRedisUnavailable:

    def test_cache_operations_safe_with_none(self):
        add_alert_to_cache(None, FakeAlert())
        pairs = get_crossed_alert_ids_sorted(None, "BTC", "up", 0, 999999)
        assert pairs == []
        prev = get_and_set_price(None, "BTC", "mid", 84000)
        assert prev is None
        dedup = check_notif_dedup(None, "client", "BTC", "up")
        assert dedup is False

    def test_engine_with_none_redis_no_crash(self):
        engine = PriceAlertEngine(None)
        result = engine.on_price_batch({"BTCUSDT": {"bid": 84000, "ask": 84100}}, lambda: MagicMock())
        assert result == 0

    @patch("services.exchange.service.ExchangeService")
    def test_precheck_proceeds_when_redis_none(self, MockSvc):
        engine = PriceAlertEngine(None)
        mock_svc = MockSvc.return_value
        mock_svc.buy.return_value = {
            "status": "completed", "order_id": uuid.uuid4(),
            "price": Decimal("85000"), "amount_crypto": Decimal("0.001"),
            "amount_fiat": Decimal("100"),
        }
        alert = FakeAlert()
        engine._execute_order_hook(alert, MagicMock())
        assert alert.execution_status == "executed"


class TestUnsupportedAsset:

    def test_unknown_symbol_skipped(self):
        assert PriceAlertEngine._symbol_to_asset("RANDOMCOIN") is None
        assert PriceAlertEngine._symbol_to_asset("") is None

    def test_batch_with_unknown_symbol(self):
        engine = PriceAlertEngine(FakeRedis())
        result = engine.on_price_batch({"XYZABC": {"bid": 1, "ask": 2}}, lambda: MagicMock())
        assert result == 0


class TestPriceMissing:

    def test_missing_bid_ask_and_last_skipped(self):
        engine = PriceAlertEngine(FakeRedis())
        result = engine.on_price_batch({"BTCUSDT": {}}, lambda: MagicMock())
        assert result == 0

    def test_fallback_to_last_when_bid_missing(self):
        engine = PriceAlertEngine(FakeRedis())
        result = engine.on_price_batch(
            {"BTCUSDT": {"last": 84000}}, lambda: MagicMock()
        )
        assert result == 0


class TestLoadScenario:

    def test_many_alerts_same_level(self):
        r = FakeRedis()
        n = 1000
        class FA:
            def __init__(self, i):
                self.id = str(uuid.uuid4())
                self.asset = "BTC"
                self.direction = "up"
                self.target_price = 100000.0
        for i in range(n):
            add_alert_to_cache(r, FA(i))
        pairs = get_crossed_alert_ids_sorted(r, "BTC", "up", 99000, 101000)
        assert len(pairs) == n

    def test_many_different_levels(self):
        r = FakeRedis()
        n = 500
        class FA:
            def __init__(self, i):
                self.id = str(uuid.uuid4())
                self.asset = "BTC"
                self.direction = "up"
                self.target_price = 90000.0 + i * 10
        for i in range(n):
            add_alert_to_cache(r, FA(i))
        pairs = get_crossed_alert_ids_sorted(r, "BTC", "up", 89000, 96000)
        triggered = [p for p in pairs if p[1] <= 96000]
        assert len(triggered) > 0
        prices = [p[1] for p in triggered]
        assert prices == sorted(prices)


class TestPrecisionRounding:

    def test_small_price_precision(self):
        r = FakeRedis()
        class FA:
            id = "small1"
            asset = "SHIB"
            direction = "up"
            target_price = 0.00002345
        add_alert_to_cache(r, FA())
        pairs = get_crossed_alert_ids_sorted(r, "SHIB", "up", 0.00002000, 0.00003000)
        assert len(pairs) == 1
        assert pairs[0][1] == pytest.approx(0.00002345, rel=1e-6)

    def test_large_price_precision(self):
        r = FakeRedis()
        class FA:
            id = "large1"
            asset = "BTC"
            direction = "up"
            target_price = 123456.78901234
        add_alert_to_cache(r, FA())
        pairs = get_crossed_alert_ids_sorted(r, "BTC", "up", 123000, 124000)
        assert len(pairs) == 1
        assert pairs[0][1] == pytest.approx(123456.78901234, rel=1e-8)

    @patch("services.exchange.service.ExchangeService")
    def test_decimal_amount_preserved(self, MockSvc):
        engine = PriceAlertEngine(FakeRedis())
        mock_svc = MockSvc.return_value
        mock_svc.buy.return_value = {
            "status": "completed", "order_id": uuid.uuid4(),
            "price": Decimal("0.00002345"), "amount_crypto": Decimal("4264392.324"),
            "amount_fiat": Decimal("100"),
        }
        alert = FakeAlert(target_price=0.00002345, order_payload={"side": "buy", "amount": 100})
        engine._execute_order_hook(alert, MagicMock())
        assert alert.execution_status == "executed"
        assert alert.metadata_["filled_amount"] == 100.0
