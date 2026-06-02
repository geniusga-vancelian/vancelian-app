"""Synchronisation transaction_intents ↔ Lombard Borrow (Phase 7C — observabilité)."""
from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .enums import IntentOperationType, IntentProductType, IntentStatus
from .raw_event_link import try_link_raw_event_to_intent
from .repository import TransactionIntentRepository
from .lombard_retry_linking import LombardRetryLinkError, resolve_lombard_prepare_link_metadata

logger = logging.getLogger(__name__)

LOMBARD_LINKED_TABLE = "onchain_vault_transactions_group"
LOMBARD_PRODUCT = IntentProductType.LOMBARD_BORROW.value
LOMBARD_OPERATION = IntentOperationType.BORROW.value

LOMBARD_STEPS = frozenset({"approve", "authorize", "open_loan"})

STEP_PENDING = "pending"
STEP_SUBMITTED = "submitted"
STEP_CONFIRMED = "confirmed"
STEP_FAILED = "failed"

LOMBARD_AUTH_STEPS = frozenset({"approve", "authorize"})
LOMBARD_TERMINAL_OUTCOME_BORROW_NOT_OPENED = "borrow_not_opened"


def _find_lombard_step(steps: list[dict[str, Any]], step_name: str) -> Optional[dict[str, Any]]:
    target = step_name.strip().lower()
    for step in steps:
        if str(step.get("step") or "").strip().lower() == target:
            return step
    return None


def lombard_auth_prerequisite_confirmed(steps: list[dict[str, Any]]) -> bool:
    """True si approve ou authorize est confirmé (prérequis retry open_loan)."""
    for name in LOMBARD_AUTH_STEPS:
        step = _find_lombard_step(steps, name)
        if step is not None and str(step.get("status") or "") == STEP_CONFIRMED:
            return True
    return False


def is_lombard_retryable_failed(steps: list[dict[str, Any]]) -> bool:
    """open_loan failed + approve/authorize confirmé → échec récupérable."""
    open_loan = _find_lombard_step(steps, "open_loan")
    if open_loan is None:
        return False
    if str(open_loan.get("status") or "") != STEP_FAILED:
        return False
    return lombard_auth_prerequisite_confirmed(steps)


def lombard_terminal_metadata_patch(status: str) -> dict[str, Any]:
    if status == IntentStatus.RETRYABLE_FAILED.value:
        return {
            "lombard_status_detail": "retryable_failed",
            "terminal_outcome": LOMBARD_TERMINAL_OUTCOME_BORROW_NOT_OPENED,
        }
    if status == IntentStatus.FAILED_FINAL.value:
        return {
            "lombard_status_detail": "failed_final",
            "terminal_outcome": "retry_exhausted",
        }
    if status == IntentStatus.SUPERSEDED.value:
        return {"lombard_status_detail": "superseded"}
    return {}


def is_lombard_terminal_intent_status(status: str) -> bool:
    norm = (status or "").strip().lower()
    return norm in {
        IntentStatus.CONFIRMED.value,
        IntentStatus.FAILED.value,
        IntentStatus.FAILED_FINAL.value,
        IntentStatus.SUPERSEDED.value,
        IntentStatus.RECONCILIATION_REQUIRED.value,
    }


def lombard_parent_intent_key(
    *,
    person_id: UUID,
    market_or_vault: str,
    idempotency_key: str,
) -> str:
    return f"lombard_borrow:{person_id}:{market_or_vault.lower()}:{idempotency_key}"


def _ledger_status_to_step_status(ledger_status: str) -> str:
    norm = (ledger_status or "").strip().lower()
    if norm == "success":
        return STEP_CONFIRMED
    if norm in ("reverted", "failed"):
        return STEP_FAILED
    if norm == "pending":
        return STEP_PENDING
    return STEP_PENDING


def _normalize_steps(steps: Any) -> list[dict[str, Any]]:
    if not isinstance(steps, list):
        return []
    out: list[dict[str, Any]] = []
    for item in steps:
        if isinstance(item, dict) and item.get("step"):
            out.append(dict(item))
    return out


def _find_step_index(steps: list[dict[str, Any]], ledger_entry_id: str) -> Optional[int]:
    for i, step in enumerate(steps):
        if str(step.get("ledger_entry_id") or "") == ledger_entry_id:
            return i
    return None


