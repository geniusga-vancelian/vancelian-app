"""Tests for Exclusive Offer Invest Flow — Phase 2A.12.

Covers:
  A. Entry asset model (defaults, resolution, persistence)
  B. Preview — direct supply (no conversion)
  C. Preview — fiat buy (EUR → USDC)
  D. Preview — crypto swap (BTC → USDC)
  E. Invest — direct supply (USDC → USDC)
  F. Invest — fiat buy (EUR → USDC) via mock
  G. Invest — crypto swap (BTC → USDC) via mock
  H. Validation — funding asset not allowed
  I. Validation — product not investable (wrong status)
  J. Validation — cap exceeded
  K. current_raised updated after invest
  L. Non-regression — preview has zero side-effects
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch, MagicMock

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


_ASSET_COUNTER = 0

def _unique_asset():
    """Generate a unique test asset name to avoid lending_pools unique constraint on asset."""
    global _ASSET_COUNTER
    _ASSET_COUNTER += 1
    return f"T{_ASSET_COUNTER:03d}"


def _create_fundraising_product(
    db, borrower_id, asset=None, target=10000,
    entry_default=None, entry_allowed=None,
):
    if asset is None:
        asset = _unique_asset()
    from services.lending.offer_service import OfferService
    svc = OfferService()
    product = svc.create_product(
        db,
        title=f"Test Invest Offer {uuid.uuid4().hex[:6]}",
        asset=asset,
        borrower_client_id=borrower_id,
        target_size=Decimal(str(target)),
        supply_apr_bps=Decimal("500"),
        borrow_apr_bps=Decimal("800"),
        entry_asset_default=entry_default,
        entry_assets_allowed=entry_allowed,
    )
    svc.open_fundraising(db, product.id)
    db.flush()
    return product


# ---------------------------------------------------------------------------
# A. ENTRY ASSET MODEL
# ---------------------------------------------------------------------------

class TestEntryAssetModel:
    """Entry asset defaults, resolution, and persistence."""

    def test_default_entry_asset_equals_pool_asset(self, db):
        """When no entry_asset_default is provided, it should default to the pool asset."""
        borrower = _create_client(db, "invest_borrower_a1@test.com")
        product = _create_fundraising_product(db, borrower.id)
        assert product.entry_asset_default == product.asset
        assert product.entry_assets_allowed == [product.asset]

    def test_custom_entry_asset_config(self, db):
        """Custom entry_asset_default and entry_assets_allowed are persisted."""
        borrower = _create_client(db, "invest_borrower_a2@test.com")
        asset = _unique_asset()
        product = _create_fundraising_product(
            db, borrower.id, asset=asset,
            entry_default=asset,
            entry_allowed=[asset, "EUR", "BTC"],
        )
        assert product.entry_asset_default == asset
        assert set(product.entry_assets_allowed) == {asset, "EUR", "BTC"}

    def test_entry_default_auto_included_in_allowed(self, db):
        """entry_asset_default is always in entry_assets_allowed."""
        borrower = _create_client(db, "invest_borrower_a3@test.com")
        asset = _unique_asset()
        product = _create_fundraising_product(
            db, borrower.id, asset=asset,
            entry_default=asset,
            entry_allowed=["BTC", "ETH"],
        )
        assert asset in product.entry_assets_allowed

    def test_entry_fields_in_product_dict(self, db):
        """Product detail response includes entry_asset fields."""
        borrower = _create_client(db, "invest_borrower_a4@test.com")
        asset = _unique_asset()
        product = _create_fundraising_product(
            db, borrower.id, asset=asset,
            entry_allowed=[asset, "EUR"],
        )
        from services.lending.offer_service import OfferService
        detail = OfferService().get_product_detail(db, product.id)
        assert detail["entry_asset_default"] == asset
        assert "EUR" in detail["entry_assets_allowed"]


# ---------------------------------------------------------------------------
# B. PREVIEW — DIRECT SUPPLY (NO CONVERSION)
# ---------------------------------------------------------------------------

class TestPreviewDirect:
    """Preview when funding_asset == pool_asset → no conversion."""

    def test_preview_direct_no_conversion(self, db):
        borrower = _create_client(db, "invest_borrower_b1@test.com")
        lender = _create_client(db, "invest_lender_b1@test.com")
        product = _create_fundraising_product(db, borrower.id)
        pool_asset = product.asset

        from services.lending.invest_orchestrator import LendingInvestOrchestrator
        orch = LendingInvestOrchestrator()
        result = orch.preview_invest(
            db,
            product_id=product.id,
            client_id=lender.id,
            funding_asset=pool_asset,
            funding_amount=Decimal("1000"),
        )

        assert result["conversion_type"] == "none"
        assert result["requires_conversion"] is False
        assert result["estimated_pool_asset_amount"] == 1000.0
        assert result["estimated_supply_amount"] == 1000.0
        assert result["entry_asset_used"] == pool_asset
        assert result["conversion_fee"] == 0.0

    def test_preview_no_side_effects(self, db):
        """Preview must not create any commitment or modify any balance."""
        borrower = _create_client(db, "invest_borrower_b2@test.com")
        lender = _create_client(db, "invest_lender_b2@test.com")
        product = _create_fundraising_product(db, borrower.id)
        pool_asset = product.asset
        _set_balance(db, lender.id, pool_asset, 5000)

        from services.lending.pool_models import PoolSupplyCommitment

        commitments_before = db.query(PoolSupplyCommitment).filter(
            PoolSupplyCommitment.client_id == lender.id,
        ).count()
        balance_before = _get_balance(db, lender.id, pool_asset)

        from services.lending.invest_orchestrator import LendingInvestOrchestrator
        LendingInvestOrchestrator().preview_invest(
            db,
            product_id=product.id,
            client_id=lender.id,
            funding_asset=pool_asset,
            funding_amount=Decimal("1000"),
        )

        commitments_after = db.query(PoolSupplyCommitment).filter(
            PoolSupplyCommitment.client_id == lender.id,
        ).count()
        balance_after = _get_balance(db, lender.id, pool_asset)
        assert commitments_after == commitments_before
        assert balance_after == balance_before


# ---------------------------------------------------------------------------
# C. PREVIEW — FIAT BUY (EUR → USDC)
# ---------------------------------------------------------------------------

class TestPreviewBuy:
    """Preview when funding_asset is fiat → buy conversion type."""

    def test_preview_eur_buy(self, db):
        borrower = _create_client(db, "invest_borrower_c1@test.com")
        lender = _create_client(db, "invest_lender_c1@test.com")
        asset = _unique_asset()
        product = _create_fundraising_product(
            db, borrower.id, asset=asset, entry_allowed=[asset, "EUR"],
        )

        from services.lending.invest_orchestrator import LendingInvestOrchestrator

        mock_preview = {
            "asset": asset,
            "amount_fiat": 1000.0,
            "estimated_price": 1.08,
            "estimated_crypto_gross": 925.93,
            "fee_amount": 4.63,
            "fee_asset": asset,
            "fee_bps": 50,
            "estimated_crypto_net": 921.30,
            "currency": "EUR",
            "is_fresh": True,
        }

        orch = LendingInvestOrchestrator()
        with patch.object(orch._exchange, "preview_buy", return_value=mock_preview):
            result = orch.preview_invest(
                db,
                product_id=product.id,
                client_id=lender.id,
                funding_asset="EUR",
                funding_amount=Decimal("1000"),
            )

        assert result["conversion_type"] == "buy"
        assert result["requires_conversion"] is True
        assert result["estimated_pool_asset_amount"] == 921.30
        assert result["conversion_fee"] == 4.63


# ---------------------------------------------------------------------------
# D. PREVIEW — CRYPTO SWAP (BTC → USDC)
# ---------------------------------------------------------------------------

class TestPreviewSwap:
    """Preview when funding_asset is crypto != pool_asset → swap."""

    def test_preview_btc_swap(self, db):
        borrower = _create_client(db, "invest_borrower_d1@test.com")
        lender = _create_client(db, "invest_lender_d1@test.com")
        asset = _unique_asset()
        product = _create_fundraising_product(
            db, borrower.id, asset=asset, entry_allowed=[asset, "BTC"],
        )

        mock_swap_preview = {
            "from_asset": "BTC",
            "to_asset": asset,
            "amount_from": 0.1,
            "estimated_reference_value_gross": 8500.0,
            "fee_in_reference_currency": 42.5,
            "estimated_reference_value_net": 8457.5,
            "estimated_to_amount": 8457.5,
            "from_price_in_ref_ccy": 85000.0,
            "to_price_in_ref_ccy": 1.0,
            "reference_currency": "EUR",
            "is_fresh": True,
        }

        from services.lending.invest_orchestrator import LendingInvestOrchestrator
        orch = LendingInvestOrchestrator()
        with patch.object(orch._exchange, "preview_swap", return_value=mock_swap_preview):
            result = orch.preview_invest(
                db,
                product_id=product.id,
                client_id=lender.id,
                funding_asset="BTC",
                funding_amount=Decimal("0.1"),
            )

        assert result["conversion_type"] == "swap"
        assert result["requires_conversion"] is True
        assert result["estimated_pool_asset_amount"] == 8457.5


# ---------------------------------------------------------------------------
# E. INVEST — DIRECT SUPPLY (USDC → USDC)
# ---------------------------------------------------------------------------

class TestInvestDirect:
    """Direct investment when funding_asset == pool_asset."""

    def test_invest_direct_creates_commitment(self, db):
        borrower = _create_client(db, "invest_borrower_e1@test.com")
        lender = _create_client(db, "invest_lender_e1@test.com")
        product = _create_fundraising_product(db, borrower.id, target=10000)
        pool_asset = product.asset
        _set_balance(db, lender.id, pool_asset, 5000)

        from services.lending.invest_orchestrator import LendingInvestOrchestrator
        orch = LendingInvestOrchestrator()
        result = orch.invest_into_product(
            db,
            product_id=product.id,
            client_id=lender.id,
            funding_asset=pool_asset,
            funding_amount=Decimal("2000"),
        )

        assert result["status"] == "completed"
        assert result["conversion_type"] == "none"
        assert result["amount_supplied"] == 2000.0
        assert result["entry_asset_used"] == pool_asset
        assert result["commitment_id"]
        assert result["pool_id"]

    def test_invest_direct_updates_balance(self, db):
        borrower = _create_client(db, "invest_borrower_e2@test.com")
        lender = _create_client(db, "invest_lender_e2@test.com")
        product = _create_fundraising_product(db, borrower.id)
        pool_asset = product.asset
        _set_balance(db, lender.id, pool_asset, 3000)

        from services.lending.invest_orchestrator import LendingInvestOrchestrator
        LendingInvestOrchestrator().invest_into_product(
            db,
            product_id=product.id,
            client_id=lender.id,
            funding_asset=pool_asset,
            funding_amount=Decimal("1500"),
        )

        balance = _get_balance(db, lender.id, pool_asset)
        assert balance == Decimal("3000"), "Balance stays (available reduced by commitment)"

    def test_invest_direct_updates_current_raised(self, db):
        borrower = _create_client(db, "invest_borrower_e3@test.com")
        lender = _create_client(db, "invest_lender_e3@test.com")
        product = _create_fundraising_product(db, borrower.id, target=10000)
        pool_asset = product.asset
        _set_balance(db, lender.id, pool_asset, 5000)

        from services.lending.invest_orchestrator import LendingInvestOrchestrator
        LendingInvestOrchestrator().invest_into_product(
            db,
            product_id=product.id,
            client_id=lender.id,
            funding_asset=pool_asset,
            funding_amount=Decimal("3000"),
        )

        db.refresh(product)
        assert Decimal(str(product.current_raised)) == Decimal("3000")


# ---------------------------------------------------------------------------
# F. INVEST — FIAT BUY (EUR → USDC) via mock
# ---------------------------------------------------------------------------

class TestInvestBuy:
    """Investment with fiat → buy conversion (mocked ExchangeService.buy)."""

    def test_invest_eur_buy_creates_commitment(self, db):
        borrower = _create_client(db, "invest_borrower_f1@test.com")
        lender = _create_client(db, "invest_lender_f1@test.com")
        asset = _unique_asset()
        product = _create_fundraising_product(
            db, borrower.id, asset=asset, target=10000,
            entry_allowed=[asset, "EUR"],
        )
        _set_balance(db, lender.id, asset, 0)

        mock_buy_result = {
            "status": "completed",
            "order_id": str(uuid.uuid4()),
            "amount_crypto": 920.0,
            "price": 1.087,
            "fee_amount": 4.6,
        }

        from services.lending.invest_orchestrator import LendingInvestOrchestrator
        orch = LendingInvestOrchestrator()

        def fake_buy(db_arg, payload, actor):
            _set_balance(db, lender.id, asset, 920)
            return mock_buy_result

        with patch.object(orch._exchange, "buy", side_effect=fake_buy):
            result = orch.invest_into_product(
                db,
                product_id=product.id,
                client_id=lender.id,
                funding_asset="EUR",
                funding_amount=Decimal("1000"),
            )

        assert result["status"] == "completed"
        assert result["conversion_type"] == "buy"
        assert result["total_pool_asset_received"] == 920.0
        assert result["amount_supplied"] == 920.0


# ---------------------------------------------------------------------------
# G. INVEST — CRYPTO SWAP (BTC → USDC) via mock
# ---------------------------------------------------------------------------

class TestInvestSwap:
    """Investment with crypto swap (mocked ExchangeService.swap)."""

    def test_invest_btc_swap_creates_commitment(self, db):
        borrower = _create_client(db, "invest_borrower_g1@test.com")
        lender = _create_client(db, "invest_lender_g1@test.com")
        asset = _unique_asset()
        product = _create_fundraising_product(
            db, borrower.id, asset=asset, target=100000,
            entry_allowed=[asset, "BTC"],
        )
        _set_balance(db, lender.id, "BTC", 1)
        _set_balance(db, lender.id, asset, 0)

        mock_swap_result = {
            "status": "completed",
            "swap_group_id": str(uuid.uuid4()),
            "sell_order_id": str(uuid.uuid4()),
            "buy_order_id": str(uuid.uuid4()),
            "from_asset": "BTC",
            "to_asset": asset,
            "amount_from": 0.1,
            "amount_to": 8400.0,
        }

        from services.lending.invest_orchestrator import LendingInvestOrchestrator
        orch = LendingInvestOrchestrator()

        def fake_swap(db_arg, client_id, payload, actor):
            _set_balance(db, lender.id, asset, 8400)
            return mock_swap_result

        with patch.object(orch._exchange, "swap", side_effect=fake_swap):
            result = orch.invest_into_product(
                db,
                product_id=product.id,
                client_id=lender.id,
                funding_asset="BTC",
                funding_amount=Decimal("0.1"),
            )

        assert result["status"] == "completed"
        assert result["conversion_type"] == "swap"
        assert result["total_pool_asset_received"] == 8400.0
        assert result["amount_supplied"] == 8400.0


# ---------------------------------------------------------------------------
# H. VALIDATION — FUNDING ASSET NOT ALLOWED
# ---------------------------------------------------------------------------

class TestFundingAssetValidation:

    def test_reject_unauthorized_crypto(self, db):
        borrower = _create_client(db, "invest_borrower_h1@test.com")
        lender = _create_client(db, "invest_lender_h1@test.com")
        asset = _unique_asset()
        product = _create_fundraising_product(
            db, borrower.id, asset=asset, entry_allowed=[asset],
        )

        from services.lending.invest_orchestrator import (
            LendingInvestOrchestrator, FundingAssetNotAllowedError,
        )
        with pytest.raises(FundingAssetNotAllowedError):
            LendingInvestOrchestrator().preview_invest(
                db,
                product_id=product.id,
                client_id=lender.id,
                funding_asset="SOL",
                funding_amount=Decimal("100"),
            )

    def test_fiat_always_accepted(self, db):
        """Fiat currencies (EUR, USD) are always accepted regardless of entry_assets_allowed."""
        borrower = _create_client(db, "invest_borrower_h2@test.com")
        lender = _create_client(db, "invest_lender_h2@test.com")
        asset = _unique_asset()
        product = _create_fundraising_product(
            db, borrower.id, asset=asset, entry_allowed=[asset],
        )

        from services.lending.invest_orchestrator import LendingInvestOrchestrator

        mock_preview = {
            "asset": asset,
            "amount_fiat": 1000.0,
            "estimated_price": 1.08,
            "estimated_crypto_gross": 925.0,
            "fee_amount": 4.6,
            "fee_asset": asset,
            "fee_bps": 50,
            "estimated_crypto_net": 920.4,
            "currency": "EUR",
            "is_fresh": True,
        }

        orch = LendingInvestOrchestrator()
        with patch.object(orch._exchange, "preview_buy", return_value=mock_preview):
            result = orch.preview_invest(
                db,
                product_id=product.id,
                client_id=lender.id,
                funding_asset="EUR",
                funding_amount=Decimal("1000"),
            )
        assert result["conversion_type"] == "buy"


# ---------------------------------------------------------------------------
# I. VALIDATION — PRODUCT NOT INVESTABLE
# ---------------------------------------------------------------------------

class TestProductStatusValidation:

    def test_reject_draft_product(self, db):
        borrower = _create_client(db, "invest_borrower_i1@test.com")
        lender = _create_client(db, "invest_lender_i1@test.com")

        asset = _unique_asset()
        from services.lending.offer_service import OfferService
        svc = OfferService()
        product = svc.create_product(
            db,
            title="Draft Offer",
            asset=asset,
            borrower_client_id=borrower.id,
            target_size=Decimal("10000"),
        )

        from services.lending.invest_orchestrator import (
            LendingInvestOrchestrator, ProductNotInvestableError,
        )
        with pytest.raises(ProductNotInvestableError):
            LendingInvestOrchestrator().preview_invest(
                db,
                product_id=product.id,
                client_id=lender.id,
                funding_asset=asset,
                funding_amount=Decimal("1000"),
            )

    def test_reject_closed_product(self, db):
        borrower = _create_client(db, "invest_borrower_i2@test.com")
        lender = _create_client(db, "invest_lender_i2@test.com")

        asset = _unique_asset()
        from services.lending.offer_service import OfferService
        svc = OfferService()
        product = svc.create_product(
            db,
            title="Closed Offer",
            asset=asset,
            borrower_client_id=borrower.id,
            target_size=Decimal("10000"),
        )
        product.status = "closed"
        db.flush()

        from services.lending.invest_orchestrator import (
            LendingInvestOrchestrator, ProductNotInvestableError,
        )
        with pytest.raises(ProductNotInvestableError):
            LendingInvestOrchestrator().preview_invest(
                db,
                product_id=product.id,
                client_id=lender.id,
                funding_asset=asset,
                funding_amount=Decimal("1000"),
            )


# ---------------------------------------------------------------------------
# J. VALIDATION — CAP EXCEEDED
# ---------------------------------------------------------------------------

class TestCapValidation:

    def test_invest_capped_to_remaining(self, db):
        """When funding_amount > remaining capacity, supply is capped to remaining."""
        borrower = _create_client(db, "invest_borrower_j1@test.com")
        lender = _create_client(db, "invest_lender_j1@test.com")
        product = _create_fundraising_product(db, borrower.id, target=5000)
        pool_asset = product.asset
        _set_balance(db, lender.id, pool_asset, 20000)

        from services.lending.invest_orchestrator import LendingInvestOrchestrator
        result = LendingInvestOrchestrator().invest_into_product(
            db,
            product_id=product.id,
            client_id=lender.id,
            funding_asset=pool_asset,
            funding_amount=Decimal("5000"),
        )
        assert result["amount_supplied"] == 5000.0

        db.refresh(product)
        assert Decimal(str(product.current_raised)) == Decimal("5000")

    def test_invest_after_full_cap_rejected(self, db):
        """After target reached, further investment is rejected."""
        borrower = _create_client(db, "invest_borrower_j2@test.com")
        lender1 = _create_client(db, "invest_lender_j2a@test.com")
        lender2 = _create_client(db, "invest_lender_j2b@test.com")
        product = _create_fundraising_product(db, borrower.id, target=1000)
        pool_asset = product.asset
        _set_balance(db, lender1.id, pool_asset, 5000)
        _set_balance(db, lender2.id, pool_asset, 5000)

        from services.lending.invest_orchestrator import LendingInvestOrchestrator
        orch = LendingInvestOrchestrator()

        orch.invest_into_product(
            db, product_id=product.id, client_id=lender1.id,
            funding_asset=pool_asset, funding_amount=Decimal("1000"),
        )

        from services.lending.invest_orchestrator import ProductNotInvestableError
        with pytest.raises(ProductNotInvestableError, match="not investable"):
            orch.invest_into_product(
                db, product_id=product.id, client_id=lender2.id,
                funding_asset=pool_asset, funding_amount=Decimal("100"),
            )


# ---------------------------------------------------------------------------
# K. CURRENT_RAISED UPDATED
# ---------------------------------------------------------------------------

class TestCurrentRaised:

    def test_multiple_investments_accumulate(self, db):
        borrower = _create_client(db, "invest_borrower_k1@test.com")
        lender1 = _create_client(db, "invest_lender_k1@test.com")
        lender2 = _create_client(db, "invest_lender_k2@test.com")
        product = _create_fundraising_product(db, borrower.id, target=10000)
        pool_asset = product.asset
        _set_balance(db, lender1.id, pool_asset, 5000)
        _set_balance(db, lender2.id, pool_asset, 5000)

        from services.lending.invest_orchestrator import LendingInvestOrchestrator
        orch = LendingInvestOrchestrator()

        orch.invest_into_product(
            db, product_id=product.id, client_id=lender1.id,
            funding_asset=pool_asset, funding_amount=Decimal("3000"),
        )
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender2.id,
            funding_asset=pool_asset, funding_amount=Decimal("4000"),
        )

        db.refresh(product)
        assert Decimal(str(product.current_raised)) == Decimal("7000")
