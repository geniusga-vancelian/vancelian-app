"""Synchronisation transaction_intents ↔ Bundle invest (Phase 7D — observabilité)."""
from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .enums import IntentOperationType, IntentProductType, IntentStatus
from .raw_event_link import try_link_raw_event_to_intent
from .repository import TransactionIntentRepository

logger = logging.getLogger(__name__)

BUNDLE_LINKED_TABLE = "bundle_invest_lock"
BUNDLE_PRODUCT = IntentProductType.BUNDLE_INVEST.value
BUNDLE_OPERATION = IntentOperationType.INVEST.value
SWAP_LINKED_TABLE = "person_wallet_swaps"

LEG_PENDING = "pending"
LEG_SUBMITTED = "submitted"
LEG_CONFIRMED = "confirmed"
LEG_FAILED = "failed"


def bundle_parent_intent_key(
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
) -> str:
    return f"bundle_invest:{person_id}:{bundle_id}:{batch_id}"


def _normalize_legs(legs: Any) -> list[dict[str, Any]]:
    if not isinstance(legs, list):
        return []
    return [dict(item) for item in legs if isinstance(item, dict) and item.get("leg_id")]


def _find_leg_index(
    legs: list[dict[str, Any]],
    *,
    leg_id: Optional[str] = None,
    swap_id: Optional[str] = None,
) -> Optional[int]:
    for i, leg in enumerate(legs):
        if leg_id and str(leg.get("leg_id") or "") == leg_id:
            return i
        if swap_id and str(leg.get("swap_id") or "") == swap_id:
            return i
    return None


def recompute_bundle_parent_status(legs: list[dict[str, Any]]) -> str:
    if not legs:
        return IntentStatus.AWAITING_SIGNATURE.value

    statuses = [str(leg.get("status") or LEG_PENDING) for leg in legs]

    if all(s == LEG_CONFIRMED for s in statuses):
        return IntentStatus.CONFIRMED.value
    if all(s == LEG_FAILED for s in statuses):
        return IntentStatus.FAILED.value
    if not any(s == LEG_CONFIRMED for s in statuses):
        if any(s in (LEG_SUBMITTED, LEG_PENDING) for s in statuses):
            return IntentStatus.AWAITING_SIGNATURE.value
        return IntentStatus.FAILED.value

    if any(s == LEG_CONFIRMED for s in statuses) and any(
        s in (LEG_FAILED, LEG_PENDING, LEG_SUBMITTED) for s in statuses
    ):
        return IntentStatus.PARTIAL.value

    if any(s in (LEG_SUBMITTED,) for s in statuses) or any(leg.get("tx_hash") for leg in legs):
        return IntentStatus.SUBMITTED.value

    return IntentStatus.AWAITING_SIGNATURE.value


def _parent_tx_hash_from_legs(legs: list[dict[str, Any]]) -> Optional[str]:
    for leg in reversed(legs):
        if leg.get("tx_hash"):
            return str(leg["tx_hash"]).strip().lower()
    return None


def _save_parent(
    db: Session,
    row: Any,
    *,
    legs: list[dict[str, Any]],
    status: Optional[str] = None,
) -> dict[str, Any]:
    meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
    row.metadata_json = {**meta, "legs": legs, "batch_id": meta.get("batch_id") or row.linked_reference_id}
    if status is not None:
        row.status = status
    tx = _parent_tx_hash_from_legs(legs)
    if tx:
        row.tx_hash = tx
    db.add(row)
    db.flush()
    if tx:
        try_link_raw_event_to_intent(db, row)
    return {"intent_id": str(row.id), "status": row.status, "legs": legs}


def _get_parent(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
) -> Optional[Any]:
    return TransactionIntentRepository.find_by_bundle_batch(
        db,
        person_id=person_id,
        bundle_id=bundle_id,
        batch_id=batch_id,
    )


def ensure_bundle_parent_intent(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
    wallet_address: Optional[str] = None,
    chain_id: int = 8453,
    extra_metadata: Optional[dict[str, Any]] = None,
) -> dict[str, Any] | None:
    try:
        row, _created = TransactionIntentRepository.upsert(
            db,
            person_id=person_id,
            product_type=BUNDLE_PRODUCT,
            operation_type=BUNDLE_OPERATION,
            idempotency_key=bundle_parent_intent_key(
                person_id=person_id,
                bundle_id=bundle_id,
                batch_id=batch_id,
            ),
            status=IntentStatus.AWAITING_SIGNATURE.value,
            wallet_address=wallet_address,
            chain_id=chain_id,
            linked_table=BUNDLE_LINKED_TABLE,
            linked_reference_id=batch_id,
            metadata_patch={
                "batch_id": batch_id,
                "bundle_id": bundle_id,
                "legs": [],
                **(extra_metadata or {}),
            },
        )
        legs = _normalize_legs((row.metadata_json or {}).get("legs"))
        return _save_parent(db, row, legs=legs, status=IntentStatus.AWAITING_SIGNATURE.value)
    except Exception as exc:
        logger.warning(
            "intent.bundle.parent_failed",
            extra={"batch_id": batch_id, "error": str(exc)},
            exc_info=True,
        )
        return None


