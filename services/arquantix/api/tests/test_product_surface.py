"""Tests for Earn / Borrow Product Surface — Phase 2A.9 (improved).

Covers:
  A. Pools overview (list, rates, utilization, APY flags)
  B. Earn positions — earning vs idle split
  C. Borrow positions (borrowed + interest due)
  D. Dashboard (combined earn + borrow + earn_breakdown)
  E. Edge cases (no positions, zero utilization, commit-only)
  F. Post-repay state (positions disappear)
  G. Multi-asset (positions per asset)
  H. APY estimation flags
  I. Idle vs earning invariants
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


def _setup_pool(db, lender, borrower, asset, supply, borrow, borrow_rate=500, supply_rate=300):
    from services.lending.pool_service import PoolLendingService
    from services.lending.pool_models import LendingPool
    svc = PoolLendingService()
    svc.create_supply_commitment(db, client_id=lender.id, asset=asset, amount=Decimal(str(supply)))
    result = svc.borrow_from_pool(db, borrower_client_id=borrower.id, asset=asset, amount=Decimal(str(borrow)))
    pool = db.query(LendingPool).filter(LendingPool.asset == asset.upper()).first()
    pool.borrow_rate_bps = Decimal(str(borrow_rate))
    pool.supply_rate_bps = Decimal(str(supply_rate))
    db.flush()
    return result, pool


# ---------------------------------------------------------------------------
# A. POOLS OVERVIEW + APY FLAGS
# ---------------------------------------------------------------------------

class TestPoolsOverview:

    def test_list_active_pools(self, db):
        lender = _create_client(db, "ps2_pools_l@test.com")
        borrower = _create_client(db, "ps2_pools_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 1000)

        from services.lending.product_surface import get_pools_overview
        pools = get_pools_overview(db)

        usdc_pool = next((p for p in pools if p["asset"] == "USDC"), None)
        assert usdc_pool is not None
        assert usdc_pool["total_supplied"] > 0
        assert usdc_pool["total_borrowed"] > 0
        assert usdc_pool["supply_apr"] > 0
        assert usdc_pool["borrow_apr"] > 0
        assert usdc_pool["utilization"] > 0

    def test_pool_rates_correct(self, db):
        lender = _create_client(db, "ps2_rates_l@test.com")
        borrower = _create_client(db, "ps2_rates_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 1000, borrow_rate=800, supply_rate=500)

        from services.lending.product_surface import get_pools_overview
        pools = get_pools_overview(db)
        usdc = next((p for p in pools if p["asset"] == "USDC"), None)

        assert usdc["borrow_apr"] == 8.0, "800 bps = 8.0%"
        assert usdc["supply_apr"] == 5.0, "500 bps = 5.0%"

    def test_pool_has_apy_estimated_flag(self, db):
        lender = _create_client(db, "ps2_apyflag_l@test.com")
        borrower = _create_client(db, "ps2_apyflag_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 1000)

        from services.lending.product_surface import get_pools_overview
        pools = get_pools_overview(db)
        usdc = next((p for p in pools if p["asset"] == "USDC"), None)

        assert usdc["is_apy_estimated"] is True
        assert isinstance(usdc["apy_explanation"], str)
        assert len(usdc["apy_explanation"]) > 10

    def test_pool_effective_apy_formula(self, db):
        """effective_apy = supply_apr × (total_borrowed / total_committed)."""
        lender = _create_client(db, "ps2_apyform_l@test.com")
        borrower = _create_client(db, "ps2_apyform_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 2000, 1000, supply_rate=400)

        from services.lending.product_surface import get_pools_overview
        pools = get_pools_overview(db)
        usdc = next((p for p in pools if p["asset"] == "USDC"), None)

        # supply_apr = 4.0%, utilization = 50% → effective_apy ≈ 2.0%
        assert usdc["supply_apr"] == 4.0
        assert abs(usdc["effective_apy"] - 2.0) < 0.1


# ---------------------------------------------------------------------------
# B. EARN POSITIONS — EARNING vs IDLE SPLIT
# ---------------------------------------------------------------------------

class TestEarnPositions:

    def test_earn_shows_earning_and_idle(self, db):
        """Supply 3000, borrow 2000 → earning=2000, idle=1000."""
        lender = _create_client(db, "ps2_earn_l@test.com")
        borrower = _create_client(db, "ps2_earn_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 2000)

        from services.lending.product_surface import get_earn_positions
        earn = get_earn_positions(db, lender.id)

        assert earn["positions_count"] >= 1
        pos = earn["positions"][0]
        assert pos["asset"] == "USDC"
        assert pos["earning_amount"] == 2000.0
        assert pos["idle_amount"] == 1000.0
        assert pos["total_supplied"] == 3000.0

    def test_earn_accrued_only_on_earning(self, db):
        lender = _create_client(db, "ps2_earnacr_l@test.com")
        borrower = _create_client(db, "ps2_earnacr_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 2000)

        from services.lending.interest_engine import InterestEngine
        for d in range(3):
            InterestEngine().run_daily_accrual(db, accrual_date=date(2027, 3, 1 + d))

        from services.lending.product_surface import get_earn_positions
        earn = get_earn_positions(db, lender.id)

        pos = earn["positions"][0]
        assert pos["accrued_interest"] > 0
        assert pos["total_value"] > pos["total_supplied"]

        # Top-level idle accrued must be 0
        assert earn["idle"]["accrued_interest_eur"] == 0.0
        assert earn["earning"]["accrued_interest_eur"] > 0

    def test_earn_backward_compat_supplied_field(self, db):
        """The old `supplied` field still exists (= earning_amount)."""
        lender = _create_client(db, "ps2_compat_l@test.com")
        borrower = _create_client(db, "ps2_compat_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 1000)

        from services.lending.product_surface import get_earn_positions
        earn = get_earn_positions(db, lender.id)

        pos = earn["positions"][0]
        assert "supplied" in pos
        assert pos["supplied"] == pos["earning_amount"]

    def test_earn_pending_commitments_still_present(self, db):
        lender = _create_client(db, "ps2_pending_l@test.com")
        _set_balance(db, lender.id, "USDC", 5000)

        from services.lending.pool_service import PoolLendingService
        PoolLendingService().create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("2000"))

        from services.lending.product_surface import get_earn_positions
        earn = get_earn_positions(db, lender.id)

        assert earn["pending_commitments_count"] >= 1
        assert earn["pending_commitments"][0]["asset"] == "USDC"
        assert earn["pending_commitments"][0]["available"] == 2000.0

    def test_earn_total_value_eur(self, db):
        lender = _create_client(db, "ps2_earntot_l@test.com")
        borrower = _create_client(db, "ps2_earntot_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 1000)

        from services.lending.product_surface import get_earn_positions
        earn = get_earn_positions(db, lender.id)

        assert earn["total_earn_value_eur"] > 0
        assert earn["earning"]["amount_eur"] > 0
        assert earn["idle"]["amount_eur"] > 0

    def test_earn_position_has_apy_flag(self, db):
        lender = _create_client(db, "ps2_posapyflag_l@test.com")
        borrower = _create_client(db, "ps2_posapyflag_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 1000)

        from services.lending.product_surface import get_earn_positions
        earn = get_earn_positions(db, lender.id)

        pos = earn["positions"][0]
        assert pos["is_apy_estimated"] is True


# ---------------------------------------------------------------------------
# C. BORROW POSITIONS
# ---------------------------------------------------------------------------

class TestBorrowPositions:

    def test_borrow_shows_borrowed_and_due(self, db):
        lender = _create_client(db, "ps2_borrow_l@test.com")
        borrower = _create_client(db, "ps2_borrow_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 1000)

        from services.lending.interest_engine import InterestEngine
        InterestEngine().run_daily_accrual(db, accrual_date=date(2027, 4, 1))

        from services.lending.product_surface import get_borrow_positions
        borrow = get_borrow_positions(db, borrower.id)

        assert borrow["positions_count"] >= 1
        pos = borrow["positions"][0]
        assert pos["asset"] == "USDC"
        assert pos["borrowed"] == 1000.0
        assert pos["accrued_interest"] > 0
        assert pos["total_due"] > 1000.0
        assert pos["apr"] > 0

    def test_borrow_total_due_eur(self, db):
        lender = _create_client(db, "ps2_bdue_l@test.com")
        borrower = _create_client(db, "ps2_bdue_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 1500)

        from services.lending.product_surface import get_borrow_positions
        borrow = get_borrow_positions(db, borrower.id)

        assert borrow["total_borrowed_eur"] > 0
        assert borrow["total_due_eur"] > 0


# ---------------------------------------------------------------------------
# D. DASHBOARD + EARN BREAKDOWN
# ---------------------------------------------------------------------------

class TestDashboard:

    def test_dashboard_combined(self, db):
        lender = _create_client(db, "ps2_dash_l@test.com")
        borrower = _create_client(db, "ps2_dash_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 1000)

        from services.lending.product_surface import get_earn_borrow_dashboard

        dash_l = get_earn_borrow_dashboard(db, lender.id)
        assert dash_l["earn"]["total_value_eur"] > 0
        assert dash_l["earn"]["positions_count"] >= 1
        assert dash_l["borrow"]["positions_count"] == 0

        dash_b = get_earn_borrow_dashboard(db, borrower.id)
        assert dash_b["borrow"]["total_borrowed_eur"] > 0
        assert dash_b["borrow"]["positions_count"] >= 1
        assert dash_b["earn"]["positions_count"] == 0

    def test_dashboard_net_position(self, db):
        lender = _create_client(db, "ps2_net_l@test.com")
        borrower = _create_client(db, "ps2_net_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 1000)

        from services.lending.product_surface import get_earn_borrow_dashboard
        dash = get_earn_borrow_dashboard(db, lender.id)

        expected_net = dash["earn"]["total_value_eur"] - dash["borrow"]["total_due_eur"]
        assert abs(dash["net_position_eur"] - expected_net) < 0.01

    def test_dashboard_earn_breakdown(self, db):
        """Dashboard includes earning_value_eur and idle_value_eur."""
        lender = _create_client(db, "ps2_dashbk_l@test.com")
        borrower = _create_client(db, "ps2_dashbk_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 1000)

        from services.lending.product_surface import get_earn_borrow_dashboard
        dash = get_earn_borrow_dashboard(db, lender.id)

        assert "earn_breakdown" in dash
        eb = dash["earn_breakdown"]
        assert eb["earning_value_eur"] > 0
        assert eb["idle_value_eur"] > 0
        total = eb["earning_value_eur"] + eb["idle_value_eur"]
        assert abs(total - dash["earn"]["total_value_eur"]) < 0.02


# ---------------------------------------------------------------------------
# E. EDGE CASES
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_no_positions_returns_empty(self, db):
        user = _create_client(db, "ps2_empty@test.com")

        from services.lending.product_surface import get_earn_positions, get_borrow_positions
        earn = get_earn_positions(db, user.id)
        borrow = get_borrow_positions(db, user.id)

        assert earn["positions_count"] == 0
        assert earn["total_earn_value_eur"] == 0.0
        assert earn["earning"]["amount_eur"] == 0.0
        assert earn["idle"]["amount_eur"] == 0.0
        assert borrow["positions_count"] == 0
        assert borrow["total_due_eur"] == 0.0

    def test_commitment_only_shows_idle_position(self, db):
        """Supply without borrow → position with idle_amount > 0, earning_amount = 0."""
        lender = _create_client(db, "ps2_commitonly@test.com")
        _set_balance(db, lender.id, "USDC", 5000)

        from services.lending.pool_service import PoolLendingService
        PoolLendingService().create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("1000"))

        from services.lending.product_surface import get_earn_positions
        earn = get_earn_positions(db, lender.id)

        assert earn["positions_count"] >= 1
        pos = next(p for p in earn["positions"] if p["asset"] == "USDC")
        assert pos["earning_amount"] == 0.0
        assert pos["idle_amount"] == 1000.0
        assert pos["accrued_interest"] == 0.0
        assert earn["idle"]["amount_eur"] > 0
        assert earn["earning"]["amount_eur"] == 0.0

    def test_zero_utilization_apy(self, db):
        """utilization = 0 → effective_apy = 0."""
        lender = _create_client(db, "ps2_zeroutil@test.com")
        _set_balance(db, lender.id, "BTC", 5)

        from services.lending.pool_service import PoolLendingService
        PoolLendingService().create_supply_commitment(db, client_id=lender.id, asset="BTC", amount=Decimal("1"))

        from services.lending.product_surface import get_pools_overview
        pools = get_pools_overview(db)
        btc = next((p for p in pools if p["asset"] == "BTC"), None)
        if btc:
            assert btc["effective_apy"] == 0.0
            assert btc["is_apy_estimated"] is True

    def test_full_borrow_zero_idle(self, db):
        """Supply 2000, borrow 2000 → idle = 0, earning = 2000."""
        lender = _create_client(db, "ps2_fullborrow_l@test.com")
        borrower = _create_client(db, "ps2_fullborrow_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 2000, 2000)

        from services.lending.product_surface import get_earn_positions
        earn = get_earn_positions(db, lender.id)

        pos = next(p for p in earn["positions"] if p["asset"] == "USDC")
        assert pos["earning_amount"] == 2000.0
        assert pos["idle_amount"] == 0.0


# ---------------------------------------------------------------------------
# F. POST-REPAY STATE
# ---------------------------------------------------------------------------

class TestPostRepay:

    def test_positions_disappear_after_repay(self, db):
        lender = _create_client(db, "ps2_repay_l@test.com")
        borrower = _create_client(db, "ps2_repay_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        result, _ = _setup_pool(db, lender, borrower, "USDC", 3000, 1000)
        borrow_id = result["borrow_position_id"]

        from services.lending.product_surface import get_earn_positions, get_borrow_positions

        earn = get_earn_positions(db, lender.id)
        borrow = get_borrow_positions(db, borrower.id)
        assert earn["positions_count"] >= 1
        assert borrow["positions_count"] >= 1

        _set_balance(db, borrower.id, "USDC", 1100)
        from services.lending.repayment_engine import RepaymentEngine
        RepaymentEngine().repay_borrow_position(db, borrow_position_id=borrow_id)

        borrow_after = get_borrow_positions(db, borrower.id)
        assert borrow_after["positions_count"] == 0


# ---------------------------------------------------------------------------
# G. MULTI-ASSET
# ---------------------------------------------------------------------------

class TestMultiAsset:

    def test_separate_positions_per_asset(self, db):
        lender = _create_client(db, "ps2_multi_l@test.com")
        borrower = _create_client(db, "ps2_multi_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, lender.id, "BTC", 2)
        _set_balance(db, borrower.id, "USDC", 0)
        _set_balance(db, borrower.id, "BTC", 0)

        _setup_pool(db, lender, borrower, "USDC", 2000, 1000)
        _setup_pool(db, lender, borrower, "BTC", 1, Decimal("0.5"))

        from services.lending.product_surface import get_earn_positions
        earn = get_earn_positions(db, lender.id)

        assets = [p["asset"] for p in earn["positions"]]
        assert "USDC" in assets
        assert "BTC" in assets
        assert earn["positions_count"] >= 2


# ---------------------------------------------------------------------------
# H. APY ESTIMATED FLAG (positions)
# ---------------------------------------------------------------------------

class TestAPYEstimatedFlag:

    def test_pool_apy_estimated_always_true(self, db):
        lender = _create_client(db, "ps2_apyest_l@test.com")
        borrower = _create_client(db, "ps2_apyest_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 1000)

        from services.lending.product_surface import get_pools_overview
        for pool in get_pools_overview(db):
            assert pool["is_apy_estimated"] is True
            assert "apy_explanation" in pool

    def test_effective_apy_correct_for_varying_utilization(self, db):
        """Supply 4000, borrow 1000 → utilization 25% → apy = supply_apr × 0.25."""
        lender = _create_client(db, "ps2_apyvar_l@test.com")
        borrower = _create_client(db, "ps2_apyvar_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 4000, 1000, supply_rate=400)

        from services.lending.product_surface import get_pools_overview
        usdc = next(p for p in get_pools_overview(db) if p["asset"] == "USDC")

        # supply_apr=4.0%, util=25% → effective_apy = 1.0%
        assert abs(usdc["effective_apy"] - 1.0) < 0.1


# ---------------------------------------------------------------------------
# I. IDLE vs EARNING INVARIANTS
# ---------------------------------------------------------------------------

class TestIdleVsEarningInvariants:

    def test_earning_plus_idle_equals_total(self, db):
        lender = _create_client(db, "ps2_inv_l@test.com")
        borrower = _create_client(db, "ps2_inv_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 1500)

        from services.lending.product_surface import get_earn_positions
        earn = get_earn_positions(db, lender.id)

        pos = next(p for p in earn["positions"] if p["asset"] == "USDC")
        assert abs(pos["earning_amount"] + pos["idle_amount"] - pos["total_supplied"]) < 0.001

    def test_earning_eur_plus_idle_eur_equals_total_eur(self, db):
        lender = _create_client(db, "ps2_inveur_l@test.com")
        borrower = _create_client(db, "ps2_inveur_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 1500)

        from services.lending.product_surface import get_earn_positions
        earn = get_earn_positions(db, lender.id)

        total_eur = earn["earning"]["amount_eur"] + earn["idle"]["amount_eur"]
        # total_earn_value_eur includes accrued interest on earning, so we add that
        expected_total = total_eur + earn["earning"]["accrued_interest_eur"]
        assert abs(earn["total_earn_value_eur"] - expected_total) < 0.02

    def test_idle_has_zero_interest(self, db):
        """Idle funds never generate interest."""
        lender = _create_client(db, "ps2_idlezero_l@test.com")
        borrower = _create_client(db, "ps2_idlezero_b@test.com")
        _set_balance(db, lender.id, "USDC", 5000)
        _set_balance(db, borrower.id, "USDC", 0)

        _setup_pool(db, lender, borrower, "USDC", 3000, 1000)

        from services.lending.interest_engine import InterestEngine
        for d in range(5):
            InterestEngine().run_daily_accrual(db, accrual_date=date(2027, 5, 1 + d))

        from services.lending.product_surface import get_earn_positions
        earn = get_earn_positions(db, lender.id)

        assert earn["idle"]["accrued_interest_eur"] == 0.0
        assert earn["earning"]["accrued_interest_eur"] > 0

    def test_no_borrow_all_idle(self, db):
        """If nobody borrows, everything is idle, no interest generated."""
        lender = _create_client(db, "ps2_allidle@test.com")
        _set_balance(db, lender.id, "USDC", 5000)

        from services.lending.pool_service import PoolLendingService
        PoolLendingService().create_supply_commitment(db, client_id=lender.id, asset="USDC", amount=Decimal("2000"))

        from services.lending.product_surface import get_earn_positions
        earn = get_earn_positions(db, lender.id)

        pos = next(p for p in earn["positions"] if p["asset"] == "USDC")
        assert pos["earning_amount"] == 0.0
        assert pos["idle_amount"] == 2000.0
        assert pos["accrued_interest"] == 0.0
        assert earn["earning"]["amount_eur"] == 0.0
        assert earn["idle"]["amount_eur"] > 0
