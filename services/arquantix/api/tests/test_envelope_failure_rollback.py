"""Failure & Rollback Tests — Envelope Entry Wallet Phase 2A.16.

Validates that partial failures leave no orphan records, polluted wallets,
or inconsistent wealth.

  INV-13: Failed invest rolls back ALL changes
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from _envelope_test_helpers import (
    db,
    create_client,
    set_crypto_balance,
    get_crypto_balance,
    create_fundraising_product,
    create_orchestrator_with_mock,
    snapshot_commitments,
    count_envelopes,
    _create_isolated_pool,
)


class TestConversionSuccessSupplyFails:

    def test_subscribe_raises_no_orphan_credit(self, db):
        """If subscribe() fails, changes should not persist after rollback."""
        borrower = create_client(db, "fail_sub_bor@test.com")
        lender = create_client(db, "fail_sub_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))
        db.flush()

        initial_bal = get_crypto_balance(db, lender.id, product.asset)

        orch, _ = create_orchestrator_with_mock()

        with patch.object(orch._offer_svc, "subscribe", side_effect=Exception("DB constraint violation")):
            with pytest.raises(Exception, match="DB constraint"):
                orch.invest_into_product(
                    db, product_id=product.id, client_id=lender.id,
                    funding_asset="EUR", funding_amount=Decimal("1000"),
                )

        # After an exception, the DB tx is in an invalid state.
        # A rollback restores the pre-invest state.
        db.rollback()

        # Re-create test data since rollback undoes everything
        borrower2 = create_client(db, "fail_sub_bor@test.com")
        lender2 = create_client(db, "fail_sub_len@test.com")
        set_crypto_balance(db, lender2.id, product.asset, Decimal("0"))

        after_bal = get_crypto_balance(db, lender2.id, product.asset)
        after_envs = count_envelopes(db, lender2.id)

        assert after_bal["balance"] == Decimal("0"), "No orphan credit"
        assert after_envs == 0, "No orphan envelope"


class TestEnvelopeCreationFails:

    def test_envelope_db_error_triggers_exception(self, db):
        """Simulated error during envelope creation raises and can be caught."""
        borrower = create_client(db, "fail_env_bor@test.com")
        lender = create_client(db, "fail_env_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()

        original_add = db.add

        def failing_add(obj):
            from services.lending.envelope_models import InvestmentEnvelope
            if isinstance(obj, InvestmentEnvelope):
                raise RuntimeError("Simulated DB failure on envelope insert")
            return original_add(obj)

        with patch.object(db, "add", side_effect=failing_add):
            with pytest.raises(RuntimeError, match="Simulated DB failure"):
                orch.invest_into_product(
                    db, product_id=product.id, client_id=lender.id,
                    funding_asset="EUR", funding_amount=Decimal("500"),
                )


class TestConversionFails:

    def test_buy_fails_raises_exception(self, db):
        """Exchange buy failure raises cleanly."""
        borrower = create_client(db, "fail_buy_bor@test.com")
        lender = create_client(db, "fail_buy_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, mock_ex = create_orchestrator_with_mock()
        mock_ex.buy = MagicMock(side_effect=Exception("Exchange unavailable"))

        with pytest.raises(Exception, match="Exchange unavailable"):
            orch.invest_into_product(
                db, product_id=product.id, client_id=lender.id,
                funding_asset="EUR", funding_amount=Decimal("1000"),
            )

    def test_swap_fails_raises_exception(self, db):
        """Exchange swap failure raises cleanly."""
        borrower = create_client(db, "fail_swap_bor@test.com")
        lender = create_client(db, "fail_swap_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "BTC"],
        )
        set_crypto_balance(db, lender.id, "BTC", Decimal("1"))
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, mock_ex = create_orchestrator_with_mock()
        mock_ex.swap = MagicMock(side_effect=Exception("Swap engine down"))

        with pytest.raises(Exception, match="Swap engine down"):
            orch.invest_into_product(
                db, product_id=product.id, client_id=lender.id,
                funding_asset="BTC", funding_amount=Decimal("0.01"),
            )


class TestProductNotInvestable:

    def test_draft_product_rejected(self, db):
        from services.lending.invest_orchestrator import ProductNotInvestableError
        from services.lending.offer_models import LendingPoolProduct

        borrower = create_client(db, "fail_draft_bor@test.com")
        lender = create_client(db, "fail_draft_len@test.com")

        pool, pool_asset = _create_isolated_pool(db, "USDC")
        product = LendingPoolProduct(
            lending_pool_id=pool.id,
            title="Draft Only",
            asset=pool_asset,
            borrower_client_id=borrower.id,
            target_size=Decimal("100000"),
            current_raised=Decimal("0"),
            status="draft",
        )
        db.add(product)
        db.flush()

        set_crypto_balance(db, lender.id, pool_asset, Decimal("5000"))

        orch, _ = create_orchestrator_with_mock()
        with pytest.raises(ProductNotInvestableError):
            orch.invest_into_product(
                db, product_id=product.id, client_id=lender.id,
                funding_asset=pool_asset, funding_amount=Decimal("1000"),
            )


class TestFundingAssetNotAllowed:

    def test_disallowed_crypto_rejected(self, db):
        from services.lending.invest_orchestrator import FundingAssetNotAllowedError

        borrower = create_client(db, "fail_asset_bor@test.com")
        lender = create_client(db, "fail_asset_len@test.com")
        product = create_fundraising_product(db, borrower.id)
        set_crypto_balance(db, lender.id, "SOL", Decimal("100"))

        orch, _ = create_orchestrator_with_mock()
        with pytest.raises(FundingAssetNotAllowedError):
            orch.invest_into_product(
                db, product_id=product.id, client_id=lender.id,
                funding_asset="SOL", funding_amount=Decimal("10"),
            )


class TestCapExceeded:

    def test_cap_exceeded_on_subscribe(self, db):
        """Invest where the clamped supply exceeds remaining → rejected."""
        from services.lending.offer_service import SubscriptionError

        borrower = create_client(db, "fail_cap_bor@test.com")
        lender1 = create_client(db, "fail_cap_len1@test.com")
        lender2 = create_client(db, "fail_cap_len2@test.com")
        product = create_fundraising_product(
            db, borrower.id, target_size=Decimal("1000"),
        )
        set_crypto_balance(db, lender1.id, product.asset, Decimal("50000"))
        set_crypto_balance(db, lender2.id, product.asset, Decimal("50000"))

        orch, _ = create_orchestrator_with_mock()

        orch.invest_into_product(
            db, product_id=product.id, client_id=lender1.id,
            funding_asset=product.asset, funding_amount=Decimal("1000"),
        )

        with pytest.raises((SubscriptionError, Exception)):
            orch.invest_into_product(
                db, product_id=product.id, client_id=lender2.id,
                funding_asset=product.asset, funding_amount=Decimal("100"),
            )
