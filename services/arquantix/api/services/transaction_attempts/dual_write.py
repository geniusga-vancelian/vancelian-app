"""Dual-write onchain_transaction_attempts — retry + trace critique si échec."""
from __future__ import annotations

import logging
import time
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.orm import Session

from config.supported_swap_assets import SUPPORTED_SWAP_CHAINS, normalize_chain_key

from .models import OnchainTransactionAttempt
from .enums import AttemptOperationType, AttemptProtocol, AttemptStepType
from .schemas import AttemptCreateInput, AttemptTransitionInput
from .service import OnchainTransactionAttemptService
from .repository import OnchainTransactionAttemptRepository
from .tx_hash_canonical import (
    attach_secondary_swap_legacy,
    find_attempt_by_chain_tx,
    swap_legacy_record,
    tx_hash_canonical_idempotency_key,
)

logger = logging.getLogger(__name__)

DUAL_WRITE_MAX_ATTEMPTS = 3
DUAL_WRITE_RETRY_DELAY_SECONDS = 0.05

LINKED_SWAPS = "person_wallet_swaps"


def _run_dual_write_with_retry(
    operation: str,
    fn: Callable[[], None],
    *,
    swap_id: str,
    tx_hash: str | None = None,
) -> None:
    last_exc: Exception | None = None
    for attempt in range(1, DUAL_WRITE_MAX_ATTEMPTS + 1):
        try:
            fn()
            return
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "attempt.dual_write.retry",
                extra={
                    "operation": operation,
                    "swap_id": swap_id,
                    "tx_hash": tx_hash,
                    "attempt": attempt,
                    "error": str(exc),
                },
                exc_info=True,
            )
            if attempt < DUAL_WRITE_MAX_ATTEMPTS:
                time.sleep(DUAL_WRITE_RETRY_DELAY_SECONDS * attempt)
    logger.critical(
        "attempt.dual_write.failed_after_retries",
        extra={
            "operation": operation,
            "swap_id": swap_id,
            "tx_hash": tx_hash,
            "attempts": DUAL_WRITE_MAX_ATTEMPTS,
            "error": str(last_exc) if last_exc else "unknown",
        },
        exc_info=last_exc is not None,
    )
    try:
        from services.transaction_trace.transaction_trace_logger import log_transaction_trace
        from services.transaction_trace.enums import TraceEventType

        log_transaction_trace(
            TraceEventType.RECONCILIATION_GAP_DETECTED,
            source="dual_write",
            message=f"dual_write_failed:{operation}",
            linked_table=LINKED_SWAPS,
            metadata_json={
                "operation": operation,
                "swap_id": swap_id,
                "tx_hash": tx_hash,
                "error": str(last_exc) if last_exc else "unknown",
            },
        )
    except Exception:
        pass
LINKED_VAULT = "onchain_vault_transactions"


def _chain_id_from_swap(swap) -> int:
    try:
        meta = SUPPORTED_SWAP_CHAINS.get(normalize_chain_key(swap.from_chain), {})
        return int(meta.get("lifi_chain_id") or 8453)
    except Exception:
        return 8453


def _lifi_protocol_for_swap(swap) -> str:
    from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
        is_bundle_internal_swap,
    )

    if is_bundle_internal_swap(swap):
        return AttemptProtocol.INTERNAL_BUNDLE.value
    return AttemptProtocol.LIFI.value


def _resolve_intent_id_for_swap(db: Session, swap) -> UUID | None:
    try:
        from services.transaction_intents.repository import TransactionIntentRepository

        row = TransactionIntentRepository.find_by_linked(
            db,
            linked_table=LINKED_SWAPS,
            linked_id=swap.id,
        )
        return row.id if row else None
    except Exception:
        return None


def _attempt_key(prefix: str, *, swap_id: UUID, step: str) -> str:
    return f"{prefix}:{swap_id}:{step}"


def _resolve_swap_attempt_for_transition(
    db: Session,
    swap,
    *,
    tx_hash: str,
    step_type: str = AttemptStepType.SWAP.value,
) -> tuple[str, Any | None]:
    """Retourne (idempotency_key, attempt_row) pour transitions swap avec tx_hash."""
    chain_id = _chain_id_from_swap(swap)
    norm_tx = tx_hash.strip().lower()
    canonical_idem = tx_hash_canonical_idempotency_key(chain_id=chain_id, tx_hash=norm_tx)
    swap_idem = _attempt_key("lifi", swap_id=swap.id, step="swap")

    by_tx = find_attempt_by_chain_tx(
        db,
        chain_id=chain_id,
        tx_hash=norm_tx,
        step_type=step_type,
    )
    if by_tx is not None:
        return by_tx.idempotency_key, by_tx

    by_swap = OnchainTransactionAttemptRepository.find_by_composite_key(
        db,
        idempotency_key=swap_idem,
        step_type=step_type,
    )
    if by_swap is not None:
        return by_swap.idempotency_key, by_swap

    return canonical_idem, None


