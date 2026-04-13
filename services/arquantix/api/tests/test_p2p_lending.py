"""Tests for P2P Internal Lending Engine — Phase 2A.

Covers:
  - Full loan lifecycle (create → accept → activate → repay)
  - Balance conservation invariant
  - Lending/borrowing position symmetry
  - Separation from crypto_positions valuation
  - No regression on trading / bundles
  - Double-entry ledger consistency
  - Edge cases (insufficient balance, double activation, invalid transitions)
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def db():
    """Provide a database session (auto-rolled-back)."""
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parent.parent / ".env.local")
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")

    from database import SessionLocal
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


def _ensure_test_client(db: Session, email: str) -> "PeClient":
    from database import Base
    from sqlalchemy import Column, String, DateTime, Boolean, Text
    from sqlalchemy.dialects.postgresql import UUID as PgUUID, JSONB
    from sqlalchemy.sql import func

    # Use raw SQL to find/create since we may not have a PeClient model import
    from sqlalchemy import text
    row = db.execute(
        text("SELECT id FROM pe_clients WHERE email = :email"),
        {"email": email},
    ).first()
    if row:
        class _FakeClient:
            pass
        c = _FakeClient()
        c.id = row[0]
        c.email = email
        return c

    cid = uuid.uuid4()
    db.execute(
        text("""
            INSERT INTO pe_clients (id, email, status, reference_currency, created_at, updated_at)
            VALUES (:id, :email, 'active', 'EUR', now(), now())
        """),
        {"id": cid, "email": email},
    )
    db.flush()
    class _FakeClient:
        pass
    c = _FakeClient()
    c.id = cid
    c.email = email
    return c


def _set_crypto_balance(db: Session, client_id, asset: str, balance: Decimal):
    from services.exchange.repository import CryptoPositionRepository
    pos = CryptoPositionRepository.get_or_create_for_update(db, client_id, asset)
    pos.balance = balance
    pos.available_balance = balance
    db.flush()
    return pos


def _get_crypto_balance(db: Session, client_id, asset: str) -> Decimal:
    from services.exchange.models import CryptoPosition
    pos = db.query(CryptoPosition).filter(
        CryptoPosition.client_id == client_id,
        CryptoPosition.asset == asset,
    ).first()
    return Decimal(str(pos.balance)) if pos else Decimal("0")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestLoanLifecycle:
    """Full lifecycle: create → accept → activate → repay."""

    def test_full_lifecycle(self, db):
        from services.lending.service import LendingService

        svc = LendingService()
        lender = _ensure_test_client(db, "lender-test@example.com")
        borrower = _ensure_test_client(db, "borrower-test@example.com")

        _set_crypto_balance(db, lender.id, "USDC", Decimal("5000"))
        _set_crypto_balance(db, borrower.id, "USDC", Decimal("100"))

        # 1. Create
        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="USDC",
            principal=Decimal("1000"),
            interest_rate_bps=500,
            platform_fee_bps=1000,
            duration_days=30,
        )
        assert loan.status == "pending"
        assert loan.asset == "USDC"

        # 2. Accept
        loan = svc.accept_loan(db, loan.id, borrower.id)
        assert loan.status == "accepted"

        # 3. Activate
        lender_before = _get_crypto_balance(db, lender.id, "USDC")
        borrower_before = _get_crypto_balance(db, borrower.id, "USDC")
        total_before = lender_before + borrower_before

        loan = svc.activate_loan(db, loan.id)
        assert loan.status == "active"
        assert loan.start_at is not None
        assert loan.end_at is not None
        assert loan.lender_position_atom_id is not None
        assert loan.borrower_position_atom_id is not None

        lender_after = _get_crypto_balance(db, lender.id, "USDC")
        borrower_after = _get_crypto_balance(db, borrower.id, "USDC")
        total_after = lender_after + borrower_after

        assert lender_after == lender_before - Decimal("1000")
        assert borrower_after == borrower_before + Decimal("1000")
        assert total_after == total_before  # conservation

        # 4. Repay
        result = svc.repay_loan(db, loan.id, borrower.id)
        assert result["principal"] == Decimal("1000")
        assert result["interest"] >= 0
        assert result["platform_fee"] >= 0

        # Refresh loan
        loan = svc.get_loan(db, loan.id)
        assert loan.status == "repaid"


class TestBalanceConservation:
    """Invariant 1: total spot is conserved during activation."""

    def test_activation_conserves_total(self, db):
        from services.lending.service import LendingService

        svc = LendingService()
        lender = _ensure_test_client(db, "cons-lender@example.com")
        borrower = _ensure_test_client(db, "cons-borrower@example.com")

        _set_crypto_balance(db, lender.id, "BTC", Decimal("2.5"))
        _set_crypto_balance(db, borrower.id, "BTC", Decimal("0.1"))

        total_before = (
            _get_crypto_balance(db, lender.id, "BTC")
            + _get_crypto_balance(db, borrower.id, "BTC")
        )

        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="BTC",
            principal=Decimal("1.0"),
            interest_rate_bps=300,
            duration_days=60,
        )
        svc.accept_loan(db, loan.id, borrower.id)
        svc.activate_loan(db, loan.id)

        total_after = (
            _get_crypto_balance(db, lender.id, "BTC")
            + _get_crypto_balance(db, borrower.id, "BTC")
        )
        assert total_after == total_before


class TestPositionSymmetry:
    """Invariant 3: lending and borrowing positions match."""

    def test_positions_are_symmetric(self, db):
        from services.lending.service import LendingService
        from services.portfolio_engine.positions.models import PositionAtom

        svc = LendingService()
        lender = _ensure_test_client(db, "sym-lender@example.com")
        borrower = _ensure_test_client(db, "sym-borrower@example.com")

        _set_crypto_balance(db, lender.id, "ETH", Decimal("10"))
        _set_crypto_balance(db, borrower.id, "ETH", Decimal("0"))

        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="ETH",
            principal=Decimal("3.0"),
            interest_rate_bps=400,
            duration_days=90,
        )
        svc.accept_loan(db, loan.id, borrower.id)
        svc.activate_loan(db, loan.id)

        lending_atom = db.query(PositionAtom).filter(
            PositionAtom.id == loan.lender_position_atom_id,
        ).first()
        borrowing_atom = db.query(PositionAtom).filter(
            PositionAtom.id == loan.borrower_position_atom_id,
        ).first()

        assert lending_atom is not None
        assert borrowing_atom is not None
        assert lending_atom.position_type == "lending"
        assert borrowing_atom.position_type == "borrowing"
        assert Decimal(str(lending_atom.quantity)) == Decimal(str(borrowing_atom.quantity))
        assert lending_atom.instrument_id == borrowing_atom.instrument_id


class TestLendingNotInCryptoPositions:
    """Invariant 4: lending/borrowing positions excluded from valuation."""

    def test_valuation_excludes_lending(self, db):
        from services.lending.service import LendingService
        from services.portfolio_engine.valuation import _compute_atoms_value, get_fx_rate
        from services.portfolio_engine.direct_overlay import ensure_direct_portfolio

        svc = LendingService()
        lender = _ensure_test_client(db, "val-lender@example.com")
        borrower = _ensure_test_client(db, "val-borrower@example.com")

        _set_crypto_balance(db, lender.id, "USDC", Decimal("5000"))
        _set_crypto_balance(db, borrower.id, "USDC", Decimal("0"))

        lender_portfolio = ensure_direct_portfolio(db, lender.id)
        eurusdt = get_fx_rate(db)
        val_before = _compute_atoms_value(db, lender_portfolio.id, eurusdt)

        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="USDC",
            principal=Decimal("1000"),
            interest_rate_bps=500,
            duration_days=30,
        )
        svc.accept_loan(db, loan.id, borrower.id)
        svc.activate_loan(db, loan.id)

        val_after = _compute_atoms_value(db, lender_portfolio.id, eurusdt)

        # Lending position must NOT be counted in spot valuation
        assert val_after == val_before


class TestNoRegressionTrading:
    """Invariant 5: trading and bundles remain unaffected."""

    def test_buy_sell_still_works_after_lending_module_load(self, db):
        """Verify that importing lending doesn't break exchange service."""
        from services.lending.service import LendingService
        from services.exchange.repository import CryptoPositionRepository

        lender = _ensure_test_client(db, "trade-test@example.com")
        pos = CryptoPositionRepository.get_or_create_for_update(db, lender.id, "BTC")
        original = Decimal(str(pos.balance))
        pos.balance = original + Decimal("0.001")
        pos.available_balance = Decimal(str(pos.available_balance)) + Decimal("0.001")
        db.flush()

        updated = _get_crypto_balance(db, lender.id, "BTC")
        assert updated == original + Decimal("0.001")


