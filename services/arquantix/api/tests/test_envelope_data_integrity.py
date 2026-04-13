"""Data Integrity Tests — Envelope Entry Wallet Phase 2A.16.

Validates every field of the envelope and entry records, and ensures
consistency between the API response, DB records, and linked commitments.

  INV-07: entry_amount matches funding
  INV-08: conversion_type matches path
  INV-09: fx_rate stored on conversion, NULL on direct
  INV-10: commitment_id links to actual PoolSupplyCommitment
"""
from __future__ import annotations

import uuid
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
    MOCK_EUR_USDC_PRICE,
)


class TestEnvelopeFields:
    """Validate envelope-level fields."""

    def test_envelope_type_exclusive_offer(self, db):
        borrower = create_client(db, "di_type_bor@test.com")
        lender = create_client(db, "di_type_len@test.com")
        product = create_fundraising_product(db, borrower.id)
        set_crypto_balance(db, lender.id, product.asset, Decimal("5000"))

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=Decimal("1000"),
        )

        envs = snapshot_envelopes(db, lender.id)
        assert len(envs) == 1
        assert envs[0]["type"] == "exclusive_offer"

    def test_envelope_reference_id_is_project_id(self, db):
        borrower = create_client(db, "di_ref_bor@test.com")
        lender = create_client(db, "di_ref_len@test.com")
        product = create_fundraising_product(db, borrower.id)
        set_crypto_balance(db, lender.id, product.asset, Decimal("5000"))

        project_id = f"test-project-{uuid.uuid4().hex[:8]}"
        product.project_id = project_id
        db.flush()

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=Decimal("500"),
        )

        envs = snapshot_envelopes(db, lender.id)
        assert envs[-1]["reference_id"] == project_id

    def test_envelope_status_active(self, db):
        borrower = create_client(db, "di_stat_bor@test.com")
        lender = create_client(db, "di_stat_len@test.com")
        product = create_fundraising_product(db, borrower.id)
        set_crypto_balance(db, lender.id, product.asset, Decimal("5000"))

        orch, _ = create_orchestrator_with_mock()
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=Decimal("500"),
        )

        envs = snapshot_envelopes(db, lender.id)
        assert envs[-1]["status"] == "active"


class TestEntryFields:
    """Validate entry-level fields for each conversion type."""

    def test_eur_entry_fields(self, db):
        borrower = create_client(db, "di_eur_bor@test.com")
        lender = create_client(db, "di_eur_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()
        funding = Decimal("2000")
        result = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=funding,
        )

        envs = snapshot_envelopes(db, lender.id)
        entry = envs[-1]["entries"][-1]

        assert entry["entry_asset"] == "EUR"
        assert entry["entry_amount"] == funding
        assert entry["target_asset"] == product.asset
        assert entry["conversion_type"] == "buy"
        assert entry["converted_amount"] > Decimal("0")
        assert entry["net_allocated"] > Decimal("0")
        assert entry["fx_rate"] is not None, "INV-09: fx_rate must be set for buy"
        assert entry["fx_rate"] == MOCK_EUR_USDC_PRICE

    def test_btc_entry_fields(self, db):
        borrower = create_client(db, "di_btc_bor@test.com")
        lender = create_client(db, "di_btc_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "BTC"],
        )
        set_crypto_balance(db, lender.id, "BTC", Decimal("1"))
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()
        funding = Decimal("0.01")
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="BTC", funding_amount=funding,
        )

        envs = snapshot_envelopes(db, lender.id)
        entry = envs[-1]["entries"][-1]

        assert entry["entry_asset"] == "BTC"
        assert entry["entry_amount"] == funding
        assert entry["target_asset"] == product.asset
        assert entry["conversion_type"] == "swap"
        assert entry["converted_amount"] > Decimal("0")

    def test_direct_entry_fields(self, db):
        borrower = create_client(db, "di_direct_bor@test.com")
        lender = create_client(db, "di_direct_len@test.com")
        product = create_fundraising_product(db, borrower.id)
        set_crypto_balance(db, lender.id, product.asset, Decimal("5000"))

        orch, _ = create_orchestrator_with_mock()
        funding = Decimal("1500")
        orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=funding,
        )

        envs = snapshot_envelopes(db, lender.id)
        entry = envs[-1]["entries"][-1]

        assert entry["entry_asset"] == product.asset
        assert entry["entry_amount"] == funding
        assert entry["target_asset"] == product.asset
        assert entry["conversion_type"] == "none"
        assert entry["converted_amount"] == funding
        assert entry["net_allocated"] == funding
        assert entry["fx_rate"] is None, "INV-09: fx_rate NULL for direct invest"
        assert entry["conversion_fee"] == Decimal("0")


class TestApiDbConsistency:
    """API response must match DB records exactly."""

    def test_api_commitment_id_matches_db(self, db):
        """INV-10: commitment_id in envelope entry = actual PoolSupplyCommitment."""
        borrower = create_client(db, "di_apidb_bor@test.com")
        lender = create_client(db, "di_apidb_len@test.com")
        product = create_fundraising_product(db, borrower.id)
        set_crypto_balance(db, lender.id, product.asset, Decimal("10000"))

        orch, _ = create_orchestrator_with_mock()
        result = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset=product.asset, funding_amount=Decimal("2000"),
        )

        api_commitment_id = result["commitment_id"]
        api_envelope_id = result["envelope_id"]

        envs = snapshot_envelopes(db, lender.id)
        entry = envs[-1]["entries"][-1]
        assert str(entry["commitment_id"]) == api_commitment_id

        comms = snapshot_commitments(db, lender.id)
        comm_ids = [str(c["id"]) for c in comms]
        assert api_commitment_id in comm_ids

    def test_api_amounts_match_db(self, db):
        borrower = create_client(db, "di_apiamt_bor@test.com")
        lender = create_client(db, "di_apiamt_len@test.com")
        product = create_fundraising_product(
            db, borrower.id, entry_assets_allowed=["USDC", "EUR"],
        )
        set_crypto_balance(db, lender.id, product.asset, Decimal("0"))

        orch, _ = create_orchestrator_with_mock()
        funding = Decimal("750")
        result = orch.invest_into_product(
            db, product_id=product.id, client_id=lender.id,
            funding_asset="EUR", funding_amount=funding,
        )

        envs = snapshot_envelopes(db, lender.id)
        entry = envs[-1]["entries"][-1]

        assert float(entry["entry_amount"]) == result["funding_amount"]
        assert float(entry["net_allocated"]) == result["net_allocated"]
        assert entry["conversion_type"] == result["conversion_type"]

    def test_one_envelope_per_invest(self, db):
        """Each invest call creates exactly one envelope with one entry."""
        borrower = create_client(db, "di_count_bor@test.com")
        lender = create_client(db, "di_count_len@test.com")
        product = create_fundraising_product(db, borrower.id)
        set_crypto_balance(db, lender.id, product.asset, Decimal("50000"))

        orch, _ = create_orchestrator_with_mock()

        for i in range(3):
            orch.invest_into_product(
                db, product_id=product.id, client_id=lender.id,
                funding_asset=product.asset, funding_amount=Decimal("500"),
            )

        envs = snapshot_envelopes(db, lender.id)
        assert len(envs) == 3
        for env in envs:
            assert len(env["entries"]) == 1
