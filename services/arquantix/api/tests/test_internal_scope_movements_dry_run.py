"""Tests Phase 2 — internal scope movements dry-run (read-only, no PE writes)."""
from __future__ import annotations

import json
import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.portfolio_engine.internal_scope_movements import (
    build_internal_scope_audit_report,
    compare_expected_scopes_vs_current_pe,
    compute_expected_bundle_scope_movements,
    compute_expected_lombard_scope_movements,
    compute_expected_vault_scope_movements,
)
from services.portfolio_engine.internal_scope_movements.enums import InternalScope
from services.portfolio_engine.portfolios.models import Portfolio
from tests.conftest import make_linked_client
from tests.test_phase4_reconciliation import _seed_wallet


def _vault_table_ready() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'onchain_vault_transactions'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


def _insert_vault_ovt(
    db: Session,
    *,
    ovt_id: str,
    person_id: uuid.UUID,
    wallet_address: str,
    operation: str,
    amount_raw: str,
    asset_symbol: str = "USDC",
    asset_decimals: int = 6,
    integration_mode: str = "direct_morpho",
    status: str = "success",
    metadata_json: dict | None = None,
    group_key: str | None = None,
) -> None:
    gk = group_key or f"grp-{uuid.uuid4().hex[:12]}"
    db.execute(
        sa.text(
            """
            INSERT INTO onchain_vault_transactions (
                id, person_id, vault_address, chain_id, chain_type, wallet_address,
                operation, amount_raw, asset_symbol, asset_decimals, status, tx_hash,
                idempotency_key, group_key, integration_mode, tx_index, metadata_json,
                created_at, updated_at
            ) VALUES (
                :id, :person_id, :vault, 8453, 'evm', :wallet,
                :operation, :amount_raw, :asset, :dec, :status, :tx_hash,
                :idem, :gk, :mode, 0, CAST(:meta AS jsonb),
                NOW(), NOW()
            )
            """
        ),
        {
            "id": ovt_id,
            "person_id": str(person_id),
            "vault": f"0x{uuid.uuid4().hex[:40]}",
            "wallet": wallet_address.lower(),
            "operation": operation,
            "amount_raw": amount_raw,
            "asset": asset_symbol,
            "dec": asset_decimals,
            "status": status,
            "tx_hash": f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}",
            "idem": gk,
            "gk": gk,
            "mode": integration_mode,
            "meta": json.dumps(metadata_json or {}),
        },
    )


