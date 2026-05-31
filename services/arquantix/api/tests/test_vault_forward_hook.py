"""Tests Phase 3A+1a — hook live vault scope movement dans dual_write_vault_step."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.vault_execution.vault_funding import (
    fund_vault_from_self_trading,
    resolve_trading_available_for_vault,
    resolve_vault_position_available,
)
from services.transaction_attempts.dual_write import dual_write_vault_step
from tests.conftest import make_linked_client
from tests.test_bundle_lifi_funding import _instrument_usdc
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


def _unique_tx(prefix: str = "vh") -> str:
    return f"0x{prefix}{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"


def _seed_trading_usdc(db: Session, client_id: uuid.UUID, amount: Decimal, cost: Decimal):
    direct_pf = ensure_direct_portfolio(db, client_id)
    usdc = _instrument_usdc(db)
    sync_direct_atom(db, direct_pf.id, usdc.id, amount, cost)
    return direct_pf, usdc


def _insert_ovt(
    db: Session,
    *,
    ovt_id: str,
    person_id: uuid.UUID,
    wallet_address: str,
    operation: str,
    amount_raw: str,
    integration_mode: str = "direct_morpho",
    status: str = "success",
    tx_hash: str | None = None,
    group_key: str | None = None,
) -> str:
    gk = group_key or f"vh-{uuid.uuid4().hex[:12]}"
    tx = tx_hash or _unique_tx("ovt")
    db.execute(
        sa.text(
            """
            INSERT INTO onchain_vault_transactions (
                id, person_id, vault_address, chain_id, chain_type, wallet_address,
                operation, amount_raw, asset_symbol, asset_decimals, status, tx_hash,
                idempotency_key, group_key, integration_mode, tx_index, created_at, updated_at
            ) VALUES (
                :id, :person_id, :vault, 8453, 'evm', :wallet,
                :operation, :amount_raw, 'USDC', 6, :status, :tx_hash,
                :gk, :gk, :mode, 0, NOW(), NOW()
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
            "status": status,
            "tx_hash": tx,
            "gk": gk,
            "mode": integration_mode,
        },
    )
    return tx


def _dual_write_success(
    db: Session,
    *,
    person_id: uuid.UUID,
    wallet_address: str,
    ovt_id: str,
    operation: str,
    integration_mode: str,
    tx_hash: str,
    group_key: str,
) -> None:
    dual_write_vault_step(
        db,
        person_id=person_id,
        vault_transaction_id=ovt_id,
        chain_id=8453,
        wallet_address=wallet_address,
        operation=operation,
        group_key=group_key,
        step_index=0,
        integration_mode=integration_mode,
        tx_hash=tx_hash,
        vault_status="success",
    )


pytestmark = pytest.mark.skipif(
    not _vault_table_ready(),
    reason="Table onchain_vault_transactions absente.",
)


