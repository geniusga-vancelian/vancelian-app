"""Tests for Pool Repayment & Settlement Engine — Phase 2A.8.

Covers:
  A. Full repayment (single lender, with interest)
  B. Multi-lender pro-rata settlement
  C. Conservation: borrower_payment == lenders_received + platform_fee
  D. Position closure (lending + borrowing atoms → closed)
  E. Insufficient balance → reject
  F. Double repay → reject
  G. Repay without interest (0 accrued)
  H. Pool state after repay (total_borrowed, utilization)
  I. Partial borrow repay (one of multiple borrows for same client)
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

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


def _get_balance(db, client_id, asset) -> Decimal:
    from services.exchange.models import CryptoPosition
    pos = db.query(CryptoPosition).filter(
        CryptoPosition.client_id == client_id, CryptoPosition.asset == asset,
    ).first()
    return Decimal(str(pos.balance)) if pos else Decimal("0")


def _setup_and_borrow(db, lender, borrower, asset, supply, borrow, borrow_rate_bps=500, supply_rate_bps=300):
    """Supply + borrow + set pool rates. Returns (borrow_result, pool)."""
    from services.lending.pool_service import PoolLendingService
    from services.lending.pool_models import LendingPool
    svc = PoolLendingService()
    svc.create_supply_commitment(db, client_id=lender.id, asset=asset, amount=Decimal(str(supply)))
    result = svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset=asset, amount=Decimal(str(borrow)))
    pool = db.query(LendingPool).filter(LendingPool.asset == asset.upper()).first()
    pool.borrow_rate_bps = Decimal(str(borrow_rate_bps))
    pool.supply_rate_bps = Decimal(str(supply_rate_bps))
    db.flush()
    return result, pool


# ---------------------------------------------------------------------------
# A. FULL REPAYMENT (SINGLE LENDER, WITH INTEREST)
# ---------------------------------------------------------------------------

class TestFullRepayment:

    def test_repay_with_interest(self, db):
        """Full cycle: supply → borrow → accrue → repay."""
        lender = _create_client(db, "repay_full_l@test.com")
        borrower = _create_client(db, "repay_full_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        result, pool = _setup_and_borrow(db, lender, borrower, "USDC", 3000, 1000)
        borrow_id = result["borrow_position_id"]

        # Accrue 3 days of interest
        from services.lending.interest_engine import InterestEngine
        engine = InterestEngine()
        for d in range(3):
            engine.run_daily_accrual(db, accrual_date=date(2026, 12, 1 + d))

        # Borrower needs enough to repay principal + interest
        # Give borrower a bit extra to cover interest
        _set_balance(db, borrower.id, "USDC", 1100)

        from services.lending.repayment_engine import RepaymentEngine
        repay = RepaymentEngine()
        result = repay.repay_borrow_position(db, borrow_position_id=borrow_id)

        assert result["principal"] == 1000.0
        assert result["accrued_interest"] > 0, "Should have accrued interest"
        assert result["total_paid"] == result["principal"] + result["accrued_interest"]
        assert result["platform_fee"] > 0, "Platform should earn fee"
        assert result["lenders_settled"] == 1

    def test_lender_receives_principal_plus_interest(self, db):
        """Lender gets back more than they put in."""
        lender = _create_client(db, "repay_lget_l@test.com")
        borrower = _create_client(db, "repay_lget_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        lender_before = _get_balance(db, lender.id, "USDC")

        result, pool = _setup_and_borrow(db, lender, borrower, "USDC", 3000, 1000)
        borrow_id = result["borrow_position_id"]

        lender_after_borrow = _get_balance(db, lender.id, "USDC")
        assert lender_after_borrow == lender_before - 1000

        from services.lending.interest_engine import InterestEngine
        InterestEngine().run_daily_accrual(db, accrual_date=date(2026, 12, 10))

        _set_balance(db, borrower.id, "USDC", 1100)

        from services.lending.repayment_engine import RepaymentEngine
        repay_result = RepaymentEngine().repay_borrow_position(db, borrow_position_id=borrow_id)

        lender_after_repay = _get_balance(db, lender.id, "USDC")
        lender_received = lender_after_repay - lender_after_borrow

        assert lender_received > 1000, f"Lender should receive more than principal: {lender_received}"

    def test_borrower_balance_decreases(self, db):
        """Borrower's balance should decrease by total_due."""
        lender = _create_client(db, "repay_bdec_l@test.com")
        borrower = _create_client(db, "repay_bdec_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        result, _ = _setup_and_borrow(db, lender, borrower, "USDC", 3000, 1000)
        borrow_id = result["borrow_position_id"]

        from services.lending.interest_engine import InterestEngine
        InterestEngine().run_daily_accrual(db, accrual_date=date(2026, 12, 15))

        _set_balance(db, borrower.id, "USDC", 2000)
        borrower_before = _get_balance(db, borrower.id, "USDC")

        from services.lending.repayment_engine import RepaymentEngine
        repay_result = RepaymentEngine().repay_borrow_position(db, borrow_position_id=borrow_id)

        borrower_after = _get_balance(db, borrower.id, "USDC")
        paid = borrower_before - borrower_after
        assert abs(float(paid) - repay_result["total_paid"]) < 0.01


# ---------------------------------------------------------------------------
# B. MULTI-LENDER SETTLEMENT
# ---------------------------------------------------------------------------

class TestMultiLenderSettlement:

    def test_multi_lender_pro_rata(self, db):
        """Multiple lenders receive proportional principal + interest."""
        l1 = _create_client(db, "repay_ml_l1@test.com")
        l2 = _create_client(db, "repay_ml_l2@test.com")
        borrower = _create_client(db, "repay_ml_b@test.com")

        _set_balance(db, l1.id, "USDC", 5000)
        _set_balance(db, l2.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        from services.lending.pool_service import PoolLendingService
        from services.lending.pool_models import LendingPool
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=l1.id, asset="USDC", amount=Decimal("600"))
        svc.create_supply_commitment(db, client_id=l2.id, asset="USDC", amount=Decimal("400"))

        result = svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset="USDC", amount=Decimal("1000"))
        borrow_id = result["borrow_position_id"]

        pool = db.query(LendingPool).filter(LendingPool.asset == "USDC").first()
        pool.borrow_rate_bps = Decimal("500")
        pool.supply_rate_bps = Decimal("300")
        db.flush()

        from services.lending.interest_engine import InterestEngine
        InterestEngine().run_daily_accrual(db, accrual_date=date(2026, 12, 20))

        l1_before = _get_balance(db, l1.id, "USDC")
        l2_before = _get_balance(db, l2.id, "USDC")

        _set_balance(db, borrower.id, "USDC", 1100)

        from services.lending.repayment_engine import RepaymentEngine
        repay_result = RepaymentEngine().repay_borrow_position(db, borrow_position_id=borrow_id)

        assert repay_result["lenders_settled"] == 2

        l1_after = _get_balance(db, l1.id, "USDC")
        l2_after = _get_balance(db, l2.id, "USDC")

        l1_received = l1_after - l1_before
        l2_received = l2_after - l2_before

        # L1 had 60%, L2 had 40% of allocation
        assert l1_received > l2_received, "L1 (60%) should receive more than L2 (40%)"
        # Verify ratio is approximately 60/40
        ratio = float(l1_received / l2_received)
        assert abs(ratio - 1.5) < 0.1, f"Ratio should be ~1.5 (60/40), got {ratio}"


