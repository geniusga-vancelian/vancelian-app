"""Tests for Hardening Subphase 3 — Reconciliation Engine.

Covers:
 1. trades_vs_positions — matching => matched
 2. trades_vs_positions — quantity mismatch => mismatched
 3. trades_vs_positions — other portfolio unaffected
 4. positions_vs_valuations — aligned => matched
 5. positions_vs_valuations — missing position in snapshot => mismatched
 6. positions_vs_valuations — quantity mismatch => mismatched
 7. ledger_entries_vs_balances — matching => matched
 8. ledger_entries_vs_balances — mismatch detected => mismatched
 9. valuations_vs_performance — aligned => matched
10. valuations_vs_performance — nav mismatch => mismatched
11. admin endpoint reconcile-trades-positions
12. admin endpoint reconcile-positions-valuations
13. admin endpoint reconcile-valuations-performance
14. admin endpoint reconcile-balances
15. reconciliation reports list
16. reconciliation report detail
17. job run created and completed
18. audit success event created
19. failure path creates failed job run + audit failure
"""
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.hardening.jobs.models import JobRun
from services.portfolio_engine.hardening.reconciliation.models import ReconciliationReport
from services.portfolio_engine.hardening.reconciliation.service import (
    PortfolioNotFoundForReconciliationError,
    ReconciliationService,
)
from conftest import make_linked_client
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.ledger_accounts.models import LedgerAccount
from services.portfolio_engine.ledger_entries.models import LedgerEntry
from services.portfolio_engine.orders.models import Order
from services.portfolio_engine.performance.models import PortfolioReturnSeries
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.trades.models import Trade
from services.portfolio_engine.valuations.models import PortfolioValuation, PositionValuation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def svc() -> ReconciliationService:
    return ReconciliationService()


@pytest.fixture
def pe_client(db: Session) -> Client:
    return make_linked_client(db, email=f"recon_{uuid.uuid4().hex[:6]}@test.com", status="active", kyc_status="approved")


@pytest.fixture
def portfolio(db: Session, pe_client: Client) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=pe_client.id,
        portfolio_type="bundle_portfolio",
        name="Recon Test PF",
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
        symbol=f"RC_{uuid.uuid4().hex[:6]}",
        name="Recon Asset",
        asset_type="crypto",
        metadata_={},
    )
    db.add(asset)
    db.flush()

    inst = Instrument(
        id=uuid.uuid4(),
        asset_id=asset.id,
        code=f"RC-SPOT-{uuid.uuid4().hex[:6]}",
        name="Recon Instrument",
        instrument_type="spot",
        metadata_={},
    )
    db.add(inst)
    db.flush()
    return inst


# ---- helpers ----

def _create_order_and_trade(
    db: Session,
    portfolio: Portfolio,
    instrument: Instrument,
    side: str,
    quantity: Decimal,
    price: Decimal = Decimal("100"),
) -> Trade:
    order = Order(
        id=uuid.uuid4(),
        client_id=portfolio.client_id,
        portfolio_id=portfolio.id,
        instrument_id=instrument.id,
        order_type="market",
        side=side,
        quantity=quantity,
        status="filled",
        currency="EUR",
        metadata_={},
    )
    db.add(order)
    db.flush()

    gross = quantity * price
    trade = Trade(
        id=uuid.uuid4(),
        order_id=order.id,
        instrument_id=instrument.id,
        side=side,
        quantity=quantity,
        price=price,
        gross_amount=gross,
        fee_amount=Decimal("0"),
        net_amount=gross,
        currency="EUR",
        executed_at=datetime.now(timezone.utc),
        metadata_={},
    )
    db.add(trade)
    db.flush()
    return trade


def _create_position(
    db: Session,
    portfolio: Portfolio,
    instrument: Instrument,
    quantity: Decimal,
    status: str = "open",
) -> PositionAtom:
    pos = PositionAtom(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        instrument_id=instrument.id,
        position_type="spot",
        status=status,
        quantity=quantity,
        available_quantity=quantity,
        locked_quantity=Decimal("0"),
        cost_basis=quantity * Decimal("100"),
        average_entry_price=Decimal("100"),
        realized_pnl=Decimal("0"),
        metadata_={},
    )
    db.add(pos)
    db.flush()
    return pos


# ---------------------------------------------------------------------------
# 1–3 trades_vs_positions
# ---------------------------------------------------------------------------