def recompute_lombard_parent_status(steps: list[dict[str, Any]]) -> str:
    if not steps:
        return IntentStatus.AWAITING_SIGNATURE.value

    statuses = [str(s.get("status") or STEP_PENDING) for s in steps]

    if all(s == STEP_CONFIRMED for s in statuses):
        return IntentStatus.CONFIRMED.value
    if all(s == STEP_FAILED for s in statuses):
        return IntentStatus.FAILED.value

    if is_lombard_retryable_failed(steps):
        return IntentStatus.RETRYABLE_FAILED.value

    open_loan = _find_lombard_step(steps, "open_loan")
    if open_loan is not None and str(open_loan.get("status") or "") == STEP_FAILED:
        return IntentStatus.FAILED.value

    if any(s == STEP_CONFIRMED for s in statuses) and any(
        s in (STEP_FAILED, STEP_PENDING, STEP_SUBMITTED) for s in statuses
    ):
        return IntentStatus.PARTIAL.value

    if any(s in (STEP_SUBMITTED, STEP_CONFIRMED, STEP_FAILED) for s in statuses):
        if any(s == STEP_PENDING for s in statuses):
            return IntentStatus.PARTIAL.value
        return IntentStatus.SUBMITTED.value

    if any(s.get("tx_hash") for s in steps):
        return IntentStatus.SUBMITTED.value

    return IntentStatus.AWAITING_SIGNATURE.value


def _parent_tx_hash_from_steps(steps: list[dict[str, Any]]) -> Optional[str]:
    for preferred in ("open_loan", "authorize", "approve"):
        for step in reversed(steps):
            if step.get("step") == preferred and step.get("tx_hash"):
                return str(step["tx_hash"]).strip().lower()
    for step in reversed(steps):
        if step.get("tx_hash"):
            return str(step["tx_hash"]).strip().lower()
    return None


def _save_parent(
    db: Session,
    row: Any,
    *,
    steps: list[dict[str, Any]],
    status: Optional[str] = None,
) -> dict[str, Any]:
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    merged = {**meta, "steps": steps, "group_key": meta.get("group_key") or row.linked_reference_id}
    if status is not None:
        row.status = status
        merged.update(lombard_terminal_metadata_patch(status))
    row.metadata_json = merged
    tx = _parent_tx_hash_from_steps(steps)
    if tx:
        row.tx_hash = tx
    db.add(row)
    db.flush()
    if tx:
        try_link_raw_event_to_intent(db, row)
    if status == IntentStatus.CONFIRMED.value:
        _maybe_supersede_lombard_retry_predecessor(db, row, merged)
    return {"intent_id": str(row.id), "status": row.status, "steps": steps}


def _maybe_supersede_lombard_retry_predecessor(
    db: Session,
    row: Any,
    merged_meta: dict[str, Any],
) -> None:
    retry_of = str(merged_meta.get("retry_of_group_key") or "").strip()
    if not retry_of:
        return
    market_or_vault = str(merged_meta.get("market_id") or "").strip()
    superseded_by_group_key = str(merged_meta.get("group_key") or row.linked_reference_id or "").strip()
    if not superseded_by_group_key:
        return
    mark_lombard_intent_superseded(
        db,
        person_id=row.person_id,
        group_key=retry_of,
        market_or_vault=market_or_vault,
        superseded_by_group_key=superseded_by_group_key,
        superseded_by_intent_id=str(row.id),
    )


def ensure_lombard_parent_intent(
    db: Session,
    *,
    person_id: UUID,
    group_key: str,
    market_or_vault: str,
    wallet_address: str,
    chain_id: int,
    steps: list[dict[str, Any]],
    extra_metadata: dict[str, Any] | None = None,
    logical_borrow_id: Optional[str] = None,
    retry_of_group_key: Optional[str] = None,
    retry_attempt_number: int = 0,
) -> dict[str, Any] | None:
    """Crée ou met à jour le parent Lombard + steps en pending."""
    try:
        link_meta = resolve_lombard_prepare_link_metadata(
            db,
            person_id=person_id,
            market_or_vault=market_or_vault,
            logical_borrow_id=logical_borrow_id,
            retry_of_group_key=retry_of_group_key,
            retry_attempt_number=retry_attempt_number,
        )
        built_steps: list[dict[str, Any]] = []
        for raw in steps:
            step_name = str(raw.get("step") or "").strip().lower()
            if step_name not in LOMBARD_STEPS:
                continue
            built_steps.append(
                {
                    "step": step_name,
                    "tx_index": int(raw.get("tx_index") or 0),
                    "ledger_entry_id": str(raw.get("ledger_entry_id") or ""),
                    "tx_hash": raw.get("tx_hash"),
                    "status": STEP_PENDING,
                    "receipt_status": None,
                    "raw_onchain_event_id": None,
                }
            )

        if not built_steps:
            return None

        row, _created = TransactionIntentRepository.upsert(
            db,
            person_id=person_id,
            product_type=LOMBARD_PRODUCT,
            operation_type=LOMBARD_OPERATION,
            idempotency_key=lombard_parent_intent_key(
                person_id=person_id,
                market_or_vault=market_or_vault,
                idempotency_key=group_key,
            ),
            status=IntentStatus.AWAITING_SIGNATURE.value,
            wallet_address=wallet_address,
            chain_id=chain_id,
            linked_table=LOMBARD_LINKED_TABLE,
            linked_reference_id=group_key,
            metadata_patch={
                "group_key": group_key,
                "market_id": market_or_vault.lower(),
                "steps": built_steps,
                **link_meta,
                **(extra_metadata or {}),
            },
        )
        return _save_parent(db, row, steps=built_steps, status=IntentStatus.AWAITING_SIGNATURE.value)
    except LombardRetryLinkError:
        raise
    except Exception as exc:
        logger.warning(
            "intent.lombard.prepare_failed",
            extra={"group_key": group_key, "error": str(exc)},
            exc_info=True,
        )
        return None


