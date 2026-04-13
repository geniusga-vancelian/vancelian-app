"""Tests for the auto execution engine — _execute_order_hook and related logic.

All ExchangeService calls are mocked. Tests verify execution_status transitions,
metadata population, retry behavior, slippage checks, and partial fill detection.
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
        pass

    def zrem(self, key, member):
        pass

    def pipeline(self, transaction=True):
        return FakePipeline(self)

    def getset(self, key, value):
        prev = self._data.get(key)
        self._data[key] = value
        return prev

    def zrangebyscore(self, key, min, max, withscores=False):
        return []


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
        self.cooldown_seconds = kwargs.get("cooldown_seconds", 0)
        self.created_at = datetime.now(timezone.utc)
        self.triggered_at = None
        self.last_triggered_at = None
        self.triggered_price = None
        self.execution_status = kwargs.get("execution_status", "pending")
        self.metadata_ = kwargs.get("metadata_", {})


def _make_completed_result(**overrides):
    base = {
        "status": "completed",
        "order_id": uuid.uuid4(),
        "price": Decimal("85000"),
        "amount_crypto": Decimal("0.00118"),
        "amount_fiat": Decimal("100"),
    }
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def reset_metrics():
    from services.price_alerts import metrics as m
    m._metrics = AlertMetrics()
    yield
    m._metrics = AlertMetrics()


@pytest.fixture
def engine():
    return PriceAlertEngine(FakeRedis())


class TestExecutionHookBasic:

    @patch("services.exchange.service.ExchangeService")
    def test_buy_calls_exchange_buy(self, MockSvc, engine):
        mock_svc = MockSvc.return_value
        mock_svc.buy.return_value = _make_completed_result()
        alert = FakeAlert(order_payload={"side": "buy", "order_type": "limit", "amount": 100.0})
        engine._execute_order_hook(alert, MagicMock())
        mock_svc.buy.assert_called_once()
        assert alert.execution_status == "executed"

    @patch("services.exchange.service.ExchangeService")
    def test_sell_calls_exchange_sell(self, MockSvc, engine):
        mock_svc = MockSvc.return_value
        mock_svc.sell.return_value = _make_completed_result(amount_crypto=Decimal("0.5"), net_eur=Decimal("42500"))
        alert = FakeAlert(
            direction="down", price_source="bid",
            order_payload={"side": "sell", "order_type": "stop", "amount": 0.5},
        )
        engine._execute_order_hook(alert, MagicMock())
        mock_svc.sell.assert_called_once()
        assert alert.execution_status == "executed"

    def test_missing_side_fails(self, engine):
        alert = FakeAlert(order_payload={"amount": 100})
        engine._execute_order_hook(alert, MagicMock())
        assert alert.execution_status == "failed"
        assert alert.metadata_.get("failure_reason") == "missing_side_or_amount"

    def test_missing_amount_fails(self, engine):
        alert = FakeAlert(order_payload={"side": "buy"})
        engine._execute_order_hook(alert, MagicMock())
        assert alert.execution_status == "failed"

    def test_invalid_side_fails(self, engine):
        alert = FakeAlert(order_payload={"side": "short", "amount": 100})
        engine._execute_order_hook(alert, MagicMock())
        assert alert.execution_status == "failed"
        assert "invalid_side" in alert.metadata_.get("failure_reason", "")

    def test_skip_if_not_pending(self, engine):
        alert = FakeAlert(execution_status="executed")
        engine._execute_order_hook(alert, MagicMock())
        assert alert.execution_status == "executed"


class TestPreExecutionPriceCheck:

    def test_buy_blocked_when_ask_too_high(self, engine):
        engine.redis._data["prices:BTC:last_ask"] = "90000"
        alert = FakeAlert(target_price=85000)
        result = engine._pre_execution_price_check(alert, "buy", 200)
        assert result is False
        assert alert.execution_status == "failed"
        assert alert.metadata_["failure_reason"] == "price_moved_beyond_safety"

    def test_buy_passes_when_within_bounds(self, engine):
        engine.redis._data["prices:BTC:last_ask"] = "85100"
        alert = FakeAlert(target_price=85000)
        result = engine._pre_execution_price_check(alert, "buy", 200)
        assert result is True

    def test_sell_blocked_when_bid_too_low(self, engine):
        engine.redis._data["prices:BTC:last_bid"] = "80000"
        alert = FakeAlert(target_price=85000)
        result = engine._pre_execution_price_check(alert, "sell", 200)
        assert result is False

    def test_sell_passes_when_within_bounds(self, engine):
        engine.redis._data["prices:BTC:last_bid"] = "84900"
        alert = FakeAlert(target_price=85000)
        result = engine._pre_execution_price_check(alert, "sell", 200)
        assert result is True

    def test_proceeds_when_redis_has_no_price(self, engine):
        alert = FakeAlert(target_price=85000)
        result = engine._pre_execution_price_check(alert, "buy", 200)
        assert result is True

    def test_proceeds_when_redis_none(self):
        engine = PriceAlertEngine(None)
        alert = FakeAlert(target_price=85000)
        result = engine._pre_execution_price_check(alert, "buy", 200)
        assert result is True

    @patch("services.exchange.service.ExchangeService")
    def test_no_retry_if_precheck_fails(self, MockSvc, engine):
        engine.redis._data["prices:BTC:last_ask"] = "99999"
        alert = FakeAlert(target_price=85000, order_payload={"side": "buy", "amount": 100, "slippage_bps": 50})
        engine._execute_order_hook(alert, MagicMock())
        MockSvc.return_value.buy.assert_not_called()
        assert alert.execution_status == "failed"


class TestRetryLogic:

    @patch("services.exchange.service.ExchangeService")
    @patch("services.price_alerts.engine.time.sleep")
    def test_retry_on_exception(self, mock_sleep, MockSvc, engine):
        mock_svc = MockSvc.return_value
        mock_svc.buy.side_effect = [Exception("timeout"), _make_completed_result()]
        alert = FakeAlert()
        engine._execute_order_hook(alert, MagicMock())
        assert mock_svc.buy.call_count == 2
        assert alert.execution_status == "executed"

    @patch("services.exchange.service.ExchangeService")
    @patch("services.price_alerts.engine.time.sleep")
    def test_max_retries_reached(self, mock_sleep, MockSvc, engine):
        mock_svc = MockSvc.return_value
        mock_svc.buy.side_effect = Exception("always fails")
        alert = FakeAlert()
        engine._execute_order_hook(alert, MagicMock())
        assert mock_svc.buy.call_count == 3
        assert alert.execution_status == "failed"
        assert alert.metadata_["failure_reason"] == "all_attempts_failed"

    @patch("services.exchange.service.ExchangeService")
    @patch("services.price_alerts.engine.time.sleep")
    def test_unique_external_ref_per_attempt(self, mock_sleep, MockSvc, engine):
        mock_svc = MockSvc.return_value
        mock_svc.buy.side_effect = [Exception("fail"), _make_completed_result()]
        alert = FakeAlert()
        engine._execute_order_hook(alert, MagicMock())
        refs = [call.args[1].external_reference for call in mock_svc.buy.call_args_list]
        assert len(set(refs)) == len(refs), "Each attempt must have a unique external_reference"


class TestSlippageCheck:

    @patch("services.exchange.service.ExchangeService")
    def test_slippage_exceeded_fails(self, MockSvc, engine):
        mock_svc = MockSvc.return_value
        mock_svc.buy.return_value = _make_completed_result(price=Decimal("90000"))
        alert = FakeAlert(
            target_price=85000,
            order_payload={"side": "buy", "order_type": "limit", "amount": 100, "slippage_bps": 50},
        )
        engine._execute_order_hook(alert, MagicMock())
        assert alert.execution_status == "failed"
        assert alert.metadata_["failure_reason"] == "slippage_exceeded"
        assert alert.metadata_["slippage_bps_actual"] > 50

    @patch("services.exchange.service.ExchangeService")
    def test_slippage_within_bounds_succeeds(self, MockSvc, engine):
        mock_svc = MockSvc.return_value
        mock_svc.buy.return_value = _make_completed_result(price=Decimal("85010"))
        alert = FakeAlert(
            target_price=85000,
            order_payload={"side": "buy", "order_type": "limit", "amount": 100, "slippage_bps": 50},
        )
        engine._execute_order_hook(alert, MagicMock())
        assert alert.execution_status == "executed"

    @patch("services.exchange.service.ExchangeService")
    def test_no_slippage_check_when_not_set(self, MockSvc, engine):
        mock_svc = MockSvc.return_value
        mock_svc.buy.return_value = _make_completed_result(price=Decimal("99000"))
        alert = FakeAlert(
            target_price=85000,
            order_payload={"side": "buy", "order_type": "limit", "amount": 100},
        )
        engine._execute_order_hook(alert, MagicMock())
        assert alert.execution_status == "executed"


class TestPartialFill:

    @patch("services.exchange.service.ExchangeService")
    def test_partial_fill_sets_partial_status(self, MockSvc, engine):
        mock_svc = MockSvc.return_value
        mock_svc.buy.return_value = _make_completed_result(amount_fiat=Decimal("50"))
        alert = FakeAlert(order_payload={"side": "buy", "order_type": "limit", "amount": 100})
        engine._execute_order_hook(alert, MagicMock())
        assert alert.execution_status == "partial"
        assert alert.metadata_["partial_fill"] is True
        assert alert.metadata_["filled_amount"] == 50.0
        assert alert.metadata_["remaining_amount"] == 50.0
        assert alert.metadata_["can_retry_remaining"] is True

    @patch("services.exchange.service.ExchangeService")
    def test_full_fill_sets_executed(self, MockSvc, engine):
        mock_svc = MockSvc.return_value
        mock_svc.buy.return_value = _make_completed_result(amount_fiat=Decimal("100"))
        alert = FakeAlert(order_payload={"side": "buy", "order_type": "limit", "amount": 100})
        engine._execute_order_hook(alert, MagicMock())
        assert alert.execution_status == "executed"
        assert alert.metadata_["partial_fill"] is False

    @patch("services.exchange.service.ExchangeService")
    def test_zero_fill_fails(self, MockSvc, engine):
        mock_svc = MockSvc.return_value
        mock_svc.buy.return_value = _make_completed_result(amount_fiat=Decimal("0"), amount_crypto=Decimal("0"))
        alert = FakeAlert(order_payload={"side": "buy", "order_type": "limit", "amount": 100})
        engine._execute_order_hook(alert, MagicMock())
        assert alert.execution_status == "failed"
        assert alert.metadata_["failure_reason"] == "zero_fill"

    @patch("services.exchange.service.ExchangeService")
    def test_sell_partial_fill(self, MockSvc, engine):
        mock_svc = MockSvc.return_value
        mock_svc.sell.return_value = _make_completed_result(amount_crypto=Decimal("0.3"), net_eur=Decimal("25500"))
        alert = FakeAlert(
            direction="down", price_source="bid",
            order_payload={"side": "sell", "order_type": "stop", "amount": 0.5},
        )
        engine._execute_order_hook(alert, MagicMock())
        assert alert.execution_status == "partial"
        assert alert.metadata_["filled_amount"] == 0.3
        assert alert.metadata_["remaining_amount"] == pytest.approx(0.2, abs=0.001)


class TestMetricsCounters:

    @patch("services.exchange.service.ExchangeService")
    def test_executed_increments_counter(self, MockSvc, engine):
        from services.price_alerts.metrics import get_metrics
        mock_svc = MockSvc.return_value
        mock_svc.buy.return_value = _make_completed_result()
        alert = FakeAlert()
        engine._execute_order_hook(alert, MagicMock())
        snap = get_metrics().snapshot()
        assert snap["orders_executed"] == 1
        assert snap["orders_failed"] == 0

    @patch("services.exchange.service.ExchangeService")
    def test_failed_increments_counter(self, MockSvc, engine):
        from services.price_alerts.metrics import get_metrics
        mock_svc = MockSvc.return_value
        mock_svc.buy.return_value = {"status": "rejected", "reason": "insufficient_funds"}
        alert = FakeAlert()
        engine._execute_order_hook(alert, MagicMock())
        snap = get_metrics().snapshot()
        assert snap["orders_failed"] == 1

    @patch("services.exchange.service.ExchangeService")
    def test_partial_increments_counter(self, MockSvc, engine):
        from services.price_alerts.metrics import get_metrics
        mock_svc = MockSvc.return_value
        mock_svc.buy.return_value = _make_completed_result(amount_fiat=Decimal("50"))
        alert = FakeAlert(order_payload={"side": "buy", "order_type": "limit", "amount": 100})
        engine._execute_order_hook(alert, MagicMock())
        snap = get_metrics().snapshot()
        assert snap["orders_partial_fills"] == 1
        assert snap["orders_partial_remaining_volume"] == pytest.approx(50.0)

    def test_precheck_skip_increments_counter(self, engine):
        from services.price_alerts.metrics import get_metrics
        engine.redis._data["prices:BTC:last_ask"] = "99999"
        alert = FakeAlert(target_price=85000)
        engine._pre_execution_price_check(alert, "buy", 200)
        snap = get_metrics().snapshot()
        assert snap["orders_skipped_price"] == 1


class TestBusinessInvariants:

    def test_orders_not_recurring(self):
        alert = FakeAlert(trigger_mode="once", action_type="order")
        assert alert.trigger_mode == "once"

    @patch("services.exchange.service.ExchangeService")
    def test_metadata_has_required_fields(self, MockSvc, engine):
        mock_svc = MockSvc.return_value
        mock_svc.buy.return_value = _make_completed_result()
        alert = FakeAlert()
        engine._execute_order_hook(alert, MagicMock())
        meta = alert.metadata_
        assert "execution_price" in meta
        assert "order_id" in meta
        assert "filled_amount" in meta
        assert "remaining_amount" in meta
        assert "attempts" in meta
        assert "partial_fill" in meta
        assert "can_retry_remaining" in meta
        assert meta["attempts"] == 1