def dual_write_lifi_approval_submitted(
    db: Session,
    swap,
    *,
    approval_tx_hash: str,
    intent_id: UUID | None = None,
) -> None:
    """Approval hash distinct = attempt distinct (doctrine LI.FI)."""

    def _write() -> None:
        protocol = _lifi_protocol_for_swap(swap)
        chain_id = _chain_id_from_swap(swap)
        resolved_intent = intent_id or _resolve_intent_id_for_swap(db, swap)
        group_key = str(swap.id)
        idem = _attempt_key("lifi", swap_id=swap.id, step="approve")

        OnchainTransactionAttemptService.create_prepared_attempt(
            db,
            AttemptCreateInput(
                person_id=swap.person_id,
                chain_id=chain_id,
                protocol=protocol,
                operation_type=AttemptOperationType.APPROVE.value,
                step_type=AttemptStepType.APPROVE.value,
                idempotency_key=idem,
                group_key=group_key,
                intent_id=resolved_intent,
                linked_table=LINKED_SWAPS,
                linked_id=swap.id,
                asset_in=swap.from_asset,
                amount_in=str(swap.amount_in) if swap.amount_in is not None else None,
                metadata_patch={"dual_write_source": "lifi_execute.approval"},
            ),
        )
        OnchainTransactionAttemptService.mark_submitted(
            db,
            idempotency_key=idem,
            step_type=AttemptStepType.APPROVE.value,
            transition=AttemptTransitionInput(tx_hash=approval_tx_hash),
        )

    _run_dual_write_with_retry(
        "lifi_approval_submitted",
        _write,
        swap_id=str(getattr(swap, "id", "")),
        tx_hash=approval_tx_hash,
    )


def dual_write_lifi_swap_submitted(
    db: Session,
    swap,
    *,
    tx_hash: str,
    intent_id: UUID | None = None,
) -> None:
    """
    Swap avec tx_hash : canonicalisation par (chain_id, tx_hash).

    Deux swaps bundle partageant le même hash → 1 attempt + secondaries en metadata.
    """

    def _write() -> None:
        protocol = _lifi_protocol_for_swap(swap)
        chain_id = _chain_id_from_swap(swap)
        resolved_intent_id = intent_id or _resolve_intent_id_for_swap(db, swap)
        norm_tx = tx_hash.strip().lower()
        canonical_idem = tx_hash_canonical_idempotency_key(chain_id=chain_id, tx_hash=norm_tx)
        swap_idem = _attempt_key("lifi", swap_id=swap.id, step="swap")
        secondary = swap_legacy_record(
            swap,
            protocol=protocol,
            intent_id=resolved_intent_id,
            chain_id=chain_id,
        )

        existing_tx = find_attempt_by_chain_tx(
            db,
            chain_id=chain_id,
            tx_hash=norm_tx,
            step_type=AttemptStepType.SWAP.value,
        )
        if existing_tx is not None:
            if existing_tx.linked_id == swap.id:
                OnchainTransactionAttemptService.mark_submitted(
                    db,
                    idempotency_key=existing_tx.idempotency_key,
                    step_type=AttemptStepType.SWAP.value,
                    transition=AttemptTransitionInput(tx_hash=norm_tx),
                )
            else:
                attach_secondary_swap_legacy(db, existing_tx, secondary)
            return

        existing_swap = OnchainTransactionAttemptRepository.find_by_composite_key(
            db,
            idempotency_key=swap_idem,
            step_type=AttemptStepType.SWAP.value,
        )
        if existing_swap is not None and existing_swap.linked_id == swap.id:
            if existing_swap.idempotency_key != canonical_idem:
                existing_swap.idempotency_key = canonical_idem
            existing_swap.tx_hash = norm_tx
            db.add(existing_swap)
            db.flush()
            OnchainTransactionAttemptService.mark_submitted(
                db,
                idempotency_key=canonical_idem,
                step_type=AttemptStepType.SWAP.value,
                transition=AttemptTransitionInput(tx_hash=norm_tx),
            )
            return

        OnchainTransactionAttemptService.create_prepared_attempt(
            db,
            AttemptCreateInput(
                person_id=swap.person_id,
                chain_id=chain_id,
                protocol=protocol,
                operation_type=AttemptOperationType.SWAP.value,
                step_type=AttemptStepType.SWAP.value,
                idempotency_key=canonical_idem,
                group_key=str(swap.id),
                intent_id=resolved_intent_id,
                linked_table=LINKED_SWAPS,
                linked_id=swap.id,
                asset_in=swap.from_asset,
                asset_out=swap.to_asset,
                amount_in=str(swap.amount_in) if swap.amount_in is not None else None,
                amount_out_expected=str(swap.estimated_receive)
                if swap.estimated_receive is not None
                else None,
                metadata_patch={
                    "dual_write_source": "lifi_execute.submit",
                    "grouped_by_tx_hash": False,
                    "secondary_legacy_records": [],
                },
            ),
        )
        OnchainTransactionAttemptService.mark_submitted(
            db,
            idempotency_key=canonical_idem,
            step_type=AttemptStepType.SWAP.value,
            transition=AttemptTransitionInput(tx_hash=norm_tx),
        )

    _run_dual_write_with_retry(
        "lifi_swap_submitted",
        _write,
        swap_id=str(getattr(swap, "id", "")),
        tx_hash=tx_hash,
    )


