"""Tests for Pool-based P2P Lending — Phase 2A.6bis.

Covers:
  A. Supply commitment (reservation, balance check, cancellation)
  B. Borrow from pool (FIFO allocation, atomic positions)
  C. Partial allocation (multi-lender split)
  D. Invariants (conservation, separation, traceability)
  E. Edge cases (insufficient balance, insufficient liquidity, self-borrow)
  F. Wealth view integration (spot + lending - borrowing)
  G. Non-regression (crypto_positions, trading)
"""
from __future__ import annotations

import uuid
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


def _get_available(db, client_id, asset) -> Decimal:
    from services.exchange.models import CryptoPosition
    pos = db.query(CryptoPosition).filter(
        CryptoPosition.client_id == client_id, CryptoPosition.asset == asset,
    ).first()
    return Decimal(str(pos.available_balance)) if pos else Decimal("0")


# ---------------------------------------------------------------------------
# A. SUPPLY COMMITMENT
# ---------------------------------------------------------------------------

class TestSupplyCommitment:
    """Lender commits liquidity to pool — funds reserved in spot."""

    def test_supply_creates_commitment(self, db):
        lender = _create_client(db, "pool_lender_a@test.com")
        _set_balance(db, lender.id, "USDC", 5000)

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        commitment = svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("2000"))

        assert commitment.status == "active"
        assert Decimal(str(commitment.amount)) == Decimal("2000")
        assert Decimal(str(commitment.available_amount)) == Decimal("2000")
        assert Decimal(str(commitment.reserved_amount)) == Decimal("2000")

    def test_supply_reserves_available_balance(self, db):
        lender = _create_client(db, "pool_lender_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("3000"))

        balance = _get_balance(db, lender.id, "USDC")
        available = _get_available(db, lender.id, "USDC")
        assert balance == Decimal("5000"), "Balance should remain unchanged"
        assert available == Decimal("2000"), "Available should be reduced by commitment"

    def test_supply_rejects_insufficient_balance(self, db):
        lender = _create_client(db, "pool_lender_c@test.com")
        _set_balance(db, lender.id, "USDC", 500)

        from services.lending.pool_service import PoolLendingService, InsufficientBalanceError
        svc = PoolLendingService()
        with pytest.raises(InsufficientBalanceError):
            svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("1000"))

    def test_supply_no_lending_position_created(self, db):
        """Before any borrow, no lending PositionAtom should exist."""
        lender = _create_client(db, "pool_lender_d@test.com")
        _set_balance(db, lender.id, "USDC", 3000)

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("1000"))

        from services.portfolio_engine.positions.models import PositionAtom
        from services.portfolio_engine.portfolios.models import Portfolio
        portfolios = db.query(Portfolio).filter(Portfolio.client_id == lender.id).all()
        if portfolios:
            atoms = db.query(PositionAtom).filter(
                PositionAtom.portfolio_id.in_([p.id for p in portfolios]),
                PositionAtom.position_type == "lending",
                PositionAtom.status == "open",
            ).all()
            assert len(atoms) == 0, "No lending position should exist before borrow"

    def test_cancel_commitment_releases_balance(self, db):
        lender = _create_client(db, "pool_lender_e@test.com")
        _set_balance(db, lender.id, "USDC", 5000)

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        commitment = svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("2000"))
        assert _get_available(db, lender.id, "USDC") == Decimal("3000")

        svc.cancel_supply_commitment(db, commitment.id, lender.id)
        assert _get_available(db, lender.id, "USDC") == Decimal("5000")
        assert commitment.status == "cancelled"


# ---------------------------------------------------------------------------
# B. BORROW FROM POOL
# ---------------------------------------------------------------------------

