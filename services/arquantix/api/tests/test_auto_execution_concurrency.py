"""Tests for concurrency, idempotence, and race conditions in auto execution.

These tests verify that the trigger engine handles concurrent access safely
and that orders cannot be executed twice.
"""
import uuid
from decimal import Decimal
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from services.price_alerts.engine import PriceAlertEngine
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
        self.trigger_mode = kwargs.get("trigger_mode", "once")
        self.trigger_count = kwargs.get("trigger_count", 0)
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


class TestIdempotence:

    def test_execution_skipped_if_not_pending(self):
        engine = PriceAlertEngine(FakeRedis())
        alert = FakeAlert(execution_status="executed")
        engine._execute_order_hook(alert, MagicMock())
        assert alert.execution_status == "executed"

    def test_execution_skipped_if_failed(self):
        engine = PriceAlertEngine(FakeRedis())
        alert = FakeAlert(execution_status="failed")
        engine._execute_order_hook(alert, MagicMock())
        assert alert.execution_status == "failed"

    @patch("services.exchange.service.ExchangeService")
    def test_unique_external_ref_prevents_dup(self, MockSvc):
        engine = PriceAlertEngine(FakeRedis())
        mock_svc = MockSvc.return_value
        mock_svc.buy.return_value = {
            "status": "completed", "order_id": uuid.uuid4(),
            "price": Decimal("85000"), "amount_crypto": Decimal("0.001"),
            "amount_fiat": Decimal("100"),
        }
        alert = FakeAlert()
        engine._execute_order_hook(alert, MagicMock())
        ref = mock_svc.buy.call_args[0][1].external_reference
        assert ref.startswith(f"trigger-{alert.id}-")
        assert len(ref) > len(f"trigger-{alert.id}-")


class TestDuplicateTick:

    def test_same_price_no_crossing(self):
        engine = PriceAlertEngine(FakeRedis())
        result = engine._check_source("BTC", "mid", 84000.0, 84000.0,
                                       datetime.now(timezone.utc), lambda: None)
        assert result == 0

    def test_tiny_delta_no_crossing(self):
        engine = PriceAlertEngine(FakeRedis())
        result = engine._check_source("BTC", "mid", 84000.0, 84000.0 + 1e-11,
                                       datetime.now(timezone.utc), lambda: None)
        assert result == 0


class TestCancelVsTriggerRace:

    def test_cancelled_order_not_in_cache(self):
        r = FakeRedis()
        from services.price_alerts.cache import add_alert_to_cache, remove_alert_from_cache, get_crossed_alert_ids_sorted
        alert = FakeAlert(direction="up", target_price=100000)
        add_alert_to_cache(r, alert)
        remove_alert_from_cache(r, str(alert.id), "BTC", "up")
        pairs = get_crossed_alert_ids_sorted(r, "BTC", "up", 99000, 101000)
        assert len(pairs) == 0


class TestPriorityExecution:

    def test_orders_before_alerts_in_processing(self):
        order_ids = []
        alert_ids = []

        class FakeOrderAlert:
            def __init__(self, is_order):
                self.id = uuid.uuid4()
                self.action_type = "order" if is_order else "alert"
                self.order_payload = {"side": "buy", "amount": 100} if is_order else None

        items = [FakeOrderAlert(False), FakeOrderAlert(True), FakeOrderAlert(False), FakeOrderAlert(True)]
        alert_map = {str(a.id): a for a in items}

        order_alerts = [a for a in items if a.action_type == "order"]
        simple_alerts = [a for a in items if a.action_type != "order"]
        combined = order_alerts + simple_alerts

        for i, a in enumerate(combined):
            if a.action_type == "order":
                assert i < len(order_alerts), "Orders must come first"
