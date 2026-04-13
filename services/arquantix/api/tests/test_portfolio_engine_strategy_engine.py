"""Tests for Portfolio Engine — Strategy Engine (Phase 7)."""
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.risk.models import RiskPolicy
from services.portfolio_engine.strategies.models import StrategyDefinition, StrategyInstance
from services.portfolio_engine.strategy_engine.enums import (
    SignalSeverity,
    StrategyActionType,
    StrategySignalType,
)
from services.portfolio_engine.strategy_engine.models import StrategyEvaluation
from services.portfolio_engine.strategy_engine.service import (
    PortfolioNotFoundForStrategyError,
    StrategyEngineService,
    StrategyInstanceNotFoundError,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def svc() -> StrategyEngineService:
    return StrategyEngineService()


@pytest.fixture
def portfolio(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        portfolio_type="bundle_portfolio",
        name="Strategy Engine Test PF",
        base_currency="EUR",
        status="active",
        metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def asset_btc(db: Session) -> Asset:
    a = Asset(
        id=uuid.uuid4(),
        symbol=f"SE_BTC_{uuid.uuid4().hex[:4]}",
        name="Bitcoin",
        asset_type="crypto",
        metadata_={},
    )
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def instrument_btc(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(),
        asset_id=asset_btc.id,
        code=f"SE_BTC-SPOT-{uuid.uuid4().hex[:4]}",
        name="BTC Spot",
        instrument_type="spot",
        metadata_={"market_data_instrument_id": 8801},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def position_btc(db: Session, portfolio: Portfolio, instrument_btc: Instrument) -> PositionAtom:
    p = PositionAtom(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        instrument_id=instrument_btc.id,
        position_type="spot",
        status="open",
        quantity=Decimal("1.0"),
        available_quantity=Decimal("1.0"),
        average_entry_price=Decimal("60000"),
        realized_pnl=Decimal("0"),
        metadata_={},
    )
    db.add(p)
    db.flush()
    return p


def _def(db, strategy_type):
    sd = StrategyDefinition(
        id=uuid.uuid4(),
        code=f"test_{strategy_type}_{uuid.uuid4().hex[:6]}",
        name=f"Test {strategy_type}",
        strategy_type=strategy_type,
        parameters_schema={},
    )
    db.add(sd)
    db.flush()
    return sd


def _instance(db, portfolio, definition, *, status="active", priority=100, parameters=None):
    si = StrategyInstance(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        strategy_definition_id=definition.id,
        name=f"Test instance {definition.strategy_type}",
        status=status,
        priority=priority,
        parameters=parameters or {},
        metadata_={},
    )
    db.add(si)
    db.flush()
    return si


def _mock_price(instrument_id_to_price: dict):
    from services.portfolio_engine.instruments.price_bridge import MarketDataLinkMissingError

    def _side_effect(db, instrument_id):
        if instrument_id in instrument_id_to_price:
            price = instrument_id_to_price[instrument_id]
            return {
                "instrument_id": str(instrument_id),
                "instrument_code": "MOCK",
                "asset_symbol": "MOCK",
                "market_data_instrument_id": 1,
                "provider": "mock",
                "provider_symbol": "MOCK",
                "price": str(price),
                "bid_price": str(price),
                "ask_price": str(price),
                "volume_24h": "1000",
                "quote_time": None,
                "updated_at": None,
            }
        raise MarketDataLinkMissingError(instrument_id)

    return _side_effect


PRICE_BRIDGE = "services.portfolio_engine.valuations.service.get_instrument_price"


# ---------------------------------------------------------------------------
# 1. threshold_rebalance triggered
# ---------------------------------------------------------------------------

class TestThresholdRebalance:

    def test_triggered_when_drift_exceeds_threshold(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        from services.portfolio_engine.allocations.models import TargetAllocation
        ta = TargetAllocation(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            instrument_id=instrument_btc.id,
            target_weight=Decimal("0.50"),
        )
        db.add(ta)
        db.flush()

        defn = _def(db, "threshold_rebalance")
        inst = _instance(db, portfolio, defn, parameters={"threshold": "0.01"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.evaluate_portfolio_strategies(db, portfolio.id)

        assert result.strategies_evaluated == 1
        assert len(result.signals) == 1
        sig = result.signals[0]
        assert sig.signal_type == StrategySignalType.REBALANCE_REQUIRED
        assert sig.action_type == StrategyActionType.CREATE_REBALANCE_PREVIEW
        assert "threshold" in sig.details
        assert "drift_score" in sig.details

    # 2. threshold_rebalance NOT triggered
    def test_not_triggered_within_threshold(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        from services.portfolio_engine.allocations.models import TargetAllocation
        ta = TargetAllocation(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            instrument_id=instrument_btc.id,
            target_weight=Decimal("1.0"),
        )
        db.add(ta)
        db.flush()

        defn = _def(db, "threshold_rebalance")
        inst = _instance(db, portfolio, defn, parameters={"threshold": "0.10"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.evaluate_portfolio_strategies(db, portfolio.id)

        sig = result.signals[0]
        assert sig.signal_type == StrategySignalType.NO_SIGNAL
        assert sig.action_type == StrategyActionType.NO_ACTION


# ---------------------------------------------------------------------------
# 3-4. periodic_rebalance
# ---------------------------------------------------------------------------

class TestPeriodicRebalance:

    def test_triggered_when_interval_exceeded(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        defn = _def(db, "periodic_rebalance")
        inst = _instance(db, portfolio, defn, parameters={"frequency": "monthly"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.evaluate_portfolio_strategies(db, portfolio.id)

        sig = result.signals[0]
        assert sig.signal_type == StrategySignalType.PERIODIC_REBALANCE
        assert sig.action_type == StrategyActionType.CREATE_REBALANCE_PREVIEW
        assert sig.details["frequency"] == "monthly"

    def test_not_triggered_within_interval(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        defn = _def(db, "periodic_rebalance")
        inst = _instance(db, portfolio, defn, parameters={"frequency": "yearly"})

        recent_eval = StrategyEvaluation(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            strategy_instance_id=inst.id,
            strategy_type="periodic_rebalance",
            signal_type=StrategySignalType.PERIODIC_REBALANCE,
            action_type=StrategyActionType.CREATE_REBALANCE_PREVIEW,
            severity=SignalSeverity.INFO,
            details={},
            evaluation_timestamp=datetime.now(timezone.utc) - timedelta(days=10),
        )
        db.add(recent_eval)
        db.flush()

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.evaluate_portfolio_strategies(db, portfolio.id)

        sig = result.signals[0]
        assert sig.signal_type == StrategySignalType.NO_SIGNAL


# ---------------------------------------------------------------------------
# 5-6. drift_guard
# ---------------------------------------------------------------------------

class TestDriftGuard:

    def test_warning_when_drift_high(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        from services.portfolio_engine.allocations.models import TargetAllocation
        ta = TargetAllocation(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            instrument_id=instrument_btc.id,
            target_weight=Decimal("0.50"),
        )
        db.add(ta)
        db.flush()

        defn = _def(db, "drift_guard")
        inst = _instance(db, portfolio, defn, parameters={"warning_threshold": "0.01"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.evaluate_portfolio_strategies(db, portfolio.id)

        sig = result.signals[0]
        assert sig.signal_type == StrategySignalType.DRIFT_WARNING
        assert sig.action_type == StrategyActionType.NO_ACTION
        assert sig.severity == SignalSeverity.WARNING

    def test_no_signal_when_drift_low(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        from services.portfolio_engine.allocations.models import TargetAllocation
        ta = TargetAllocation(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            instrument_id=instrument_btc.id,
            target_weight=Decimal("1.0"),
        )
        db.add(ta)
        db.flush()

        defn = _def(db, "drift_guard")
        inst = _instance(db, portfolio, defn, parameters={"warning_threshold": "0.50"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.evaluate_portfolio_strategies(db, portfolio.id)

        sig = result.signals[0]
        assert sig.signal_type == StrategySignalType.NO_SIGNAL


# ---------------------------------------------------------------------------
# 7-8. risk_limit
# ---------------------------------------------------------------------------

class TestRiskLimit:

    def test_exceeded_when_weight_over_limit(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        rp = RiskPolicy(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            max_asset_weight=Decimal("0.30"),
        )
        db.add(rp)
        db.flush()

        defn = _def(db, "risk_limit")
        inst = _instance(db, portfolio, defn)

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.evaluate_portfolio_strategies(db, portfolio.id)

        sig = result.signals[0]
        assert sig.signal_type == StrategySignalType.RISK_LIMIT_EXCEEDED
        assert sig.action_type == StrategyActionType.ALERT_RISK
        assert sig.severity == SignalSeverity.CRITICAL
        assert len(sig.details["breached_instruments"]) >= 1

    def test_ok_when_weight_within_limit(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        rp = RiskPolicy(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            max_asset_weight=Decimal("1.0"),
        )
        db.add(rp)
        db.flush()

        defn = _def(db, "risk_limit")
        inst = _instance(db, portfolio, defn)

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.evaluate_portfolio_strategies(db, portfolio.id)

        sig = result.signals[0]
        assert sig.signal_type == StrategySignalType.NO_SIGNAL

    def test_no_risk_policy_skips_gracefully(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        defn = _def(db, "risk_limit")
        inst = _instance(db, portfolio, defn)

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.evaluate_portfolio_strategies(db, portfolio.id)

        sig = result.signals[0]
        assert sig.signal_type == StrategySignalType.NO_SIGNAL
        assert any("No RiskPolicy" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# 9. Multiple strategies on one portfolio
# ---------------------------------------------------------------------------

class TestMultipleStrategies:

    def test_multiple_strategies_evaluated(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        from services.portfolio_engine.allocations.models import TargetAllocation
        ta = TargetAllocation(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            instrument_id=instrument_btc.id,
            target_weight=Decimal("0.50"),
        )
        db.add(ta)
        db.flush()

        defn_threshold = _def(db, "threshold_rebalance")
        defn_drift = _def(db, "drift_guard")
        inst1 = _instance(db, portfolio, defn_threshold, priority=1, parameters={"threshold": "0.01"})
        inst2 = _instance(db, portfolio, defn_drift, priority=2, parameters={"warning_threshold": "0.01"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.evaluate_portfolio_strategies(db, portfolio.id)

        assert result.strategies_evaluated == 2
        assert len(result.signals) == 2

        types = {s.signal_type for s in result.signals}
        assert StrategySignalType.REBALANCE_REQUIRED in types
        assert StrategySignalType.DRIFT_WARNING in types


# ---------------------------------------------------------------------------
# 10. No active strategies
# ---------------------------------------------------------------------------

class TestNoStrategies:

    def test_portfolio_without_strategies(self, db, svc, portfolio):
        result = svc.evaluate_portfolio_strategies(db, portfolio.id)
        assert result.strategies_evaluated == 0
        assert len(result.signals) == 0
        assert any("no active strategies" in w.lower() for w in result.warnings)


# ---------------------------------------------------------------------------
# 11. Paused/archived strategy ignored
# ---------------------------------------------------------------------------

class TestIgnoredStrategies:

    def test_paused_strategy_not_evaluated(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        defn = _def(db, "threshold_rebalance")
        inst = _instance(db, portfolio, defn, status="paused", parameters={"threshold": "0.01"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.evaluate_portfolio_strategies(db, portfolio.id)

        assert result.strategies_evaluated == 0

    def test_archived_strategy_not_evaluated(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        defn = _def(db, "threshold_rebalance")
        inst = _instance(db, portfolio, defn, status="archived")

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.evaluate_portfolio_strategies(db, portfolio.id)

        assert result.strategies_evaluated == 0


# ---------------------------------------------------------------------------
# 12. Append-only logging
# ---------------------------------------------------------------------------

class TestLogging:

    def test_evaluation_logged_append_only(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        defn = _def(db, "periodic_rebalance")
        inst = _instance(db, portfolio, defn, parameters={"frequency": "daily"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            svc.evaluate_portfolio_strategies(db, portfolio.id)

        logs = (
            db.query(StrategyEvaluation)
            .filter(StrategyEvaluation.portfolio_id == portfolio.id)
            .all()
        )
        assert len(logs) >= 1
        log = logs[0]
        assert log.strategy_type == "periodic_rebalance"
        assert log.signal_type is not None
        assert log.action_type is not None
        assert log.evaluation_timestamp is not None


# ---------------------------------------------------------------------------
# 13. execute_strategy_action creates rebalance preview
# ---------------------------------------------------------------------------

class TestExecuteAction:

    def test_execute_creates_rebalance_preview(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        from services.portfolio_engine.allocations.models import TargetAllocation
        ta = TargetAllocation(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            instrument_id=instrument_btc.id,
            target_weight=Decimal("0.50"),
        )
        db.add(ta)
        db.flush()

        defn = _def(db, "threshold_rebalance")
        inst = _instance(db, portfolio, defn, parameters={"threshold": "0.01"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.execute_strategy_action(db, inst.id)

        assert result.strategies_evaluated == 1
        sig = result.signals[0]
        assert sig.action_type == StrategyActionType.CREATE_REBALANCE_PREVIEW

        from services.portfolio_engine.rebalance_preview.models import RebalancePreview
        previews = (
            db.query(RebalancePreview)
            .filter(RebalancePreview.portfolio_id == portfolio.id)
            .all()
        )
        assert len(previews) >= 1

    def test_execute_instance_not_found(self, db, svc):
        with pytest.raises(StrategyInstanceNotFoundError):
            svc.execute_strategy_action(db, uuid.uuid4())


# ---------------------------------------------------------------------------
# 14. Unknown strategy type
# ---------------------------------------------------------------------------

class TestUnknownStrategyType:

    def test_unknown_type_returns_no_signal(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        defn = _def(db, "exotic_strategy_xyz")
        inst = _instance(db, portfolio, defn)

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.evaluate_portfolio_strategies(db, portfolio.id)

        assert result.strategies_evaluated == 1
        sig = result.signals[0]
        assert sig.signal_type == StrategySignalType.NO_SIGNAL
        assert sig.action_type == StrategyActionType.NO_ACTION
        assert "Unsupported" in sig.details.get("reason", "")


# ---------------------------------------------------------------------------
# 15. Portfolio not found
# ---------------------------------------------------------------------------

class TestPortfolioNotFound:

    def test_evaluate_portfolio_not_found(self, db, svc):
        with pytest.raises(PortfolioNotFoundForStrategyError):
            svc.evaluate_portfolio_strategies(db, uuid.uuid4())