class TestBorrowFromPool:
    """Borrower takes liquidity from pool — atomic FIFO allocation."""

    def test_single_lender_full_borrow(self, db):
        """One lender, one borrower, full commitment consumed."""
        lender = _create_client(db, "pool_borrow_lender1@test.com")
        borrower = _create_client(db, "pool_borrow_borrower1@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("3000"))

        result = svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset="USDC", amount=Decimal("3000"))

        assert result["borrowed_amount"] == 3000.0
        assert result["lenders_count"] == 1

        # Lender: balance debited, available unchanged (was already reserved)
        assert _get_balance(db, lender.id, "USDC") == Decimal("2000")

        # Borrower: spot credited
        assert _get_balance(db, borrower.id, "USDC") == Decimal("3000")

    def test_borrow_creates_positions(self, db):
        """Verify lending + borrowing PositionAtoms are created."""
        lender = _create_client(db, "pool_pos_lender@test.com")
        borrower = _create_client(db, "pool_pos_borrower@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("2000"))
        result = svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset="USDC", amount=Decimal("2000"))

        from services.portfolio_engine.positions.models import PositionAtom
        from services.portfolio_engine.portfolios.models import Portfolio

        # Lending atom (lender side)
        lender_portfolios = db.query(Portfolio).filter(Portfolio.client_id == lender.id).all()
        lending_atoms = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id.in_([p.id for p in lender_portfolios]),
            PositionAtom.position_type == "lending",
            PositionAtom.status == "open",
        ).all()
        assert len(lending_atoms) >= 1
        assert Decimal(str(lending_atoms[0].quantity)) == Decimal("2000")

        # Borrowing atom (borrower side)
        borrower_portfolios = db.query(Portfolio).filter(Portfolio.client_id == borrower.id).all()
        borrowing_atoms = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id.in_([p.id for p in borrower_portfolios]),
            PositionAtom.position_type == "borrowing",
            PositionAtom.status == "open",
        ).all()
        assert len(borrowing_atoms) >= 1
        assert Decimal(str(borrowing_atoms[0].quantity)) == Decimal("2000")

    def test_borrow_updates_commitment_status(self, db):
        lender = _create_client(db, "pool_commit_status@test.com")
        borrower = _create_client(db, "pool_commit_borrower@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        commitment = svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("2000"))
        svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset="USDC", amount=Decimal("2000"))

        db.refresh(commitment)
        assert commitment.status == "fully_used"
        assert Decimal(str(commitment.available_amount)) == Decimal("0")


# ---------------------------------------------------------------------------
# C. PARTIAL ALLOCATION (MULTI-LENDER)
# ---------------------------------------------------------------------------