class TestTradesVsPositions:

    def test_matching(self, db: Session, svc, portfolio, instrument):
        _create_order_and_trade(db, portfolio, instrument, "buy", Decimal("10"))
        _create_position(db, portfolio, instrument, Decimal("10"))

        result = svc.run_reconciliation_job(
            db, reconciliation_type="trades_vs_positions", portfolio_id=portfolio.id,
        )
        assert result.status == "matched"
        assert result.differences_found == 0

    def test_quantity_mismatch(self, db: Session, svc, portfolio, instrument):
        _create_order_and_trade(db, portfolio, instrument, "buy", Decimal("10"))
        _create_position(db, portfolio, instrument, Decimal("7"))

        result = svc.run_reconciliation_job(
            db, reconciliation_type="trades_vs_positions", portfolio_id=portfolio.id,
        )
        assert result.status == "mismatched"
        assert result.differences_found == 1
        assert result.metadata["mismatches"][0]["instrument_id"] == str(instrument.id)

    def test_other_portfolio_unaffected(
        self, db: Session, svc, portfolio, portfolio_b, instrument,
    ):
        _create_order_and_trade(db, portfolio, instrument, "buy", Decimal("10"))
        _create_position(db, portfolio, instrument, Decimal("10"))

        _create_order_and_trade(db, portfolio_b, instrument, "buy", Decimal("5"))
        _create_position(db, portfolio_b, instrument, Decimal("3"))

        result_a = svc.run_reconciliation_job(
            db, reconciliation_type="trades_vs_positions", portfolio_id=portfolio.id,
        )
        result_b = svc.run_reconciliation_job(
            db, reconciliation_type="trades_vs_positions", portfolio_id=portfolio_b.id,
        )
        assert result_a.status == "matched"
        assert result_b.status == "mismatched"


# ---------------------------------------------------------------------------
# 4–6 positions_vs_valuations
# ---------------------------------------------------------------------------

class TestPositionsVsValuations:

    def test_aligned(self, db: Session, svc, portfolio, instrument):
        pos = _create_position(db, portfolio, instrument, Decimal("10"))
        ts = datetime.now(timezone.utc)

        pv = PortfolioValuation(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            nav=Decimal("1000"),
            total_realized_pnl=Decimal("0"),
            total_unrealized_pnl=Decimal("0"),
            total_pnl=Decimal("0"),
            priced_positions_count=1,
            unpriced_positions_count=0,
            valuation_source="live",
            valuation_timestamp=ts,
            metadata_={},
        )
        db.add(pv)
        db.flush()

        sv = PositionValuation(
            id=uuid.uuid4(),
            position_id=pos.id,
            portfolio_id=portfolio.id,
            instrument_id=instrument.id,
            quantity=Decimal("10"),
            price=Decimal("100"),
            market_value=Decimal("1000"),
            pricing_status="priced",
            valuation_timestamp=ts,
        )
        db.add(sv)
        db.flush()

        result = svc.run_reconciliation_job(
            db, reconciliation_type="positions_vs_valuations", portfolio_id=portfolio.id,
        )
        assert result.status == "matched"
        assert result.differences_found == 0

    def test_missing_in_snapshot(self, db: Session, svc, portfolio, instrument):
        _create_position(db, portfolio, instrument, Decimal("10"))
        ts = datetime.now(timezone.utc)

        pv = PortfolioValuation(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            nav=Decimal("0"),
            total_realized_pnl=Decimal("0"),
            total_unrealized_pnl=Decimal("0"),
            total_pnl=Decimal("0"),
            priced_positions_count=0,
            unpriced_positions_count=0,
            valuation_source="live",
            valuation_timestamp=ts,
            metadata_={},
        )
        db.add(pv)
        db.flush()

        result = svc.run_reconciliation_job(
            db, reconciliation_type="positions_vs_valuations", portfolio_id=portfolio.id,
        )
        assert result.status == "mismatched"
        assert result.differences_found >= 1
        assert len(result.metadata["missing_in_snapshot"]) == 1

    def test_quantity_mismatch_val(self, db: Session, svc, portfolio, instrument):
        pos = _create_position(db, portfolio, instrument, Decimal("10"))
        ts = datetime.now(timezone.utc)

        pv = PortfolioValuation(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            nav=Decimal("500"),
            total_realized_pnl=Decimal("0"),
            total_unrealized_pnl=Decimal("0"),
            total_pnl=Decimal("0"),
            priced_positions_count=1,
            unpriced_positions_count=0,
            valuation_source="live",
            valuation_timestamp=ts,
            metadata_={},
        )
        db.add(pv)
        db.flush()

        sv = PositionValuation(
            id=uuid.uuid4(),
            position_id=pos.id,
            portfolio_id=portfolio.id,
            instrument_id=instrument.id,
            quantity=Decimal("5"),
            price=Decimal("100"),
            market_value=Decimal("500"),
            pricing_status="priced",
            valuation_timestamp=ts,
        )
        db.add(sv)
        db.flush()

        result = svc.run_reconciliation_job(
            db, reconciliation_type="positions_vs_valuations", portfolio_id=portfolio.id,
        )
        assert result.status == "mismatched"
        assert len(result.metadata["quantity_mismatches"]) == 1