def mark_lombard_step_submitted(
    db: Session,
    *,
    person_id: UUID,
    group_key: str,
    market_or_vault: str,
    ledger_entry_id: str,
    tx_hash: str,
) -> dict[str, Any] | None:
    try:
        row = TransactionIntentRepository.find_by_lombard_group(
            db,
            person_id=person_id,
            group_key=group_key,
            market_or_vault=market_or_vault,
        )
        if row is None:
            return None

        steps = _normalize_steps((row.metadata_json or {}).get("steps"))
        idx = _find_step_index(steps, ledger_entry_id)
        if idx is None:
            return None

        steps[idx]["tx_hash"] = tx_hash.strip().lower()
        steps[idx]["status"] = STEP_SUBMITTED
        parent_status = recompute_lombard_parent_status(steps)
        return _save_parent(db, row, steps=steps, status=parent_status)
    except Exception as exc:
        logger.warning("intent.lombard.step_submitted_failed", extra={"error": str(exc)})
        return None


def mark_lombard_step_confirmed(
    db: Session,
    *,
    person_id: UUID,
    group_key: str,
    market_or_vault: str,
    ledger_entry_id: str,
    tx_hash: Optional[str] = None,
    receipt_status: Optional[str] = None,
) -> dict[str, Any] | None:
    return _mark_lombard_step_terminal(
        db,
        person_id=person_id,
        group_key=group_key,
        market_or_vault=market_or_vault,
        ledger_entry_id=ledger_entry_id,
        step_status=STEP_CONFIRMED,
        tx_hash=tx_hash,
        receipt_status=receipt_status or "success",
    )


def mark_lombard_step_failed(
    db: Session,
    *,
    person_id: UUID,
    group_key: str,
    market_or_vault: str,
    ledger_entry_id: str,
    tx_hash: Optional[str] = None,
    receipt_status: Optional[str] = None,
) -> dict[str, Any] | None:
    return _mark_lombard_step_terminal(
        db,
        person_id=person_id,
        group_key=group_key,
        market_or_vault=market_or_vault,
        ledger_entry_id=ledger_entry_id,
        step_status=STEP_FAILED,
        tx_hash=tx_hash,
        receipt_status=receipt_status,
    )


def _mark_lombard_step_terminal(
    db: Session,
    *,
    person_id: UUID,
    group_key: str,
    market_or_vault: str,
    ledger_entry_id: str,
    step_status: str,
    tx_hash: Optional[str],
    receipt_status: Optional[str],
) -> dict[str, Any] | None:
    try:
        row = TransactionIntentRepository.find_by_lombard_group(
            db,
            person_id=person_id,
            group_key=group_key,
            market_or_vault=market_or_vault,
        )
        if row is None:
            return None

        steps = _normalize_steps((row.metadata_json or {}).get("steps"))
        idx = _find_step_index(steps, ledger_entry_id)
        if idx is None:
            return None

        if tx_hash:
            steps[idx]["tx_hash"] = tx_hash.strip().lower()
        steps[idx]["status"] = step_status
        steps[idx]["receipt_status"] = receipt_status
        parent_status = recompute_lombard_parent_status(steps)
        return _save_parent(db, row, steps=steps, status=parent_status)
    except Exception as exc:
        logger.warning("intent.lombard.step_terminal_failed", extra={"error": str(exc)})
        return None


