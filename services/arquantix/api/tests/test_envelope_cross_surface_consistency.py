"""Cross-Surface Consistency Tests — Envelope Entry Wallet Phase 2A.16.

After an investment, verifies coherence across all client-facing surfaces:
  - crypto_positions (free balance only)
  - earn positions (committed + envelope data)
  - commitments

  INV-04: No artificial value creation
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
    snapshot_crypto,
    snapshot_envelopes,
    snapshot_commitments,
)


class TestCryptoVsPlacementsPostInvest:
    """After invest, Crypto and Placements must show complementary data."""

    def test_eur_invest_crypto_zero_placements_positive(self, db):
        """EUR invest: Crypto free pool asset = 0, Placements committed > 0."""
        borrower = create_client(db, "cs_eur_bor@test.com")
        lender = create_client(db, "cs_eur_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()
        result = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=Decimal("1000"),
        )

        pool_bal = get_crypto_balance(db, lender.id, product.asset)
        assert pool_bal["balance"] == Decimal("0"), "Crypto: no free pool asset"
        assert pool_bal["available_balance"] <= Decimal("0"), "Crypto: nothing available"

        comms = snapshot_commitments(db, lender.id)
        total_committed = sum(c["amount"] for c in comms)
        assert total_committed > Decimal("0"), "Placements: committed amount > 0"
        assert float(total_committed) == result["amount_supplied"]

    def test_direct_invest_available_reduced(self, db):
        """Direct pool asset: balance unchanged, available reduced, commitment matches."""
        borrower = create_client(db, "cs_direct_bor@test.com")
        lender = create_client(db, "cs_direct_len@test.com")
        product = create_fundraising_product(db, borrower.id)

        initial = Decimal("5000")
        invest = Decimal("2000")
        set_crypto_balance(db, lender.id, product.asset, initial)

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=invest,
        )

        pool_bal = get_crypto_balance(db, lender.id, product.asset)
        assert pool_bal["balance"] == initial
        assert pool_bal["available_balance"] == initial - invest

        comms = snapshot_commitments(db, lender.id)
        assert len(comms) == 1
        assert comms[0]["amount"] == invest


class TestEnvelopeMatchesCommitment:
    """Envelope data must match commitment data exactly."""

    def test_envelope_commitment_amount_match(self, db):
        borrower = create_client(db, "cs_match_bor@test.com")
        lender = create_client(db, "cs_match_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=Decimal("3000"),
        )

        envs = snapshot_envelopes(db, lender.id)
        comms = snapshot_commitments(db, lender.id)

        entry = envs[-1]["entries"][-1]
        comm = [c for c in comms if c["id"] == entry["commitment_id"]][0]

        assert entry["net_allocated"] == comm["amount"], (
            f"Envelope net_allocated ({entry['net_allocated']}) != "
            f"commitment amount ({comm['amount']})"
        )

    def test_multiple_invests_all_match(self, db):
        borrower = create_client(db, "cs_multi_bor@test.com")
        lender = create_client(db, "cs_multi_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("100000"))

        orch, _ = create_orchestrator_with_mock()

        for amount in [Decimal("500"), Decimal("1000"), Decimal("2000")]:
            orch.invest_into_product(
                db, product_id=product.id, client_id=lender.id,
                funding_asset=product.asset, funding_amount=amount,
            )

        envs = snapshot_envelopes(db, lender.id)
        comms = snapshot_commitments(db, lender.id)
        comm_map = {c["id"]: c for c in comms}

        for env in envs:
            for entry in env["entries"]:
                comm = comm_map[entry["commitment_id"]]
                assert entry["net_allocated"] == comm["amount"]


class TestTotalWealthConservation:
    """Total tracked value must not increase post-invest."""

    def test_eur_invest_total_wealth_conservation(self, db):
        """
        Before: 5000 pool asset free
        After EUR invest: 5000 pool asset free + committed pool asset from conversion
        Total should not exceed initial + new funding equivalent.
        """
        borrower = create_client(db, "cs_wealth_bor@test.com")
        lender = create_client(db, "cs_wealth_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )

        initial = Decimal("5000")
        set_crypto_balance(db, lender.id, product.asset, initial)

        orch, _ = create_orchestrator_with_mock()
        result = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=Decimal("1000"),
        )

        pool_bal = get_crypto_balance(db, lender.id, product.asset)
        comms = snapshot_commitments(db, lender.id)

        free_pool = pool_bal["balance"]
        committed_pool = sum(c["amount"] for c in comms)
        total_pool = free_pool + committed_pool

        assert total_pool == initial + Decimal(str(result["amount_supplied"]))


class TestEarnPositionsIncludeEnvelopeData:
    """Earn positions surface must include envelope data when available."""

    def test_earn_positions_have_envelope_field(self, db):
        borrower = create_client(db, "cs_earn_bor@test.com")
        lender = create_client(db, "cs_earn_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=Decimal("1500"),
        )

        from services.lending.product_surface import get_earn_positions
        earn = get_earn_positions(db, lender.id)

        pool_pos = [p for p in earn["positions"] if p["asset"] == product.asset]
        assert len(pool_pos) >= 1

        pos = pool_pos[0]
        assert "envelope" in pos
        if pos["envelope"] is not None:
            assert pos["envelope"]["entry_asset"] == "EUR"
            assert pos["envelope"]["entry_amount"] == 1500.0
            assert pos["envelope"]["conversion_type"] == "buy"
