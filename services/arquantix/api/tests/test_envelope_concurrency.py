"""Concurrency Tests — Envelope Entry Wallet Phase 2A.16.

Validates behavior under concurrent or repeated investment attempts.

  INV-12: No duplicate commitments from concurrent invests
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from _envelope_test_helpers import (
    db,
    create_client,
    set_crypto_balance,
    create_fundraising_product,
    create_orchestrator_with_mock,
    snapshot_envelopes,
    snapshot_commitments,
    count_envelopes,
)


class TestDoubleTapSameClient:
    """Same client taps Invest twice rapidly."""

    def test_two_sequential_invests_create_two_envelopes(self, db):
        """Each tap should create its own envelope + commitment."""
        borrower = create_client(db, "conc_double_bor@test.com")
        lender = create_client(db, "conc_double_len@test.com")
        product = create_fundraising_product(db, borrower.id)
        set_crypto_balance(db, lender.id, product.asset, Decimal("100000"))

        orch, _ = create_orchestrator_with_mock()

        r1 = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=Decimal("1000"),
        )
        r2 = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=Decimal("1000"),
        )

        assert r1["commitment_id"] != r2["commitment_id"]
        assert r1["envelope_id"] != r2["envelope_id"]

        envs = snapshot_envelopes(db, lender.id)
        assert len(envs) == 2

        comms = snapshot_commitments(db, lender.id)
        assert len(comms) == 2

    def test_two_invests_raised_amount_correct(self, db):
        """current_raised reflects both investments."""
        borrower = create_client(db, "conc_raised_bor@test.com")
        lender = create_client(db, "conc_raised_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, target_size=Decimal("50000"),
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("100000"))

        orch, _ = create_orchestrator_with_mock()

        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=Decimal("5000"),
        )
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=Decimal("3000"),
        )

        from services.lending.offer_service import OfferService
        svc = OfferService()
        detail = svc.get_product_detail(db, product.id)
        assert detail["current_raised"] == 8000.0


class TestCapRace:
    """Two investors compete for the last slot in a nearly-full product."""

    def test_second_invest_after_full_is_rejected(self, db):
        """After first fills the cap, second invest is rejected (status or cap)."""
        borrower = create_client(db, "conc_cap_bor@test.com")
        lender1 = create_client(db, "conc_cap_len1@test.com")
        lender2 = create_client(db, "conc_cap_len2@test.com")
        product = create_fundraising_product(
            db, borrower.id, target_size=Decimal("5000"),
        )
        set_crypto_balance(db, lender1.id, product.asset, Decimal("50000"))
        set_crypto_balance(db, lender2.id, product.asset, Decimal("50000"))

        orch, _ = create_orchestrator_with_mock()

        orch.invest_into_product(
            db, product_id=product.id, client_id=lender1.id,
            funding_asset=product.asset, funding_amount=Decimal("5000"),
        )

        with pytest.raises(Exception):
            orch.invest_into_product(
                db, product_id=product.id, client_id=lender2.id,
                funding_asset=product.asset, funding_amount=Decimal("1000"),
            )

    def test_second_invest_fits_exactly(self, db):
        """With target=5000, invest 3000 then 2000 → both succeed, product fills."""
        borrower = create_client(db, "conc_fit_bor@test.com")
        lender1 = create_client(db, "conc_fit_len1@test.com")
        lender2 = create_client(db, "conc_fit_len2@test.com")
        product = create_fundraising_product(
            db, borrower.id, target_size=Decimal("5000"),
        )
        set_crypto_balance(db, lender1.id, product.asset, Decimal("50000"))
        set_crypto_balance(db, lender2.id, product.asset, Decimal("50000"))

        orch, _ = create_orchestrator_with_mock()

        r1 = orch.invest_into_product(
            db, product_id=product.id, client_id=lender1.id,
            funding_asset=product.asset, funding_amount=Decimal("3000"),
        )
        r2 = orch.invest_into_product(
            db, product_id=product.id, client_id=lender2.id,
            funding_asset=product.asset, funding_amount=Decimal("2000"),
        )

        assert r1["status"] == "completed"
        assert r2["status"] == "completed"

        total_envs_1 = count_envelopes(db, lender1.id)
        total_envs_2 = count_envelopes(db, lender2.id)
        assert total_envs_1 == 1
        assert total_envs_2 == 1


class TestRetryIdempotency:
    """Retry with same logical payload creates separate records (no idempotency at orchestrator level)."""

    def test_same_amount_creates_distinct_envelopes(self, db):
        borrower = create_client(db, "conc_retry_bor@test.com")
        lender = create_client(db, "conc_retry_len@test.com")
        product = create_fundraising_product(db, borrower.id)
        set_crypto_balance(db, lender.id, product.asset, Decimal("100000"))

        orch, _ = create_orchestrator_with_mock()

        r1 = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=Decimal("1000"),
        )
        r2 = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=Decimal("1000"),
        )

        assert r1["envelope_id"] != r2["envelope_id"]
        assert r1["commitment_id"] != r2["commitment_id"]


class TestMultipleClientsNoCrossContamination:
    """Two different clients investing: no cross-contamination of envelopes."""

    def test_separate_envelopes_per_client(self, db):
        borrower = create_client(db, "conc_multi_bor@test.com")
        lender_a = create_client(db, "conc_multi_a@test.com")
        lender_b = create_client(db, "conc_multi_b@test.com")
        product = create_fundraising_product(db, borrower.id)
        set_crypto_balance(db, lender_a.id, product.asset, Decimal("50000"))
        set_crypto_balance(db, lender_b.id, product.asset, Decimal("50000"))

        orch, _ = create_orchestrator_with_mock()

        orch.invest_into_product(
            db, product_id=product.id, client_id=lender_a.id,
            funding_asset=product.asset, funding_amount=Decimal("2000"),
        )
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender_b.id,
            funding_asset=product.asset, funding_amount=Decimal("3000"),
        )

        envs_a = snapshot_envelopes(db, lender_a.id)
        envs_b = snapshot_envelopes(db, lender_b.id)
        assert len(envs_a) == 1
        assert len(envs_b) == 1

        entry_a = envs_a[0]["entries"][0]
        entry_b = envs_b[0]["entries"][0]
        assert entry_a["entry_amount"] == Decimal("2000")
        assert entry_b["entry_amount"] == Decimal("3000")