def sync_lombard_step_from_ledger_receipt(
    db: Session,
    *,
    person_id: UUID,
    group_key: str,
    market_or_vault: str,
    ledger_entry_id: str,
    tx_hash: Optional[str],
    ledger_status: str,
) -> dict[str, Any] | None:
    """Met à jour une step depuis un receipt confirm (idempotent)."""
    norm = (ledger_status or "").strip().lower()
    if tx_hash:
        mark_lombard_step_submitted(
            db,
            person_id=person_id,
            group_key=group_key,
            market_or_vault=market_or_vault,
            ledger_entry_id=ledger_entry_id,
            tx_hash=tx_hash,
        )

    if norm == "success":
        result = mark_lombard_step_confirmed(
            db,
            person_id=person_id,
            group_key=group_key,
            market_or_vault=market_or_vault,
            ledger_entry_id=ledger_entry_id,
            tx_hash=tx_hash,
            receipt_status=norm,
        )
    elif norm in ("reverted", "failed"):
        result = mark_lombard_step_failed(
            db,
            person_id=person_id,
            group_key=group_key,
            market_or_vault=market_or_vault,
            ledger_entry_id=ledger_entry_id,
            tx_hash=tx_hash,
            receipt_status=norm,
        )
    else:
        result = None

    from services.transaction_attempts.dual_write import dual_write_lombard_step_from_receipt

    dual_write_lombard_step_from_receipt(
        db,
        person_id=person_id,
        group_key=group_key,
        market_or_vault=market_or_vault,
        ledger_entry_id=ledger_entry_id,
        tx_hash=tx_hash,
        ledger_status=norm,
    )
    return result


def recompute_lombard_parent_intent(
    db: Session,
    *,
    person_id: UUID,
    group_key: str,
    market_or_vault: str,
) -> dict[str, Any] | None:
    try:
        row = TransactionIntentRepository.find_by_lombard_group(
            db,
            person_id=person_id,
            group_key=group_key,
            market_or_vault=market_or_vault,
        )
        if row is None:
            return None
        steps = _normalize_steps((row.metadata_json or {}).get("steps"))
        parent_status = recompute_lombard_parent_status(steps)
        return _save_parent(db, row, steps=steps, status=parent_status)
    except Exception as exc:
        logger.warning("intent.lombard.recompute_failed", extra={"error": str(exc)})
        return None


def mark_lombard_intent_superseded(
    db: Session,
    *,
    person_id: UUID,
    group_key: str,
    market_or_vault: str,
    superseded_by_group_key: str,
    superseded_by_intent_id: Optional[str] = None,
) -> dict[str, Any] | None:
    """Marque une tentative Lombard remplacée par un retry réussi (R3)."""
    try:
        row = TransactionIntentRepository.find_by_lombard_group(
            db,
            person_id=person_id,
            group_key=group_key,
            market_or_vault=market_or_vault,
        )
        if row is None:
            return None
        steps = _normalize_steps((row.metadata_json or {}).get("steps"))
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        row.metadata_json = {
            **meta,
            "superseded_by_group_key": superseded_by_group_key,
            **({"superseded_by_intent_id": superseded_by_intent_id} if superseded_by_intent_id else {}),
        }
        return _save_parent(db, row, steps=steps, status=IntentStatus.SUPERSEDED.value)
    except Exception as exc:
        logger.warning("intent.lombard.superseded_failed", extra={"error": str(exc)})
        return None


def mark_lombard_intent_failed_final(
    db: Session,
    *,
    person_id: UUID,
    group_key: str,
    market_or_vault: str,
    reason: str = "retry_exhausted",
) -> dict[str, Any] | None:
    """Clôture métier Lombard après retry épuisé (R3)."""
    try:
        row = TransactionIntentRepository.find_by_lombard_group(
            db,
            person_id=person_id,
            group_key=group_key,
            market_or_vault=market_or_vault,
        )
        if row is None:
            return None
        steps = _normalize_steps((row.metadata_json or {}).get("steps"))
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        row.metadata_json = {**meta, "failed_final_reason": reason}
        return _save_parent(db, row, steps=steps, status=IntentStatus.FAILED_FINAL.value)
    except Exception as exc:
        logger.warning("intent.lombard.failed_final_failed", extra={"error": str(exc)})
        return None


def mark_lombard_reconciliation_required(
    db: Session,
    *,
    person_id: UUID,
    group_key: str,
    market_or_vault: str,
    reason: str,
) -> dict[str, Any] | None:
    try:
        row = TransactionIntentRepository.find_by_lombard_group(
            db,
            person_id=person_id,
            group_key=group_key,
            market_or_vault=market_or_vault,
        )
        if row is None:
            return None
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        row.metadata_json = {**meta, "reconciliation_reason": reason}
        steps = _normalize_steps(meta.get("steps"))
        return _save_parent(
            db,
            row,
            steps=steps,
            status=IntentStatus.RECONCILIATION_REQUIRED.value,
        )
    except Exception as exc:
        logger.warning("intent.lombard.reconciliation_required_failed", extra={"error": str(exc)})
        return None