@pytest.mark.skipif(not _vault_table_ready(), reason="OVT table absente.")
def test_vault_deposit_produces_expected_scope_movements(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"
    _insert_vault_ovt(
        db,
        ovt_id=ovt_id,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        operation="deposit",
        amount_raw="10000000",
    )
    db.flush()

    result = compute_expected_vault_scope_movements(db, pe.person_id)
    assert len(result.movements) == 1
    m = result.movements[0]
    assert m.source_scope == InternalScope.TRADING_AVAILABLE.value
    assert m.destination_scope == InternalScope.VAULT_POSITION.value
    assert m.asset == "USDC"
    assert m.quantity == Decimal("10")
    assert result.net_by_scope[(InternalScope.VAULT_POSITION.value, "USDC")] == Decimal("10")
    assert result.net_by_scope[(InternalScope.TRADING_AVAILABLE.value, "USDC")] == Decimal("-10")


@pytest.mark.skipif(not _vault_table_ready(), reason="OVT table absente.")
def test_vault_withdraw_produces_inverse_movements(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    gk = f"wd-{uuid.uuid4().hex[:10]}"
    _insert_vault_ovt(
        db,
        ovt_id=f"cl{uuid.uuid4().hex[:22]}",
        person_id=pe.person_id,
        wallet_address=wallet.address,
        operation="deposit",
        amount_raw="10000000",
        group_key=gk,
    )
    _insert_vault_ovt(
        db,
        ovt_id=f"cl{uuid.uuid4().hex[:22]}",
        person_id=pe.person_id,
        wallet_address=wallet.address,
        operation="withdraw",
        amount_raw="4000000",
        group_key=gk,
    )
    db.flush()

    result = compute_expected_vault_scope_movements(db, pe.person_id)
    assert len(result.movements) == 2
    net_vault = result.net_by_scope.get((InternalScope.VAULT_POSITION.value, "USDC"), Decimal("0"))
    net_trading = result.net_by_scope.get((InternalScope.TRADING_AVAILABLE.value, "USDC"), Decimal("0"))
    assert net_vault == Decimal("6")
    assert net_trading == Decimal("-6")


@pytest.mark.skipif(not _vault_table_ready(), reason="OVT table absente.")
def test_lombard_collateral_lock_expected_movements(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    meta = {
        "lombard_operation": "open_loan",
        "collateral": "cbBTC",
        "guarantee_amount_raw": "10000000",
        "borrow_amount_raw": "1000000000",
    }
    _insert_vault_ovt(
        db,
        ovt_id=f"cl{uuid.uuid4().hex[:22]}",
        person_id=pe.person_id,
        wallet_address=wallet.address,
        operation="deposit",
        amount_raw="1000000000",
        integration_mode="lombard_v1",
        metadata_json=meta,
    )
    db.flush()

    result = compute_expected_lombard_scope_movements(db, pe.person_id)
    lock = next(m for m in result.movements if m.movement_type == "lock")
    assert lock.source_scope == InternalScope.TRADING_AVAILABLE.value
    assert lock.destination_scope == InternalScope.TRADING_LOCKED_COLLATERAL.value
    assert lock.asset == "CBBTC"
    assert lock.quantity == Decimal("0.1")


@pytest.mark.skipif(not _vault_table_ready(), reason="OVT table absente.")
def test_lombard_borrow_expected_usdc_and_liability(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    meta = {
        "lombard_operation": "open_loan",
        "collateral": "cbBTC",
        "guarantee_amount": "0.05",
        "borrow_amount_raw": "500000000",
    }
    _insert_vault_ovt(
        db,
        ovt_id=f"cl{uuid.uuid4().hex[:22]}",
        person_id=pe.person_id,
        wallet_address=wallet.address,
        operation="deposit",
        amount_raw="500000000",
        integration_mode="lombard_v1",
        metadata_json=meta,
    )
    db.flush()

    result = compute_expected_lombard_scope_movements(db, pe.person_id)
    borrow = next(m for m in result.movements if m.movement_type == "borrow")
    assert borrow.asset == "USDC"
    assert borrow.quantity == Decimal("500")
    assert result.net_by_scope[(InternalScope.LIABILITY.value, "USDC")] == Decimal("500")
    assert result.net_by_scope[(InternalScope.TRADING_AVAILABLE.value, "USDC")] == Decimal("500")


def test_bundle_pe_atoms_readable_without_module_writes(db: Session):
    pe = make_linked_client(db)
    portfolio = Portfolio(
        client_id=pe.id,
        portfolio_type="bundle_portfolio",
        name="Test Bundle",
        base_currency="USD",
        status="active",
    )
    db.add(portfolio)
    db.flush()

    from services.portfolio_engine.hardening.audit_models import AuditEvent

    batch_id = f"batch-{uuid.uuid4().hex[:8]}"
    db.add(
        AuditEvent(
            entity_type="portfolio",
            entity_id=str(portfolio.id),
            action="bundle.fund_cash_leg",
            metadata_={
                "client_id": str(pe.id),
                "portfolio_id": str(portfolio.id),
                "batch_id": batch_id,
                "entry_asset": "USDC",
                "amount": 25.0,
            },
        )
    )
    db.flush()

    add_mock = MagicMock(wraps=db.add)
    commit_mock = MagicMock(wraps=db.commit)
    db.add = add_mock  # type: ignore[method-assign]
    db.commit = commit_mock  # type: ignore[method-assign]

    bundle_result = compute_expected_bundle_scope_movements(db, pe.person_id)
    compare_expected_scopes_vs_current_pe(db, pe.person_id)
    build_internal_scope_audit_report(db, person_id=pe.person_id)

    assert len(bundle_result.movements) >= 1
    fund = bundle_result.movements[0]
    assert fund.destination_scope == InternalScope.BUNDLE_CASH.value
    assert fund.quantity == Decimal("25")
    add_mock.assert_not_called()
    commit_mock.assert_not_called()


@pytest.mark.skipif(not _vault_table_ready(), reason="OVT table absente.")
def test_compare_detects_vault_gap_when_pe_has_no_vault_scope(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    _insert_vault_ovt(
        db,
        ovt_id=f"cl{uuid.uuid4().hex[:22]}",
        person_id=pe.person_id,
        wallet_address=wallet.address,
        operation="deposit",
        amount_raw="10000000",
    )
    db.flush()

    report = compare_expected_scopes_vs_current_pe(db, pe.person_id)
    gap_types = {g["gap_type"] for g in report["gaps"]}
    assert "scope_pe_missing_or_divergent" in gap_types or "vault_position_not_in_pe" in gap_types
    assert report["summary"]["vault_movement_count"] == 1
    assert len(report["gaps"]) >= 1