def register_bundle_leg(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
    leg_id: str,
    swap_id: str,
    asset: str,
    target_weight: Optional[float] = None,
) -> dict[str, Any] | None:
    try:
        row = _get_parent(db, person_id=person_id, bundle_id=bundle_id, batch_id=batch_id)
        if row is None:
            ensure_bundle_parent_intent(
                db,
                person_id=person_id,
                bundle_id=bundle_id,
                batch_id=batch_id,
            )
            row = _get_parent(db, person_id=person_id, bundle_id=bundle_id, batch_id=batch_id)
        if row is None:
            return None

        legs = _normalize_legs((row.metadata_json or {}).get("legs"))
        if _find_leg_index(legs, leg_id=leg_id) is None:
            legs.append(
                {
                    "leg_id": leg_id,
                    "swap_id": str(swap_id),
                    "asset": asset.upper(),
                    "target_weight": target_weight,
                    "tx_hash": None,
                    "status": LEG_PENDING,
                    "linked_table": SWAP_LINKED_TABLE,
                    "linked_id": str(swap_id),
                    "raw_onchain_event_id": None,
                }
            )
        parent_status = recompute_bundle_parent_status(legs)
        return _save_parent(db, row, legs=legs, status=parent_status)
    except Exception as exc:
        logger.warning("intent.bundle.register_leg_failed", extra={"leg_id": leg_id, "error": str(exc)})
        return None


def _update_bundle_leg(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
    leg_status: str,
    leg_id: Optional[str] = None,
    swap_id: Optional[str] = None,
    tx_hash: Optional[str] = None,
    receipt_status: Optional[str] = None,
) -> dict[str, Any] | None:
    row = _get_parent(db, person_id=person_id, bundle_id=bundle_id, batch_id=batch_id)
    if row is None:
        return None

    legs = _normalize_legs((row.metadata_json or {}).get("legs"))
    idx = _find_leg_index(legs, leg_id=leg_id, swap_id=swap_id)
    if idx is None:
        return None

    legs[idx]["status"] = leg_status
    if tx_hash:
        legs[idx]["tx_hash"] = tx_hash.strip().lower()
    if receipt_status:
        legs[idx]["receipt_status"] = receipt_status

    parent_status = recompute_bundle_parent_status(legs)
    return _save_parent(db, row, legs=legs, status=parent_status)


def mark_bundle_leg_submitted(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
    swap_id: UUID,
    tx_hash: str,
    leg_id: Optional[str] = None,
) -> dict[str, Any] | None:
    try:
        return _update_bundle_leg(
            db,
            person_id=person_id,
            bundle_id=bundle_id,
            batch_id=batch_id,
            leg_id=leg_id,
            swap_id=str(swap_id),
            leg_status=LEG_SUBMITTED,
            tx_hash=tx_hash,
        )
    except Exception as exc:
        logger.warning("intent.bundle.leg_submitted_failed", extra={"error": str(exc)})
        return None


def mark_bundle_leg_confirmed(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
    swap_id: UUID,
    tx_hash: Optional[str] = None,
    leg_id: Optional[str] = None,
) -> dict[str, Any] | None:
    try:
        return _update_bundle_leg(
            db,
            person_id=person_id,
            bundle_id=bundle_id,
            batch_id=batch_id,
            leg_id=leg_id,
            swap_id=str(swap_id),
            leg_status=LEG_CONFIRMED,
            tx_hash=tx_hash,
            receipt_status="confirmed",
        )
    except Exception as exc:
        logger.warning("intent.bundle.leg_confirmed_failed", extra={"error": str(exc)})
        return None


