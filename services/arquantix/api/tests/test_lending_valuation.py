"""Tests for Lending Valuation Layer — Phase 2A.5.

Covers:
  A. Lending valuation = spot_price × quantity
  B. Borrowing valuation = negative
  C. Net portfolio value = spot + lending - borrowing
  D. No regression on spot valuation
  E. Separation: lending NOT in crypto_positions
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


def _ensure_client(db: Session, email: str):
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


def _create_and_activate_loan(db, lender, borrower, asset, principal):
    """Helper: full loan creation + activation."""
    from services.lending.service import LendingService
    svc = LendingService()
    loan = svc.create_loan(
        db,
        lender_client_id=lender.id,
        borrower_client_id=borrower.id,
        asset=asset,
        principal=Decimal(str(principal)),
        interest_rate_bps=500,
        duration_days=30,
    )
    svc.accept_loan(db, loan.id, borrower.id)
    svc.activate_loan(db, loan.id)
    return svc.get_loan(db, loan.id)


# ---------------------------------------------------------------------------
# A. Lending valuation = spot_price × quantity
# ---------------------------------------------------------------------------

class TestLendingValuation:

    def test_lending_position_has_positive_value(self, db):
        from services.lending.valuation import compute_position_market_value
        from services.portfolio_engine.positions.models import PositionAtom

        lender = _ensure_client(db, "val-a-lender@test.com")
        borrower = _ensure_client(db, "val-a-borrower@test.com")
        _set_balance(db, lender.id, "USDC", 5000)

        loan = _create_and_activate_loan(db, lender, borrower, "USDC", 1000)

        atom = db.query(PositionAtom).filter(
            PositionAtom.id == loan.lender_position_atom_id,
        ).first()
        assert atom is not None
        assert atom.position_type == "lending"

        val = compute_position_market_value(db, atom)
        assert val["market_value_eur"] > 0
        assert val["position_type"] == "lending"
        assert val["asset"] == "USDC"
        assert val["quantity"] == 1000.0

    def test_lending_uses_same_price_as_spot(self, db):
        """Invariant 2: lending price == spot price for the same asset."""
        from services.lending.valuation import compute_position_market_value
        from services.portfolio_engine.valuation import get_asset_price_eur
        from services.portfolio_engine.positions.models import PositionAtom

        lender = _ensure_client(db, "val-price-lender@test.com")
        borrower = _ensure_client(db, "val-price-borrower@test.com")
        _set_balance(db, lender.id, "BTC", Decimal("2.0"))

        loan = _create_and_activate_loan(db, lender, borrower, "BTC", Decimal("1.0"))

        atom = db.query(PositionAtom).filter(
            PositionAtom.id == loan.lender_position_atom_id,
        ).first()

        val = compute_position_market_value(db, atom)
        spot_price_eur = get_asset_price_eur(db, "BTC")

        if spot_price_eur and spot_price_eur > 0:
            expected = float(spot_price_eur.quantize(Decimal("0.01")))
            assert abs(val["price_eur"] - expected) < 0.02, \
                f"Lending price {val['price_eur']} != spot price {expected}"


# ---------------------------------------------------------------------------
# B. Borrowing valuation = negative
# ---------------------------------------------------------------------------

class TestBorrowingNegativeValue:

    def test_borrowing_position_is_negative(self, db):
        from services.lending.valuation import compute_position_market_value
        from services.portfolio_engine.positions.models import PositionAtom

        lender = _ensure_client(db, "neg-lender@test.com")
        borrower = _ensure_client(db, "neg-borrower@test.com")
        _set_balance(db, lender.id, "USDC", 5000)

        loan = _create_and_activate_loan(db, lender, borrower, "USDC", 2000)

        atom = db.query(PositionAtom).filter(
            PositionAtom.id == loan.borrower_position_atom_id,
        ).first()
        assert atom is not None
        assert atom.position_type == "borrowing"

        val = compute_position_market_value(db, atom)
        assert val["market_value_eur"] < 0, \
            f"Borrowing value should be negative, got {val['market_value_eur']}"
        assert val["position_type"] == "borrowing"

    def test_borrowing_absolute_equals_lending(self, db):
        """Lending value and borrowing value should have same absolute."""
        from services.lending.valuation import compute_position_market_value
        from services.portfolio_engine.positions.models import PositionAtom

        lender = _ensure_client(db, "abs-lender@test.com")
        borrower = _ensure_client(db, "abs-borrower@test.com")
        _set_balance(db, lender.id, "ETH", Decimal("10"))

        loan = _create_and_activate_loan(db, lender, borrower, "ETH", Decimal("3.0"))

        lending_atom = db.query(PositionAtom).filter(PositionAtom.id == loan.lender_position_atom_id).first()
        borrowing_atom = db.query(PositionAtom).filter(PositionAtom.id == loan.borrower_position_atom_id).first()

        l_val = compute_position_market_value(db, lending_atom)
        b_val = compute_position_market_value(db, borrowing_atom)

        assert abs(l_val["market_value_eur"] + b_val["market_value_eur"]) < 0.02, \
            f"lending({l_val['market_value_eur']}) + borrowing({b_val['market_value_eur']}) should ≈ 0"


# ---------------------------------------------------------------------------
# C. Net portfolio value = spot + lending - borrowing
# ---------------------------------------------------------------------------

class TestPortfolioNetValue:

    def test_net_value_formula(self, db):
        from services.lending.valuation import compute_total_portfolio_value_v2

        lender = _ensure_client(db, "net-lender@test.com")
        borrower = _ensure_client(db, "net-borrower@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 100)

        _create_and_activate_loan(db, lender, borrower, "USDC", 1000)

        lender_wealth = compute_total_portfolio_value_v2(db, lender.id)
        borrower_wealth = compute_total_portfolio_value_v2(db, borrower.id)

        # Lender: spot decreased by 1000, gained lending position of 1000
        assert lender_wealth["lending_value_eur"] > 0
        assert lender_wealth["lending_count"] == 1

        # Borrower: spot increased by 1000, gained borrowing obligation of 1000
        assert borrower_wealth["borrowing_value_eur"] > 0
        assert borrower_wealth["borrowing_count"] == 1

        # Net value formula: spot + lending - borrowing
        for w in [lender_wealth, borrower_wealth]:
            expected_net = w["spot_value_eur"] + w["lending_value_eur"] - w["borrowing_value_eur"]
            assert abs(w["net_value_eur"] - expected_net) < 0.02, \
                f"net({w['net_value_eur']}) != spot({w['spot_value_eur']}) + lending({w['lending_value_eur']}) - borrowing({w['borrowing_value_eur']})"

    def test_wealth_with_no_lending(self, db):
        """Client without loans should have lending=0, borrowing=0."""
        from services.lending.valuation import compute_total_portfolio_value_v2

        client = _ensure_client(db, "no-loan@test.com")
        _set_balance(db, client.id, "USDC", 1000)

        wealth = compute_total_portfolio_value_v2(db, client.id)
        assert wealth["lending_value_eur"] == 0.0
        assert wealth["borrowing_value_eur"] == 0.0
        assert wealth["lending_count"] == 0
        assert wealth["borrowing_count"] == 0


# ---------------------------------------------------------------------------
# D. No regression on spot valuation
# ---------------------------------------------------------------------------

class TestNoRegressionSpot:

    def test_existing_valuation_unchanged(self, db):
        """_compute_atoms_value must not change after lending module is loaded."""
        from services.lending.valuation import compute_total_portfolio_value_v2
        from services.portfolio_engine.valuation import _compute_atoms_value, get_fx_rate
        from services.portfolio_engine.direct_overlay import ensure_direct_portfolio

        lender = _ensure_client(db, "reg-lender@test.com")
        borrower = _ensure_client(db, "reg-borrower@test.com")
        _set_balance(db, lender.id, "USDC", 5000)

        portfolio = ensure_direct_portfolio(db, lender.id)
        eurusdt = get_fx_rate(db)
        spot_val_before = _compute_atoms_value(db, portfolio.id, eurusdt)

        _create_and_activate_loan(db, lender, borrower, "USDC", 1000)

        spot_val_after = _compute_atoms_value(db, portfolio.id, eurusdt)

        # _compute_atoms_value only counts spot — must not change due to lending atoms
        assert spot_val_after == spot_val_before, \
            f"Spot valuation changed! before={spot_val_before}, after={spot_val_after}"

    def test_crypto_positions_untouched(self, db):
        """crypto_positions table should reflect actual spot balances, not lending."""
        from services.exchange.models import CryptoPosition

        lender = _ensure_client(db, "crpos-lender@test.com")
        borrower = _ensure_client(db, "crpos-borrower@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 100)

        _create_and_activate_loan(db, lender, borrower, "USDC", 1000)

        lender_pos = db.query(CryptoPosition).filter(
            CryptoPosition.client_id == lender.id, CryptoPosition.asset == "USDC",
        ).first()
        borrower_pos = db.query(CryptoPosition).filter(
            CryptoPosition.client_id == borrower.id, CryptoPosition.asset == "USDC",
        ).first()

        # Lender: 5000 - 1000 = 4000
        assert Decimal(str(lender_pos.balance)) == Decimal("4000")
        # Borrower: 100 + 1000 = 1100
        assert Decimal(str(borrower_pos.balance)) == Decimal("1100")

    def test_get_lending_positions_only(self, db):
        """get_lending_positions should return ONLY lending, not spot."""
        from services.lending.valuation import get_lending_positions

        lender = _ensure_client(db, "only-lender@test.com")
        borrower = _ensure_client(db, "only-borrower@test.com")
        _set_balance(db, lender.id, "USDC", 5000)

        _create_and_activate_loan(db, lender, borrower, "USDC", 1000)

        positions = get_lending_positions(db, lender.id)
        assert len(positions) == 1
        assert all(p["position_type"] == "lending" for p in positions)

        borrower_positions = get_lending_positions(db, borrower.id)
        assert len(borrower_positions) == 0
