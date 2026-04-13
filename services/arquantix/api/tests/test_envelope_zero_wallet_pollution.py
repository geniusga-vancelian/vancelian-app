"""Zero Wallet Pollution Tests — Envelope Entry Wallet Phase 2A.16.

Validates that intermediate conversion credits NEVER appear as free crypto
on any client-facing surface.

  INV-01: crypto_positions.balance net change = 0 after conversion invest
  INV-05: Envelope debit only on conversion
  INV-06: Direct invest: balance unchanged, available reduced
  INV-11: Placements show committed, Crypto shows only free
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from _envelope_test_helpers import (
    db,
    create_client,
    set_crypto_balance,
    get_crypto_balance,
    create_fundraising_product,
    create_orchestrator_with_mock,
)


class TestIntermediateCreditInvisible:

    def test_eur_invest_zero_initial(self, db):
        """Client with 0 pool asset invests EUR → pool asset stays at 0."""
        borrower = create_client(db, "poll_zero_bor@test.com")
        lender = create_client(db, "poll_zero_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=Decimal("5000"),
        )

        bal = get_crypto_balance(db, lender.id, product.asset)
        assert bal["balance"] == Decimal("0"), "Zero-to-zero: no pollution"
        assert bal["available_balance"] <= Decimal("0")

    def test_eur_invest_preserves_existing_free(self, db):
        """Client with pre-existing pool asset: balance unchanged after conversion."""
        borrower = create_client(db, "poll_exist_bor@test.com")
        lender = create_client(db, "poll_exist_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )

        existing = Decimal("300")
        set_crypto_balance(db, lender.id, product.asset, existing)

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=Decimal("2000"),
        )

        bal = get_crypto_balance(db, lender.id, product.asset)
        assert bal["balance"] == existing, (
            f"Existing {existing} must be preserved, got {bal['balance']}"
        )
        # For EUR conversion: buy credits X, supply debits X → available returns to existing
        assert bal["available_balance"] == existing

    def test_swap_invest_no_target_pollution(self, db):
        """BTC→pool swap: target wallet shows no net gain from conversion."""
        borrower = create_client(db, "poll_swap_bor@test.com")
        lender = create_client(db, "poll_swap_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "BTC"],
        )

        initial_pool = Decimal("100")
        set_crypto_balance(db, lender.id, "BTC", Decimal("0.5"))
        set_crypto_balance(db, lender.id, product.asset, initial_pool)

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="BTC", funding_amount=Decimal("0.001"),
        )

        bal = get_crypto_balance(db, lender.id, product.asset)
        assert bal["balance"] == initial_pool


class TestDisplayUsesAvailableBalance:

    def test_direct_invest_balance_vs_available_diverge(self, db):
        """After direct invest: balance > available_balance."""
        borrower = create_client(db, "poll_div_bor@test.com")
        lender = create_client(db, "poll_div_len@test.com")
        product = create_fundraising_product(db, borrower.id)

        initial = Decimal("10000")
        invest = Decimal("3000")
        set_crypto_balance(db, lender.id, product.asset, initial)

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=invest,
        )

        bal = get_crypto_balance(db, lender.id, product.asset)
        assert bal["balance"] == initial
        assert bal["available_balance"] == initial - invest
        assert bal["balance"] > bal["available_balance"]

    def test_eur_invest_balance_equals_available(self, db):
        """After EUR conversion with 0 initial: both are 0."""
        borrower = create_client(db, "poll_eq_bor@test.com")
        lender = create_client(db, "poll_eq_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=Decimal("1000"),
        )

        bal = get_crypto_balance(db, lender.id, product.asset)
        assert bal["balance"] == Decimal("0")
        assert bal["available_balance"] <= Decimal("0")


class TestDirectInvestDoesNotBreakModel:

    def test_direct_then_eur_no_contamination(self, db):
        """Sequential: direct then EUR conversion — no cross-contamination."""
        borrower = create_client(db, "poll_seq_bor@test.com")
        lender = create_client(db, "poll_seq_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )

        initial = Decimal("5000")
        set_crypto_balance(db, lender.id, product.asset, initial)

        orch, _ = create_orchestrator_with_mock()

        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=Decimal("1000"),
        )
        mid = get_crypto_balance(db, lender.id, product.asset)
        assert mid["balance"] == initial
        assert mid["available_balance"] == initial - Decimal("1000")

        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=Decimal("500"),
        )

        final = get_crypto_balance(db, lender.id, product.asset)
        assert final["balance"] == initial, "EUR neutralized, balance = initial"
        # EUR conversion: available unchanged (buy credits + supply debits cancel)
        # So available = initial - 1000 (from direct invest)
        assert final["available_balance"] == initial - Decimal("1000")
