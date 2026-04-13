"""Tests for Exclusive Offer Lending Products — Phase 2A.10.

Covers:
  A. Product creation (model, lifecycle)
  B. Subscription (min/max ticket, cap, borrower exclusion)
  C. Activation (auto borrow, positions, balances)
  D. Borrower restriction (external borrow rejected)
  E. Full E2E cycle (create → subscribe → activate → accrue → repay)
  F. Edge cases (overfund, double activate, wrong status transitions)
  G. Listing and user positions
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session
from sqlalchemy import text


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


# ---------------------------------------------------------------------------
# A. PRODUCT CREATION
# ---------------------------------------------------------------------------

class TestProductCreation:

    def test_create_product(self, db):
        borrower = _create_client(db, "offer_borrower@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db,
            title="Solar Project UAE",
            asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("100000"),
            supply_apr_bps=Decimal("800"),
            borrow_apr_bps=Decimal("1000"),
            min_ticket=Decimal("1000"),
            max_ticket=Decimal("50000"),
            description="Solar energy project in UAE",
            use_of_funds="Equipment purchase",
        )

        assert product.status == "draft"
        assert product.title == "Solar Project UAE"
        assert product.asset == "USDC"
        assert product.borrower_client_id == borrower.id
        assert float(product.target_size) == 100000.0

    def test_create_product_with_dedicated_pool(self, db):
        borrower = _create_client(db, "offer_pool@test.com")
        from services.lending.offer_service import OfferService
        from services.lending.pool_models import LendingPool
        svc = OfferService()

        product = svc.create_product(
            db,
            title="Test Offer Pool",
            asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("50000"),
        )

        pool = db.query(LendingPool).filter(LendingPool.id == product.lending_pool_id).first()
        assert pool is not None
        assert pool.asset == "USDC"

    def test_open_fundraising(self, db):
        borrower = _create_client(db, "offer_fund@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db, title="Test", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("10000"),
        )
        assert product.status == "draft"

        product = svc.open_fundraising(db, product.id)
        assert product.status == "fundraising"

    def test_cannot_open_fundraising_twice(self, db):
        borrower = _create_client(db, "offer_fundtwice@test.com")
        from services.lending.offer_service import OfferService, InvalidOfferStatusError
        svc = OfferService()

        product = svc.create_product(
            db, title="Test", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("10000"),
        )
        svc.open_fundraising(db, product.id)

        with pytest.raises(InvalidOfferStatusError):
            svc.open_fundraising(db, product.id)


# ---------------------------------------------------------------------------
# B. SUBSCRIPTION
# ---------------------------------------------------------------------------

class TestSubscription:

    def test_subscribe_success(self, db):
        borrower = _create_client(db, "offer_sub_bor@test.com")
        lender = _create_client(db, "offer_sub_len@test.com")
        _set_balance(db, lender.id, "USDC", 50000)

        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db, title="Sub Test", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("10000"),
        )
        svc.open_fundraising(db, product.id)

        commitment = svc.subscribe(
            db, product_id=product.id,
            lender_client_id=lender.id,
            amount=Decimal("5000"),
        )

        assert commitment is not None
        assert float(commitment.amount) == 5000.0

        # current_raised updated
        detail = svc.get_product_detail(db, product.id)
        assert detail["current_raised"] == 5000.0

    def test_subscribe_min_ticket_violation(self, db):
        borrower = _create_client(db, "offer_minsub_b@test.com")
        lender = _create_client(db, "offer_minsub_l@test.com")
        _set_balance(db, lender.id, "USDC", 50000)

        from services.lending.offer_service import OfferService, SubscriptionError
        svc = OfferService()

        product = svc.create_product(
            db, title="Min Ticket Test", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("100000"),
            min_ticket=Decimal("5000"),
        )
        svc.open_fundraising(db, product.id)

        with pytest.raises(SubscriptionError, match="below minimum ticket"):
            svc.subscribe(db, product_id=product.id, lender_client_id=lender.id, amount=Decimal("1000"))

    def test_subscribe_max_ticket_violation(self, db):
        borrower = _create_client(db, "offer_maxsub_b@test.com")
        lender = _create_client(db, "offer_maxsub_l@test.com")
        _set_balance(db, lender.id, "USDC", 100000)

        from services.lending.offer_service import OfferService, SubscriptionError
        svc = OfferService()

        product = svc.create_product(
            db, title="Max Ticket Test", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("100000"),
            max_ticket=Decimal("10000"),
        )
        svc.open_fundraising(db, product.id)

        with pytest.raises(SubscriptionError, match="exceeds maximum ticket"):
            svc.subscribe(db, product_id=product.id, lender_client_id=lender.id, amount=Decimal("20000"))

    def test_subscribe_cap_exceeded(self, db):
        borrower = _create_client(db, "offer_cap_b@test.com")
        lender = _create_client(db, "offer_cap_l@test.com")
        _set_balance(db, lender.id, "USDC", 50000)

        from services.lending.offer_service import OfferService, SubscriptionError
        svc = OfferService()

        product = svc.create_product(
            db, title="Cap Test", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("5000"),
        )
        svc.open_fundraising(db, product.id)

        svc.subscribe(db, product_id=product.id, lender_client_id=lender.id, amount=Decimal("4000"))

        with pytest.raises(SubscriptionError, match="exceeds remaining capacity"):
            svc.subscribe(db, product_id=product.id, lender_client_id=lender.id, amount=Decimal("2000"))

    def test_subscribe_borrower_cannot_lend_to_self(self, db):
        borrower = _create_client(db, "offer_selfbor@test.com")
        _set_balance(db, borrower.id, "USDC", 50000)

        from services.lending.offer_service import OfferService, SubscriptionError
        svc = OfferService()

        product = svc.create_product(
            db, title="Self Test", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("10000"),
        )
        svc.open_fundraising(db, product.id)

        with pytest.raises(SubscriptionError, match="cannot subscribe"):
            svc.subscribe(db, product_id=product.id, lender_client_id=borrower.id, amount=Decimal("5000"))

    def test_auto_funded_on_target_reached(self, db):
        borrower = _create_client(db, "offer_autofund_b@test.com")
        lender = _create_client(db, "offer_autofund_l@test.com")
        _set_balance(db, lender.id, "USDC", 50000)

        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db, title="Auto Fund", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("5000"),
        )
        svc.open_fundraising(db, product.id)

        svc.subscribe(db, product_id=product.id, lender_client_id=lender.id, amount=Decimal("5000"))

        detail = svc.get_product_detail(db, product.id)
        assert detail["status"] == "funded"
        assert detail["progress_pct"] == 100.0

    def test_cannot_subscribe_to_non_fundraising(self, db):
        borrower = _create_client(db, "offer_nonfund_b@test.com")
        lender = _create_client(db, "offer_nonfund_l@test.com")
        _set_balance(db, lender.id, "USDC", 50000)

        from services.lending.offer_service import OfferService, SubscriptionError
        svc = OfferService()

        product = svc.create_product(
            db, title="Draft Test", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("10000"),
        )

        with pytest.raises(SubscriptionError, match="not open for subscription"):
            svc.subscribe(db, product_id=product.id, lender_client_id=lender.id, amount=Decimal("1000"))


# ---------------------------------------------------------------------------
# C. ACTIVATION
# ---------------------------------------------------------------------------

class TestActivation:

    def test_activate_triggers_borrow(self, db):
        borrower = _create_client(db, "offer_act_b@test.com")
        lender = _create_client(db, "offer_act_l@test.com")
        _set_balance(db, lender.id, "USDC", 50000)
        _set_balance(db, borrower.id, "USDC", 0)

        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db, title="Activate Test", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("10000"),
        )
        svc.open_fundraising(db, product.id)
        svc.subscribe(db, product_id=product.id, lender_client_id=lender.id, amount=Decimal("10000"))

        result = svc.activate_product(db, product.id)

        assert result["status"] == "active"
        assert result["borrow_result"]["borrowed_amount"] == 10000.0

        # Borrower received the funds
        from services.exchange.repository import CryptoPositionRepository
        bpos = CryptoPositionRepository.get_or_create_for_update(db, borrower.id, "USDC")
        assert float(bpos.balance) == 10000.0

    def test_activate_creates_positions(self, db):
        borrower = _create_client(db, "offer_actpos_b@test.com")
        lender = _create_client(db, "offer_actpos_l@test.com")
        _set_balance(db, lender.id, "USDC", 50000)
        _set_balance(db, borrower.id, "USDC", 0)

        from services.lending.offer_service import OfferService
        from services.portfolio_engine.positions.models import PositionAtom
        from services.portfolio_engine.portfolios.models import Portfolio
        svc = OfferService()

        product = svc.create_product(
            db, title="Pos Test", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("5000"),
        )
        svc.open_fundraising(db, product.id)
        svc.subscribe(db, product_id=product.id, lender_client_id=lender.id, amount=Decimal("5000"))
        svc.activate_product(db, product.id)

        # Lending atom for lender
        lp = db.query(Portfolio).filter(Portfolio.client_id == lender.id, Portfolio.status == "active").first()
        lending_atom = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == lp.id,
            PositionAtom.position_type == "lending",
            PositionAtom.status == "open",
        ).first()
        assert lending_atom is not None
        assert float(lending_atom.quantity) == 5000.0

        # Borrowing atom for borrower
        bp = db.query(Portfolio).filter(Portfolio.client_id == borrower.id, Portfolio.status == "active").first()
        borrowing_atom = db.query(PositionAtom).filter(
            PositionAtom.portfolio_id == bp.id,
            PositionAtom.position_type == "borrowing",
            PositionAtom.status == "open",
        ).first()
        assert borrowing_atom is not None
        assert float(borrowing_atom.quantity) == 5000.0

    def test_cannot_activate_unfunded(self, db):
        borrower = _create_client(db, "offer_unfund_b@test.com")
        lender = _create_client(db, "offer_unfund_l@test.com")
        _set_balance(db, lender.id, "USDC", 50000)

        from services.lending.offer_service import OfferService, InvalidOfferStatusError
        svc = OfferService()

        product = svc.create_product(
            db, title="Unfund Test", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("10000"),
        )
        svc.open_fundraising(db, product.id)
        svc.subscribe(db, product_id=product.id, lender_client_id=lender.id, amount=Decimal("3000"))

        with pytest.raises(InvalidOfferStatusError, match="raised .* < target"):
            svc.activate_product(db, product.id)


# ---------------------------------------------------------------------------
# D. BORROWER RESTRICTION
# ---------------------------------------------------------------------------

class TestBorrowerRestriction:

    def test_external_borrow_rejected(self, db):
        """Non-designated borrower cannot borrow from a product pool."""
        borrower = _create_client(db, "offer_restrict_b@test.com")
        lender = _create_client(db, "offer_restrict_l@test.com")
        intruder = _create_client(db, "offer_restrict_i@test.com")
        _set_balance(db, lender.id, "USDC", 50000)

        from services.lending.offer_service import OfferService, BorrowerRestrictionError
        from services.lending.pool_service import PoolLendingService
        svc = OfferService()

        product = svc.create_product(
            db, title="Restrict Test", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("10000"),
        )
        svc.open_fundraising(db, product.id)
        svc.subscribe(db, product_id=product.id, lender_client_id=lender.id, amount=Decimal("10000"))

        pool_svc = PoolLendingService()
        with pytest.raises(BorrowerRestrictionError, match="only borrower"):
            pool_svc.borrow_from_pool(
                db,
                borrower_client_id=intruder.id,
                asset="USDC",
                amount=Decimal("5000"),
            )


# ---------------------------------------------------------------------------
# E. FULL E2E CYCLE
# ---------------------------------------------------------------------------

class TestFullE2ECycle:

    def test_complete_lifecycle(self, db):
        """create → fundraise → subscribe → activate → accrue → repay → close."""
        borrower = _create_client(db, "offer_e2e_b@test.com")
        lender1 = _create_client(db, "offer_e2e_l1@test.com")
        lender2 = _create_client(db, "offer_e2e_l2@test.com")
        _set_balance(db, lender1.id, "USDC", 50000)
        _set_balance(db, lender2.id, "USDC", 50000)
        _set_balance(db, borrower.id, "USDC", 0)

        from services.lending.offer_service import OfferService
        from services.lending.interest_engine import InterestEngine
        from services.lending.repayment_engine import RepaymentEngine
        from services.lending.pool_models import PoolBorrowPosition
        svc = OfferService()

        # 1. Create
        product = svc.create_product(
            db, title="E2E Solar", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("8000"),
            supply_apr_bps=Decimal("500"),
            borrow_apr_bps=Decimal("700"),
        )

        # 2. Fundraise
        svc.open_fundraising(db, product.id)

        # 3. Subscribe (2 lenders)
        svc.subscribe(db, product_id=product.id, lender_client_id=lender1.id, amount=Decimal("5000"))
        svc.subscribe(db, product_id=product.id, lender_client_id=lender2.id, amount=Decimal("3000"))

        detail = svc.get_product_detail(db, product.id)
        assert detail["status"] == "funded"
        assert detail["current_raised"] == 8000.0

        # 4. Activate
        result = svc.activate_product(db, product.id)
        assert result["status"] == "active"
        assert result["borrow_result"]["lenders_count"] == 2

        # Borrower has 8000
        from services.exchange.repository import CryptoPositionRepository
        bpos = CryptoPositionRepository.get_or_create_for_update(db, borrower.id, "USDC")
        assert float(bpos.balance) == 8000.0

        # 5. Accrue interest
        for d in range(5):
            InterestEngine().run_daily_accrual(db, accrual_date=date(2027, 6, 1 + d))

        # 6. Repay
        bp = db.query(PoolBorrowPosition).filter(
            PoolBorrowPosition.client_id == borrower.id,
            PoolBorrowPosition.status == "active",
        ).first()
        assert bp is not None

        _set_balance(db, borrower.id, "USDC", 10000)
        RepaymentEngine().repay_borrow_position(db, borrow_position_id=bp.id)

        # 7. Mark repaid + close
        svc.mark_repaid(db, product.id)
        detail = svc.get_product_detail(db, product.id)
        assert detail["status"] == "repaid"

        svc.close_product(db, product.id)
        detail = svc.get_product_detail(db, product.id)
        assert detail["status"] == "closed"


# ---------------------------------------------------------------------------
# F. EDGE CASES
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_cannot_activate_from_draft(self, db):
        borrower = _create_client(db, "offer_edge_draft_b@test.com")
        from services.lending.offer_service import OfferService, InvalidOfferStatusError
        svc = OfferService()

        product = svc.create_product(
            db, title="Draft Edge", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("10000"),
        )

        with pytest.raises(InvalidOfferStatusError):
            svc.activate_product(db, product.id)

    def test_multi_lender_subscription(self, db):
        borrower = _create_client(db, "offer_multi_b@test.com")
        l1 = _create_client(db, "offer_multi_l1@test.com")
        l2 = _create_client(db, "offer_multi_l2@test.com")
        l3 = _create_client(db, "offer_multi_l3@test.com")
        _set_balance(db, l1.id, "USDC", 10000)
        _set_balance(db, l2.id, "USDC", 10000)
        _set_balance(db, l3.id, "USDC", 10000)

        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db, title="Multi Lender", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("15000"),
        )
        svc.open_fundraising(db, product.id)

        svc.subscribe(db, product_id=product.id, lender_client_id=l1.id, amount=Decimal("5000"))
        svc.subscribe(db, product_id=product.id, lender_client_id=l2.id, amount=Decimal("5000"))
        svc.subscribe(db, product_id=product.id, lender_client_id=l3.id, amount=Decimal("5000"))

        detail = svc.get_product_detail(db, product.id)
        assert detail["status"] == "funded"
        assert detail["current_raised"] == 15000.0

    def test_lifecycle_invalid_transitions(self, db):
        borrower = _create_client(db, "offer_invalid_b@test.com")
        from services.lending.offer_service import OfferService, InvalidOfferStatusError
        svc = OfferService()

        product = svc.create_product(
            db, title="Invalid Trans", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("10000"),
        )

        with pytest.raises(InvalidOfferStatusError):
            svc.mark_repaid(db, product.id)

        with pytest.raises(InvalidOfferStatusError):
            svc.close_product(db, product.id)


# ---------------------------------------------------------------------------
# G. LISTING AND USER POSITIONS
# ---------------------------------------------------------------------------

class TestListingAndPositions:

    def test_list_products(self, db):
        borrower = _create_client(db, "offer_list_b@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        svc.create_product(
            db, title="List Test A", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("10000"),
        )
        svc.create_product(
            db, title="List Test B", asset="BTC",
            borrower_client_id=borrower.id,
            target_size=Decimal("5"),
        )

        products = svc.list_products(db)
        titles = [p["title"] for p in products]
        assert "List Test A" in titles
        assert "List Test B" in titles

    def test_list_products_filter_asset(self, db):
        borrower = _create_client(db, "offer_filter_b@test.com")
        from services.lending.offer_service import OfferService
        svc = OfferService()

        svc.create_product(
            db, title="Filter USDC", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("10000"),
        )
        svc.create_product(
            db, title="Filter ETH", asset="ETH",
            borrower_client_id=borrower.id,
            target_size=Decimal("10"),
        )

        usdc_products = svc.list_products(db, asset="USDC")
        assets = {p["asset"] for p in usdc_products}
        assert "USDC" in assets

    def test_user_subscriptions(self, db):
        borrower = _create_client(db, "offer_usersub_b@test.com")
        lender = _create_client(db, "offer_usersub_l@test.com")
        _set_balance(db, lender.id, "USDC", 50000)

        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db, title="User Sub Test", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("10000"),
        )
        svc.open_fundraising(db, product.id)
        svc.subscribe(db, product_id=product.id, lender_client_id=lender.id, amount=Decimal("5000"))

        positions = svc.get_user_subscriptions(db, lender.id)
        assert len(positions) >= 1
        pos = next(p for p in positions if p["title"] == "User Sub Test")
        assert pos["committed"] == 5000.0
        assert pos["asset"] == "USDC"

    def test_product_detail_includes_progress(self, db):
        borrower = _create_client(db, "offer_prog_b@test.com")
        lender = _create_client(db, "offer_prog_l@test.com")
        _set_balance(db, lender.id, "USDC", 50000)

        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db, title="Progress Test", asset="USDC",
            borrower_client_id=borrower.id,
            target_size=Decimal("10000"),
        )
        svc.open_fundraising(db, product.id)
        svc.subscribe(db, product_id=product.id, lender_client_id=lender.id, amount=Decimal("2500"))

        detail = svc.get_product_detail(db, product.id)
        assert detail["progress_pct"] == 25.0
        assert detail["remaining"] == 7500.0
