"""End-to-End tests for P2P Lending Product Surface — Phase 2A.6.

Validates the full product flow between 2 clients:
  1. Lender creates an offer
  2. Borrower accepts
  3. System activates (atomic)
  4. Funds move internally
  5. Positions appear
  6. Wealth view is correct

Also validates rejection, insufficient balance, and double activation.
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


# ---------------------------------------------------------------------------
# E2E PRINCIPAL — Full flow lender → borrower → activate → verify
# ---------------------------------------------------------------------------

class TestE2EFullFlow:
    """
    Given: user A has 1000 USDC, user B has 0 USDC
    When:  A lends 1000 USDC to B
    Then:
      Balances: A spot = 0, B spot = 1000
      Positions: A → lending 1000, B → borrowing 1000
      Wealth: A net = 1000 (0 spot + 1000 lending), B net = 0 (1000 spot - 1000 borrowing)
    """

    def test_full_e2e_flow(self, db):
        from services.lending.service import LendingService
        from services.lending.valuation import (
            compute_total_portfolio_value_v2,
            get_lending_positions,
            get_borrowing_positions,
        )
        from services.portfolio_engine.positions.models import PositionAtom

        svc = LendingService()

        # ── Setup ──
        lender = _create_client(db, "e2e-lender@test.com")
        borrower = _create_client(db, "e2e-borrower@test.com")
        _set_balance(db, lender.id, "USDC", Decimal("1000"))
        _set_balance(db, borrower.id, "USDC", Decimal("0"))

        # ── Step 1: Create offer ──
        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="USDC",
            principal=Decimal("1000"),
            interest_rate_bps=0,
            duration_days=30,
        )
        assert loan.status == "pending"

        # Balances unchanged after creation
        assert _get_balance(db, lender.id, "USDC") == Decimal("1000")
        assert _get_balance(db, borrower.id, "USDC") == Decimal("0")

        # ── Step 2: Borrower accepts ──
        loan = svc.accept_loan(db, loan.id, borrower.id)
        assert loan.status == "accepted"

        # Balances still unchanged
        assert _get_balance(db, lender.id, "USDC") == Decimal("1000")
        assert _get_balance(db, borrower.id, "USDC") == Decimal("0")

        # ── Step 3: Activate (atomic) ──
        loan = svc.activate_loan(db, loan.id)
        assert loan.status == "active"
        assert loan.start_at is not None
        assert loan.lender_position_atom_id is not None
        assert loan.borrower_position_atom_id is not None

        # ── Verify balances ──
        assert _get_balance(db, lender.id, "USDC") == Decimal("0"), "Lender spot should be 0"
        assert _get_balance(db, borrower.id, "USDC") == Decimal("1000"), "Borrower spot should be 1000"

        # ── Verify balance conservation ──
        total_spot = _get_balance(db, lender.id, "USDC") + _get_balance(db, borrower.id, "USDC")
        assert total_spot == Decimal("1000"), f"Total spot should be conserved: {total_spot}"

        # ── Verify positions ──
        lending_atom = db.query(PositionAtom).filter(
            PositionAtom.id == loan.lender_position_atom_id,
        ).first()
        borrowing_atom = db.query(PositionAtom).filter(
            PositionAtom.id == loan.borrower_position_atom_id,
        ).first()

        assert lending_atom.position_type == "lending"
        assert Decimal(str(lending_atom.quantity)) == Decimal("1000")
        assert lending_atom.status == "open"

        assert borrowing_atom.position_type == "borrowing"
        assert Decimal(str(borrowing_atom.quantity)) == Decimal("1000")
        assert borrowing_atom.status == "open"

        # ── Verify symmetry ──
        assert Decimal(str(lending_atom.quantity)) == Decimal(str(borrowing_atom.quantity))
        assert lending_atom.instrument_id == borrowing_atom.instrument_id

        # ── Verify lending positions API ──
        lender_lending = get_lending_positions(db, lender.id)
        assert len(lender_lending) == 1
        assert lender_lending[0]["asset"] == "USDC"
        assert lender_lending[0]["market_value_eur"] > 0

        borrower_borrowing = get_borrowing_positions(db, borrower.id)
        assert len(borrower_borrowing) == 1
        assert borrower_borrowing[0]["market_value_eur"] < 0

        # ── Verify wealth view ──
        lender_wealth = compute_total_portfolio_value_v2(db, lender.id)
        borrower_wealth = compute_total_portfolio_value_v2(db, borrower.id)

        # Lender: 0 spot + lending value ≈ net
        assert lender_wealth["lending_count"] == 1
        assert lender_wealth["lending_value_eur"] > 0
        assert lender_wealth["net_value_eur"] > 0, "Lender net should be positive (has lending claim)"

        # Borrower: spot + (-borrowing) ≈ 0 net
        assert borrower_wealth["borrowing_count"] == 1
        assert borrower_wealth["borrowing_value_eur"] > 0
        # net ≈ spot(1000 USDC value) - borrowing(1000 USDC value) ≈ 0
        assert abs(borrower_wealth["net_value_eur"]) < 5.0, \
            f"Borrower net should be ≈ 0 (got {borrower_wealth['net_value_eur']})"

    def test_role_based_listing(self, db):
        """Verify ?role=lender and ?role=borrower filtering."""
        from services.lending.service import LendingService

        svc = LendingService()
        lender = _create_client(db, "role-lender@test.com")
        borrower = _create_client(db, "role-borrower@test.com")
        _set_balance(db, lender.id, "USDC", Decimal("5000"))

        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="USDC",
            principal=Decimal("1000"),
            interest_rate_bps=0,
            duration_days=30,
        )
        svc.accept_loan(db, loan.id, borrower.id)
        svc.activate_loan(db, loan.id)

        # Lender role
        lender_loans, _ = svc.list_loans_by_role(db, client_id=lender.id, role="lender")
        assert len(lender_loans) >= 1
        assert all(l.lender_client_id == lender.id for l in lender_loans)

        # Borrower role
        borrower_loans, _ = svc.list_loans_by_role(db, client_id=borrower.id, role="borrower")
        assert len(borrower_loans) >= 1
        assert all(l.borrower_client_id == borrower.id for l in borrower_loans)

        # Cross-check: lender should NOT appear as borrower for this loan
        lender_as_borrower, _ = svc.list_loans_by_role(
            db, client_id=lender.id, role="borrower",
        )
        assert not any(l.id == loan.id for l in lender_as_borrower)

    def test_lending_summary(self, db):
        """Verify the dashboard summary endpoint."""
        from services.lending.service import LendingService

        svc = LendingService()
        lender = _create_client(db, "sum-lender@test.com")
        borrower = _create_client(db, "sum-borrower@test.com")
        _set_balance(db, lender.id, "USDC", Decimal("5000"))

        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="USDC",
            principal=Decimal("1000"),
            interest_rate_bps=0,
            duration_days=30,
        )
        svc.accept_loan(db, loan.id, borrower.id)
        svc.activate_loan(db, loan.id)

        # Lender summary
        lender_summary = svc.get_client_summary(db, lender.id)
        assert lender_summary["total_lent_count"] == 1
        assert lender_summary["total_borrowed_count"] == 0
        assert lender_summary["total_lent_value_eur"] > 0
        assert len(lender_summary["active_loans_as_lender"]) == 1
        assert lender_summary["active_loans_as_lender"][0]["role"] == "lender"

        # Borrower summary
        borrower_summary = svc.get_client_summary(db, borrower.id)
        assert borrower_summary["total_lent_count"] == 0
        assert borrower_summary["total_borrowed_count"] == 1
        assert borrower_summary["total_borrowed_value_eur"] > 0
        assert len(borrower_summary["active_loans_as_borrower"]) == 1


# ---------------------------------------------------------------------------
# E2E — Rejection case
# ---------------------------------------------------------------------------

class TestE2ERejection:

    def test_rejection_changes_nothing(self, db):
        """When borrower rejects, all balances and positions remain unchanged."""
        from services.lending.service import LendingService
        from services.lending.valuation import get_lending_positions

        svc = LendingService()
        lender = _create_client(db, "rej-lender@test.com")
        borrower = _create_client(db, "rej-borrower@test.com")
        _set_balance(db, lender.id, "USDC", Decimal("1000"))
        _set_balance(db, borrower.id, "USDC", Decimal("0"))

        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="USDC",
            principal=Decimal("1000"),
            interest_rate_bps=0,
            duration_days=30,
        )

        # Reject
        loan = svc.reject_loan(db, loan.id, borrower.id)
        assert loan.status == "rejected"

        # Nothing moved
        assert _get_balance(db, lender.id, "USDC") == Decimal("1000")
        assert _get_balance(db, borrower.id, "USDC") == Decimal("0")

        # No positions created
        assert get_lending_positions(db, lender.id) == []
        assert get_lending_positions(db, borrower.id) == []


# ---------------------------------------------------------------------------
# E2E — Double activation
# ---------------------------------------------------------------------------

class TestE2EDoubleActivation:

    def test_double_activation_blocked(self, db):
        from services.lending.service import LendingService, InvalidStateTransitionError

        svc = LendingService()
        lender = _create_client(db, "dbl2-lender@test.com")
        borrower = _create_client(db, "dbl2-borrower@test.com")
        _set_balance(db, lender.id, "USDC", Decimal("5000"))

        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="USDC",
            principal=Decimal("1000"),
            interest_rate_bps=0,
            duration_days=30,
        )
        svc.accept_loan(db, loan.id, borrower.id)
        svc.activate_loan(db, loan.id)

        # Second activation must fail
        with pytest.raises(InvalidStateTransitionError):
            svc.activate_loan(db, loan.id)

        # Balances should still be correct (single transfer only)
        assert _get_balance(db, lender.id, "USDC") == Decimal("4000")
        assert _get_balance(db, borrower.id, "USDC") == Decimal("1000")


# ---------------------------------------------------------------------------
# E2E — Insufficient balance
# ---------------------------------------------------------------------------

class TestE2EInsufficientBalance:

    def test_activation_rejected_if_insufficient(self, db):
        from services.lending.service import LendingService, InsufficientBalanceError

        svc = LendingService()
        lender = _create_client(db, "insuf-lender@test.com")
        borrower = _create_client(db, "insuf-borrower@test.com")
        _set_balance(db, lender.id, "USDC", Decimal("100"))

        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="USDC",
            principal=Decimal("5000"),
            interest_rate_bps=0,
            duration_days=30,
        )
        svc.accept_loan(db, loan.id, borrower.id)

        with pytest.raises(InsufficientBalanceError):
            svc.activate_loan(db, loan.id)

        # Nothing moved
        assert _get_balance(db, lender.id, "USDC") == Decimal("100")


# ---------------------------------------------------------------------------
# E2E — Multi-asset lending
# ---------------------------------------------------------------------------

class TestE2EMultiAsset:

    def test_lend_btc_and_usdc(self, db):
        """Verify lending works across multiple assets simultaneously."""
        from services.lending.service import LendingService
        from services.lending.valuation import compute_total_portfolio_value_v2

        svc = LendingService()
        lender = _create_client(db, "multi-lender@test.com")
        borrower = _create_client(db, "multi-borrower@test.com")
        _set_balance(db, lender.id, "USDC", Decimal("5000"))
        _set_balance(db, lender.id, "BTC", Decimal("1.0"))

        # Loan 1: USDC
        loan1 = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="USDC",
            principal=Decimal("1000"),
            interest_rate_bps=0,
            duration_days=30,
        )
        svc.accept_loan(db, loan1.id, borrower.id)
        svc.activate_loan(db, loan1.id)

        # Loan 2: BTC
        loan2 = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="BTC",
            principal=Decimal("0.5"),
            interest_rate_bps=0,
            duration_days=30,
        )
        svc.accept_loan(db, loan2.id, borrower.id)
        svc.activate_loan(db, loan2.id)

        # Verify balances
        assert _get_balance(db, lender.id, "USDC") == Decimal("4000")
        assert _get_balance(db, lender.id, "BTC") == Decimal("0.5")

        # Wealth view should show 2 lending positions
        wealth = compute_total_portfolio_value_v2(db, lender.id)
        assert wealth["lending_count"] == 2


# ---------------------------------------------------------------------------
# E2E — Cancellation by lender
# ---------------------------------------------------------------------------

class TestE2ECancellation:

    def test_lender_can_cancel_before_activation(self, db):
        from services.lending.service import LendingService

        svc = LendingService()
        lender = _create_client(db, "cancel-lender@test.com")
        borrower = _create_client(db, "cancel-borrower@test.com")
        _set_balance(db, lender.id, "USDC", Decimal("1000"))

        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="USDC",
            principal=Decimal("1000"),
            interest_rate_bps=0,
            duration_days=30,
        )

        # Cancel before accept
        loan = svc.cancel_loan(db, loan.id, lender.id)
        assert loan.status == "cancelled"

        # Balance unchanged
        assert _get_balance(db, lender.id, "USDC") == Decimal("1000")

    def test_lender_can_cancel_accepted_loan(self, db):
        from services.lending.service import LendingService

        svc = LendingService()
        lender = _create_client(db, "cancacc-lender@test.com")
        borrower = _create_client(db, "cancacc-borrower@test.com")
        _set_balance(db, lender.id, "USDC", Decimal("1000"))

        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="USDC",
            principal=Decimal("1000"),
            interest_rate_bps=0,
            duration_days=30,
        )
        svc.accept_loan(db, loan.id, borrower.id)

        # Cancel after accept, before activation
        loan = svc.cancel_loan(db, loan.id, lender.id)
        assert loan.status == "cancelled"
        assert _get_balance(db, lender.id, "USDC") == Decimal("1000")