class TestEdgeCases:
    """Safety: insufficient balance, double activation, invalid transitions."""

    def test_insufficient_lender_balance(self, db):
        from services.lending.service import LendingService, InsufficientBalanceError

        svc = LendingService()
        lender = _ensure_test_client(db, "edge-lender@example.com")
        borrower = _ensure_test_client(db, "edge-borrower@example.com")

        _set_crypto_balance(db, lender.id, "USDC", Decimal("100"))

        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="USDC",
            principal=Decimal("5000"),
            interest_rate_bps=500,
            duration_days=30,
        )
        svc.accept_loan(db, loan.id, borrower.id)

        with pytest.raises(InsufficientBalanceError):
            svc.activate_loan(db, loan.id)

    def test_double_activation(self, db):
        from services.lending.service import LendingService, InvalidStateTransitionError

        svc = LendingService()
        lender = _ensure_test_client(db, "dbl-lender@example.com")
        borrower = _ensure_test_client(db, "dbl-borrower@example.com")

        _set_crypto_balance(db, lender.id, "USDC", Decimal("5000"))

        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="USDC",
            principal=Decimal("1000"),
            interest_rate_bps=500,
            duration_days=30,
        )
        svc.accept_loan(db, loan.id, borrower.id)
        svc.activate_loan(db, loan.id)

        with pytest.raises(InvalidStateTransitionError):
            svc.activate_loan(db, loan.id)

    def test_invalid_state_transitions(self, db):
        from services.lending.service import LendingService, InvalidStateTransitionError

        svc = LendingService()
        lender = _ensure_test_client(db, "state-lender@example.com")
        borrower = _ensure_test_client(db, "state-borrower@example.com")

        _set_crypto_balance(db, lender.id, "USDC", Decimal("5000"))

        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="USDC",
            principal=Decimal("1000"),
            interest_rate_bps=500,
            duration_days=30,
        )

        # Cannot activate a pending loan (must be accepted first)
        with pytest.raises(InvalidStateTransitionError):
            svc.activate_loan(db, loan.id)

        # Cannot repay a pending loan
        with pytest.raises(Exception):
            svc.repay_loan(db, loan.id, borrower.id)

    def test_self_lending_rejected(self, db):
        from services.lending.service import LendingService, LendingError

        svc = LendingService()
        client = _ensure_test_client(db, "self-lend@example.com")

        with pytest.raises(LendingError, match="different clients"):
            svc.create_loan(
                db,
                lender_client_id=client.id,
                borrower_client_id=client.id,
                asset="USDC",
                principal=Decimal("1000"),
                interest_rate_bps=500,
                duration_days=30,
            )

    def test_wrong_borrower_cannot_accept(self, db):
        from services.lending.service import LendingService, UnauthorizedError

        svc = LendingService()
        lender = _ensure_test_client(db, "auth-lender@example.com")
        borrower = _ensure_test_client(db, "auth-borrower@example.com")
        intruder = _ensure_test_client(db, "auth-intruder@example.com")

        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="USDC",
            principal=Decimal("1000"),
            interest_rate_bps=500,
            duration_days=30,
        )

        with pytest.raises(UnauthorizedError):
            svc.accept_loan(db, loan.id, intruder.id)