def test_morpho_deposit_success_creates_fund_pe_and_audit(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    _seed_trading_usdc(db, pe.id, Decimal("100"), Decimal("86"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"
    group_key = f"morpho-dep-{uuid.uuid4().hex[:10]}"
    tx = _insert_ovt(
        db,
        ovt_id=ovt_id,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        operation="deposit",
        amount_raw="10000000",
        group_key=group_key,
    )

    _dual_write_success(
        db,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        ovt_id=ovt_id,
        operation="deposit",
        integration_mode="direct_morpho",
        tx_hash=tx,
        group_key=group_key,
    )
    db.flush()

    usdc = _instrument_usdc(db)
    assert resolve_trading_available_for_vault(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("90")
    assert resolve_vault_position_available(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("10")

    audits = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_id == ovt_id,
            AuditEvent.action == "vault.fund_from_self_trading",
        )
        .all()
    )
    assert len(audits) == 1


def test_morpho_withdraw_success_creates_release_pe_and_audit(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    _, usdc = _seed_trading_usdc(db, pe.id, Decimal("100"), Decimal("86"))
    fund_ovt = f"cl{uuid.uuid4().hex[:22]}"
    fund_vault_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        asset="USDC",
        instrument_id=usdc.id,
        amount=Decimal("30"),
        linked_reference_id=fund_ovt,
    )

    ovt_id = f"cl{uuid.uuid4().hex[:22]}"
    group_key = f"morpho-wd-{uuid.uuid4().hex[:10]}"
    tx = _insert_ovt(
        db,
        ovt_id=ovt_id,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        operation="withdraw",
        amount_raw="8000000",
        group_key=group_key,
    )

    _dual_write_success(
        db,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        ovt_id=ovt_id,
        operation="withdraw",
        integration_mode="direct_morpho",
        tx_hash=tx,
        group_key=group_key,
    )
    db.flush()

    assert resolve_vault_position_available(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("22")
    assert resolve_trading_available_for_vault(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("78")

    audits = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_id == ovt_id,
            AuditEvent.action == "vault.release_to_self_trading",
        )
        .all()
    )
    assert len(audits) == 1


def test_double_confirm_same_ovt_creates_single_audit(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    _seed_trading_usdc(db, pe.id, Decimal("50"), Decimal("43"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"
    group_key = f"morpho-idem-{uuid.uuid4().hex[:10]}"
    tx = _insert_ovt(
        db,
        ovt_id=ovt_id,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        operation="deposit",
        amount_raw="5000000",
        group_key=group_key,
    )

    for _ in range(2):
        _dual_write_success(
            db,
            person_id=pe.person_id,
            wallet_address=wallet.address,
            ovt_id=ovt_id,
            operation="deposit",
            integration_mode="direct_morpho",
            tx_hash=tx,
            group_key=group_key,
        )
    db.flush()

    usdc = _instrument_usdc(db)
    assert resolve_vault_position_available(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("5")
    audit_count = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_id == ovt_id,
            AuditEvent.action == "vault.fund_from_self_trading",
        )
        .count()
    )
    assert audit_count == 1


def test_ledgity_deposit_success_creates_fund_pe(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    _seed_trading_usdc(db, pe.id, Decimal("40"), Decimal("34"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"
    group_key = f"ledgity-dep-{uuid.uuid4().hex[:10]}"
    tx = _insert_ovt(
        db,
        ovt_id=ovt_id,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        operation="deposit",
        amount_raw="3000000",
        integration_mode="ledgity_vault",
        group_key=group_key,
    )

    _dual_write_success(
        db,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        ovt_id=ovt_id,
        operation="deposit",
        integration_mode="ledgity_vault",
        tx_hash=tx,
        group_key=group_key,
    )
    db.flush()

    usdc = _instrument_usdc(db)
    assert resolve_vault_position_available(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("3")
    assert (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_id == ovt_id,
            AuditEvent.action == "vault.fund_from_self_trading",
        )
        .count()
    ) == 1


def test_lombard_receipt_does_not_create_vault_scope_movement(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    _seed_trading_usdc(db, pe.id, Decimal("100"), Decimal("86"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"
    group_key = f"lombard-{uuid.uuid4().hex[:10]}"
    tx = _insert_ovt(
        db,
        ovt_id=ovt_id,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        operation="deposit",
        amount_raw="10000000",
        integration_mode="lombard_v1",
        group_key=group_key,
    )

    _dual_write_success(
        db,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        ovt_id=ovt_id,
        operation="deposit",
        integration_mode="lombard_v1",
        tx_hash=tx,
        group_key=group_key,
    )
    db.flush()

    usdc = _instrument_usdc(db)
    assert resolve_vault_position_available(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("0")
    assert resolve_trading_available_for_vault(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("100")
    assert (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_id == ovt_id,
            AuditEvent.action.in_(
                ["vault.fund_from_self_trading", "vault.release_to_self_trading"]
            ),
        )
        .count()
    ) == 0


def test_insufficient_trading_logs_warning_without_crashing(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    _seed_trading_usdc(db, pe.id, Decimal("1"), Decimal("0.86"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"
    group_key = f"morpho-insuf-{uuid.uuid4().hex[:10]}"
    tx = _insert_ovt(
        db,
        ovt_id=ovt_id,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        operation="deposit",
        amount_raw="10000000",
        group_key=group_key,
    )

    with patch(
        "services.transaction_attempts.dual_write.logger.warning"
    ) as mock_warning:
        _dual_write_success(
            db,
            person_id=pe.person_id,
            wallet_address=wallet.address,
            ovt_id=ovt_id,
            operation="deposit",
            integration_mode="direct_morpho",
            tx_hash=tx,
            group_key=group_key,
        )
        db.flush()

    usdc = _instrument_usdc(db)
    assert resolve_vault_position_available(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("0")
    assert resolve_trading_available_for_vault(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("1")
    assert (
        db.query(AuditEvent)
        .filter(AuditEvent.entity_id == ovt_id)
        .count()
    ) == 0

    skipped_calls = [
        c
        for c in mock_warning.call_args_list
        if c.args and c.args[0] == "attempt.dual_write.vault_scope_movement_skipped"
    ]
    assert len(skipped_calls) == 1
    assert skipped_calls[0].kwargs["extra"]["reason"] == "vault.funding.insufficient_trading_available"
    assert "insuffisant" in (skipped_calls[0].kwargs["extra"].get("detail") or "")
