"""Tests audit lecture seule person_crypto_reconciliation — doctrine custody v2."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from services.audit.legacy_frozen import load_frozen_scope
from services.audit.person_crypto_reconciliation import (
    AUDIT_VERSION,
    _build_success_criteria,
    _classify_raw_asset_signals,
    _classify_recommendations,
    _collect_legacy_frozen,
    _fmt,
    build_person_crypto_audit,
    resolve_person_ids_by_email,
)
from services.auth.person_identity_bridge import PROVIDER_PRIVY, link_external_identity_to_person
from tests.conftest import make_linked_client


def test_fmt_decimal():
    assert _fmt(Decimal("1.5000")) == "1.5"
    assert _fmt(None) == "0"


def test_load_frozen_scope_has_legacy_frozen():
    scope = load_frozen_scope()
    assert scope.get("legacy_frozen") is True
    assert scope.get("do_not_auto_fix") is True
    assert any(s.get("id") == "uvp_user_vault_positions" for s in scope.get("frozen_scopes", []))


def test_resolve_person_ids_by_email_empty(db: Session):
    assert resolve_person_ids_by_email(db, f"no-such-{uuid.uuid4().hex}@test.local") == []


def test_build_audit_minimal_person(db: Session):
    pe = make_linked_client(db)
    email = f"audit-{uuid.uuid4().hex[:8]}@test.local"
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=f"did:privy:{uuid.uuid4().hex[:12]}",
        external_email=email,
    )
    report = build_person_crypto_audit(db, email=email)
    assert report["audit_version"] == AUDIT_VERSION
    assert report["person"]["person_id"] == str(pe.person_id)
    assert "success_criteria" in report
    assert report["success_criteria"]["global_delta_usd"] is None
    assert "liquid_wallet_delta_usd" in report["success_criteria"]
    assert "legacy_frozen" in report
    assert "reporting_gaps" in report
    assert "informational" in report


def test_bundle_overlap_is_informational_not_custody_issue():
    custody, informational, _ = _classify_raw_asset_signals(
        asset="USDC",
        ledger_bal=Decimal("100"),
        chain_bal=Decimal("80"),
        ledger_liquid=Decimal("80"),
        vault_alloc=Decimal("20"),
        bundle_alloc=Decimal("10"),
        collateral=Decimal("0"),
        debt=Decimal("0"),
        direct_avail=Decimal("70"),
        delta_liquid=Decimal("0"),
        tol=Decimal("0.01"),
        ethereum_bal=Decimal("0"),
    )
    assert "bundle_overlap_expected" in informational
    assert "bundle_overlap_expected" not in custody


def test_vault_explains_delta_informational():
    custody, informational, _ = _classify_raw_asset_signals(
        asset="USDC",
        ledger_bal=Decimal("176"),
        chain_bal=Decimal("62"),
        ledger_liquid=Decimal("62"),
        vault_alloc=Decimal("114"),
        bundle_alloc=Decimal("0"),
        collateral=Decimal("0"),
        debt=Decimal("69"),
        direct_avail=Decimal("62"),
        delta_liquid=Decimal("0"),
        tol=Decimal("0.01"),
        ethereum_bal=Decimal("0"),
    )
    assert custody == []
    assert "vault_explains_delta" in informational
    assert "active_debt" in informational


def test_usdt_on_ethereum_only_is_out_of_scope_not_custody():
    custody, informational, _ = _classify_raw_asset_signals(
        asset="USDT",
        ledger_bal=Decimal("150"),
        chain_bal=Decimal("0"),
        ethereum_bal=Decimal("150"),
        ledger_liquid=Decimal("150"),
        vault_alloc=Decimal("0"),
        bundle_alloc=Decimal("0"),
        collateral=Decimal("0"),
        debt=Decimal("0"),
        direct_avail=Decimal("150"),
        delta_liquid=Decimal("150"),
        tol=Decimal("0.01"),
    )
    assert "ethereum_out_of_scope" in informational
    assert "ethereum_explains_ledger_gap" in informational
    assert custody == []


def test_usdc_ethereum_extra_not_custody_when_base_matches_ledger():
    custody, informational, _ = _classify_raw_asset_signals(
        asset="USDC",
        ledger_bal=Decimal("176.737796"),
        chain_bal=Decimal("62.641746"),
        ethereum_bal=Decimal("10"),
        ledger_liquid=Decimal("62.641746"),
        vault_alloc=Decimal("114.09605"),
        bundle_alloc=Decimal("17.566654"),
        collateral=Decimal("0"),
        debt=Decimal("69"),
        direct_avail=Decimal("62.641746"),
        delta_liquid=Decimal("0"),
        tol=Decimal("0.01"),
    )
    assert "ethereum_out_of_scope" in informational
    assert custody == []


def test_eth_micro_delta_suppressed_when_ethereum_explains_base_gap():
    custody, informational, _ = _classify_raw_asset_signals(
        asset="ETH",
        ledger_bal=Decimal("0.041263354"),
        chain_bal=Decimal("0.006542223"),
        ethereum_bal=Decimal("0.03"),
        ledger_liquid=Decimal("0.041263354"),
        vault_alloc=Decimal("0"),
        bundle_alloc=Decimal("0.0107519855"),
        collateral=Decimal("0"),
        debt=Decimal("0"),
        direct_avail=Decimal("0"),
        delta_liquid=Decimal("0.034721131"),
        tol=Decimal("0.00000001"),
    )
    assert "ethereum_out_of_scope" in informational
    assert "ethereum_explains_ledger_gap" in informational
    assert "ledger_liquid_vs_onchain" not in custody
    assert custody == []


def test_gaelitier_base_only_custody_reconciled():
    """gaelitier — périmètre Base uniquement, Ethereum gelé hors scope."""
    asset_rows = [
        {
            "asset": "EURC",
            "ledger_liquid": "91.414272",
            "on_chain_balance": "91.414272",
            "delta_ledger_liquid_vs_onchain": "0",
            "custody_tolerance": "0.01",
            "custody_issues": [],
            "informational": [],
        },
        {
            "asset": "USDC",
            "ledger_liquid": "62.641746",
            "on_chain_balance": "62.641746",
            "delta_ledger_liquid_vs_onchain": "0",
            "custody_tolerance": "0.01",
            "custody_issues": [],
            "informational": ["ethereum_out_of_scope", "bundle_overlap_expected", "active_debt"],
        },
        {
            "asset": "USDT",
            "ledger_liquid": "150.02925",
            "on_chain_balance": "0",
            "delta_ledger_liquid_vs_onchain": "150.02925",
            "custody_tolerance": "0.01",
            "custody_issues": [],
            "informational": ["ethereum_out_of_scope", "ethereum_explains_ledger_gap"],
        },
        {
            "asset": "ETH",
            "ledger_liquid": "0.041263354",
            "on_chain_balance": "0.006542223",
            "delta_ledger_liquid_vs_onchain": "0.034721131",
            "custody_tolerance": "0.00000001",
            "custody_issues": [],
            "informational": [
                "ethereum_out_of_scope",
                "ethereum_explains_ledger_gap",
                "bundle_overlap_expected",
            ],
        },
    ]
    db = MagicMock()
    criteria = _build_success_criteria(
        db,
        asset_rows=asset_rows,
        issues=[],
        informational=[],
        reporting_gaps=[{"type": "cost_basis_missing"}] * 26,
        legacy_frozen=[{"type": "legacy_frozen"}] * 12,
        swaps={"submitted_confirmed_onchain": [], "confirmed_incomplete_settlement": []},
    )
    assert criteria["custody_reconciled"] is True
    assert criteria["stablecoin_custody_ok"] is True
    assert criteria["custody_issue_count"] == 0
    assert criteria["liquid_wallet_delta_usd"] == "0"


def test_liquid_wallet_delta_usd_only_counts_custody_issues():
    asset_rows = [
        {
            "asset": "USDC",
            "ledger_liquid": "62.641746",
            "on_chain_balance": "62.641746",
            "delta_ledger_liquid_vs_onchain": "0",
            "custody_tolerance": "0.01",
            "custody_issues": [],
            "informational": ["ethereum_out_of_scope"],
        },
        {
            "asset": "CBBTC",
            "ledger_liquid": "0.00205098",
            "on_chain_balance": "0",
            "delta_ledger_liquid_vs_onchain": "0.00205098",
            "custody_tolerance": "0.00000001",
            "custody_issues": [],
            "informational": ["collateral_locked_matches_wallet"],
        },
    ]
    db = MagicMock()
    criteria = _build_success_criteria(
        db,
        asset_rows=asset_rows,
        issues=[],
        informational=[],
        reporting_gaps=[],
        legacy_frozen=[],
        swaps={"submitted_confirmed_onchain": [], "confirmed_incomplete_settlement": []},
    )
    assert criteria["liquid_wallet_delta_usd"] == "0"


def test_gaelitier_stablecoin_custody_success_criteria():
    """Simulation post-réconciliation gaelitier — stablecoins custody OK."""
    asset_rows = [
        {
            "asset": "EURC",
            "ledger_liquid": "91.414272",
            "on_chain_balance": "91.414272",
            "delta_ledger_liquid_vs_onchain": "0",
            "custody_tolerance": "0.01",
            "custody_issues": [],
            "informational": [],
        },
        {
            "asset": "USDC",
            "ledger_liquid": "62.641746",
            "on_chain_balance": "62.641746",
            "delta_ledger_liquid_vs_onchain": "0",
            "custody_tolerance": "0.01",
            "custody_issues": [],
            "informational": ["vault_explains_delta", "bundle_overlap_expected", "active_debt"],
        },
        {
            "asset": "USDT",
            "ledger_liquid": "150.02925",
            "on_chain_balance": "150.02925",
            "delta_ledger_liquid_vs_onchain": "0",
            "custody_tolerance": "0.01",
            "custody_issues": [],
            "informational": [],
        },
    ]
    db = MagicMock()
    criteria = _build_success_criteria(
        db,
        asset_rows=asset_rows,
        issues=[],
        informational=[],
        reporting_gaps=[{"type": "cost_basis_missing"}] * 26,
        legacy_frozen=[{"type": "legacy_frozen"}] * 10,
        swaps={
            "submitted_confirmed_onchain": [],
            "confirmed_incomplete_settlement": [],
        },
    )
    assert criteria["custody_reconciled"] is True
    assert criteria["stablecoin_custody_ok"] is True
    assert criteria["liquid_wallet_delta_usd"] == "0"
    assert criteria["reporting_gaps_count"] == 26
    assert criteria["legacy_frozen_count"] == 10
    assert criteria["global_delta_usd"] is None


def test_collect_legacy_frozen_from_scope_gaps():
    frozen = _collect_legacy_frozen(
        {
            "gaps": [
                {
                    "gap_type": "scope_pe_missing_or_divergent",
                    "asset": "USDC",
                    "expected_scope": "liability",
                    "expected_quantity": "252",
                    "current_quantity": "69",
                }
            ],
            "double_counting_risks": [
                {
                    "risk_type": "vault_uvp_and_pe_vault_mismatch",
                    "asset": "USDC",
                    "message": "divergent",
                }
            ],
        }
    )
    assert len(frozen) == 2
    assert all(f.get("do_not_auto_fix") for f in frozen)
    assert frozen[0]["frozen_scope_id"] == "lombard_liability_historical_delta"


def test_classify_recommendations_no_auto_fix_on_legacy():
    report = {
        "swaps": {"confirmed_incomplete_settlement": [], "submitted_confirmed_onchain": []},
        "reporting_gaps": [{"type": "cost_basis_missing", "swap_id": "x"}],
        "issues": [],
        "legacy_frozen": [{"frozen_scope_id": "uvp_user_vault_positions", "asset": "EURC"}],
    }
    actions = _classify_recommendations(report, frozen_scope=load_frozen_scope())
    assert any(a["type"] == "legacy_frozen" for a in actions["do_not_auto_fix"])
    assert any(a.get("category") == "reporting_gap" for a in actions["requires_review"])


def test_classify_recommendations_swap_safe():
    report = {
        "swaps": {
            "confirmed_incomplete_settlement": [{"swap_id": "abc"}],
            "submitted_confirmed_onchain": [],
        },
        "reporting_gaps": [],
        "issues": [],
        "legacy_frozen": [],
    }
    actions = _classify_recommendations(report, frozen_scope=load_frozen_scope())
    assert actions["safe_auto"][0]["type"] == "swap_settlement_repair"