class TestPartialAllocation:
    """Borrow split across multiple lenders (FIFO)."""

    def test_multi_lender_fifo_allocation(self, db):
        """3 lenders, borrower takes 2500 — FIFO allocation."""
        l1 = _create_client(db, "pool_fifo_l1@test.com")
        l2 = _create_client(db, "pool_fifo_l2@test.com")
        l3 = _create_client(db, "pool_fifo_l3@test.com")
        borrower = _create_client(db, "pool_fifo_borrower@test.com")

        _set_balance(db, l1.id, "USDC", 3000)
        _set_balance(db, l2.id, "USDC", 3000)
        _set_balance(db, l3.id, "USDC", 3000)
        _set_balance(db, borrower.id, "USDC", 0)

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()

        # L1 commits 1000, L2 commits 1000, L3 commits 1000 (order matters)
        c1 = svc.create_supply_commitment(db, client_id=l1.id, asset="USDC", amount=Decimal("1000"))
        c2 = svc.create_supply_commitment(db, client_id=l2.id, asset="USDC", amount=Decimal("1000"))
        c3 = svc.create_supply_commitment(db, client_id=l3.id, asset="USDC", amount=Decimal("1000"))

        result = svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset="USDC", amount=Decimal("2500"))

        assert result["lenders_count"] == 3
        assert result["borrowed_amount"] == 2500.0

        # L1: fully used (1000)
        db.refresh(c1)
        assert c1.status == "fully_used"
        assert _get_balance(db, l1.id, "USDC") == Decimal("2000")

        # L2: fully used (1000)
        db.refresh(c2)
        assert c2.status == "fully_used"
        assert _get_balance(db, l2.id, "USDC") == Decimal("2000")

        # L3: partially used (500)
        db.refresh(c3)
        assert c3.status == "partially_used"
        assert Decimal(str(c3.available_amount)) == Decimal("500")
        assert _get_balance(db, l3.id, "USDC") == Decimal("2500")

        # Borrower: received 2500
        assert _get_balance(db, borrower.id, "USDC") == Decimal("2500")

    def test_allocation_audit_trail(self, db):
        """Verify pool_allocations table has correct records."""
        l1 = _create_client(db, "pool_audit_l1@test.com")
        l2 = _create_client(db, "pool_audit_l2@test.com")
        borrower = _create_client(db, "pool_audit_borrower@test.com")

        _set_balance(db, l1.id, "USDC", 3000)
        _set_balance(db, l2.id, "USDC", 3000)
        _set_balance(db, borrower.id, "USDC", 0)

        from services.lending.pool_service import PoolLendingService
        from services.lending.pool_models import PoolAllocation
        svc = PoolLendingService()
        c1 = svc.create_supply_commitment(db, client_id=l1.id, asset="USDC", amount=Decimal("600"))
        c2 = svc.create_supply_commitment(db, client_id=l2.id, asset="USDC", amount=Decimal("800"))

        result = svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset="USDC", amount=Decimal("1000"))

        borrow_id = result["borrow_position_id"]
        allocations = db.query(PoolAllocation).filter(
            PoolAllocation.borrow_position_id == borrow_id,
        ).order_by(PoolAllocation.created_at.asc()).all()

        assert len(allocations) == 2
        assert Decimal(str(allocations[0].amount)) == Decimal("600")  # FIFO: L1 first
        assert Decimal(str(allocations[1].amount)) == Decimal("400")  # L2 partial


# ---------------------------------------------------------------------------
# D. INVARIANTS
# ---------------------------------------------------------------------------

class TestPoolInvariants:
    """Conservation, separation, traceability."""

    def test_conservation_total_assets(self, db):
        """total_spot + lending = constant across all participants."""
        lender = _create_client(db, "pool_inv_lender@test.com")
        borrower = _create_client(db, "pool_inv_borrower@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 1000)

        total_before = _get_balance(db, lender.id, "USDC") + _get_balance(db, borrower.id, "USDC")

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("3000"))
        svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset="USDC", amount=Decimal("3000"))

        total_after = _get_balance(db, lender.id, "USDC") + _get_balance(db, borrower.id, "USDC")
        assert total_after == total_before, f"Conservation violated: {total_before} → {total_after}"

    def test_position_symmetry(self, db):
        """lending quantity == borrowing quantity for each borrow."""
        lender = _create_client(db, "pool_sym_lender@test.com")
        borrower = _create_client(db, "pool_sym_borrower@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("2000"))
        svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset="USDC", amount=Decimal("2000"))

        from services.portfolio_engine.positions.models import PositionAtom
        from services.portfolio_engine.portfolios.models import Portfolio

        all_portfolios = db.query(Portfolio).filter(
            Portfolio.client_id.in_([lender.id, borrower.id]),
        ).all()
        pids = [p.id for p in all_portfolios]

        lending_sum = sum(
            Decimal(str(a.quantity))
            for a in db.query(PositionAtom).filter(
                PositionAtom.portfolio_id.in_(pids),
                PositionAtom.position_type == "lending",
                PositionAtom.status == "open",
            ).all()
        )
        borrowing_sum = sum(
            Decimal(str(a.quantity))
            for a in db.query(PositionAtom).filter(
                PositionAtom.portfolio_id.in_(pids),
                PositionAtom.position_type == "borrowing",
                PositionAtom.status == "open",
            ).all()
        )
        assert lending_sum == borrowing_sum, f"Symmetry broken: lending={lending_sum}, borrowing={borrowing_sum}"

    def test_pool_stats_accuracy(self, db):
        """Pool total_committed and total_borrowed are correct."""
        lender = _create_client(db, "pool_stats_lender@test.com")
        borrower = _create_client(db, "pool_stats_borrower@test.com")
        _set_balance(db, lender.id, "USDC", 10000)
        _set_balance(db, borrower.id, "USDC", 0)

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("5000"))
        svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset="USDC", amount=Decimal("2000"))

        summary = svc.get_pool_summary(db, "USDC")
        assert summary["exists"] is True
        assert summary["total_borrowed"] == 2000.0
        # Utilization = 2000 / 5000 * 100 = 40%
        assert summary["utilization_rate"] == 40.0