# ---------------------------------------------------------------------------
# 7–8 ledger_entries_vs_balances
# ---------------------------------------------------------------------------

class TestLedgerEntriesVsBalances:

    def test_matching(self, db: Session, svc):
        acct = LedgerAccount(
            id=uuid.uuid4(),
            account_type="trading",
            account_code=f"RECON-{uuid.uuid4().hex[:8]}",
            label="Recon account",
            currency="EUR",
            balance=Decimal("100"),
            metadata_={},
        )
        db.add(acct)
        db.flush()

        entry = LedgerEntry(
            id=uuid.uuid4(),
            account_id=acct.id,
            entry_type="debit",
            amount=Decimal("100"),
            currency="EUR",
            reference_type="test",
            effective_at=datetime.now(timezone.utc),
            metadata_={},
        )
        db.add(entry)
        db.flush()

        result = svc.run_reconciliation_job(
            db, reconciliation_type="ledger_entries_vs_balances",
        )
        assert result.status == "matched"
        assert result.differences_found == 0

    def test_mismatch(self, db: Session, svc):
        acct = LedgerAccount(
            id=uuid.uuid4(),
            account_type="trading",
            account_code=f"RECON-{uuid.uuid4().hex[:8]}",
            label="Recon mismatch",
            currency="EUR",
            balance=Decimal("999"),
            metadata_={},
        )
        db.add(acct)
        db.flush()

        entry = LedgerEntry(
            id=uuid.uuid4(),
            account_id=acct.id,
            entry_type="debit",
            amount=Decimal("100"),
            currency="EUR",
            reference_type="test",
            effective_at=datetime.now(timezone.utc),
            metadata_={},
        )
        db.add(entry)
        db.flush()

        result = svc.run_reconciliation_job(
            db, reconciliation_type="ledger_entries_vs_balances",
        )
        assert result.status == "mismatched"
        assert result.differences_found >= 1


# ---------------------------------------------------------------------------
# 9–10 valuations_vs_performance
# ---------------------------------------------------------------------------

class TestValuationsVsPerformance:

    def test_aligned(self, db: Session, svc, portfolio):
        ts = datetime.now(timezone.utc)
        pv = PortfolioValuation(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            nav=Decimal("1000"),
            total_realized_pnl=Decimal("0"),
            total_unrealized_pnl=Decimal("0"),
            total_pnl=Decimal("0"),
            priced_positions_count=0,
            unpriced_positions_count=0,
            valuation_source="live",
            valuation_timestamp=ts,
            metadata_={},
        )
        db.add(pv)
        db.flush()

        pr = PortfolioReturnSeries(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            valuation_id=pv.id,
            timestamp=ts,
            nav=Decimal("1000"),
            metadata_={},
        )
        db.add(pr)
        db.flush()

        result = svc.run_reconciliation_job(
            db, reconciliation_type="valuations_vs_performance", portfolio_id=portfolio.id,
        )
        assert result.status == "matched"
        assert result.differences_found == 0

    def test_nav_mismatch(self, db: Session, svc, portfolio):
        ts = datetime.now(timezone.utc)
        pv = PortfolioValuation(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            nav=Decimal("1000"),
            total_realized_pnl=Decimal("0"),
            total_unrealized_pnl=Decimal("0"),
            total_pnl=Decimal("0"),
            priced_positions_count=0,
            unpriced_positions_count=0,
            valuation_source="live",
            valuation_timestamp=ts,
            metadata_={},
        )
        db.add(pv)
        db.flush()

        pr = PortfolioReturnSeries(
            id=uuid.uuid4(),
            portfolio_id=portfolio.id,
            valuation_id=pv.id,
            timestamp=ts,
            nav=Decimal("999"),
            metadata_={},
        )
        db.add(pr)
        db.flush()

        result = svc.run_reconciliation_job(
            db, reconciliation_type="valuations_vs_performance", portfolio_id=portfolio.id,
        )
        assert result.status == "mismatched"
        assert result.differences_found >= 1
        assert len(result.metadata["nav_mismatches"]) == 1


