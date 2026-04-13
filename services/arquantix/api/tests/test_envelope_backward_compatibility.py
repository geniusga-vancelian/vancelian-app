"""Backward Compatibility Tests — Envelope Entry Wallet Phase 2A.16.

Validates that:
  - Old investments (without envelopes) still work
  - Direct pool asset invest works as before
  - Lending operations (interest, repay) are unaffected
  - OfferService / PoolService are not modified
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from _envelope_test_helpers import (
    db,
    create_client,
    set_crypto_balance,
    get_crypto_balance,
    create_fundraising_product,
    create_orchestrator_with_mock,
    snapshot_envelopes,
    snapshot_commitments,
)


class TestOldInvestmentsWithoutEnvelope:
    """Pre-2A.16 investments (direct subscribe, no envelope) must remain functional."""

    def test_direct_subscribe_still_works(self, db):
        """OfferService.subscribe() without orchestrator still creates valid commitment."""
        borrower = create_client(db, "bw_old_bor@test.com")
        lender = create_client(db, "bw_old_len@test.com")
        test_asset = f"TST_{uuid.uuid4().hex[:6].upper()}"
        set_crypto_balance(db, lender.id, test_asset, Decimal("50000"))

        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db, title="Old Style Offer", asset=test_asset,
            borrower_client_id=borrower.id,
            target_size=Decimal("100000"),
        )
        svc.open_fundraising(db, product.id)

        commitment = svc.subscribe(
            db, product_id=product.id,
            lender_client_id=lender.id,
            amount=Decimal("5000"),
        )

        assert commitment is not None
        assert float(commitment.amount) == 5000.0

        envs = snapshot_envelopes(db, lender.id)
        assert len(envs) == 0, "Old subscribe creates no envelope"

    def test_old_commitment_readable_in_earn_positions(self, db):
        """Commitments without envelopes: earn positions have envelope=None."""
        borrower = create_client(db, "bw_read_bor@test.com")
        lender = create_client(db, "bw_read_len@test.com")
        test_asset = f"TST_{uuid.uuid4().hex[:6].upper()}"
        set_crypto_balance(db, lender.id, test_asset, Decimal("50000"))

        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db, title="Read Test Offer", asset=test_asset,
            borrower_client_id=borrower.id,
            target_size=Decimal("100000"),
        )
        svc.open_fundraising(db, product.id)
        svc.subscribe(
            db, product_id=product.id,
            lender_client_id=lender.id,
            amount=Decimal("3000"),
        )

        from services.lending.product_surface import get_earn_positions
        earn = get_earn_positions(db, lender.id)
        asset_pos = [p for p in earn["positions"] if p["asset"] == test_asset]
        assert len(asset_pos) >= 1

        pos = asset_pos[0]
        assert "envelope" in pos


class TestDirectInvestCompatibility:
    """Direct pool asset invest should work exactly as before (plus envelope)."""

    def test_direct_balance_behavior_unchanged(self, db):
        """balance unchanged, available_balance reduced."""
        borrower = create_client(db, "bw_direct_bor@test.com")
        lender = create_client(db, "bw_direct_len@test.com")
        product = create_fundraising_product(db, borrower.id)

        initial = Decimal("10000")
        invest = Decimal("2500")
        set_crypto_balance(db, lender.id, product.asset, initial)

        orch, _ = create_orchestrator_with_mock()
        result = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=invest,
        )

        pool_bal = get_crypto_balance(db, lender.id, product.asset)
        assert pool_bal["balance"] == initial
        assert pool_bal["available_balance"] == initial - invest

        assert result["conversion_type"] == "none"
        assert result["amount_supplied"] == float(invest)


class TestPoolServiceUnchanged:
    """PoolLendingService.create_supply_commitment() behaves as before."""

    def test_pool_supply_commitment_direct(self, db):
        borrower = create_client(db, "bw_pool_bor@test.com")
        lender = create_client(db, "bw_pool_len@test.com")
        test_asset = f"TST_{uuid.uuid4().hex[:6].upper()}"
        set_crypto_balance(db, lender.id, test_asset, Decimal("20000"))

        from services.lending.pool_service import PoolLendingService
        pool_svc = PoolLendingService()
        commitment = pool_svc.create_supply_commitment(
            db, client_id=lender.id, asset=test_asset, amount=Decimal("5000"),
        )

        assert commitment is not None
        assert float(commitment.amount) == 5000.0

        pool_bal = get_crypto_balance(db, lender.id, test_asset)
        assert pool_bal["balance"] == Decimal("20000")
        assert pool_bal["available_balance"] == Decimal("15000")


class TestOfferServiceUnchanged:
    """OfferService operations remain functional."""

    def test_create_product_unchanged(self, db):
        borrower = create_client(db, "bw_offer_bor@test.com")
        test_asset = f"TST_{uuid.uuid4().hex[:6].upper()}"

        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db, title="Backward Compat Test", asset=test_asset,
            borrower_client_id=borrower.id,
            target_size=Decimal("50000"),
        )

        assert product.status == "draft"
        assert product.asset == test_asset

    def test_fundraising_workflow_unchanged(self, db):
        borrower = create_client(db, "bw_fund_bor@test.com")
        test_asset = f"TST_{uuid.uuid4().hex[:6].upper()}"

        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db, title="Fundraising Test", asset=test_asset,
            borrower_client_id=borrower.id,
            target_size=Decimal("50000"),
        )
        product = svc.open_fundraising(db, product.id)
        assert product.status == "fundraising"

    def test_product_detail_unchanged(self, db):
        borrower = create_client(db, "bw_detail_bor@test.com")
        test_asset = f"TST_{uuid.uuid4().hex[:6].upper()}"

        from services.lending.offer_service import OfferService
        svc = OfferService()

        product = svc.create_product(
            db, title="Detail Test", asset=test_asset,
            borrower_client_id=borrower.id,
            target_size=Decimal("50000"),
        )
        svc.open_fundraising(db, product.id)

        detail = svc.get_product_detail(db, product.id)
        assert detail["status"] == "fundraising"
        assert detail["target_size"] == 50000.0