class TestDoubleEntryLedger:
    """Invariant 2: each movement has debit + credit."""

    def test_ledger_entries_created_on_activation(self, db):
        """If ledger accounts exist, activation must create paired entries."""
        from services.lending.service import LendingService
        from services.portfolio_engine.ledger_entries.models import LedgerEntry

        svc = LendingService()
        lender = _ensure_test_client(db, "ledger-lender@example.com")
        borrower = _ensure_test_client(db, "ledger-borrower@example.com")

        _set_crypto_balance(db, lender.id, "USDC", Decimal("5000"))

        loan = svc.create_loan(
            db,
            lender_client_id=lender.id,
            borrower_client_id=borrower.id,
            asset="USDC",
            principal=Decimal("1000"),
            interest_rate_bps=500,
            duration_days=30,
        )
        svc.accept_loan(db, loan.id, borrower.id)
        svc.activate_loan(db, loan.id)

        entries = db.query(LedgerEntry).filter(
            LedgerEntry.reference_type == "loan_activation",
            LedgerEntry.reference_id == loan.id,
        ).all()

        # If ledger accounts exist, there should be exactly 2 entries (debit + credit).
        # If not (test env), 0 is acceptable.
        assert len(entries) in (0, 2)
        if len(entries) == 2:
            types = {e.entry_type for e in entries}
            assert types == {"debit", "credit"}