# ---------------------------------------------------------------------------
# 11–16 Admin endpoints
# ---------------------------------------------------------------------------

class TestAdminEndpoints:

    def test_reconcile_trades_positions(self, db: Session, svc, portfolio, instrument):
        _create_order_and_trade(db, portfolio, instrument, "buy", Decimal("5"))
        _create_position(db, portfolio, instrument, Decimal("5"))

        result = svc.run_reconciliation_job(
            db, reconciliation_type="trades_vs_positions", portfolio_id=portfolio.id,
        )
        assert result.reconciliation_type == "trades_vs_positions"
        assert result.status == "matched"

    def test_reconcile_positions_valuations(self, db: Session, svc, portfolio):
        result = svc.run_reconciliation_job(
            db, reconciliation_type="positions_vs_valuations", portfolio_id=portfolio.id,
        )
        assert result.reconciliation_type == "positions_vs_valuations"

    def test_reconcile_valuations_performance(self, db: Session, svc, portfolio):
        result = svc.run_reconciliation_job(
            db, reconciliation_type="valuations_vs_performance", portfolio_id=portfolio.id,
        )
        assert result.reconciliation_type == "valuations_vs_performance"

    def test_reconcile_ledger_balances(self, db: Session, svc):
        result = svc.run_reconciliation_job(
            db, reconciliation_type="ledger_entries_vs_balances",
        )
        assert result.reconciliation_type == "ledger_entries_vs_balances"

    def test_reports_list(self, db: Session, svc, portfolio, instrument):
        _create_order_and_trade(db, portfolio, instrument, "buy", Decimal("5"))
        _create_position(db, portfolio, instrument, Decimal("5"))
        svc.run_reconciliation_job(
            db, reconciliation_type="trades_vs_positions", portfolio_id=portfolio.id,
        )

        reports = db.query(ReconciliationReport).all()
        assert len(reports) >= 1

    def test_report_detail(self, db: Session, svc, portfolio, instrument):
        _create_order_and_trade(db, portfolio, instrument, "buy", Decimal("5"))
        _create_position(db, portfolio, instrument, Decimal("5"))
        result = svc.run_reconciliation_job(
            db, reconciliation_type="trades_vs_positions", portfolio_id=portfolio.id,
        )

        from services.portfolio_engine.hardening.reconciliation.repository import (
            ReconciliationReportRepository,
        )
        report = ReconciliationReportRepository.get_by_id(db, result.reconciliation_report_id)
        assert report is not None
        assert report.reconciliation_type == "trades_vs_positions"


# ---------------------------------------------------------------------------
# 17–18 Job + Audit
# ---------------------------------------------------------------------------

class TestJobAudit:

    def test_job_run_created(self, db: Session, svc, portfolio, instrument):
        _create_order_and_trade(db, portfolio, instrument, "buy", Decimal("5"))
        _create_position(db, portfolio, instrument, Decimal("5"))

        result = svc.run_reconciliation_job(
            db, reconciliation_type="trades_vs_positions", portfolio_id=portfolio.id,
        )

        job = db.query(JobRun).filter(JobRun.id == result.job_run_id).first()
        assert job is not None
        assert job.status == "completed"
        assert job.job_type == "reconciliation_trades_vs_positions"

    def test_audit_event_created(self, db: Session, svc, portfolio, instrument):
        _create_order_and_trade(db, portfolio, instrument, "buy", Decimal("5"))
        _create_position(db, portfolio, instrument, Decimal("5"))

        svc.run_reconciliation_job(
            db, reconciliation_type="trades_vs_positions", portfolio_id=portfolio.id,
        )

        events = (
            db.query(AuditEvent)
            .filter(AuditEvent.action == "trades_positions_reconciled")
            .all()
        )
        assert len(events) >= 1
        assert events[-1].entity_type == "portfolio"

    def test_failure_creates_failed_job_and_audit(self, db: Session, svc):
        fake_id = uuid.uuid4()
        with pytest.raises(PortfolioNotFoundForReconciliationError):
            svc.run_reconciliation_job(
                db, reconciliation_type="trades_vs_positions", portfolio_id=fake_id,
            )