# ---------------------------------------------------------------------------
# E. EDGE CASES
# ---------------------------------------------------------------------------

class TestPoolEdgeCases:
    """Rejection, safety, self-borrow guard."""

    def test_borrow_exceeds_liquidity(self, db):
        lender = _create_client(db, "pool_edge_lender1@test.com")
        borrower = _create_client(db, "pool_edge_borrower1@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        from services.lending.pool_service import PoolLendingService, InsufficientPoolLiquidityError
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("1000"))

        with pytest.raises(InsufficientPoolLiquidityError):
            svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset="USDC", amount=Decimal("2000"))

    def test_self_borrow_excluded(self, db):
        """A lender cannot borrow from their own commitment."""
        user = _create_client(db, "pool_self_borrow@test.com")
        _set_balance(db, user.id, "USDC", 5000)

        from services.lending.pool_service import PoolLendingService, InsufficientPoolLiquidityError
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=user.id, asset="USDC", amount=Decimal("3000"))

        with pytest.raises(InsufficientPoolLiquidityError):
            svc.borrow_from_pool(db, borrower_client_id=user.id, asset="USDC", amount=Decimal("1000"))

    def test_cancel_used_commitment_rejected(self, db):
        """Cannot cancel a fully_used commitment."""
        lender = _create_client(db, "pool_cancel_used_l@test.com")
        borrower = _create_client(db, "pool_cancel_used_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        from services.lending.pool_service import PoolLendingService, PoolError
        svc = PoolLendingService()
        commitment = svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("1000"))
        svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset="USDC", amount=Decimal("1000"))

        with pytest.raises(PoolError, match="Cannot cancel"):
            svc.cancel_supply_commitment(db, commitment.id, lender.id)

    def test_multiple_borrows_deplete_pool(self, db):
        """Sequential borrows deplete pool correctly."""
        lender = _create_client(db, "pool_deplete_lender@test.com")
        b1 = _create_client(db, "pool_deplete_b1@test.com")
        b2 = _create_client(db, "pool_deplete_b2@test.com")
        _set_balance(db, lender.id, "USDC", 10000)
        _set_balance(db, b1.id, "USDC", 0)
        _set_balance(db, b2.id, "USDC", 0)

        from services.lending.pool_service import PoolLendingService, InsufficientPoolLiquidityError
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("5000"))

        svc.borrow_from_pool(db, borrower_client_id=b1.id, asset="USDC", amount=Decimal("3000"))
        svc.borrow_from_pool(db, borrower_client_id=b2.id, asset="USDC", amount=Decimal("2000"))

        with pytest.raises(InsufficientPoolLiquidityError):
            svc.borrow_from_pool(db, borrower_client_id=b2.id, asset="USDC", amount=Decimal("1"))


# ---------------------------------------------------------------------------
# F. WEALTH VIEW INTEGRATION
# ---------------------------------------------------------------------------