def dual_write_lifi_swap_confirmed(
    db: Session,
    swap,
    *,
    tx_hash: str | None = None,
    failed: bool = False,
    reverted: bool = False,
    error_message: str | None = None,
) -> None:
    def _write() -> None:
        effective_tx = (tx_hash or swap.tx_hash or "").strip()
        if not effective_tx:
            idem = _attempt_key("lifi", swap_id=swap.id, step="swap")
        else:
            idem, attempt = _resolve_swap_attempt_for_transition(
                db,
                swap,
                tx_hash=effective_tx,
            )
            if attempt is not None and attempt.linked_id != swap.id:
                protocol = _lifi_protocol_for_swap(swap)
                intent_id = _resolve_intent_id_for_swap(db, swap)
                attach_secondary_swap_legacy(
                    db,
                    attempt,
                    swap_legacy_record(
                        swap,
                        protocol=protocol,
                        chain_id=_chain_id_from_swap(swap),
                        intent_id=intent_id,
                    ),
                )
                return

        transition = AttemptTransitionInput(
            tx_hash=effective_tx or None,
            error_message=error_message,
        )
        if failed or reverted:
            OnchainTransactionAttemptService.mark_failed(
                db,
                idempotency_key=idem,
                step_type=AttemptStepType.SWAP.value,
                transition=transition,
                reverted=reverted,
            )
            return
        OnchainTransactionAttemptService.mark_confirmed(
            db,
            idempotency_key=idem,
            step_type=AttemptStepType.SWAP.value,
            transition=transition,
        )

    _run_dual_write_with_retry(
        "lifi_swap_confirmed",
        _write,
        swap_id=str(getattr(swap, "id", "")),
        tx_hash=tx_hash or getattr(swap, "tx_hash", None),
    )


def _vault_protocol(integration_mode: str | None) -> str:
    mode = (integration_mode or "").strip().lower()
    if mode == "ledgity_vault":
        return AttemptProtocol.LEDGITY.value
    if mode == "lombard_v1":
        return AttemptProtocol.LOMBARD.value
    return AttemptProtocol.MORPHO.value


def _vault_step_type(operation: str) -> str | None:
    op = (operation or "").strip().lower()
    mapping = {
        "approve": AttemptStepType.APPROVE.value,
        "deposit": AttemptStepType.DEPOSIT.value,
        "withdraw": AttemptStepType.WITHDRAW.value,
        "authorize": AttemptStepType.AUTHORIZE.value,
        "open_loan": AttemptStepType.OPEN_LOAN.value,
        "collateral_supply": AttemptStepType.COLLATERAL_SUPPLY.value,
    }
    return mapping.get(op)


def _vault_operation_type(operation: str) -> str:
    op = (operation or "").strip().lower()
    if op in ("approve", "authorize"):
        return AttemptOperationType.APPROVE.value
    if op == "open_loan":
        return AttemptOperationType.BORROW.value
    if op == "withdraw":
        return AttemptOperationType.WITHDRAW.value
    return AttemptOperationType.DEPOSIT.value


