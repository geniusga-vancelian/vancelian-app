"""Tests Phase 3B — hook live Lombard scope movement dans dual_write_vault_step."""
from __future__ import annotations

import json
import uuid
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.portfolio_engine.direct_overlay import (
    _resolve_or_create_instrument,
    ensure_direct_portfolio,
    sync_direct_atom,
)
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.portfolio_engine.internal_scope_movements.pe_reader import read_current_pe_scope_snapshot
from services.portfolio_engine.vault_execution.vault_funding import (
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


def _unique_tx(prefix: str = "lb") -> str:
    return f"0x{prefix}{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"


def _seed_trading_cbbtc(db: Session, client_id: uuid.UUID, amount: Decimal, cost: Decimal):
    direct_pf = ensure_direct_portfolio(db, client_id)
    cbbtc = _resolve_or_create_instrument(db, "CBBTC")
    sync_direct_atom(db, direct_pf.id, cbbtc.id, amount, cost)
    return direct_pf, cbbtc


def _insert_lombard_ovt(
    db: Session,
    *,
    ovt_id: str,
    person_id: uuid.UUID,
    wallet_address: str,
    amount_raw: str,
    metadata_json: dict,
    operation: str = "deposit",
    status: str = "success",
    tx_hash: str | None = None,
    group_key: str | None = None,
) -> str:
    gk = group_key or f"lombard-{uuid.uuid4().hex[:10]}"
    tx = tx_hash or _unique_tx("ovt")
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
                :operation, :amount_raw, 'USDC', 6, :status, :tx_hash,
                :gk, :gk, 'lombard_v1', 0, CAST(:meta AS jsonb),
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
            "status": status,
            "tx_hash": tx,
            "gk": gk,
            "meta": json.dumps(metadata_json),
        },
    )
    return tx


def _dual_write_lombard(
    db: Session,
    *,
    person_id: uuid.UUID,
    wallet_address: str,
    ovt_id: str,
    operation: str,
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
        step_index=1,
        integration_mode="lombard_v1",
        tx_hash=tx_hash,
        vault_status="success",
    )


pytestmark = pytest.mark.skipif(
    not _vault_table_ready(),
    reason="Table onchain_vault_transactions absente.",
)


def test_lombard_open_loan_receipt_creates_scope_atoms(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    _seed_trading_cbbtc(db, pe.id, Decimal("0.001"), Decimal("50"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"
    group_key = f"lombard-open-{uuid.uuid4().hex[:8]}"
    meta = {
        "lombard_operation": "open_loan",
        "collateral": "cbBTC",
        "guarantee_amount": "0.000125",
        "borrow_amount_raw": "5000000",
    }
    tx = _insert_lombard_ovt(
        db,
        ovt_id=ovt_id,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        amount_raw="5000000",
        metadata_json=meta,
        group_key=group_key,
    )

    _dual_write_lombard(
        db,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        ovt_id=ovt_id,
        operation="open_loan",
        tx_hash=tx,
        group_key=group_key,
    )
    db.flush()

    snap = read_current_pe_scope_snapshot(db, pe.person_id)
    assert snap.trading_locked_collateral.get("CBBTC") == Decimal("0.000125")
    assert snap.trading_available.get("USDC") == Decimal("5")
    assert snap.liability.get("USDC") == Decimal("5")

    audits = (
        db.query(AuditEvent)
        .filter(AuditEvent.entity_id == ovt_id)
        .all()
    )
    assert {a.action for a in audits} == {"lombard.lock_collateral", "lombard.open_borrow"}


def test_lombard_approve_only_no_scope(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    _seed_trading_cbbtc(db, pe.id, Decimal("0.001"), Decimal("50"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"
    group_key = f"lombard-appr-{uuid.uuid4().hex[:8]}"
    tx = _insert_lombard_ovt(
        db,
        ovt_id=ovt_id,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        amount_raw="0",
        metadata_json={"lombard_operation": "approve"},
        operation="approve",
        group_key=group_key,
    )

    _dual_write_lombard(
        db,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        ovt_id=ovt_id,
        operation="approve",
        tx_hash=tx,
        group_key=group_key,
    )
    db.flush()

    snap = read_current_pe_scope_snapshot(db, pe.person_id)
    assert not snap.trading_locked_collateral
    assert not snap.liability
    assert (
        db.query(AuditEvent)
        .filter(AuditEvent.entity_id == ovt_id)
        .count()
    ) == 0


def test_lombard_receipt_still_no_vault_fund(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    usdc = _instrument_usdc(db)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("100"), Decimal("86"))
    _seed_trading_cbbtc(db, pe.id, Decimal("0.001"), Decimal("50"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"
    group_key = f"lombard-nvault-{uuid.uuid4().hex[:8]}"
    meta = {
        "lombard_operation": "open_loan",
        "collateral": "cbBTC",
        "guarantee_amount": "0.000125",
        "borrow_amount_raw": "5000000",
    }
    tx = _insert_lombard_ovt(
        db,
        ovt_id=ovt_id,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        amount_raw="5000000",
        metadata_json=meta,
        group_key=group_key,
    )

    _dual_write_lombard(
        db,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        ovt_id=ovt_id,
        operation="open_loan",
        tx_hash=tx,
        group_key=group_key,
    )
    db.flush()

    assert resolve_vault_position_available(db, client_id=pe.id, instrument_id=usdc.id) == Decimal("0")
    trading_usdc = resolve_trading_available_for_vault(db, client_id=pe.id, instrument_id=usdc.id)
    assert trading_usdc == Decimal("105")
    assert (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_id == ovt_id,
            AuditEvent.action.in_(["vault.fund_from_self_trading", "vault.release_to_self_trading"]),
        )
        .count()
    ) == 0


def test_lombard_hook_idempotent_on_receipt_replay(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    _seed_trading_cbbtc(db, pe.id, Decimal("0.001"), Decimal("50"))
    ovt_id = f"cl{uuid.uuid4().hex[:22]}"
    group_key = f"lombard-idem-{uuid.uuid4().hex[:8]}"
    meta = {
        "lombard_operation": "open_loan",
        "collateral": "cbBTC",
        "guarantee_amount": "0.000125",
        "borrow_amount_raw": "5000000",
    }
    tx = _insert_lombard_ovt(
        db,
        ovt_id=ovt_id,
        person_id=pe.person_id,
        wallet_address=wallet.address,
        amount_raw="5000000",
        metadata_json=meta,
        group_key=group_key,
    )

    for _ in range(2):
        _dual_write_lombard(
            db,
            person_id=pe.person_id,
            wallet_address=wallet.address,
            ovt_id=ovt_id,
            operation="open_loan",
            tx_hash=tx,
            group_key=group_key,
        )
    db.flush()

    snap = read_current_pe_scope_snapshot(db, pe.person_id)
    assert snap.trading_locked_collateral.get("CBBTC") == Decimal("0.000125")
    assert (
        db.query(AuditEvent)
        .filter(AuditEvent.entity_id == ovt_id)
        .count()
    ) == 2