class TestPoolWealthIntegration:
    """Pool positions integrate with wealth view (Phase 2A.5)."""

    def test_lender_wealth_after_borrow(self, db):
        """Lender: spot decreases, lending appears in wealth."""
        lender = _create_client(db, "pool_wealth_lender@test.com")
        borrower = _create_client(db, "pool_wealth_borrower@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("3000"))
        svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset="USDC", amount=Decimal("3000"))

        from services.lending.valuation import compute_total_portfolio_value_v2
        wealth = compute_total_portfolio_value_v2(db, lender.id)

        assert wealth["lending_count"] >= 1, "Lender should have lending positions"
        assert wealth["lending_value_eur"] > 0, "Lending value should be positive"

    def test_borrower_wealth_after_borrow(self, db):
        """Borrower: spot increases, borrowing (negative) appears in wealth."""
        lender = _create_client(db, "pool_wealthb_lender@test.com")
        borrower = _create_client(db, "pool_wealthb_borrower@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("2000"))
        svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset="USDC", amount=Decimal("2000"))

        from services.lending.valuation import compute_total_portfolio_value_v2
        wealth = compute_total_portfolio_value_v2(db, borrower.id)

        assert wealth["borrowing_count"] >= 1, "Borrower should have borrowing positions"
        assert wealth["borrowing_value_eur"] > 0, "Borrowing value (absolute) should be positive"
        assert wealth["spot_value_eur"] > 0, "Borrower should have spot from borrow"

    def test_no_borrow_no_positions(self, db):
        """Supply commitment alone = no lending/borrowing positions in wealth."""
        lender = _create_client(db, "pool_nopos_lender@test.com")
        _set_balance(db, lender.id, "USDC", 5000)

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("2000"))

        from services.lending.valuation import compute_total_portfolio_value_v2
        wealth = compute_total_portfolio_value_v2(db, lender.id)

        assert wealth["lending_count"] == 0, "No lending without a borrow"
        assert wealth["borrowing_count"] == 0


# ---------------------------------------------------------------------------
# G. NON-REGRESSION
# ---------------------------------------------------------------------------

class TestPoolNonRegression:
    """Verify crypto_positions and spot valuation are not broken."""

    def test_crypto_positions_unchanged_by_commitment(self, db):
        """Supply commitment should NOT create/modify crypto_positions beyond available_balance."""
        lender = _create_client(db, "pool_noreg_lender@test.com")
        _set_balance(db, lender.id, "BTC", 2)

        from services.exchange.models import CryptoPosition
        count_before = db.query(CryptoPosition).filter(
            CryptoPosition.client_id == lender.id, CryptoPosition.asset == "BTC",
        ).count()

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="BTC", amount=Decimal("1"))

        count_after = db.query(CryptoPosition).filter(
            CryptoPosition.client_id == lender.id, CryptoPosition.asset == "BTC",
        ).count()
        assert count_after == count_before, "No new crypto_positions should be created"

        balance = _get_balance(db, lender.id, "BTC")
        assert balance == Decimal("2"), "Balance should be unchanged (only available_balance reduced)"

    def test_multi_asset_pools(self, db):
        """Each asset has its own pool — no cross-contamination."""
        lender = _create_client(db, "pool_multi_lender@test.com")
        borrower = _create_client(db, "pool_multi_borrower@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, lender.id, "BTC", 2)
        _set_balance(db, borrower.id, "USDC", 0)
        _set_balance(db, borrower.id, "BTC", 0)

        from services.lending.pool_service import PoolLendingService
        svc = PoolLendingService()
        svc.create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("1000"))
        svc.create_supply_commitment(db, client_id=lender.id, asset="BTC", amount=Decimal("0.5"))

        svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset="USDC", amount=Decimal("1000"))
        svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset="BTC", amount=Decimal("0.5"))

        assert _get_balance(db, borrower.id, "USDC") == Decimal("1000")
        assert _get_balance(db, borrower.id, "BTC") == Decimal("0.5")

        usdc_summary = svc.get_pool_summary(db, "USDC")
        btc_summary = svc.get_pool_summary(db, "BTC")
        assert usdc_summary["total_borrowed"] == 1000.0
        assert btc_summary["total_borrowed"] == 0.5