def _apply_vault_attempt_status(
    db: Session,
    attempt: OnchainTransactionAttempt,
    *,
    vault_status: str,
    tx_hash: str | None,
    intent_id: UUID | None = None,
) -> None:
    """Met à jour un attempt vault existant (pending → receipt success/failed)."""
    from .enums import AttemptStatus

    if intent_id is not None and attempt.intent_id is None:
        attempt.intent_id = intent_id
        db.add(attempt)
        db.flush()

    status_norm = (vault_status or "").strip().lower()
    norm_tx = tx_hash.strip().lower() if tx_hash else None
    current = (attempt.status or AttemptStatus.PREPARED.value).strip().lower()
    idem = attempt.idempotency_key
    step_type = attempt.step_type
    transition = AttemptTransitionInput(tx_hash=norm_tx) if norm_tx else AttemptTransitionInput()

    if status_norm == "success":
        if (
            current == AttemptStatus.CONFIRMED.value
            and attempt.tx_hash
            and (norm_tx is None or attempt.tx_hash == norm_tx)
        ):
            return
        OnchainTransactionAttemptService.mark_confirmed(
            db,
            idempotency_key=idem,
            step_type=step_type,
            transition=transition,
        )
        return

    if status_norm in ("failed", "reverted"):
        if current in (AttemptStatus.FAILED.value, AttemptStatus.REVERTED.value):
            return
        OnchainTransactionAttemptService.mark_failed(
            db,
            idempotency_key=idem,
            step_type=step_type,
            transition=transition,
            reverted=status_norm == "reverted",
        )
        return

    if norm_tx and status_norm in ("pending", "submitted", ""):
        if current in (AttemptStatus.CONFIRMED.value, AttemptStatus.SUBMITTED.value):
            return
        OnchainTransactionAttemptService.mark_submitted(
            db,
            idempotency_key=idem,
            step_type=step_type,
            transition=transition,
        )


def _find_existing_vault_attempt(
    db: Session,
    *,
    vault_transaction_id: str,
    step_type: str,
    idempotency_key: str,
    chain_id: int,
    tx_hash: str | None,
) -> OnchainTransactionAttempt | None:
    existing_ref = (
        db.query(OnchainTransactionAttempt)
        .filter(
            OnchainTransactionAttempt.linked_reference_id == vault_transaction_id,
            OnchainTransactionAttempt.step_type == step_type,
        )
        .first()
    )
    if existing_ref is not None:
        return existing_ref

    by_idem = OnchainTransactionAttemptRepository.find_by_composite_key(
        db,
        idempotency_key=idempotency_key,
        step_type=step_type,
    )
    if by_idem is not None:
        return by_idem

    if tx_hash:
        norm_tx = tx_hash.strip().lower()
        by_tx = find_attempt_by_chain_tx(
            db,
            chain_id=chain_id,
            tx_hash=norm_tx,
            step_type=step_type,
        )
        if by_tx is not None and by_tx.linked_reference_id == vault_transaction_id:
            return by_tx
    return None


VAULT_SCOPE_HOOK_MODES = frozenset({"direct_morpho", "ledgity_vault"})
VAULT_SCOPE_HOOK_OPERATIONS = frozenset({"deposit", "withdraw"})


def _maybe_apply_vault_scope_movement_after_success(
    db: Session,
    *,
    person_id: UUID,
    vault_transaction_id: str,
    integration_mode: str,
    operation: str,
    vault_status: str | None,
) -> None:
    """Phase 3A+1a — best-effort PE vault scope après OVT Morpho/Ledgity success."""
    mode = (integration_mode or "").strip().lower()
    if mode == "lombard_v1" or mode not in VAULT_SCOPE_HOOK_MODES:
        return
    op = (operation or "").strip().lower()
    if op not in VAULT_SCOPE_HOOK_OPERATIONS:
        return
    if (vault_status or "").strip().lower() != "success":
        return
    try:
        from services.portfolio_engine.vault_execution.vault_ovt_bridge import (
            apply_vault_scope_movement_for_ovt,
        )

        result = apply_vault_scope_movement_for_ovt(
            db,
            ovt_id=vault_transaction_id,
            person_id=person_id,
            dry_run=False,
        )
        if not result.get("ok"):
            logger.warning(
                "attempt.dual_write.vault_scope_movement_skipped",
                extra={
                    "vault_transaction_id": vault_transaction_id,
                    "person_id": str(person_id),
                    "integration_mode": mode,
                    "operation": op,
                    "reason": result.get("reason"),
                    "detail": result.get("message"),
                },
            )
    except Exception as exc:
        logger.warning(
            "attempt.dual_write.vault_scope_movement_failed",
            extra={
                "vault_transaction_id": vault_transaction_id,
                "person_id": str(person_id),
                "integration_mode": mode,
                "operation": op,
                "error": str(exc),
            },
            exc_info=True,
        )


