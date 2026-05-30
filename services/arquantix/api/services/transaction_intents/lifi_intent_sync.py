"""Synchronisation transaction_intents ↔ swaps LI.FI (traçabilité uniquement)."""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from config.supported_swap_assets import SUPPORTED_SWAP_CHAINS, normalize_chain_key
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_actual_receive import _resolve_swap_wallet
from services.lifi.lifi_swap_settlement import swap_settlement_already_applied
from services.lifi.signing_wallet_service import read_signing_wallet_from_audit
from services.privy_wallet.asset_mapping import normalize_evm_address

from .enums import IntentOperationType, IntentProductType, IntentStatus
from .raw_event_link import try_link_raw_event_to_intent
from .repository import TransactionIntentRepository

logger = logging.getLogger(__name__)

LINKED_TABLE = "person_wallet_swaps"


def _idempotency_key(swap_id: UUID) -> str:
    return f"lifi_swap:{swap_id}"


def _chain_id_for_swap(swap) -> int | None:
    try:
        meta = SUPPORTED_SWAP_CHAINS.get(normalize_chain_key(swap.to_chain), {})
        return int(meta.get("lifi_chain_id") or 0) or None
    except Exception:
        return None


def _wallet_for_swap(db: Session, swap) -> str | None:
    try:
        wallet = _resolve_swap_wallet(db, swap)
        return normalize_evm_address(wallet.address)
    except Exception:
        _, addr = read_signing_wallet_from_audit(swap.audit_log)
        return normalize_evm_address(addr) if addr else None


def _audit_has_event(swap, event_name: str) -> bool:
    audit = swap.audit_log
    if not isinstance(audit, list):
        return False
    return any(isinstance(e, dict) and e.get("event") == event_name for e in audit)


def sync_lifi_swap_intent(
    db: Session,
    swap,
    *,
    status: str | None = None,
    metadata_patch: dict[str, Any] | None = None,
) -> None:
    """Upsert intent LI.FI — n'appelle jamais settlement ni balances."""
    if swap is None or not swap.person_id:
        return

    from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
        is_bundle_internal_swap,
    )

    if is_bundle_internal_swap(swap):
        logger.info(
            "skip_lifi_swap_intent_for_bundle_internal_swap",
            extra={"swap_id": str(swap.id), "person_id": str(swap.person_id)},
        )
        return

    mapped_status = status or _map_swap_status_to_intent(swap)
    wallet = _wallet_for_swap(db, swap)
    chain_id = _chain_id_for_swap(swap)

    row, created = TransactionIntentRepository.upsert(
        db,
        person_id=swap.person_id,
        product_type=IntentProductType.LIFI_SWAP.value,
        operation_type=IntentOperationType.SWAP.value,
        idempotency_key=_idempotency_key(swap.id),
        status=mapped_status,
        wallet_address=wallet,
        chain_id=chain_id,
        tx_hash=swap.tx_hash,
        linked_table=LINKED_TABLE,
        linked_id=swap.id,
        metadata_patch={
            "swap_status": swap.status,
            "from_asset": swap.from_asset,
            "to_asset": swap.to_asset,
            "from_chain": swap.from_chain,
            "to_chain": swap.to_chain,
            **(metadata_patch or {}),
        },
    )

    if swap.tx_hash:
        try_link_raw_event_to_intent(db, row)

    if created:
        logger.info(
            "intent.lifi.created",
            extra={"swap_id": str(swap.id), "intent_id": str(row.id)},
        )


def _map_swap_status_to_intent(swap) -> str:
    swap_status = str(swap.status or "").upper()

    if _audit_has_event(swap, "partial_confirmed"):
        return IntentStatus.PARTIAL.value

    if _audit_has_event(swap, "settlement_blocked"):
        return IntentStatus.RECONCILIATION_REQUIRED.value

    if swap_status == SwapSessionStatus.PENDING.value:
        return IntentStatus.CREATED.value
    if swap_status == SwapSessionStatus.QUOTE_RECEIVED.value:
        return IntentStatus.CREATED.value
    if swap_status == SwapSessionStatus.AWAITING_SIGNATURE.value:
        return IntentStatus.AWAITING_SIGNATURE.value
    if swap_status == SwapSessionStatus.SUBMITTED.value:
        return IntentStatus.CONFIRMING.value
    if swap_status == SwapSessionStatus.CONFIRMED.value:
        if swap_settlement_already_applied(swap):
            return IntentStatus.CONFIRMED.value
        return IntentStatus.RECONCILIATION_REQUIRED.value
    if swap_status == SwapSessionStatus.FAILED.value:
        return IntentStatus.FAILED.value
    if swap_status == SwapSessionStatus.EXPIRED.value:
        return IntentStatus.FAILED.value

    return IntentStatus.CREATED.value


def on_swap_approval_submitted(db: Session, swap, *, approval_tx_hash: str) -> None:
    sync_lifi_swap_intent(
        db,
        swap,
        metadata_patch={"approval_tx_hash": approval_tx_hash.strip().lower()},
    )


def on_swap_created(db: Session, swap) -> None:
    sync_lifi_swap_intent(db, swap, status=IntentStatus.CREATED.value)


def on_swap_awaiting_signature(db: Session, swap) -> None:
    sync_lifi_swap_intent(db, swap, status=IntentStatus.AWAITING_SIGNATURE.value)


def on_swap_submitted(db: Session, swap, *, tx_hash: str) -> None:
    sync_lifi_swap_intent(
        db,
        swap,
        status=IntentStatus.SUBMITTED.value,
        metadata_patch={"submitted": True},
    )


def on_swap_lifi_poll(db: Session, swap, *, lifi_status: str, substatus: str) -> None:
    from services.lifi.lifi_actual_receive import is_lifi_partial_substatus

    if lifi_status == "DONE" and is_lifi_partial_substatus(substatus):
        sync_lifi_swap_intent(
            db,
            swap,
            status=IntentStatus.PARTIAL.value,
            metadata_patch={"lifi_substatus": substatus, "reconciliation_required": True},
        )
        return
    if lifi_status == "FAILED":
        sync_lifi_swap_intent(db, swap, status=IntentStatus.FAILED.value)
        return
    sync_lifi_swap_intent(db, swap, status=IntentStatus.CONFIRMING.value)


def on_swap_settlement_blocked(db: Session, swap, *, reason: str) -> None:
    sync_lifi_swap_intent(
        db,
        swap,
        status=IntentStatus.RECONCILIATION_REQUIRED.value,
        metadata_patch={"settlement_blocked_reason": reason},
    )


def on_swap_confirmed(db: Session, swap) -> None:
    sync_lifi_swap_intent(db, swap, status=IntentStatus.CONFIRMED.value)


def on_swap_failed(db: Session, swap) -> None:
    sync_lifi_swap_intent(db, swap, status=IntentStatus.FAILED.value)
