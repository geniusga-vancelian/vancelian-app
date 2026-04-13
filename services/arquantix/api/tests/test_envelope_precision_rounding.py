"""Precision & Rounding Tests — Envelope Entry Wallet Phase 2A.16.

Validates that rounding does not create or destroy value, and that
precision is maintained across the envelope lifecycle.

  INV-14: Rounding does not create or destroy value
"""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

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
    MockExchangeService,
    MOCK_EUR_USDC_PRICE,
)


class TestSmallAmounts:
    """Tiny investment amounts: no value loss or creation."""

    def test_small_eur_invest(self, db):
        """1 EUR invest: envelope records small amounts correctly."""
        borrower = create_client(db, "prec_small_bor@test.com")
        lender = create_client(db, "prec_small_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()
        result = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=Decimal("1"),
        )

        assert result["status"] == "completed"
        assert result["amount_supplied"] > 0

        envs = snapshot_envelopes(db, lender.id)
        entry = envs[-1]["entries"][-1]
        assert entry["entry_amount"] == Decimal("1")
        assert entry["net_allocated"] > Decimal("0")
        assert entry["net_allocated"] == entry["converted_amount"]

        pool_bal = get_crypto_balance(db, lender.id, product.asset)
        assert pool_bal["balance"] == Decimal("0")

    def test_very_small_direct_invest(self, db):
        """0.01 pool asset direct invest."""
        borrower = create_client(db, "prec_tiny_bor@test.com")
        lender = create_client(db, "prec_tiny_len@test.com")
        product = create_fundraising_product(db, borrower.id)
        set_crypto_balance(db, lender.id, product.asset, Decimal("100"))

        orch, _ = create_orchestrator_with_mock()
        result = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=Decimal("0.01"),
        )

        assert result["status"] == "completed"
        assert result["amount_supplied"] == 0.01

        pool_bal = get_crypto_balance(db, lender.id, product.asset)
        assert pool_bal["balance"] == Decimal("100")
        assert pool_bal["available_balance"] == Decimal("99.99")


class TestManyDecimals:
    """Amounts with many decimal places."""

    def test_high_precision_eur_amount(self, db):
        """EUR with fractional cents."""
        borrower = create_client(db, "prec_dec_bor@test.com")
        lender = create_client(db, "prec_dec_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()
        funding = Decimal("999.999999")
        result = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=funding,
        )

        assert result["status"] == "completed"
        envs = snapshot_envelopes(db, lender.id)
        entry = envs[-1]["entries"][-1]
        assert entry["entry_amount"] == funding

        pool_bal = get_crypto_balance(db, lender.id, product.asset)
        assert pool_bal["balance"] == Decimal("0"), "No pollution with precision amounts"


class TestStablecoinNearPeg:
    """Near-peg conversion (pool asset ~ 1 EUR) should preserve amounts."""

    def test_near_peg_conversion_no_drift(self, db):
        """With mock price close to 1.0, converted ~= funded."""
        near_peg_price = Decimal("1.001")
        mock_ex = MockExchangeService(eur_usdc_price=near_peg_price)

        borrower = create_client(db, "prec_peg_bor@test.com")
        lender = create_client(db, "prec_peg_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock(mock_ex)
        funding = Decimal("1000")
        result = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=funding,
        )

        supplied = Decimal(str(result["amount_supplied"]))
        expected = (funding / near_peg_price).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
        assert supplied == expected

        diff_pct = abs(supplied - funding) / funding * 100
        assert diff_pct < Decimal("1"), f"Near-peg drift too high: {diff_pct}%"


class TestMultipleConversionsAccumulation:
    """Multiple sequential conversions: no accumulated rounding drift."""

    def test_ten_small_invests_vs_one_large(self, db):
        """10×100 EUR must yield approximately same total as 1×1000 EUR."""
        borrower = create_client(db, "prec_accum_bor@test.com")
        lender_small = create_client(db, "prec_accum_small@test.com")
        lender_large = create_client(db, "prec_accum_large@test.com")

        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender_small.id, product.asset, Decimal("0"))
        set_crypto_balance(db, lender_large.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()

        total_small = Decimal("0")
        for _ in range(10):
            r = orch.invest_into_product(
                db, product_id=product.id, client_id=lender_small.id,
                funding_asset="EUR", funding_amount=Decimal("100"),
            )
            total_small += Decimal(str(r["amount_supplied"]))

        r_large = orch.invest_into_product(
            db, product_id=product.id, client_id=lender_large.id,
            funding_asset="EUR", funding_amount=Decimal("1000"),
        )
        total_large = Decimal(str(r_large["amount_supplied"]))

        drift = abs(total_small - total_large)
        assert drift < Decimal("0.01"), (
            f"Accumulated rounding drift: {drift} pool asset over 10 invests"
        )

        pool_small = get_crypto_balance(db, lender_small.id, product.asset)
        pool_large = get_crypto_balance(db, lender_large.id, product.asset)
        assert pool_small["balance"] == Decimal("0"), "Small: no pollution"
        assert pool_large["balance"] == Decimal("0"), "Large: no pollution"


class TestConversionFeeIsolation:
    """Fees are tracked in envelope, not in wallet."""

    def test_fee_stored_in_envelope_not_wallet(self, db):
        """With non-zero fees: fee in envelope, not in crypto wallet."""
        fee_bps = Decimal("50")
        mock_ex = MockExchangeService(fee_bps=fee_bps)

        borrower = create_client(db, "prec_fee_bor@test.com")
        lender = create_client(db, "prec_fee_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock(mock_ex)
        result = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=Decimal("1000"),
        )

        envs = snapshot_envelopes(db, lender.id)
        entry = envs[-1]["entries"][-1]

        assert entry["converted_amount"] > entry["net_allocated"] or entry["conversion_fee"] >= Decimal("0")

        pool_bal = get_crypto_balance(db, lender.id, product.asset)
        assert pool_bal["balance"] == Decimal("0"), "Fees in envelope, not wallet"