# ---------------------------------------------------------------------------
# C. CONSERVATION
# ---------------------------------------------------------------------------

class TestRepaymentConservation:

    def test_borrower_payment_equals_lenders_plus_fee(self, db):
        """total_paid == sum(lender_received) + platform_fee."""
        lender = _create_client(db, "repay_cons_l@test.com")
        borrower = _create_client(db, "repay_cons_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        result, _ = _setup_and_borrow(db, lender, borrower, "USDC", 3000, 1000)
        borrow_id = result["borrow_position_id"]

        from services.lending.interest_engine import InterestEngine
        for d in range(5):
            InterestEngine().run_daily_accrual(db, accrual_date=date(2027, 1, 1 + d))

        _set_balance(db, borrower.id, "USDC", 1200)

        from services.lending.repayment_engine import RepaymentEngine
        r = RepaymentEngine().repay_borrow_position(db, borrow_position_id=borrow_id)

        total_to_lenders = sum(d["total_received"] for d in r["lender_details"])
        platform_fee = r["platform_fee"]
        total_paid = r["total_paid"]

        assert abs(total_paid - total_to_lenders - platform_fee) < 0.01, \
            f"Conservation: {total_paid} != {total_to_lenders} + {platform_fee}"


# ---------------------------------------------------------------------------
# D. POSITION CLOSURE
# ---------------------------------------------------------------------------

class TestPositionClosure:

    def test_positions_closed_after_repay(self, db):
        """Borrowing and lending PositionAtoms should be closed after repay."""
        lender = _create_client(db, "repay_close_l@test.com")
        borrower = _create_client(db, "repay_close_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        result, _ = _setup_and_borrow(db, lender, borrower, "USDC", 3000, 1000)
        borrow_id = result["borrow_position_id"]

        _set_balance(db, borrower.id, "USDC", 1100)

        from services.lending.repayment_engine import RepaymentEngine
        RepaymentEngine().repay_borrow_position(db, borrow_position_id=borrow_id)

        from services.portfolio_engine.positions.models import PositionAtom
        from services.portfolio_engine.portfolios.models import Portfolio

        # Borrowing atom closed
        bp = db.query(Portfolio).filter(Portfolio.client_id == borrower.id).all()
        if bp:
            borrowing_atoms = db.query(PositionAtom).filter(
                PositionAtom.portfolio_id.in_([p.id for p in bp]),
                PositionAtom.position_type == "borrowing",
                PositionAtom.status == "open",
            ).all()
            assert len(borrowing_atoms) == 0, "Borrowing atom should be closed"

        # Lending atom closed
        lp = db.query(Portfolio).filter(Portfolio.client_id == lender.id).all()
        if lp:
            lending_atoms = db.query(PositionAtom).filter(
                PositionAtom.portfolio_id.in_([p.id for p in lp]),
                PositionAtom.position_type == "lending",
                PositionAtom.status == "open",
            ).all()
            assert len(lending_atoms) == 0, "Lending atom should be closed"

    def test_borrow_position_status_repaid(self, db):
        """PoolBorrowPosition.status should be 'repaid'."""
        lender = _create_client(db, "repay_stat_l@test.com")
        borrower = _create_client(db, "repay_stat_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        result, _ = _setup_and_borrow(db, lender, borrower, "USDC", 3000, 1000)
        borrow_id = result["borrow_position_id"]

        _set_balance(db, borrower.id, "USDC", 1100)

        from services.lending.repayment_engine import RepaymentEngine
        RepaymentEngine().repay_borrow_position(db, borrow_position_id=borrow_id)

        from services.lending.pool_models import PoolBorrowPosition
        bp = db.query(PoolBorrowPosition).filter(PoolBorrowPosition.id == borrow_id).first()
        assert bp.status == "repaid"


# ---------------------------------------------------------------------------
# E. INSUFFICIENT BALANCE
# ---------------------------------------------------------------------------

class TestInsufficientBalance:

    def test_reject_if_borrower_cannot_pay(self, db):
        lender = _create_client(db, "repay_insuf_l@test.com")
        borrower = _create_client(db, "repay_insuf_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        result, _ = _setup_and_borrow(db, lender, borrower, "USDC", 3000, 1000)
        borrow_id = result["borrow_position_id"]

        from services.lending.interest_engine import InterestEngine
        InterestEngine().run_daily_accrual(db, accrual_date=date(2027, 2, 1))

        # Borrower has 500, but owes ~1000 + interest
        _set_balance(db, borrower.id, "USDC", 500)

        from services.lending.repayment_engine import RepaymentEngine
        from services.lending.pool_service import InsufficientBalanceError
        with pytest.raises(InsufficientBalanceError):
            RepaymentEngine().repay_borrow_position(db, borrow_position_id=borrow_id)


# ---------------------------------------------------------------------------
# F. DOUBLE REPAY
# ---------------------------------------------------------------------------

class TestDoubleRepay:

    def test_cannot_repay_twice(self, db):
        lender = _create_client(db, "repay_double_l@test.com")
        borrower = _create_client(db, "repay_double_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        result, _ = _setup_and_borrow(db, lender, borrower, "USDC", 3000, 1000)
        borrow_id = result["borrow_position_id"]

        _set_balance(db, borrower.id, "USDC", 2000)

        from services.lending.repayment_engine import RepaymentEngine, RepaymentError
        engine = RepaymentEngine()
        engine.repay_borrow_position(db, borrow_position_id=borrow_id)

        with pytest.raises(RepaymentError, match="not active"):
            engine.repay_borrow_position(db, borrow_position_id=borrow_id)


# ---------------------------------------------------------------------------
# G. REPAY WITHOUT INTEREST
# ---------------------------------------------------------------------------

class TestRepayNoInterest:

    def test_repay_zero_accrued(self, db):
        """Repay immediately after borrow — 0 interest."""
        lender = _create_client(db, "repay_zero_l@test.com")
        borrower = _create_client(db, "repay_zero_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        result, _ = _setup_and_borrow(db, lender, borrower, "USDC", 3000, 1000)
        borrow_id = result["borrow_position_id"]

        # No accrual — borrower has exactly the borrowed funds
        from services.lending.repayment_engine import RepaymentEngine
        r = RepaymentEngine().repay_borrow_position(db, borrow_position_id=borrow_id)

        assert r["accrued_interest"] == 0.0
        assert r["total_paid"] == 1000.0
        assert r["platform_fee"] == 0.0


# ---------------------------------------------------------------------------
# H. POOL STATE AFTER REPAY
# ---------------------------------------------------------------------------

class TestPoolStateAfterRepay:

    def test_total_borrowed_decreases(self, db):
        lender = _create_client(db, "repay_pool_l@test.com")
        borrower = _create_client(db, "repay_pool_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        result, pool = _setup_and_borrow(db, lender, borrower, "USDC", 3000, 1000)
        borrow_id = result["borrow_position_id"]

        assert float(pool.total_borrowed) == 1000.0

        _set_balance(db, borrower.id, "USDC", 1100)

        from services.lending.repayment_engine import RepaymentEngine
        r = RepaymentEngine().repay_borrow_position(db, borrow_position_id=borrow_id)

        db.refresh(pool)
        assert float(pool.total_borrowed) == 0.0
        assert r["pool_total_borrowed_after"] == 0.0

    def test_utilization_rate_drops(self, db):
        """Pool utilization should drop after repayment."""
        lender = _create_client(db, "repay_util_l@test.com")
        borrower = _create_client(db, "repay_util_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        result, pool = _setup_and_borrow(db, lender, borrower, "USDC", 5000, 2500)
        borrow_id = result["borrow_position_id"]

        db.refresh(pool)
        util_before = float(pool.utilization_rate)
        assert util_before > 0

        _set_balance(db, borrower.id, "USDC", 3000)

        from services.lending.repayment_engine import RepaymentEngine
        RepaymentEngine().repay_borrow_position(db, borrow_position_id=borrow_id)

        db.refresh(pool)
        assert float(pool.utilization_rate) < util_before


# ---------------------------------------------------------------------------
# I. WEALTH VIEW AFTER REPAY
# ---------------------------------------------------------------------------

class TestWealthAfterRepay:

    def test_no_lending_borrowing_in_wealth_after_repay(self, db):
        """After repay, wealth view should show 0 lending/borrowing."""
        lender = _create_client(db, "repay_wealth_l@test.com")
        borrower = _create_client(db, "repay_wealth_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        result, _ = _setup_and_borrow(db, lender, borrower, "USDC", 3000, 1000)
        borrow_id = result["borrow_position_id"]

        _set_balance(db, borrower.id, "USDC", 1100)

        from services.lending.repayment_engine import RepaymentEngine
        RepaymentEngine().repay_borrow_position(db, borrow_position_id=borrow_id)

        from services.lending.valuation import compute_total_portfolio_value_v2

        lender_wealth = compute_total_portfolio_value_v2(db, lender.id)
        assert lender_wealth["lending_count"] == 0
        assert lender_wealth["lending_value_eur"] == 0.0

        borrower_wealth = compute_total_portfolio_value_v2(db, borrower.id)
        assert borrower_wealth["borrowing_count"] == 0
        assert borrower_wealth["borrowing_value_eur"] == 0.0
