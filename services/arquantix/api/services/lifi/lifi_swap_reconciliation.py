"""Réconciliation idempotente des swaps LI.FI — settlement partiel ledger ↔ on-chain."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_actual_receive import resolve_lifi_actual_receive_amount
from services.lifi.lifi_swap_settlement import (
    SWAP_LEDGER_LOG_INDEX_DEBIT_PREFERRED,
    SwapSettlementBlocked,
    _chain_id_for_swap,
    _create_swap_ledger_entry,
    _resolve_swap_wallet,
    swap_credit_idempotency_key,
    swap_debit_idempotency_key,
)
from services.lifi.lifi_validation_service import SwapValidationError
from services.lifi.swap_repository import PersonWalletSwapRepository
from services.lifi.swap_trace_service import log_swap_trace
from services.privy_wallet.enums import PersonWalletDirection
from services.privy_wallet.evm_chain_config import resolve_chain_rpc_url
from services.privy_wallet.evm_rpc_client import fetch_transaction_receipt
from services.privy_wallet.models import PersonWalletDeposit
from services.privy_wallet.repository import PersonWalletDepositRepository
from services.transaction_intents.lifi_intent_sync import on_swap_confirmed

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SwapLedgerLegStatus:
    debit_exists: bool
    credit_exists: bool
    debit_deposit_id: UUID | None
    credit_deposit_id: UUID | None
    credit_amount: Decimal | None
    credit_source: str | None


@dataclass(frozen=True)
class SwapReconciliationResult:
    swap_id: str
    dry_run: bool
    action: str
    status_before: str
    status_after: str
    debit_applied: bool
    credit_applied: bool
    cost_basis_applied: bool
    would_write: list[dict[str, Any]]
    preview: dict[str, Any] | None = None


def _swap_id_str(swap) -> str:
    return str(swap.id)


def _deposit_matches_swap(deposit: PersonWalletDeposit, swap_id: str) -> bool:
    meta = deposit.metadata_json if isinstance(deposit.metadata_json, dict) else {}
    if str(meta.get("swap_id") or "") == swap_id:
        return True
    if deposit.idempotency_key in {swap_debit_idempotency_key(swap_id), swap_credit_idempotency_key(swap_id)}:
        return True
    return False


def swap_ledger_legs_complete(db: Session, swap) -> bool:
    legs = detect_swap_ledger_legs(db, swap)
    return legs.debit_exists and legs.credit_exists


def detect_swap_ledger_legs(db: Session, swap) -> SwapLedgerLegStatus:
    """Détecte les jambes debit/credit déjà présentes (swap settlement ou webhook Privy)."""
    swap_id = _swap_id_str(swap)
    tx_hash = str(swap.tx_hash or "").strip().lower()
    to_asset = str(swap.to_asset).upper()

    deposit_repo = PersonWalletDepositRepository()
    debit_exists = False
    credit_exists = False
    debit_id: UUID | None = None
    credit_id: UUID | None = None
    credit_amount: Decimal | None = None
    credit_source: str | None = None

    debit_by_key = deposit_repo.find_by_deposit_idempotency_key(db, swap_debit_idempotency_key(swap_id))
    if debit_by_key is not None:
        debit_exists = True
        debit_id = debit_by_key.id

    credit_by_key = deposit_repo.find_by_deposit_idempotency_key(db, swap_credit_idempotency_key(swap_id))
    if credit_by_key is not None:
        credit_exists = True
        credit_id = credit_by_key.id
        credit_amount = Decimal(str(credit_by_key.amount))
        meta = credit_by_key.metadata_json if isinstance(credit_by_key.metadata_json, dict) else {}
        credit_source = str(meta.get("source") or credit_by_key.transaction_kind or "lifi_swap")

    if tx_hash:
        for dep in deposit_repo.find_confirmed_by_tx_hash(db, tx_hash=tx_hash, person_id=swap.person_id):
            if _deposit_matches_swap(dep, swap_id):
                if dep.direction == PersonWalletDirection.DEBIT.value and dep.asset.upper() == str(swap.from_asset).upper():
                    debit_exists = True
                    debit_id = dep.id
                if dep.direction == PersonWalletDirection.CREDIT.value and dep.asset.upper() == to_asset:
                    credit_exists = True
                    credit_id = dep.id
                    credit_amount = Decimal(str(dep.amount))
                    meta = dep.metadata_json if isinstance(dep.metadata_json, dict) else {}
                    credit_source = str(meta.get("source") or dep.transaction_kind or "unknown")

        if not credit_exists:
            for dep in deposit_repo.find_confirmed_by_tx_hash(db, tx_hash=tx_hash, person_id=swap.person_id):
                if dep.direction == PersonWalletDirection.CREDIT.value and dep.asset.upper() == to_asset:
                    credit_exists = True
                    credit_id = dep.id
                    credit_amount = Decimal(str(dep.amount))
                    meta = dep.metadata_json if isinstance(dep.metadata_json, dict) else {}
                    credit_source = str(meta.get("source") or dep.transaction_kind or "privy_webhook")

    rows = (
        db.query(PersonWalletDeposit)
        .filter(
            PersonWalletDeposit.person_id == swap.person_id,
            PersonWalletDeposit.metadata_json["swap_id"].astext == swap_id,
        )
        .all()
    )
    for dep in rows:
        if dep.direction == PersonWalletDirection.DEBIT.value:
            debit_exists = True
            debit_id = dep.id
        if dep.direction == PersonWalletDirection.CREDIT.value:
            credit_exists = True
            credit_id = dep.id
            credit_amount = Decimal(str(dep.amount))
            meta = dep.metadata_json if isinstance(dep.metadata_json, dict) else {}
            credit_source = str(meta.get("source") or dep.transaction_kind or "unknown")

    return SwapLedgerLegStatus(
        debit_exists=debit_exists,
        credit_exists=credit_exists,
        debit_deposit_id=debit_id,
        credit_deposit_id=credit_id,
        credit_amount=credit_amount,
        credit_source=credit_source,
    )


def is_tx_confirmed_on_chain(swap, *, chain_id: int | None = None) -> bool:
    tx_hash = str(swap.tx_hash or "").strip().lower()
    if not tx_hash.startswith("0x"):
        return False
    cid = chain_id or _chain_id_for_swap(str(swap.from_chain))
    rpc = resolve_chain_rpc_url(cid)
    if not rpc:
        return False
    try:
        receipt = fetch_transaction_receipt(rpc, tx_hash)
        return str(receipt.get("status") or "").lower() in {"0x1", "1"}
    except Exception:
        logger.warning("swap.reconciliation.receipt_failed swap_id=%s", _swap_id_str(swap), exc_info=True)
        return False


def _load_swap(db: Session, swap_or_id: Any):
    from services.lifi.models import PersonWalletSwap

    if isinstance(swap_or_id, PersonWalletSwap):
        return swap_or_id
    swap_id = swap_or_id if isinstance(swap_or_id, UUID) else UUID(str(swap_or_id))
    row = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == swap_id).first()
    if row is None:
        raise SwapValidationError("swap.not_found", f"Swap introuvable: {swap_id}")
    return row


def _cost_basis_missing(db: Session, swap) -> bool:
    from services.cost_basis.models import CostBasisExecution

    swap_id = _swap_id_str(swap)
    prefix = f"lifi:{swap_id}:"
    existing = (
        db.query(CostBasisExecution)
        .filter(CostBasisExecution.provider_execution_id.like(f"{prefix}%"))
        .count()
    )
    return existing == 0


def _credit_already_linked_to_swap(db: Session, swap, legs: SwapLedgerLegStatus) -> bool:
    if legs.credit_deposit_id is None:
        return False
    dep = db.query(PersonWalletDeposit).filter(PersonWalletDeposit.id == legs.credit_deposit_id).first()
    if dep is None:
        return False
    meta = dep.metadata_json if isinstance(dep.metadata_json, dict) else {}
    return str(meta.get("swap_id") or "") == _swap_id_str(swap)


def build_reconciliation_dry_run_summary(db: Session, swap) -> dict[str, Any]:
    """Résumé ops pour dry-run ciblé (swap prod 76830776…)."""
    legs = detect_swap_ledger_legs(db, swap)
    on_chain_ok = is_tx_confirmed_on_chain(swap)
    from_asset = str(swap.from_asset).upper()
    to_asset = str(swap.to_asset).upper()
    would_debit = not legs.debit_exists
    would_credit = not legs.credit_exists
    credit_already_linked = _credit_already_linked_to_swap(db, swap, legs)
    would_link_credit = legs.credit_exists and not legs.debit_exists and not credit_already_linked
    already_confirmed = str(swap.status) == SwapSessionStatus.CONFIRMED.value

    return {
        "swap_id": _swap_id_str(swap),
        "status": str(swap.status),
        "tx_hash": swap.tx_hash,
        "already_confirmed": already_confirmed,
        "would_mark_confirmed": on_chain_ok
        and str(swap.status) == SwapSessionStatus.SUBMITTED.value,
        f"would_create_debit_{from_asset}": would_debit,
        f"would_create_credit_{to_asset}": would_credit,
        f"would_link_existing_credit_{to_asset}": would_link_credit,
        f"already_linked_credit_{to_asset}": credit_already_linked,
        "would_create_cost_basis": _cost_basis_missing(db, swap),
        "no_double_write_risk": True,
        "on_chain_confirmed": on_chain_ok,
        "ledger_legs": {
            "debit_exists": legs.debit_exists,
            "credit_exists": legs.credit_exists,
            "credit_amount": str(legs.credit_amount) if legs.credit_amount is not None else None,
        },
    }


def _link_existing_credit_to_swap(db: Session, swap, deposit: PersonWalletDeposit) -> None:
    meta = dict(deposit.metadata_json or {})
    meta.setdefault("swap_id", _swap_id_str(swap))
    meta.setdefault("source", "lifi_swap_reconciled")
    meta.setdefault("reconciled_from", meta.get("event_source") or deposit.transaction_kind)
    meta["observed_external_deposit"] = False
    deposit.metadata_json = meta
    if deposit.transaction_kind != "crypto_swap":
        deposit.title = f"Échange {swap.from_asset.upper()} → {swap.to_asset.upper()}"
    db.add(deposit)


def settle_lifi_swap_idempotently(
    db: Session,
    swap_or_id: Any,
    *,
    dry_run: bool = True,
    sync_source: str = "lifi_swap_reconciliation",
    allow_rpc_confirm: bool = True,
) -> SwapReconciliationResult:
    """
    Règle un swap confirmé on-chain de façon idempotente.

    - Crée uniquement les jambes ledger manquantes (debit source / credit destination).
    - Ne recrédite pas EURC si un crédit webhook existe déjà sur la même tx.
    - Passe le swap en CONFIRMED si la tx est confirmée on-chain.
    """
    swap = _load_swap(db, swap_or_id)
    repo = PersonWalletSwapRepository()
    swap_id = _swap_id_str(swap)
    status_before = str(swap.status)
    would_write: list[dict[str, Any]] = []
    preview = build_reconciliation_dry_run_summary(db, swap)

    if not str(swap.tx_hash or "").strip():
        raise SwapValidationError("swap.missing_tx_hash", "tx_hash requis pour la réconciliation")

    legs = detect_swap_ledger_legs(db, swap)
    if legs.debit_exists and legs.credit_exists:
        return SwapReconciliationResult(
            swap_id=swap_id,
            dry_run=dry_run,
            action="noop_legs_complete",
            status_before=status_before,
            status_after=status_before,
            debit_applied=False,
            credit_applied=False,
            cost_basis_applied=False,
            would_write=[],
            preview=preview,
        )
    on_chain_ok = allow_rpc_confirm and is_tx_confirmed_on_chain(swap)

    if status_before not in {SwapSessionStatus.CONFIRMED.value, SwapSessionStatus.SUBMITTED.value}:
        raise SwapValidationError(
            "swap.invalid_state",
            f"Réconciliation impossible depuis status={status_before}",
        )

    if status_before == SwapSessionStatus.SUBMITTED.value and not on_chain_ok:
        raise SwapValidationError(
            "swap.not_confirmed_on_chain",
            "Tx non confirmée on-chain — réconciliation refusée",
        )

    amount_in = Decimal(str(swap.amount_in))
    if amount_in <= 0:
        raise SwapValidationError("swap.invalid_amounts", "Montant source invalide")

    actual = resolve_lifi_actual_receive_amount(db, swap)
    if actual is None and legs.credit_amount is not None:
        from services.lifi.lifi_actual_receive import LifiActualReceiveResult

        actual = LifiActualReceiveResult(
            amount=legs.credit_amount,
            source=legs.credit_source or "existing_ledger_credit",
            receive_tx_hash=str(swap.tx_hash),
        )
    if actual is None or actual.amount <= 0:
        raise SwapSettlementBlocked(
            "actual_amount_missing",
            "Montant destination introuvable pour réconciliation",
        )

    wallet = _resolve_swap_wallet(db, swap)
    from_chain_id = _chain_id_for_swap(str(swap.from_chain))
    to_chain_id = _chain_id_for_swap(str(swap.to_chain))
    from_asset = str(swap.from_asset).upper()

    settlement_meta = {
        "actual_receive_source": actual.source,
        "actual_receive_amount": str(actual.amount),
        "reconciliation": True,
    }
    if actual.receive_tx_hash:
        settlement_meta["actual_receive_tx_hash"] = actual.receive_tx_hash

    debit_applied = False
    credit_applied = False

    if not legs.debit_exists:
        would_write.append(
            {
                "table": "person_wallet_deposits",
                "direction": "debit",
                "asset": from_asset,
                "amount": str(amount_in),
                "idempotency_key": swap_debit_idempotency_key(swap_id),
                "log_index": SWAP_LEDGER_LOG_INDEX_DEBIT_PREFERRED,
            }
        )
        if not dry_run:
            debit_applied = _create_swap_ledger_entry(
                db,
                swap=swap,
                wallet=wallet,
                direction=PersonWalletDirection.DEBIT.value,
                asset=from_asset,
                amount=amount_in,
                chain_id=from_chain_id,
                log_index=SWAP_LEDGER_LOG_INDEX_DEBIT_PREFERRED,
                idempotency_key=swap_debit_idempotency_key(swap_id),
                sync_source=sync_source,
                settlement_meta=settlement_meta,
            )

    if not legs.credit_exists:
        credit_log_index = actual.log_index if actual.log_index is not None else 1
        would_write.append(
            {
                "table": "person_wallet_deposits",
                "direction": "credit",
                "asset": str(swap.to_asset).upper(),
                "amount": str(actual.amount),
                "idempotency_key": swap_credit_idempotency_key(swap_id),
                "log_index": credit_log_index,
            }
        )
        if not dry_run:
            credit_applied = _create_swap_ledger_entry(
                db,
                swap=swap,
                wallet=wallet,
                direction=PersonWalletDirection.CREDIT.value,
                asset=str(swap.to_asset).upper(),
                amount=actual.amount,
                chain_id=to_chain_id,
                log_index=credit_log_index,
                idempotency_key=swap_credit_idempotency_key(swap_id),
                sync_source=sync_source,
                settlement_meta=settlement_meta,
            )
    credit_linked = False
    if legs.credit_deposit_id and not _credit_already_linked_to_swap(db, swap, legs):
        would_write.append(
            {
                "table": "person_wallet_deposits",
                "action": "link_existing_credit",
                "deposit_id": str(legs.credit_deposit_id),
                "swap_id": swap_id,
            }
        )
        if not dry_run:
            dep = db.query(PersonWalletDeposit).filter(PersonWalletDeposit.id == legs.credit_deposit_id).first()
            if dep is not None:
                _link_existing_credit_to_swap(db, swap, dep)
                credit_linked = True

    would_create_cost_basis = _cost_basis_missing(db, swap)
    if would_create_cost_basis:
        would_write.append({"table": "cost_basis_executions", "action": "create_if_missing"})

    cost_basis_applied = False
    if not dry_run and (debit_applied or credit_applied or legs.credit_exists):
        try:
            from services.cost_basis.ingest_lifi import ingest_lifi_swap_settlement

            created = ingest_lifi_swap_settlement(db, swap, wallet=wallet, amount_out=actual.amount)
            cost_basis_applied = created > 0
            if cost_basis_applied:
                would_write.append({"table": "cost_basis_executions", "rows": created})
        except Exception:
            logger.exception("swap.reconciliation.cost_basis_failed swap_id=%s", swap_id)

    if debit_applied and legs.credit_exists and status_before == SwapSessionStatus.CONFIRMED.value:
        action = "reconciled_complete_missing_debit"
    elif legs.credit_exists and not legs.debit_exists:
        action = "reconciled_partial_settlement"
    else:
        action = "reconciled_full_settlement"

    audit_event = (
        "swap_reconciled_complete_missing_debit"
        if action == "reconciled_complete_missing_debit"
        else "swap_reconciled_partial_settlement"
        if action == "reconciled_partial_settlement"
        else "swap_settled"
    )
    will_mutate = (
        not legs.debit_exists
        or not legs.credit_exists
        or (legs.credit_deposit_id and not _credit_already_linked_to_swap(db, swap, legs))
        or would_create_cost_basis
        or (swap.status != SwapSessionStatus.CONFIRMED.value and on_chain_ok)
    )

    if dry_run:
        if swap.status != SwapSessionStatus.CONFIRMED.value and on_chain_ok:
            would_write.append({"table": "person_wallet_swaps", "status": "CONFIRMED"})
        if will_mutate:
            would_write.append({"table": "person_wallet_swaps", "audit_event": audit_event})
            would_write.append({"table": "transaction_trace_events", "event": "reconciliation_applied"})
        if not legs.debit_exists or not legs.credit_exists or would_create_cost_basis:
            would_write.append({"table": "onchain_transaction_attempts", "status": "confirmed"})
        return SwapReconciliationResult(
            swap_id=swap_id,
            dry_run=True,
            action=action,
            status_before=status_before,
            status_after=SwapSessionStatus.CONFIRMED.value if on_chain_ok else status_before,
            debit_applied=False,
            credit_applied=False,
            cost_basis_applied=False,
            would_write=would_write,
            preview=preview,
        )

    if not dry_run and (debit_applied or credit_applied or credit_linked or cost_basis_applied):
        if swap.status != SwapSessionStatus.CONFIRMED.value:
            swap.status = SwapSessionStatus.CONFIRMED.value
            swap.confirmed_at = datetime.now(timezone.utc)
            would_write.append({"table": "person_wallet_swaps", "status": "CONFIRMED"})

        repo.append_audit(
            swap,
            {
                "event": audit_event,
                "tx_hash": swap.tx_hash,
                "source": sync_source,
                "debit_applied": debit_applied,
                "credit_applied": credit_applied,
                "credit_preexisting": legs.credit_exists and not credit_applied,
                "credit_linked": credit_linked,
            },
        )
        on_swap_confirmed(db, swap)
        log_swap_trace(
            db,
            swap,
            event="reconciliation_applied",
            status=swap.status,
            tx_hash=swap.tx_hash,
            source=sync_source,
            metadata_patch={
                "action": action,
                "debit_applied": debit_applied,
                "credit_applied": credit_applied,
            },
        )
        from services.transaction_attempts.dual_write import dual_write_lifi_swap_confirmed

        dual_write_lifi_swap_confirmed(db, swap, tx_hash=str(swap.tx_hash))
        db.commit()

    status_after = SwapSessionStatus.CONFIRMED.value if on_chain_ok else status_before

    return SwapReconciliationResult(
        swap_id=swap_id,
        dry_run=False,
        action=action,
        status_before=status_before,
        status_after=status_after,
        debit_applied=debit_applied,
        credit_applied=credit_applied,
        cost_basis_applied=cost_basis_applied,
        would_write=would_write,
        preview=preview,
    )


def find_partial_settlement_candidates(
    db: Session,
    *,
    limit: int = 50,
) -> list[Any]:
    """Swaps SUBMITTED/CONFIRMED avec crédit destination mais sans débit source."""
    from services.lifi.models import PersonWalletSwap

    rows = (
        db.query(PersonWalletSwap)
        .filter(
            PersonWalletSwap.status.in_(
                [SwapSessionStatus.SUBMITTED.value, SwapSessionStatus.CONFIRMED.value]
            ),
            PersonWalletSwap.tx_hash.isnot(None),
        )
        .order_by(PersonWalletSwap.updated_at.asc())
        .limit(limit * 3)
        .all()
    )

    out = []
    seen: set[str] = set()
    for swap in rows:
        sid = _swap_id_str(swap)
        if sid in seen:
            continue
        legs = detect_swap_ledger_legs(db, swap)
        if legs.debit_exists and legs.credit_exists:
            continue
        on_chain_ok = is_tx_confirmed_on_chain(swap)
        needs_reconcile = False
        if legs.credit_exists and not legs.debit_exists:
            needs_reconcile = True
        elif legs.debit_exists and not legs.credit_exists:
            needs_reconcile = True
        elif swap.status == SwapSessionStatus.CONFIRMED.value and not (
            legs.debit_exists and legs.credit_exists
        ):
            needs_reconcile = True
        elif (
            swap.status == SwapSessionStatus.SUBMITTED.value
            and on_chain_ok
            and not (legs.debit_exists and legs.credit_exists)
        ):
            needs_reconcile = True
        if needs_reconcile:
            out.append(swap)
            seen.add(sid)
        if len(out) >= limit:
            break
    return out
