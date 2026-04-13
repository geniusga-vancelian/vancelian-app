"""Tests for Pool Interest Engine — Phase 2A.7.

Covers:
  A. No-borrow: interest = 0, no accrual rows
  B. Single lender/borrower: correct rates, lender gets full supply interest
  C. Multi-lender pro-rata distribution
  D. Multi-borrower aggregate
  E. Conservation: borrow_interest = lender_interest + platform_fee
  F. Double accrual prevention (idempotent)
  G. Rounding: small amounts
  H. Valuation impact: accrued_income reflected in wealth view
  I. Rate update
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import text


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    from database import SessionLocal
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


def _create_client(db: Session, email: str):
    row = db.execute(text("SELECT id FROM pe_clients WHERE email = :e"), {"e": email}).first()
    if row:
        class _C: pass
        c = _C(); c.id = row[0]; c.email = email
        return c
    cid = uuid.uuid4()
    db.execute(text(
        "INSERT INTO pe_clients (id, email, status, reference_currency, created_at, updated_at) "
        "VALUES (:id, :e, 'active', 'EUR', now(), now())"
    ), {"id": cid, "e": email})
    db.flush()
    class _C: pass
    c = _C(); c.id = cid; c.email = email
    return c


def _set_balance(db, client_id, asset, amount):
    from services.exchange.repository import CryptoPositionRepository
    pos = CryptoPositionRepository.get_or_create_for_update(db, client_id, asset)
    pos.balance = Decimal(str(amount))
    pos.available_balance = Decimal(str(amount))
    db.flush()


def _setup_pool_with_borrow(db, lender, borrower, asset, supply_amount, borrow_amount, borrow_rate_bps=500, supply_rate_bps=300):
    """Helper: create supply + borrow, set pool rates."""
    from services.lending.pool_service import PoolLendingService
    from services.lending.pool_models import LendingPool
    svc = PoolLendingService()
    svc.create_supply_commitment(db, client_id=lender.id, asset=asset, amount=Decimal(str(supply_amount)))
    result = svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset=asset, amount=Decimal(str(borrow_amount)))

    pool = db.query(LendingPool).filter(LendingPool.asset == asset.upper()).first()
    pool.borrow_rate_bps = Decimal(str(borrow_rate_bps))
    pool.supply_rate_bps = Decimal(str(supply_rate_bps))
    db.flush()
    return result, pool


# ---------------------------------------------------------------------------
# A. NO BORROW — interest = 0
# ---------------------------------------------------------------------------

class TestNoBorrow:

    def test_no_interest_without_borrow(self, db):
        """If total_borrowed == 0, no interest is generated."""
        lender = _create_client(db, "int_noborrow_l@test.com")
        _set_balance(db, lender.id, "USDC", 5000)

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("3000"))

        from services.lending.interest_engine import InterestEngine
        engine = InterestEngine()
        result = engine.run_daily_accrual(db, accrual_date=date(2026, 3, 21))

        assert result["pools_processed"] == 0
        assert result["total_interest_generated"] == 0.0

    def test_no_accrual_rows_without_borrow(self, db):
        """No snapshot/accrual rows created when no borrow."""
        from services.lending.interest_models import PoolInterestSnapshot
        from services.lending.pool_models import LendingPool

        lender = _create_client(db, "int_norows_l@test.com")
        _set_balance(db, lender.id, "USDC", 5000)

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("2000"))

        pool = db.query(LendingPool).filter(LendingPool.asset == "USDC").first()

        from services.lending.interest_engine import InterestEngine
        InterestEngine().run_daily_accrual(db, accrual_date=date(2026, 3, 20))

        snapshots = db.query(PoolInterestSnapshot).filter(
            PoolInterestSnapshot.pool_id == pool.id,
            PoolInterestSnapshot.date == date(2026, 3, 20),
        ).all()
        assert len(snapshots) == 0


# ---------------------------------------------------------------------------
# B. SINGLE LENDER / SINGLE BORROWER
# ---------------------------------------------------------------------------

class TestSingleLenderBorrower:

    def test_correct_interest_computation(self, db):
        """Verify exact interest amounts with known rates.

        Pool: 1000 USDC borrowed
        borrow_rate = 500 bps (5% APR)
        supply_rate = 300 bps (3% APR)

        daily_borrow = 500/10000/365 = 0.000136986...
        daily_supply = 300/10000/365 = 0.000082191...

        interest_generated  = 1000 * 0.000136986 = 0.136986...
        interest_to_lenders = 1000 * 0.000082191 = 0.082191...
        platform_fee        = 0.054794...
        """
        lender = _create_client(db, "int_single_l@test.com")
        borrower = _create_client(db, "int_single_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool_with_borrow(db, lender, borrower, "USDC", 3000, 1000)

        from services.lending.interest_engine import InterestEngine
        engine = InterestEngine()
        result = engine.run_daily_accrual(db, accrual_date=date(2026, 3, 21))

        assert result["pools_processed"] == 1
        pool_r = result["pools"][0]

        expected_generated = float(Decimal("1000") * Decimal("500") / Decimal("10000") / Decimal("365"))
        expected_to_lenders = float(Decimal("1000") * Decimal("300") / Decimal("10000") / Decimal("365"))
        expected_fee = expected_generated - expected_to_lenders

        assert abs(pool_r["interest_generated"] - expected_generated) < 1e-8
        assert abs(pool_r["interest_to_lenders"] - expected_to_lenders) < 1e-8
        assert abs(pool_r["platform_fee"] - expected_fee) < 1e-8

    def test_lender_gets_full_supply_interest(self, db):
        """Single lender → gets 100% of supply interest."""
        lender = _create_client(db, "int_full_l@test.com")
        borrower = _create_client(db, "int_full_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _, pool = _setup_pool_with_borrow(db, lender, borrower, "USDC", 3000, 2000)

        from services.lending.interest_engine import InterestEngine
        engine = InterestEngine()
        engine.run_daily_accrual(db, accrual_date=date(2026, 3, 22))

        total_lender = engine.get_total_accrued_interest(db, lender.id, pool.id, role="lender")
        total_borrower = engine.get_total_accrued_interest(db, borrower.id, pool.id, role="borrower")

        assert total_lender > 0, "Lender should earn interest"
        assert total_borrower > 0, "Borrower should owe interest"
        assert total_borrower > total_lender, "Borrower pays more than lender receives (platform fee)"

    def test_snapshot_created(self, db):
        """Verify snapshot row is created."""
        lender = _create_client(db, "int_snap_l@test.com")
        borrower = _create_client(db, "int_snap_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _, pool = _setup_pool_with_borrow(db, lender, borrower, "USDC", 3000, 1000)

        from services.lending.interest_engine import InterestEngine
        engine = InterestEngine()
        engine.run_daily_accrual(db, accrual_date=date(2026, 4, 1))

        snapshots = engine.get_snapshots(db, pool.id)
        assert len(snapshots) >= 1
        s = snapshots[0]
        assert s.date == date(2026, 4, 1)
        assert float(s.total_borrowed) == 1000.0


# ---------------------------------------------------------------------------
# C. MULTI-LENDER PRO-RATA
# ---------------------------------------------------------------------------

class TestMultiLenderProRata:

    def test_pro_rata_distribution(self, db):
        """3 lenders, borrow split → interest distributed proportionally."""
        l1 = _create_client(db, "int_prorata_l1@test.com")
        l2 = _create_client(db, "int_prorata_l2@test.com")
        l3 = _create_client(db, "int_prorata_l3@test.com")
        borrower = _create_client(db, "int_prorata_b@test.com")

        _set_balance(db, l1.id, "USDC", 5000)
        _set_balance(db, l2.id, "USDC", 5000)
        _set_balance(db, l3.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        from services.lending.pool_service import PoolLendingService
        from services.lending.pool_models import LendingPool
        svc = PoolLendingService()

        svc.create_supply_commitment(db, client_id=l1.id, asset="USDC", amount=Decimal("1000"))
        svc.create_supply_commitment(db, client_id=l2.id, asset="USDC", amount=Decimal("2000"))
        svc.create_supply_commitment(db, client_id=l3.id, asset="USDC", amount=Decimal("1000"))

        svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset="USDC", amount=Decimal("4000"))

        pool = db.query(LendingPool).filter(LendingPool.asset == "USDC").first()
        pool.borrow_rate_bps = Decimal("500")
        pool.supply_rate_bps = Decimal("300")
        db.flush()

        from services.lending.interest_engine import InterestEngine
        engine = InterestEngine()
        engine.run_daily_accrual(db, accrual_date=date(2026, 5, 1))

        i1 = engine.get_total_accrued_interest(db, l1.id, pool.id, role="lender")
        i2 = engine.get_total_accrued_interest(db, l2.id, pool.id, role="lender")
        i3 = engine.get_total_accrued_interest(db, l3.id, pool.id, role="lender")

        # L1: 1000/4000 = 25%, L2: 2000/4000 = 50%, L3: 1000/4000 = 25%
        assert i1 > 0
        assert i2 > 0
        assert i3 > 0
        assert abs(i2 - 2 * i1) < Decimal("0.0001"), "L2 (50%) should earn ~2x L1 (25%)"
        assert abs(i1 - i3) < Decimal("0.0001"), "L1 and L3 (same share) should earn same"


# ---------------------------------------------------------------------------
# D. MULTI-BORROWER
# ---------------------------------------------------------------------------

class TestMultiBorrower:

    def test_multiple_borrowers_aggregate(self, db):
        """Multiple borrowers — each gets their own interest_due."""
        lender = _create_client(db, "int_multib_l@test.com")
        b1 = _create_client(db, "int_multib_b1@test.com")
        b2 = _create_client(db, "int_multib_b2@test.com")
        _set_balance(db, lender.id, "USDC", 10000)
        _set_balance(db, b1.id, "USDC", 0)
        _set_balance(db, b2.id, "USDC", 0)

        from services.lending.pool_service import PoolLendingService
        from services.lending.pool_models import LendingPool
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("8000"))

        svc.borrow_from_pool(db, borrower_client_id=b1.id, asset="USDC", amount=Decimal("3000"))
        svc.borrow_from_pool(db, borrower_client_id=b2.id, asset="USDC", amount=Decimal("5000"))

        pool = db.query(LendingPool).filter(LendingPool.asset == "USDC").first()
        pool.borrow_rate_bps = Decimal("500")
        pool.supply_rate_bps = Decimal("300")
        db.flush()

        from services.lending.interest_engine import InterestEngine
        engine = InterestEngine()
        engine.run_daily_accrual(db, accrual_date=date(2026, 6, 1))

        i_b1 = engine.get_total_accrued_interest(db, b1.id, pool.id, role="borrower")
        i_b2 = engine.get_total_accrued_interest(db, b2.id, pool.id, role="borrower")

        assert i_b1 > 0
        assert i_b2 > 0
        # B2 borrows 5/3 of B1 → proportional interest
        ratio = i_b2 / i_b1
        assert abs(ratio - Decimal("5") / Decimal("3")) < Decimal("0.01")


# ---------------------------------------------------------------------------
# E. CONSERVATION
# ---------------------------------------------------------------------------

class TestConservation:

    def test_borrow_equals_lenders_plus_fee(self, db):
        """interest_generated = interest_to_lenders + platform_fee."""
        lender = _create_client(db, "int_cons_l@test.com")
        borrower = _create_client(db, "int_cons_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool_with_borrow(db, lender, borrower, "USDC", 3000, 2000)

        from services.lending.interest_engine import InterestEngine
        engine = InterestEngine()
        result = engine.run_daily_accrual(db, accrual_date=date(2026, 7, 1))

        p = result["pools"][0]
        gen = Decimal(str(p["interest_generated"]))
        to_l = Decimal(str(p["interest_to_lenders"]))
        fee = Decimal(str(p["platform_fee"]))

        assert abs(gen - to_l - fee) < Decimal("0.0000000001"), \
            f"Conservation broken: {gen} != {to_l} + {fee}"

    def test_borrower_interest_equals_generated(self, db):
        """Sum of all borrower interest_due == interest_generated."""
        lender = _create_client(db, "int_cons2_l@test.com")
        borrower = _create_client(db, "int_cons2_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _, pool = _setup_pool_with_borrow(db, lender, borrower, "USDC", 3000, 1500)

        from services.lending.interest_engine import InterestEngine
        engine = InterestEngine()
        result = engine.run_daily_accrual(db, accrual_date=date(2026, 7, 2))

        borrower_due = engine.get_total_accrued_interest(db, borrower.id, pool.id, role="borrower")
        gen = Decimal(str(result["pools"][0]["interest_generated"]))

        assert abs(borrower_due - gen) < Decimal("0.0000000001"), \
            f"Borrower due {borrower_due} != generated {gen}"


# ---------------------------------------------------------------------------
# F. DOUBLE ACCRUAL PREVENTION
# ---------------------------------------------------------------------------

class TestDoubleAccrual:

    def test_idempotent_accrual(self, db):
        """Running accrual twice for the same date should skip the second run."""
        lender = _create_client(db, "int_idem_l@test.com")
        borrower = _create_client(db, "int_idem_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool_with_borrow(db, lender, borrower, "USDC", 3000, 1000)

        from services.lending.interest_engine import InterestEngine
        engine = InterestEngine()

        r1 = engine.run_daily_accrual(db, accrual_date=date(2026, 8, 1))
        assert r1["pools_processed"] == 1

        r2 = engine.run_daily_accrual(db, accrual_date=date(2026, 8, 1))
        assert r2["pools_processed"] == 0, "Second run should skip (already accrued)"

    def test_different_dates_both_accrue(self, db):
        """Different dates should both produce accruals."""
        lender = _create_client(db, "int_dates_l@test.com")
        borrower = _create_client(db, "int_dates_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _, pool = _setup_pool_with_borrow(db, lender, borrower, "USDC", 3000, 1000)

        from services.lending.interest_engine import InterestEngine
        engine = InterestEngine()

        engine.run_daily_accrual(db, accrual_date=date(2026, 8, 1))
        engine.run_daily_accrual(db, accrual_date=date(2026, 8, 2))

        total = engine.get_total_accrued_interest(db, lender.id, pool.id, role="lender")
        single_day = Decimal("1000") * Decimal("300") / Decimal("10000") / Decimal("365")
        expected_2_days = single_day * 2

        assert abs(total - expected_2_days) < Decimal("0.0001"), \
            f"2-day accrual: expected ~{expected_2_days}, got {total}"


# ---------------------------------------------------------------------------
# G. ROUNDING
# ---------------------------------------------------------------------------

class TestRounding:

    def test_small_amount_rounding(self, db):
        """Very small amounts should still produce non-negative interest."""
        lender = _create_client(db, "int_round_l@test.com")
        borrower = _create_client(db, "int_round_b@test.com")
        _set_balance(db, lender.id, "USDC", 100)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool_with_borrow(db, lender, borrower, "USDC", 50, 1, borrow_rate_bps=100, supply_rate_bps=50)

        from services.lending.interest_engine import InterestEngine
        engine = InterestEngine()
        result = engine.run_daily_accrual(db, accrual_date=date(2026, 9, 1))

        p = result["pools"][0]
        assert p["interest_generated"] >= 0
        assert p["platform_fee"] >= 0
        assert p["interest_to_lenders"] >= 0


# ---------------------------------------------------------------------------
# H. VALUATION IMPACT
# ---------------------------------------------------------------------------

class TestValuationImpact:

    def test_accrued_income_on_position_atoms(self, db):
        """After accrual, PositionAtom.accrued_income should be > 0."""
        lender = _create_client(db, "int_val_l@test.com")
        borrower = _create_client(db, "int_val_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool_with_borrow(db, lender, borrower, "USDC", 3000, 2000)

        from services.lending.interest_engine import InterestEngine
        InterestEngine().run_daily_accrual(db, accrual_date=date(2026, 10, 1))

        from services.portfolio_engine.positions.models import PositionAtom
        from services.portfolio_engine.portfolios.models import Portfolio

        lender_portfolios = db.query(Portfolio).filter(Portfolio.client_id == lender.id).all()
        lending_atom = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id.in_([p.id for p in lender_portfolios]),
            PositionAtom.position_type == "lending",
            PositionAtom.status == "open",
        ).first()
        assert lending_atom is not None
        assert Decimal(str(lending_atom.accrued_income)) > 0, "Lending atom should have accrued income"

        borrower_portfolios = db.query(Portfolio).filter(Portfolio.client_id == borrower.id).all()
        borrowing_atom = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id.in_([p.id for p in borrower_portfolios]),
            PositionAtom.position_type == "borrowing",
            PositionAtom.status == "open",
        ).first()
        assert borrowing_atom is not None
        assert Decimal(str(borrowing_atom.accrued_income)) > 0, "Borrowing atom should have accrued income"

    def test_wealth_includes_accrued_interest(self, db):
        """Wealth view should reflect accrued interest in lending/borrowing values."""
        lender = _create_client(db, "int_wealth_l@test.com")
        borrower = _create_client(db, "int_wealth_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool_with_borrow(db, lender, borrower, "USDC", 3000, 2000)

        from services.lending.valuation import compute_total_portfolio_value_v2

        wealth_before = compute_total_portfolio_value_v2(db, lender.id)
        lending_before = wealth_before["lending_value_eur"]

        from services.lending.interest_engine import InterestEngine
        # Run multiple days for visible effect
        for d in range(5):
            InterestEngine().run_daily_accrual(db, accrual_date=date(2026, 10, 1) + timedelta(days=d))

        wealth_after = compute_total_portfolio_value_v2(db, lender.id)
        lending_after = wealth_after["lending_value_eur"]

        assert lending_after > lending_before, \
            f"Lending value should increase after accrual: {lending_before} → {lending_after}"


# ---------------------------------------------------------------------------
# I. RATE UPDATE
# ---------------------------------------------------------------------------

class TestRateUpdate:

    def test_rate_change_affects_next_accrual(self, db):
        """Changing pool rates should affect subsequent accruals."""
        lender = _create_client(db, "int_rate_l@test.com")
        borrower = _create_client(db, "int_rate_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _, pool = _setup_pool_with_borrow(db, lender, borrower, "USDC", 3000, 1000, borrow_rate_bps=500, supply_rate_bps=300)

        from services.lending.interest_engine import InterestEngine
        engine = InterestEngine()

        r1 = engine.run_daily_accrual(db, accrual_date=date(2026, 11, 1))
        gen1 = r1["pools"][0]["interest_generated"]

        # Double the rates
        pool.borrow_rate_bps = Decimal("1000")
        pool.supply_rate_bps = Decimal("600")
        db.flush()

        r2 = engine.run_daily_accrual(db, accrual_date=date(2026, 11, 2))
        gen2 = r2["pools"][0]["interest_generated"]

        assert abs(gen2 - gen1 * 2) < 1e-8, f"Doubling rate should double interest: {gen1} → {gen2}"
