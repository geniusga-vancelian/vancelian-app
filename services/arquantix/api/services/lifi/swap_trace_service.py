"""Trace events swap LI.FI — observabilité systématique."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.signing_wallet_service import read_signing_wallet_from_audit
from services.transaction_intents.repository import TransactionIntentRepository
from services.transaction_trace.enums import TraceEventType
from services.transaction_trace.transaction_trace_logger import log_transaction_trace

LINKED_SWAPS = "person_wallet_swaps"

_SWAP_TRACE_EVENT_MAP: dict[str, TraceEventType] = {
    "quote_received": TraceEventType.SWAP_QUOTE_RECEIVED,
    "quote_refreshed": TraceEventType.SWAP_QUOTE_REFRESHED,
    "awaiting_signature": TraceEventType.SWAP_AWAITING_SIGNATURE,
    "approval_required": TraceEventType.SWAP_APPROVAL_REQUIRED,
    "approval_submitted": TraceEventType.SWAP_APPROVAL_SUBMITTED,
    "swap_submitted": TraceEventType.SWAP_SUBMITTED,
    "confirming": TraceEventType.SWAP_CONFIRMING,
    "confirmed": TraceEventType.SWAP_CONFIRMED,
    "failed": TraceEventType.SWAP_FAILED,
    "expired": TraceEventType.SWAP_EXPIRED,
    "reconciliation_required": TraceEventType.SWAP_RECONCILIATION_REQUIRED,
    "reconciliation_applied": TraceEventType.SWAP_RECONCILIATION_APPLIED,
}


def _resolve_intent_id(db: Session | None, swap) -> UUID | None:
    if db is None or swap is None:
        return None
    try:
        row = TransactionIntentRepository.find_by_linked(
            db,
            linked_table=LINKED_SWAPS,
            linked_id=swap.id,
        )
        return row.id if row else None
    except Exception:
        return None


def _chain_id_from_swap(swap) -> int | None:
    try:
        from config.supported_swap_assets import SUPPORTED_SWAP_CHAINS, normalize_chain_key

        meta = SUPPORTED_SWAP_CHAINS.get(normalize_chain_key(swap.from_chain), {})
        return int(meta.get("lifi_chain_id") or 8453)
    except Exception:
        return 8453


def log_swap_trace(
    db: Session | None,
    swap,
    *,
    event: str,
    status: str | None = None,
    error_code: str | None = None,
    tx_hash: str | None = None,
    attempt_id: UUID | str | None = None,
    message: str | None = None,
    metadata_patch: dict[str, Any] | None = None,
    source: str = "lifi_swap",
) -> None:
    """Émet un trace event swap — best-effort, ne lève pas."""
    if swap is None:
        return
    trace_type = _SWAP_TRACE_EVENT_MAP.get(event)
    if trace_type is None:
        return

    _, wallet_address = read_signing_wallet_from_audit(swap.audit_log)
    intent_id = _resolve_intent_id(db, swap)
    meta: dict[str, Any] = {
        "swap_id": str(swap.id),
        "from_token": swap.from_asset,
        "to_token": swap.to_asset,
        "amount": str(swap.amount_in) if swap.amount_in is not None else None,
        "swap_status": status or swap.status,
    }
    if error_code:
        meta["error_code"] = error_code
    if metadata_patch:
        meta.update(metadata_patch)

    log_transaction_trace(
        trace_type,
        db=db,
        person_id=getattr(swap, "person_id", None),
        intent_id=intent_id,
        attempt_id=attempt_id,
        protocol="lifi",
        operation_type="swap",
        status_to=status or str(swap.status or ""),
        tx_hash=tx_hash or getattr(swap, "tx_hash", None),
        chain_id=_chain_id_from_swap(swap),
        linked_table=LINKED_SWAPS,
        linked_id=swap.id,
        source=source,
        message=message or event,
        metadata_json=meta,
    )
