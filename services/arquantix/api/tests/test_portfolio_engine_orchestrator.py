"""Tests for Portfolio Engine — Rebalance Orchestrator (Phase 8)."""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.allocations.models import TargetAllocation
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.orchestrator.enums import (
    OrchestrationStatus,
    RebalanceExecutionMode,
)
from services.portfolio_engine.orchestrator.models import OrchestrationRun
from services.portfolio_engine.orchestrator.service import (
    PortfolioNotFoundForOrchestrationError,
    RebalanceOrchestratorService,
)
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.rebalancing.models import RebalancePolicy
from services.portfolio_engine.strategies.models import (
    StrategyDefinition,
    StrategyInstance,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def svc() -> RebalanceOrchestratorService:
    return RebalanceOrchestratorService()


@pytest.fixture
def portfolio(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=uuid.uuid4(),
        portfolio_type="bundle_portfolio",
        name="Orchestrator Test PF",
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
        symbol=f"ORCH_BTC_{uuid.uuid4().hex[:4]}",
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
        code=f"ORCH_BTC-SPOT-{uuid.uuid4().hex[:4]}",
        name="BTC Spot",
        instrument_type="spot",
        metadata_={"market_data_instrument_id": 9901},
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
        code=f"orch_{strategy_type}_{uuid.uuid4().hex[:6]}",
        name=f"Orch test {strategy_type}",
        strategy_type=strategy_type,
        parameters_schema={},
    )
    db.add(sd)
    db.flush()
    return sd


def _instance(db, portfolio, definition, *, parameters=None):
    si = StrategyInstance(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        strategy_definition_id=definition.id,
        name=f"Orch instance {definition.strategy_type}",
        status="active",
        priority=100,
        parameters=parameters or {},
        metadata_={},
    )
    db.add(si)
    db.flush()
    return si


def _policy(db, portfolio, *, orchestration_mode=None, **kwargs):
    params = kwargs.get("parameters", {})
    if orchestration_mode:
        params["orchestration_mode"] = orchestration_mode
    rp = RebalancePolicy(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        method="threshold",
        parameters=params,
    )
    db.add(rp)
    db.flush()
    return rp


def _alloc(db, portfolio, instrument, weight):
    ta = TargetAllocation(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        instrument_id=instrument.id,
        target_weight=Decimal(str(weight)),
    )
    db.add(ta)
    db.flush()
    return ta


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
# 1. Manual mode: evaluate + log, no preview
# ---------------------------------------------------------------------------

class TestManualMode:

    def test_manual_no_preview_created(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        _policy(db, portfolio, orchestration_mode="manual")
        _alloc(db, portfolio, instrument_btc, "0.50")
        defn = _def(db, "threshold_rebalance")
        _instance(db, portfolio, defn, parameters={"threshold": "0.01"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.run_portfolio_cycle(db, portfolio.id)

        assert result.status == OrchestrationStatus.COMPLETED
        assert result.mode == RebalanceExecutionMode.MANUAL
        assert result.rebalance_preview_id is None
        assert result.actions_taken == 0
        assert result.signals_detected >= 1


# ---------------------------------------------------------------------------
# 2. Assisted mode: evaluate + preview
# ---------------------------------------------------------------------------

class TestAssistedMode:

    def test_assisted_creates_preview(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        _policy(db, portfolio, orchestration_mode="assisted")
        _alloc(db, portfolio, instrument_btc, "0.50")
        defn = _def(db, "threshold_rebalance")
        _instance(db, portfolio, defn, parameters={"threshold": "0.01"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.run_portfolio_cycle(db, portfolio.id)

        assert result.status == OrchestrationStatus.COMPLETED
        assert result.mode == RebalanceExecutionMode.ASSISTED
        assert result.rebalance_preview_id is not None
        assert result.actions_taken == 1


# ---------------------------------------------------------------------------
# 3. Automatic mode: preview + execution_eligible
# ---------------------------------------------------------------------------

class TestAutomaticMode:

    def test_automatic_creates_preview_and_marks_eligible(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        _policy(db, portfolio, orchestration_mode="automatic")
        _alloc(db, portfolio, instrument_btc, "0.50")
        defn = _def(db, "threshold_rebalance")
        _instance(db, portfolio, defn, parameters={"threshold": "0.01"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.run_portfolio_cycle(db, portfolio.id)

        assert result.status == OrchestrationStatus.COMPLETED
        assert result.mode == RebalanceExecutionMode.AUTOMATIC
        assert result.rebalance_preview_id is not None

        run = db.query(OrchestrationRun).filter(
            OrchestrationRun.id == result.run_id
        ).first()
        assert run is not None
        assert run.metadata_.get("execution_eligible") is True

    def test_automatic_no_execution_instructions_generated(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        """Verify that no pe_execution_instructions are created in automatic mode v1."""
        _policy(db, portfolio, orchestration_mode="automatic")
        _alloc(db, portfolio, instrument_btc, "0.50")
        defn = _def(db, "threshold_rebalance")
        _instance(db, portfolio, defn, parameters={"threshold": "0.01"})

        from services.portfolio_engine.execution.models import ExecutionInstruction

        before_count = db.query(ExecutionInstruction).count()

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            svc.run_portfolio_cycle(db, portfolio.id)

        after_count = db.query(ExecutionInstruction).count()
        assert after_count == before_count


# ---------------------------------------------------------------------------
# 4. Preview creation when signals detected
# ---------------------------------------------------------------------------

class TestPreviewCreation:

    def test_preview_created_on_threshold_signal(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        _policy(db, portfolio, orchestration_mode="assisted")
        _alloc(db, portfolio, instrument_btc, "0.50")
        defn = _def(db, "threshold_rebalance")
        _instance(db, portfolio, defn, parameters={"threshold": "0.01"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.run_portfolio_cycle(db, portfolio.id)

        assert result.rebalance_preview_id is not None

        from services.portfolio_engine.rebalance_preview.models import RebalancePreview
        preview = db.query(RebalancePreview).filter(
            RebalancePreview.id == result.rebalance_preview_id
        ).first()
        assert preview is not None
        assert preview.portfolio_id == portfolio.id


# ---------------------------------------------------------------------------
# 5. Preview NOT created in manual mode
# ---------------------------------------------------------------------------

class TestManualNoPreview:

    def test_no_preview_in_manual_even_with_signals(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        _policy(db, portfolio, orchestration_mode="manual")
        _alloc(db, portfolio, instrument_btc, "0.50")
        defn = _def(db, "threshold_rebalance")
        _instance(db, portfolio, defn, parameters={"threshold": "0.01"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.run_portfolio_cycle(db, portfolio.id)

        assert result.rebalance_preview_id is None


# ---------------------------------------------------------------------------
# 6. NAV = 0 abort
# ---------------------------------------------------------------------------

class TestNavZeroAbort:

    def test_nav_zero_aborts(self, db, svc, portfolio):
        _policy(db, portfolio, orchestration_mode="assisted")
        defn = _def(db, "threshold_rebalance")
        _instance(db, portfolio, defn)

        with patch(PRICE_BRIDGE, side_effect=_mock_price({})):
            result = svc.run_portfolio_cycle(db, portfolio.id)

        assert result.status == OrchestrationStatus.ABORTED
        assert result.abort_reason == "NAV is zero"


# ---------------------------------------------------------------------------
# 7. Portfolio without strategies
# ---------------------------------------------------------------------------

class TestNoStrategies:

    def test_portfolio_without_strategies(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        _policy(db, portfolio, orchestration_mode="assisted")

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.run_portfolio_cycle(db, portfolio.id)

        assert result.status == OrchestrationStatus.COMPLETED
        assert result.signals_detected == 0
        assert result.actions_taken == 0
        assert result.rebalance_preview_id is None


# ---------------------------------------------------------------------------
# 8. Preview with no actionable items (no signal for rebalance)
# ---------------------------------------------------------------------------

class TestNoActionableSignals:

    def test_no_rebalance_action_no_preview(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        _policy(db, portfolio, orchestration_mode="assisted")
        _alloc(db, portfolio, instrument_btc, "1.0")
        defn = _def(db, "threshold_rebalance")
        _instance(db, portfolio, defn, parameters={"threshold": "0.99"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.run_portfolio_cycle(db, portfolio.id)

        assert result.status == OrchestrationStatus.COMPLETED
        assert result.rebalance_preview_id is None
        assert result.actions_taken == 0


# ---------------------------------------------------------------------------
# 9. Orchestration run logging
# ---------------------------------------------------------------------------

class TestRunLogging:

    def test_run_persisted(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        _policy(db, portfolio, orchestration_mode="assisted")
        _alloc(db, portfolio, instrument_btc, "0.50")
        defn = _def(db, "threshold_rebalance")
        _instance(db, portfolio, defn, parameters={"threshold": "0.01"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.run_portfolio_cycle(db, portfolio.id)

        run = db.query(OrchestrationRun).filter(
            OrchestrationRun.id == result.run_id
        ).first()
        assert run is not None
        assert run.portfolio_id == portfolio.id
        assert run.status == OrchestrationStatus.COMPLETED
        assert run.completed_at is not None
        assert run.started_at is not None


# ---------------------------------------------------------------------------
# 10. Run history retrieval
# ---------------------------------------------------------------------------

class TestRunHistory:

    def test_history_returned(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        _policy(db, portfolio, orchestration_mode="assisted")
        defn = _def(db, "periodic_rebalance")
        _instance(db, portfolio, defn, parameters={"frequency": "daily"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            svc.run_portfolio_cycle(db, portfolio.id)
            svc.run_portfolio_cycle(db, portfolio.id)

        from services.portfolio_engine.orchestrator.repository import OrchestrationRunRepository
        repo = OrchestrationRunRepository()
        items, total = repo.list_by_portfolio(db, portfolio.id)

        assert total >= 2
        assert len(items) >= 2


# ---------------------------------------------------------------------------
# 11. metadata.execution_eligible in automatic mode
# ---------------------------------------------------------------------------

class TestExecutionEligible:

    def test_execution_eligible_only_in_automatic(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        _policy(db, portfolio, orchestration_mode="assisted")
        _alloc(db, portfolio, instrument_btc, "0.50")
        defn = _def(db, "threshold_rebalance")
        _instance(db, portfolio, defn, parameters={"threshold": "0.01"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.run_portfolio_cycle(db, portfolio.id)

        run = db.query(OrchestrationRun).filter(
            OrchestrationRun.id == result.run_id
        ).first()
        assert run.metadata_.get("execution_eligible") is not True


# ---------------------------------------------------------------------------
# 12. Policy missing → fallback manual
# ---------------------------------------------------------------------------

class TestPolicyMissing:

    def test_no_policy_defaults_to_manual(
        self, db, svc, portfolio, instrument_btc, position_btc,
    ):
        _alloc(db, portfolio, instrument_btc, "0.50")
        defn = _def(db, "threshold_rebalance")
        _instance(db, portfolio, defn, parameters={"threshold": "0.01"})

        prices = {instrument_btc.id: Decimal("70000")}
        with patch(PRICE_BRIDGE, side_effect=_mock_price(prices)):
            result = svc.run_portfolio_cycle(db, portfolio.id)

        assert result.mode == RebalanceExecutionMode.MANUAL
        assert result.rebalance_preview_id is None


# ---------------------------------------------------------------------------
# 13. Portfolio not found
# ---------------------------------------------------------------------------

class TestPortfolioNotFound:

    def test_orchestrate_portfolio_not_found(self, db, svc):
        with pytest.raises(PortfolioNotFoundForOrchestrationError):
            svc.run_portfolio_cycle(db, uuid.uuid4())
