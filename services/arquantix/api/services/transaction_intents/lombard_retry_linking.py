"""Lombard logical borrow linking (Phase 3B-R3 — metadata only, no migration)."""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from .enums import IntentProductType, IntentOperationType, IntentStatus
from .repository import TransactionIntentRepository, intent_to_dict

LOMBARD_LINKED_TABLE = "onchain_vault_transactions_group"
LOMBARD_PRODUCT = IntentProductType.LOMBARD_BORROW.value
LOMBARD_OPERATION = IntentOperationType.BORROW.value

LOMBARD_MAX_RETRY_ATTEMPTS = 1


class LombardRetryLinkError(ValueError):
    """Retry prepare rejected (exhausted, invalid predecessor, etc.)."""


def new_logical_borrow_id() -> str:
    return str(uuid4())


def lombard_link_metadata_from_intent(row: Any) -> dict[str, Any]:
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    return {
        "logical_borrow_id": meta.get("logical_borrow_id"),
        "retry_of_group_key": meta.get("retry_of_group_key"),
        "retry_attempt_number": int(meta.get("retry_attempt_number") or 0),
        "max_retry_attempts": int(meta.get("max_retry_attempts") or LOMBARD_MAX_RETRY_ATTEMPTS),
        "group_key": meta.get("group_key") or row.linked_reference_id,
        "status": row.status,
        "intent_id": str(row.id),
    }


def _query_lombard_by_logical_borrow_id(
    db: Session,
    *,
    person_id: UUID,
    logical_borrow_id: str,
) -> list[Any]:
    from services.onchain_indexer.models import TransactionIntent

    norm = logical_borrow_id.strip()
    return (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.person_id == person_id,
            TransactionIntent.product_type == LOMBARD_PRODUCT,
            TransactionIntent.operation_type == LOMBARD_OPERATION,
            TransactionIntent.linked_table == LOMBARD_LINKED_TABLE,
            TransactionIntent.metadata_json["logical_borrow_id"].as_string() == norm,
        )
        .order_by(TransactionIntent.created_at.asc())
        .all()
    )


def resolve_lombard_prepare_link_metadata(
    db: Session,
    *,
    person_id: UUID,
    market_or_vault: str,
    logical_borrow_id: Optional[str] = None,
    retry_of_group_key: Optional[str] = None,
    retry_attempt_number: int = 0,
) -> dict[str, Any]:
    """Build metadata for initial or retry Lombard prepare."""
    attempt = int(retry_attempt_number or 0)
    retry_key = (retry_of_group_key or "").strip() or None

    if retry_key:
        if attempt <= 0:
            raise LombardRetryLinkError("retry_attempt_number must be >= 1 for retry prepare")
        if attempt > LOMBARD_MAX_RETRY_ATTEMPTS:
            raise LombardRetryLinkError("max_retry_attempts exceeded")

        predecessor = TransactionIntentRepository.find_by_lombard_group(
            db,
            person_id=person_id,
            group_key=retry_key,
            market_or_vault=market_or_vault,
        )
        if predecessor is None:
            raise LombardRetryLinkError("retry predecessor intent not found")

        prev_meta = predecessor.metadata_json if isinstance(predecessor.metadata_json, dict) else {}
        if predecessor.status != IntentStatus.RETRYABLE_FAILED.value:
            raise LombardRetryLinkError("retry predecessor is not retryable_failed")

        resolved_logical = (logical_borrow_id or prev_meta.get("logical_borrow_id") or "").strip()
        if not resolved_logical:
            resolved_logical = new_logical_borrow_id()
        prev_logical = (prev_meta.get("logical_borrow_id") or "").strip()
        if prev_logical and resolved_logical != prev_logical:
            raise LombardRetryLinkError("logical_borrow_id mismatch with retry predecessor")

        siblings = _query_lombard_by_logical_borrow_id(
            db, person_id=person_id, logical_borrow_id=resolved_logical
        )
        if any(int((s.metadata_json or {}).get("retry_attempt_number") or 0) >= 1 for s in siblings):
            raise LombardRetryLinkError("retry already attempted for logical_borrow_id")

        return {
            "logical_borrow_id": resolved_logical,
            "retry_of_group_key": retry_key,
            "retry_attempt_number": attempt,
            "max_retry_attempts": LOMBARD_MAX_RETRY_ATTEMPTS,
        }

    if attempt != 0:
        raise LombardRetryLinkError("initial prepare requires retry_attempt_number=0")

    resolved_logical = (logical_borrow_id or "").strip() or new_logical_borrow_id()
    return {
        "logical_borrow_id": resolved_logical,
        "retry_attempt_number": 0,
        "max_retry_attempts": LOMBARD_MAX_RETRY_ATTEMPTS,
    }


def project_lombard_logical_borrow_terminal_status(intents: list[dict[str, Any]]) -> str:
    """Read-only global terminal status for a logical borrow group."""
    if not intents:
        return IntentStatus.AWAITING_SIGNATURE.value

    statuses = [str(i.get("status") or "") for i in intents]
    if IntentStatus.CONFIRMED.value in statuses:
        return IntentStatus.CONFIRMED.value
    if IntentStatus.FAILED_FINAL.value in statuses:
        return IntentStatus.FAILED_FINAL.value
    if IntentStatus.RECONCILIATION_REQUIRED.value in statuses:
        return IntentStatus.RECONCILIATION_REQUIRED.value

    ordered = sorted(
        intents,
        key=lambda row: int((row.get("metadata_json") or {}).get("retry_attempt_number") or 0),
    )
    latest = ordered[-1]
    latest_status = str(latest.get("status") or "")
    latest_meta = latest.get("metadata_json") if isinstance(latest.get("metadata_json"), dict) else {}
    attempt = int(latest_meta.get("retry_attempt_number") or 0)
    max_retry = int(latest_meta.get("max_retry_attempts") or LOMBARD_MAX_RETRY_ATTEMPTS)

    if latest_status == IntentStatus.RETRYABLE_FAILED.value and attempt < max_retry:
        return IntentStatus.RETRYABLE_FAILED.value
    if latest_status == IntentStatus.SUPERSEDED.value:
        if IntentStatus.CONFIRMED.value in statuses:
            return IntentStatus.CONFIRMED.value
        return IntentStatus.SUPERSEDED.value
    if latest_status in (IntentStatus.FAILED.value, IntentStatus.RETRYABLE_FAILED.value):
        return latest_status
    return latest_status or IntentStatus.PARTIAL.value


def project_lombard_logical_borrow_group(
    db: Session,
    *,
    person_id: UUID,
    logical_borrow_id: str,
) -> dict[str, Any]:
    rows = _query_lombard_by_logical_borrow_id(
        db, person_id=person_id, logical_borrow_id=logical_borrow_id
    )
    intents = [intent_to_dict(row) for row in rows]
    return {
        "logical_borrow_id": logical_borrow_id,
        "intents": intents,
        "terminal_status": project_lombard_logical_borrow_terminal_status(intents),
    }
