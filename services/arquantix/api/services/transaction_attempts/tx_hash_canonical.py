"""Canonicalisation attempts par (chain_id, tx_hash) — aligné backfill + forward."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .models import OnchainTransactionAttempt
from .repository import OnchainTransactionAttemptRepository


def tx_hash_canonical_idempotency_key(*, chain_id: int, tx_hash: str) -> str:
    """Clé idempotente unique par transaction on-chain (backfill + forward)."""
    return f"backfill:chain:{chain_id}:tx:{tx_hash.strip().lower()}"


def find_attempt_by_chain_tx(
    db: Session,
    *,
    chain_id: int,
    tx_hash: str,
    step_type: str,
) -> OnchainTransactionAttempt | None:
    norm = tx_hash.strip().lower()
    return (
        db.query(OnchainTransactionAttempt)
        .filter(
            OnchainTransactionAttempt.chain_id == chain_id,
            OnchainTransactionAttempt.tx_hash == norm,
            OnchainTransactionAttempt.step_type == step_type,
        )
        .first()
    )


def swap_legacy_record(
    swap,
    *,
    protocol: str,
    chain_id: int,
    intent_id: UUID | str | None = None,
) -> dict[str, Any]:
    return {
        "source": "person_wallet_swaps",
        "reference_id": str(swap.id),
        "person_id": str(swap.person_id),
        "chain_id": chain_id,
        "protocol": protocol,
        "step_type": "swap",
        "intent_id": str(intent_id) if intent_id else None,
        "amount_in": str(swap.amount_in) if swap.amount_in is not None else None,
        "swap_status": swap.status,
    }


def _secondary_records_from_attempt(attempt: OnchainTransactionAttempt) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for blob in (attempt.metadata_json, attempt.raw_submission_json):
        if not isinstance(blob, dict):
            continue
        raw = blob.get("secondary_legacy_records")
        if isinstance(raw, list):
            for item in raw:
                if isinstance(item, dict) and item.get("reference_id"):
                    records.append(item)
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in records:
        ref = str(item["reference_id"])
        if ref in seen:
            continue
        seen.add(ref)
        unique.append(item)
    return unique


def swap_covered_by_attempt(
    db: Session,
    swap,
    *,
    chain_id: int,
    tx_hash: str,
    step_type: str,
    swap_idempotency_key: str | None = None,
) -> bool:
    """Swap couvert si attempt canonique ou secondary_legacy_records."""
    attempt = find_attempt_by_chain_tx(
        db,
        chain_id=chain_id,
        tx_hash=tx_hash,
        step_type=step_type,
    )
    if attempt is not None:
        if attempt.linked_id == swap.id:
            return True
        swap_id = str(swap.id)
        return any(r.get("reference_id") == swap_id for r in _secondary_records_from_attempt(attempt))

    if swap_idempotency_key and OnchainTransactionAttemptRepository.find_by_composite_key(
        db,
        idempotency_key=swap_idempotency_key,
        step_type=step_type,
    ):
        return True

    linked = OnchainTransactionAttemptRepository.find_by_linked(
        db,
        linked_table="person_wallet_swaps",
        linked_id=swap.id,
        step_type=step_type,
    )
    return linked is not None


def attach_secondary_swap_legacy(
    db: Session,
    attempt: OnchainTransactionAttempt,
    secondary_record: dict[str, Any],
) -> OnchainTransactionAttempt:
    ref = str(secondary_record.get("reference_id") or "")
    if not ref:
        return attempt

    meta = attempt.metadata_json if isinstance(attempt.metadata_json, dict) else {}
    submission = attempt.raw_submission_json if isinstance(attempt.raw_submission_json, dict) else {}
    secondaries = _secondary_records_from_attempt(attempt)

    if attempt.linked_id and str(attempt.linked_id) == ref:
        return attempt
    if any(str(r.get("reference_id")) == ref for r in secondaries):
        return attempt

    secondaries.append(secondary_record)
    grouping_patch = {
        "grouped_by_tx_hash": True,
        "secondary_legacy_records": secondaries,
    }
    attempt.metadata_json = {**meta, **grouping_patch}
    attempt.raw_submission_json = {**submission, **grouping_patch}
    db.add(attempt)
    db.flush()
    try:
        from services.transaction_trace.enums import TraceEventType
        from services.transaction_trace.transaction_trace_logger import log_transaction_trace

        log_transaction_trace(
            TraceEventType.LEGACY_RECORD_LINKED,
            db=db,
            person_id=attempt.person_id,
            intent_id=attempt.intent_id,
            attempt_id=attempt.id,
            group_key=attempt.group_key,
            idempotency_key=attempt.idempotency_key,
            protocol=attempt.protocol,
            operation_type=attempt.operation_type,
            step_type=attempt.step_type,
            tx_hash=attempt.tx_hash,
            chain_id=attempt.chain_id,
            linked_table=secondary_record.get("source"),
            linked_id=secondary_record.get("reference_id"),
            source="transaction_attempts.tx_hash_canonical.attach_secondary",
            message="secondary legacy record grouped under tx_hash attempt",
            metadata_json={
                "grouped_by_tx_hash": True,
                "secondary_legacy_record": secondary_record,
            },
        )
    except Exception:
        pass
    return attempt
