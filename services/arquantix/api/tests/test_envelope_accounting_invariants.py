"""Accounting Invariants Tests — Envelope Entry Wallet Phase 2A.16.

Validates that for each conversion path (EUR→pool, BTC→pool, direct),
the accounting identities hold:

  INV-01: After conversion invest, crypto_positions.balance net change = 0
  INV-02: available_balance correctly reflects committed funds
  INV-03: Envelope net_allocated = commitment amount
  INV-04: No artificial value creation
  INV-05: Envelope debit ONLY on conversion, NOT direct
  INV-06: Direct invest: balance unchanged, available reduced
  INV-07: Envelope entry_amount matches funding amount
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
    snapshot_envelopes,
    snapshot_commitments,
    MOCK_EUR_USDC_PRICE,
)


class TestEurToPoolAccounting:
    """A. EUR → pool_asset → Exclusive Offer"""

    def test_balance_net_change_zero_after_eur_invest(self, db):
        """INV-01: crypto_positions.balance for pool_asset must not change."""
        borrower = create_client(db, "acct_eur_bor@test.com")
        lender = create_client(db, "acct_eur_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        pool_asset = product.asset

        initial = Decimal("200")
        set_crypto_balance(db, lender.id, pool_asset, initial)

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=Decimal("1000"),
        )

        after = get_crypto_balance(db, lender.id, pool_asset)
        assert after["balance"] == initial, (
            f"Balance should return to initial after envelope debit: "
            f"expected {initial}, got {after['balance']}"
        )

    def test_available_balance_returns_to_initial_on_conversion(self, db):
        """INV-02: For conversion invest, available_balance returns to initial
        because buy credits and supply debits the same amount."""
        borrower = create_client(db, "acct_eur_avail_bor@test.com")
        lender = create_client(db, "acct_eur_avail_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        pool_asset = product.asset
        initial = Decimal("500")
        set_crypto_balance(db, lender.id, pool_asset, initial)

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=Decimal("500"),
        )

        after = get_crypto_balance(db, lender.id, pool_asset)
        assert after["available_balance"] == initial, (
            "EUR conversion: buy credits + supply debits cancel out on available"
        )

    def test_envelope_net_allocated_equals_commitment(self, db):
        """INV-03: envelope.net_allocated = commitment.amount"""
        borrower = create_client(db, "acct_eur_net_bor@test.com")
        lender = create_client(db, "acct_eur_net_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("100"))

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=Decimal("1000"),
        )

        envs = snapshot_envelopes(db, lender.id)
        comms = snapshot_commitments(db, lender.id)
        assert len(envs) >= 1
        entry = envs[-1]["entries"][-1]
        comm = [c for c in comms if c["id"] == entry["commitment_id"]][0]
        assert entry["net_allocated"] == comm["amount"]

    def test_entry_amount_matches_funding(self, db):
        """INV-07: envelope.entry_amount = original funding amount."""
        borrower = create_client(db, "acct_eur_ea_bor@test.com")
        lender = create_client(db, "acct_eur_ea_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()
        funding = Decimal("2500")
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=funding,
        )

        envs = snapshot_envelopes(db, lender.id)
        entry = envs[-1]["entries"][-1]
        assert entry["entry_amount"] == funding
        assert entry["entry_asset"] == "EUR"

    def test_no_artificial_value_creation(self, db):
        """INV-04: total tracked value does not exceed funding amount."""
        borrower = create_client(db, "acct_eur_val_bor@test.com")
        lender = create_client(db, "acct_eur_val_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()
        funding = Decimal("1000")
        result = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=funding,
        )

        pool_received = Decimal(str(result["total_pool_asset_received"]))
        eur_equivalent = pool_received * MOCK_EUR_USDC_PRICE
        assert eur_equivalent <= funding + Decimal("1"), (
            f"Value created: {eur_equivalent} EUR equivalent > {funding} EUR funded"
        )


class TestBtcToPoolAccounting:
    """B. BTC → pool_asset → Exclusive Offer"""

    def test_btc_balance_debited(self, db):
        """Source wallet (BTC) must be debited."""
        borrower = create_client(db, "acct_btc_bor@test.com")
        lender = create_client(db, "acct_btc_len@test.com")

        initial_btc = Decimal("0.1")
        invest_btc = Decimal("0.01")
        set_crypto_balance(db, lender.id, "BTC", initial_btc)
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "BTC"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="BTC", funding_amount=invest_btc,
        )

        btc_after = get_crypto_balance(db, lender.id, "BTC")
        assert btc_after["balance"] == initial_btc - invest_btc

    def test_pool_asset_balance_neutralized_after_swap(self, db):
        """INV-01: pool_asset balance net change = 0 after BTC swap."""
        borrower = create_client(db, "acct_btc_neut_bor@test.com")
        lender = create_client(db, "acct_btc_neut_len@test.com")

        set_crypto_balance(db, lender.id, "BTC", Decimal("1"))
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "BTC"],
        )
        initial_pool = Decimal("50")
        set_crypto_balance(db, lender.id, product.asset, initial_pool)

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="BTC", funding_amount=Decimal("0.001"),
        )

        pool_after = get_crypto_balance(db, lender.id, product.asset)
        assert pool_after["balance"] == initial_pool

    def test_envelope_records_swap_conversion(self, db):
        borrower = create_client(db, "acct_btc_conv_bor@test.com")
        lender = create_client(db, "acct_btc_conv_len@test.com")
        set_crypto_balance(db, lender.id, "BTC", Decimal("1"))
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "BTC"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="BTC", funding_amount=Decimal("0.001"),
        )

        envs = snapshot_envelopes(db, lender.id)
        entry = envs[-1]["entries"][-1]
        assert entry["conversion_type"] == "swap"
        assert entry["entry_asset"] == "BTC"
        assert entry["target_asset"] == product.asset


class TestDirectPoolAssetAccounting:
    """C. pool_asset → pool_asset → Exclusive Offer (no conversion)"""

    def test_no_envelope_debit_on_direct(self, db):
        """INV-05: no balance debit when funding_asset == pool_asset."""
        borrower = create_client(db, "acct_direct_bor@test.com")
        lender = create_client(db, "acct_direct_len@test.com")
        product = create_fundraising_product(db, borrower.id)
        pool_asset = product.asset

        initial = Decimal("5000")
        invest = Decimal("1000")
        set_crypto_balance(db, lender.id, pool_asset, initial)

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=pool_asset, funding_amount=invest,
        )

        after = get_crypto_balance(db, lender.id, pool_asset)
        assert after["balance"] == initial, (
            "Direct invest: balance should stay unchanged (no envelope debit)"
        )
        assert after["available_balance"] == initial - invest

    def test_direct_invest_creates_envelope(self, db):
        borrower = create_client(db, "acct_direct_env_bor@test.com")
        lender = create_client(db, "acct_direct_env_len@test.com")
        product = create_fundraising_product(db, borrower.id)
        set_crypto_balance(db, lender.id, product.asset, Decimal("5000"))

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=Decimal("1000"),
        )

        envs = snapshot_envelopes(db, lender.id)
        assert len(envs) >= 1
        entry = envs[-1]["entries"][-1]
        assert entry["conversion_type"] == "none"
        assert entry["entry_amount"] == Decimal("1000")
        assert entry["net_allocated"] == Decimal("1000")

    def test_available_balance_reduced_on_direct(self, db):
        """INV-06: direct invest reduces available_balance by invest amount."""
        borrower = create_client(db, "acct_direct_avail_bor@test.com")
        lender = create_client(db, "acct_direct_avail_len@test.com")
        product = create_fundraising_product(db, borrower.id)
        pool_asset = product.asset

        initial = Decimal("3000")
        invest = Decimal("750")
        set_crypto_balance(db, lender.id, pool_asset, initial)

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=pool_asset, funding_amount=invest,
        )

        after = get_crypto_balance(db, lender.id, pool_asset)
        assert after["balance"] == initial
        assert after["available_balance"] == initial - invest


class TestMultipleInvests:
    """Multiple sequential investments maintain accounting consistency."""

    def test_two_eur_invests_balance_stays_consistent(self, db):
        borrower = create_client(db, "acct_multi_bor@test.com")
        lender = create_client(db, "acct_multi_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()

        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=Decimal("500"),
        )
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=Decimal("300"),
        )

        after = get_crypto_balance(db, lender.id, product.asset)
        assert after["balance"] == Decimal("0"), (
            "Two EUR invests: pool_asset balance must remain 0"
        )

        envs = snapshot_envelopes(db, lender.id)
        assert len(envs) == 2

    def test_mixed_conversion_and_direct(self, db):
        borrower = create_client(db, "acct_mixed_bor@test.com")
        lender = create_client(db, "acct_mixed_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        pool_asset = product.asset
        initial = Decimal("2000")
        set_crypto_balance(db, lender.id, pool_asset, initial)

        orch, _ = create_orchestrator_with_mock()

        r1 = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=Decimal("1000"),
        )
        r2 = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=pool_asset, funding_amount=Decimal("500"),
        )

        after = get_crypto_balance(db, lender.id, pool_asset)
        assert after["balance"] == initial, (
            "EUR invest neutralized + direct: balance = initial"
        )
        # EUR conversion: available returns to initial (buy credits + supply debits cancel)
        # Direct: available reduced by 500
        expected_avail = initial - Decimal("500")
        assert after["available_balance"] == expected_avail