def _maybe_apply_lombard_scope_movement_after_success(
    db: Session,
    *,
    person_id: UUID,
    vault_transaction_id: str,
    integration_mode: str,
    operation: str,
    vault_status: str | None,
) -> None:
    """Phase 3B — best-effort PE Lombard scope après OVT open_loan success."""
    mode = (integration_mode or "").strip().lower()
    if mode != "lombard_v1":
        return
    if (vault_status or "").strip().lower() != "success":
        return
    op = (operation or "").strip().lower()
    if op not in ("open_loan", "deposit"):
        return
    try:
        from services.portfolio_engine.lombard_execution.lombard_ovt_bridge import (
            apply_lombard_scope_movement_for_ovt,
        )

        result = apply_lombard_scope_movement_for_ovt(
            db,
            ovt_id=vault_transaction_id,
            person_id=person_id,
            dry_run=False,
        )
        if not result.get("ok"):
            reason = str(result.get("reason") or "")
            if reason in ("not_lombard_open_loan", "ovt_not_found"):
                return
            logger.warning(
                "attempt.dual_write.lombard_scope_movement_skipped",
                extra={
                    "vault_transaction_id": vault_transaction_id,
                    "person_id": str(person_id),
                    "integration_mode": mode,
                    "operation": op,
                    "reason": reason,
                    "detail": result.get("message"),
                },
            )
    except Exception as exc:
        logger.warning(
            "attempt.dual_write.lombard_scope_movement_failed",
            extra={
                "vault_transaction_id": vault_transaction_id,
                "person_id": str(person_id),
                "integration_mode": mode,
                "operation": op,
                "error": str(exc),
            },
            exc_info=True,
        )


