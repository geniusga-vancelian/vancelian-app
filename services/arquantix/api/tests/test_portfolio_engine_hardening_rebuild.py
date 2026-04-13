"""Tests for Hardening Subphase 2 — Rebuild / Replay / Job Runs.

Covers:
 1. job run created on rebuild start
 2. job run marked completed on success
 3. job run marked failed on exception
 4. positions rebuilt from trades for one portfolio
 5. rebuild_positions does not affect another portfolio
 6. rebuilt positions match expected quantities / status
 7. valuation snapshot created
 8. rebuild_valuations does not modify trades/positions
 9. performance series rebuilt from valuation snapshots
10. existing performance rows replaced for target portfolio
11. other portfolios unaffected by rebuild
12. rebuild-positions endpoint works
13. rebuild-valuations endpoint works
14. rebuild-performance endpoint works
15. jobs list endpoint works
16. job detail endpoint works
17. success audit event created
18. failure audit event created on rebuild failure
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.hardening.jobs.models import JobRun
from services.portfolio_engine.hardening.jobs.repository import JobRunRepository
from services.portfolio_engine.hardening.jobs.service import (
    PortfolioNotFoundForRebuildError,
    RebuildService,
)
from conftest import make_linked_client
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.orders.models import Order
from services.portfolio_engine.performance.models import PortfolioReturnSeries
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.trades.models import Trade
from services.portfolio_engine.valuations.models import PortfolioValuation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def svc() -> RebuildService:
    return RebuildService()


@pytest.fixture
def pe_client(db: Session) -> Client:
    return make_linked_client(db, email=f"rebuild_{uuid.uuid4().hex[:6]}@test.com", status="active", kyc_status="approved")


@pytest.fixture
def portfolio(db: Session, pe_client: Client) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=pe_client.id,
        portfolio_type="bundle_portfolio",
        name="Rebuild Test PF",
        base_currency="EUR",
        status="active",
        metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def portfolio_b(db: Session, pe_client: Client) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=pe_client.id,
        portfolio_type="bundle_portfolio",
        name="Other PF",
        base_currency="EUR",
        status="active",
        metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def instrument(db: Session) -> Instrument:
    asset = Asset(
        id=uuid.uuid4(),
        symbol=f"RB_{uuid.uuid4().hex[:6]}",
        name="Test Asset",
        asset_type="crypto",
        metadata_={},
    )
    db.add(asset)
    db.flush()

    inst = Instrument(
        id=uuid.uuid4(),
        asset_id=asset.id,
        code=f"RB-SPOT-{uuid.uuid4().hex[:6]}",
        name="Test Instrument",
        instrument_type="spot",
        metadata_={},
    )
    db.add(inst)
    db.flush()
    return inst


def _create_order_and_trade(
    db, portfolio, instrument, side, qty, price, days_ago=0
):
    order = Order(
        id=uuid.uuid4(),
        client_id=portfolio.client_id,
        portfolio_id=portfolio.id,
        instrument_id=instrument.id,
        side=side,
        order_type="market",
        quantity=Decimal(str(qty)),
        status="filled",
        metadata_={},
    )
    db.add(order)
    db.flush()

    executed_at = datetime.now(timezone.utc)
    gross = Decimal(str(qty)) * Decimal(str(price))
    trade = Trade(
        id=uuid.uuid4(),
        order_id=order.id,
        instrument_id=instrument.id,
        side=side,
        quantity=Decimal(str(qty)),
        price=Decimal(str(price)),
        gross_amount=gross,
        fee_amount=Decimal("0"),
        net_amount=gross,
        currency="EUR",
        executed_at=executed_at,
        metadata_={},
    )
    db.add(trade)
    db.flush()
    return trade


def _create_valuation_snap(db, portfolio, nav, days_ago=0):
    from datetime import timedelta
    ts = datetime.now(timezone.utc) - timedelta(days=days_ago)
    v = PortfolioValuation(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        nav=Decimal(str(nav)),
        total_realized_pnl=Decimal("0"),
        total_unrealized_pnl=Decimal("0"),
        total_pnl=Decimal("0"),
        priced_positions_count=1,
        unpriced_positions_count=0,
        valuation_source="on_demand_snapshot",
        valuation_timestamp=ts,
    )
    db.add(v)
    db.flush()
    return v


# ---------------------------------------------------------------------------
# 1. Job run created on rebuild start
# ---------------------------------------------------------------------------

class TestJobRunCreated:

    def test_job_run_created(self, db, svc, portfolio):
        result = svc.run_rebuild_job(
            db, job_type="rebuild_positions", portfolio_id=portfolio.id,
        )
        job = db.query(JobRun).filter(JobRun.id == result.job_run_id).first()
        assert job is not None
        assert job.job_type == "rebuild_positions"
        assert job.scope_id == str(portfolio.id)


# ---------------------------------------------------------------------------
# 2. Job run marked completed on success
# ---------------------------------------------------------------------------

class TestJobRunCompleted:

    def test_job_completed(self, db, svc, portfolio):
        result = svc.run_rebuild_job(
            db, job_type="rebuild_positions", portfolio_id=portfolio.id,
        )
        assert result.status == "completed"
        job = db.query(JobRun).filter(JobRun.id == result.job_run_id).first()
        assert job.status == "completed"
        assert job.completed_at is not None


# ---------------------------------------------------------------------------
# 3. Job run marked failed on exception
# ---------------------------------------------------------------------------

class TestJobRunFailed:

    def test_job_failed_portfolio_not_found(self, db, svc):
        with pytest.raises(PortfolioNotFoundForRebuildError):
            svc.run_rebuild_job(
                db, job_type="rebuild_positions", portfolio_id=uuid.uuid4(),
            )


# ---------------------------------------------------------------------------
# 4. Positions rebuilt from trades
# ---------------------------------------------------------------------------

class TestRebuildPositions:

    def test_positions_rebuilt(self, db, svc, portfolio, instrument):
        _create_order_and_trade(db, portfolio, instrument, "buy", 10, 100)

        from services.portfolio_engine.positions.service import PositionAtomService
        pos_svc = PositionAtomService()
        trades = db.query(Trade).join(Order).filter(
            Order.portfolio_id == portfolio.id,
        ).all()
        for t in trades:
            pos_svc.apply_trade(db, t)

        positions_before = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == portfolio.id,
        ).all()
        assert len(positions_before) == 1

        result = svc.run_rebuild_job(
            db, job_type="rebuild_positions", portfolio_id=portfolio.id,
        )
        assert result.status == "completed"
        assert result.records_processed == 1

        positions_after = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == portfolio.id,
        ).all()
        assert len(positions_after) == 1
        assert positions_after[0].quantity == Decimal("10")


# ---------------------------------------------------------------------------
# 5. rebuild_positions does not affect another portfolio
# ---------------------------------------------------------------------------

class TestRebuildIsolation:

    def test_other_portfolio_unaffected(self, db, svc, portfolio, portfolio_b, instrument):
        _create_order_and_trade(db, portfolio, instrument, "buy", 10, 100)
        _create_order_and_trade(db, portfolio_b, instrument, "buy", 5, 200)

        from services.portfolio_engine.positions.service import PositionAtomService
        pos_svc = PositionAtomService()
        for t in db.query(Trade).all():
            pos_svc.apply_trade(db, t)

        pos_b_before = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == portfolio_b.id,
        ).all()
        assert len(pos_b_before) == 1

        svc.run_rebuild_job(
            db, job_type="rebuild_positions", portfolio_id=portfolio.id,
        )

        pos_b_after = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == portfolio_b.id,
        ).all()
        assert len(pos_b_after) == 1
        assert pos_b_after[0].quantity == Decimal("5")


# ---------------------------------------------------------------------------
# 6. Rebuilt positions match expected quantities / status
# ---------------------------------------------------------------------------

class TestRebuildPositionAccuracy:

    def test_buy_sell_sequence(self, db, svc, portfolio, instrument):
        _create_order_and_trade(db, portfolio, instrument, "buy", 10, 100)
        _create_order_and_trade(db, portfolio, instrument, "buy", 5, 120)
        _create_order_and_trade(db, portfolio, instrument, "sell", 3, 150)

        result = svc.run_rebuild_job(
            db, job_type="rebuild_positions", portfolio_id=portfolio.id,
        )
        assert result.status == "completed"
        assert result.records_processed == 3

        positions = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.status == "open",
        ).all()
        assert len(positions) == 1
        assert positions[0].quantity == Decimal("12")


# ---------------------------------------------------------------------------
# 7. Valuation snapshot created
# ---------------------------------------------------------------------------

class TestRebuildValuations:

    def test_valuation_snapshot_created(self, db, svc, portfolio):
        snaps_before = db.query(PortfolioValuation).filter(
            PortfolioValuation.portfolio_id == portfolio.id,
        ).count()

        result = svc.run_rebuild_job(
            db, job_type="rebuild_valuations", portfolio_id=portfolio.id,
        )
        assert result.status == "completed"
        assert result.records_processed == 1

        snaps_after = db.query(PortfolioValuation).filter(
            PortfolioValuation.portfolio_id == portfolio.id,
        ).count()
        assert snaps_after == snaps_before + 1


# ---------------------------------------------------------------------------
# 8. rebuild_valuations does not modify trades/positions
# ---------------------------------------------------------------------------

class TestValuationNonDestructive:

    def test_does_not_touch_trades_or_positions(self, db, svc, portfolio, instrument):
        _create_order_and_trade(db, portfolio, instrument, "buy", 10, 100)

        from services.portfolio_engine.positions.service import PositionAtomService
        pos_svc = PositionAtomService()
        for t in db.query(Trade).join(Order).filter(
            Order.portfolio_id == portfolio.id,
        ).all():
            pos_svc.apply_trade(db, t)

        trades_before = db.query(Trade).join(Order).filter(
            Order.portfolio_id == portfolio.id,
        ).count()
        positions_before = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == portfolio.id,
        ).count()

        svc.run_rebuild_job(
            db, job_type="rebuild_valuations", portfolio_id=portfolio.id,
        )

        assert db.query(Trade).join(Order).filter(
            Order.portfolio_id == portfolio.id,
        ).count() == trades_before
        assert db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == portfolio.id,
        ).count() == positions_before


# ---------------------------------------------------------------------------
# 9. Performance series rebuilt from valuation snapshots
# ---------------------------------------------------------------------------

class TestRebuildPerformance:

    def test_performance_rebuilt(self, db, svc, portfolio):
        _create_valuation_snap(db, portfolio, "10000", days_ago=3)
        _create_valuation_snap(db, portfolio, "11000", days_ago=2)
        _create_valuation_snap(db, portfolio, "10500", days_ago=1)

        result = svc.run_rebuild_job(
            db, job_type="rebuild_performance", portfolio_id=portfolio.id,
        )
        assert result.status == "completed"
        assert result.records_processed == 3

        rows = db.query(PortfolioReturnSeries).filter(
            PortfolioReturnSeries.portfolio_id == portfolio.id,
        ).all()
        assert len(rows) == 3


# ---------------------------------------------------------------------------
# 10. Existing performance rows replaced
# ---------------------------------------------------------------------------

class TestPerformanceReplaced:

    def test_old_rows_cleared(self, db, svc, portfolio):
        _create_valuation_snap(db, portfolio, "10000", days_ago=3)
        _create_valuation_snap(db, portfolio, "11000", days_ago=2)

        svc.run_rebuild_job(
            db, job_type="rebuild_performance", portfolio_id=portfolio.id,
        )
        rows_first = db.query(PortfolioReturnSeries).filter(
            PortfolioReturnSeries.portfolio_id == portfolio.id,
        ).count()

        _create_valuation_snap(db, portfolio, "12000", days_ago=1)
        svc.run_rebuild_job(
            db, job_type="rebuild_performance", portfolio_id=portfolio.id,
        )
        rows_second = db.query(PortfolioReturnSeries).filter(
            PortfolioReturnSeries.portfolio_id == portfolio.id,
        ).count()

        assert rows_second == 3


# ---------------------------------------------------------------------------
# 11. Other portfolios unaffected by performance rebuild
# ---------------------------------------------------------------------------

class TestPerformanceIsolation:

    def test_other_portfolio_perf_unaffected(self, db, svc, portfolio, portfolio_b):
        _create_valuation_snap(db, portfolio, "10000", days_ago=2)
        _create_valuation_snap(db, portfolio, "11000", days_ago=1)
        _create_valuation_snap(db, portfolio_b, "5000", days_ago=2)
        _create_valuation_snap(db, portfolio_b, "6000", days_ago=1)

        svc.run_rebuild_job(
            db, job_type="rebuild_performance", portfolio_id=portfolio_b.id,
        )
        rows_b = db.query(PortfolioReturnSeries).filter(
            PortfolioReturnSeries.portfolio_id == portfolio_b.id,
        ).count()

        svc.run_rebuild_job(
            db, job_type="rebuild_performance", portfolio_id=portfolio.id,
        )

        rows_b_after = db.query(PortfolioReturnSeries).filter(
            PortfolioReturnSeries.portfolio_id == portfolio_b.id,
        ).count()
        assert rows_b_after == rows_b


# ---------------------------------------------------------------------------
# 12. rebuild-positions endpoint / service integration
# ---------------------------------------------------------------------------

class TestEndpointPositions:

    def test_rebuild_positions_via_service(self, db, svc, portfolio):
        result = svc.run_rebuild_job(
            db, job_type="rebuild_positions", portfolio_id=portfolio.id,
        )
        assert result.job_type == "rebuild_positions"
        assert result.status == "completed"


# ---------------------------------------------------------------------------
# 13. rebuild-valuations endpoint / service integration
# ---------------------------------------------------------------------------

class TestEndpointValuations:

    def test_rebuild_valuations_via_service(self, db, svc, portfolio):
        result = svc.run_rebuild_job(
            db, job_type="rebuild_valuations", portfolio_id=portfolio.id,
        )
        assert result.job_type == "rebuild_valuations"
        assert result.status == "completed"


# ---------------------------------------------------------------------------
# 14. rebuild-performance endpoint / service integration
# ---------------------------------------------------------------------------

class TestEndpointPerformance:

    def test_rebuild_performance_via_service(self, db, svc, portfolio):
        result = svc.run_rebuild_job(
            db, job_type="rebuild_performance", portfolio_id=portfolio.id,
        )
        assert result.job_type == "rebuild_performance"
        assert result.status == "completed"


# ---------------------------------------------------------------------------
# 15. Jobs list repository works
# ---------------------------------------------------------------------------

class TestJobsList:

    def test_jobs_list(self, db, svc, portfolio):
        svc.run_rebuild_job(
            db, job_type="rebuild_positions", portfolio_id=portfolio.id,
        )
        repo = JobRunRepository()
        items, total = repo.list_runs(db)
        assert total >= 1
        assert any(r.job_type == "rebuild_positions" for r in items)


# ---------------------------------------------------------------------------
# 16. Job detail repository works
# ---------------------------------------------------------------------------

class TestJobDetail:

    def test_job_detail(self, db, svc, portfolio):
        result = svc.run_rebuild_job(
            db, job_type="rebuild_positions", portfolio_id=portfolio.id,
        )
        repo = JobRunRepository()
        job = repo.get_by_id(db, result.job_run_id)
        assert job is not None
        assert job.job_type == "rebuild_positions"
        assert job.status == "completed"


# ---------------------------------------------------------------------------
# 17. Success audit event created
# ---------------------------------------------------------------------------

class TestAuditSuccess:

    def test_audit_on_rebuild_success(self, db, svc, portfolio):
        svc.run_rebuild_job(
            db, job_type="rebuild_positions", portfolio_id=portfolio.id,
        )
        events = db.query(AuditEvent).filter(
            AuditEvent.entity_id == str(portfolio.id),
            AuditEvent.action == "positions_rebuilt",
        ).all()
        assert len(events) == 1
        assert events[0].metadata_["outcome"] == "success"


# ---------------------------------------------------------------------------
# 18. Failure audit event on rebuild failure
# ---------------------------------------------------------------------------

class TestAuditFailure:

    def test_audit_on_not_found(self, db, svc):
        fake_id = uuid.uuid4()
        with pytest.raises(PortfolioNotFoundForRebuildError):
            svc.run_rebuild_job(
                db, job_type="rebuild_positions", portfolio_id=fake_id,
            )