def mark_bundle_leg_failed(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
    swap_id: UUID,
    tx_hash: Optional[str] = None,
    leg_id: Optional[str] = None,
    reason: Optional[str] = None,
) -> dict[str, Any] | None:
    try:
        result = _update_bundle_leg(
            db,
            person_id=person_id,
            bundle_id=bundle_id,
            batch_id=batch_id,
            leg_id=leg_id,
            swap_id=str(swap_id),
            leg_status=LEG_FAILED,
            tx_hash=tx_hash,
            receipt_status=reason or "failed",
        )
        if result and reason:
            row = _get_parent(db, person_id=person_id, bundle_id=bundle_id, batch_id=batch_id)
            if row and isinstance(row.metadata_json, dict):
                meta = dict(row.metadata_json)
                legs = _normalize_legs(meta.get("legs"))
                idx = _find_leg_index(legs, leg_id=leg_id, swap_id=str(swap_id))
                if idx is not None:
                    legs[idx]["failure_reason"] = reason
                    _save_parent(db, row, legs=legs, status=row.status)
        return result
    except Exception as exc:
        logger.warning("intent.bundle.leg_failed_failed", extra={"error": str(exc)})
        return None


def recompute_bundle_parent_intent(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
) -> dict[str, Any] | None:
    try:
        row = _get_parent(db, person_id=person_id, bundle_id=bundle_id, batch_id=batch_id)
        if row is None:
            return None
        legs = _normalize_legs((row.metadata_json or {}).get("legs"))
        parent_status = recompute_bundle_parent_status(legs)
        return _save_parent(db, row, legs=legs, status=parent_status)
    except Exception as exc:
        logger.warning("intent.bundle.recompute_failed", extra={"error": str(exc)})
        return None


def sync_bundle_parent_from_batch_status(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
    batch_status: str,
) -> dict[str, Any] | None:
    """Aligne le parent sur le statut orchestrateur (completed / partial / failed / pending_*)."""
    norm = (batch_status or "").strip().lower()
    mapped = {
        "completed": IntentStatus.CONFIRMED.value,
        "partial": IntentStatus.PARTIAL.value,
        "partial_pending": IntentStatus.PARTIAL.value,
        "failed": IntentStatus.FAILED.value,
        "pending_signature": IntentStatus.AWAITING_SIGNATURE.value,
    }.get(norm)

    try:
        row = _get_parent(db, person_id=person_id, bundle_id=bundle_id, batch_id=batch_id)
        if row is None:
            return None
        legs = _normalize_legs((row.metadata_json or {}).get("legs"))
        if mapped:
            status = mapped
        else:
            status = recompute_bundle_parent_status(legs)
        return _save_parent(db, row, legs=legs, status=status)
    except Exception as exc:
        logger.warning("intent.bundle.batch_status_sync_failed", extra={"error": str(exc)})
        return None


def mark_bundle_reconciliation_required(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
    reason: str,
) -> dict[str, Any] | None:
    try:
        row = _get_parent(db, person_id=person_id, bundle_id=bundle_id, batch_id=batch_id)
        if row is None:
            return None
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        row.metadata_json = {**meta, "reconciliation_reason": reason}
        legs = _normalize_legs(meta.get("legs"))
        return _save_parent(
            db,
            row,
            legs=legs,
            status=IntentStatus.RECONCILIATION_REQUIRED.value,
        )
    except Exception as exc:
        logger.warning("intent.bundle.reconciliation_required_failed", extra={"error": str(exc)})
        return None


def bundle_context_from_swap_audit(swap: Any) -> Optional[dict[str, Any]]:
    audit = getattr(swap, "audit_log", None)
    if not isinstance(audit, list):
        return None
    for entry in reversed(audit):
        if isinstance(entry, dict) and entry.get("event") == "bundle_leg_context":
            return entry
    return None


def sync_bundle_leg_from_swap(
    db: Session,
    *,
    person_id: UUID,
    swap: Any,
    leg: Any,
) -> None:
    """Point d’entrée pratique depuis BundleLifiLegService (ne lève pas)."""
    ctx = bundle_context_from_swap_audit(swap)
    batch_id = (ctx or {}).get("batch_id") or getattr(leg, "batch_id", None)
    if not batch_id:
        return
    bundle_id = str((ctx or {}).get("portfolio_id") or getattr(leg, "portfolio_id", ""))
    leg_id = str((ctx or {}).get("leg_id") or getattr(leg, "leg_id", ""))
    asset = str(getattr(swap, "to_asset", "") or "")
    bundle_action = str(getattr(leg, "bundle_action", "") or (ctx or {}).get("bundle_action") or "")

    if bundle_action == "withdraw":
        from .bundle_withdraw_intent_sync import register_bundle_withdraw_leg

        register_bundle_withdraw_leg(
            db,
            person_id=person_id,
            bundle_id=bundle_id,
            batch_id=str(batch_id),
            leg_id=leg_id,
            swap_id=str(swap.id),
            asset=asset,
        )
        return

    register_bundle_leg(
        db,
        person_id=person_id,
        bundle_id=bundle_id,
        batch_id=str(batch_id),
        leg_id=leg_id,
        swap_id=str(swap.id),
        asset=asset,
    )