def dual_write_vault_step(
    db: Session,
    *,
    person_id: UUID,
    vault_transaction_id: str,
    chain_id: int,
    wallet_address: str,
    operation: str,
    group_key: str,
    step_index: int,
    integration_mode: str,
    tx_hash: str | None = None,
    vault_status: str | None = None,
    intent_id: UUID | None = None,
    asset_symbol: str | None = None,
    amount_raw: str | None = None,
    dual_write_source: str = "vault_intent_sync",
) -> None:
    step_type = _vault_step_type(operation)
    if step_type is None:
        return
    try:
        protocol = _vault_protocol(integration_mode)
        idem = f"{protocol}:{person_id}:{group_key}:{step_type}:{step_index}"
        status_norm = (vault_status or "").strip().lower()

        existing = _find_existing_vault_attempt(
            db,
            vault_transaction_id=vault_transaction_id,
            step_type=step_type,
            idempotency_key=idem,
            chain_id=chain_id,
            tx_hash=tx_hash,
        )
        if existing is not None:
            _apply_vault_attempt_status(
                db,
                existing,
                vault_status=status_norm,
                tx_hash=tx_hash,
                intent_id=intent_id,
            )
            _maybe_apply_vault_scope_movement_after_success(
                db,
                person_id=person_id,
                vault_transaction_id=vault_transaction_id,
                integration_mode=integration_mode,
                operation=operation,
                vault_status=status_norm,
            )
            _maybe_apply_lombard_scope_movement_after_success(
                db,
                person_id=person_id,
                vault_transaction_id=vault_transaction_id,
                integration_mode=integration_mode,
                operation=operation,
                vault_status=status_norm,
            )
            return

        if tx_hash:
            norm_tx = tx_hash.strip().lower()
            existing_tx = find_attempt_by_chain_tx(
                db,
                chain_id=chain_id,
                tx_hash=norm_tx,
                step_type=step_type,
            )
            if existing_tx is not None:
                _maybe_apply_vault_scope_movement_after_success(
                    db,
                    person_id=person_id,
                    vault_transaction_id=vault_transaction_id,
                    integration_mode=integration_mode,
                    operation=operation,
                    vault_status=status_norm,
                )
                _maybe_apply_lombard_scope_movement_after_success(
                    db,
                    person_id=person_id,
                    vault_transaction_id=vault_transaction_id,
                    integration_mode=integration_mode,
                    operation=operation,
                    vault_status=status_norm,
                )
                return

        OnchainTransactionAttemptService.create_prepared_attempt(
            db,
            AttemptCreateInput(
                person_id=person_id,
                chain_id=chain_id,
                protocol=protocol,
                operation_type=_vault_operation_type(operation),
                step_type=step_type,
                idempotency_key=idem,
                step_index=step_index,
                group_key=group_key,
                intent_id=intent_id,
                wallet_address=wallet_address,
                linked_table=LINKED_VAULT,
                linked_reference_id=vault_transaction_id,
                asset_in=asset_symbol,
                amount_in=amount_raw,
                metadata_patch={
                    "dual_write_source": dual_write_source,
                    "integration_mode": integration_mode,
                    "vault_operation": operation,
                },
            ),
        )

        if tx_hash and status_norm in ("pending", "submitted", ""):
            OnchainTransactionAttemptService.mark_submitted(
                db,
                idempotency_key=idem,
                step_type=step_type,
                transition=AttemptTransitionInput(tx_hash=tx_hash),
            )
        elif status_norm == "success":
            OnchainTransactionAttemptService.mark_confirmed(
                db,
                idempotency_key=idem,
                step_type=step_type,
                transition=AttemptTransitionInput(tx_hash=tx_hash),
            )
        elif status_norm in ("failed", "reverted"):
            OnchainTransactionAttemptService.mark_failed(
                db,
                idempotency_key=idem,
                step_type=step_type,
                transition=AttemptTransitionInput(tx_hash=tx_hash),
                reverted=status_norm == "reverted",
            )

        _maybe_apply_vault_scope_movement_after_success(
            db,
            person_id=person_id,
            vault_transaction_id=vault_transaction_id,
            integration_mode=integration_mode,
            operation=operation,
            vault_status=status_norm,
        )
        _maybe_apply_lombard_scope_movement_after_success(
            db,
            person_id=person_id,
            vault_transaction_id=vault_transaction_id,
            integration_mode=integration_mode,
            operation=operation,
            vault_status=status_norm,
        )
    except Exception as exc:
        logger.warning(
            "attempt.dual_write.vault_step_failed",
            extra={
                "vault_transaction_id": vault_transaction_id,
                "operation": operation,
                "error": str(exc),
            },
            exc_info=True,
        )


def dual_write_lombard_step_from_receipt(
    db: Session,
    *,
    person_id: UUID,
    group_key: str,
    market_or_vault: str,
    ledger_entry_id: str,
    tx_hash: str | None,
    ledger_status: str,
) -> None:
    try:
        from services.transaction_intents.repository import TransactionIntentRepository
        from services.transaction_intents.lombard_intent_sync import _find_step_index, _normalize_steps

        row = TransactionIntentRepository.find_by_lombard_group(
            db,
            person_id=person_id,
            group_key=group_key,
            market_or_vault=market_or_vault,
        )
        if row is None:
            return
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        steps = _normalize_steps(meta.get("steps"))
        idx = _find_step_index(steps, ledger_entry_id)
        if idx is None:
            return
        step = steps[idx]
        operation = str(step.get("step") or "approve")
        step_index = idx
        chain_id = row.chain_id or 8453
        dual_write_vault_step(
            db,
            person_id=person_id,
            vault_transaction_id=ledger_entry_id,
            chain_id=chain_id,
            wallet_address=row.wallet_address or "",
            operation=operation,
            group_key=group_key,
            step_index=step_index,
            integration_mode="lombard_v1",
            tx_hash=tx_hash,
            vault_status=ledger_status,
            intent_id=row.id,
        )
    except Exception as exc:
        logger.warning(
            "attempt.dual_write.lombard_step_failed",
            extra={"ledger_entry_id": ledger_entry_id, "error": str(exc)},
            exc_info=True,
        )


def resolve_intent_id_for_vault_transaction(
    db: Session,
    *,
    person_id: UUID,
    vault_transaction_id: str,
) -> UUID | None:
    try:
        from services.transaction_intents.repository import TransactionIntentRepository

        row = TransactionIntentRepository.find_by_vault_transaction(
            db,
            vault_transaction_id=vault_transaction_id,
            person_id=person_id,
        )
        return row.id if row else None
    except Exception:
        return None
