"""Synchronisation transaction_intents ↔ retrait bundle."""
from __future__ import annotations

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .bundle_intent_sync import (
    LEG_CONFIRMED,
    LEG_FAILED,
    LEG_PENDING,
    LEG_SUBMITTED,
    _get_parent,
    _normalize_legs,
    _save_parent,
    register_bundle_leg,
)
from .enums import IntentOperationType, IntentProductType, IntentStatus
from .repository import TransactionIntentRepository

logger = logging.getLogger(__name__)

BUNDLE_WITHDRAW_LINKED_TABLE = "bundle_withdraw_lock"
BUNDLE_WITHDRAW_PRODUCT = IntentProductType.BUNDLE_WITHDRAW.value
BUNDLE_WITHDRAW_OPERATION = IntentOperationType.WITHDRAW.value


def bundle_withdraw_parent_intent_key(
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
) -> str:
    return f"bundle_withdraw:{person_id}:{bundle_id}:{batch_id}"


def ensure_bundle_withdraw_parent_intent(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
    withdraw_phase: str,
    requested_amount: str,
    full_withdraw: bool,
    wallet_address: Optional[str] = None,
    chain_id: int = 8453,
) -> dict[str, Any] | None:
    try:
        row, _created = TransactionIntentRepository.upsert(
            db,
            person_id=person_id,
            product_type=BUNDLE_WITHDRAW_PRODUCT,
            operation_type=BUNDLE_WITHDRAW_OPERATION,
            idempotency_key=bundle_withdraw_parent_intent_key(
                person_id=person_id,
                bundle_id=bundle_id,
                batch_id=batch_id,
            ),
            status=IntentStatus.CREATED.value,
            wallet_address=wallet_address,
            chain_id=chain_id,
            linked_table=BUNDLE_WITHDRAW_LINKED_TABLE,
            linked_reference_id=batch_id,
            metadata_patch={
                "batch_id": batch_id,
                "bundle_id": bundle_id,
                "withdraw_phase": withdraw_phase,
                "requested_release_amount": requested_amount,
                "full_withdraw": full_withdraw,
                "legs": [],
            },
        )
        legs = _normalize_legs((row.metadata_json or {}).get("legs"))
        return _save_parent(db, row, legs=legs, status=IntentStatus.CREATED.value)
    except Exception as exc:
        logger.warning(
            "intent.bundle_withdraw.parent_failed",
            extra={"batch_id": batch_id, "error": str(exc)},
            exc_info=True,
        )
        return None


def _find_withdraw_parent(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
) -> Optional[Any]:
    return TransactionIntentRepository.find_by_composite_key(
        db,
        person_id=person_id,
        product_type=BUNDLE_WITHDRAW_PRODUCT,
        operation_type=BUNDLE_WITHDRAW_OPERATION,
        idempotency_key=bundle_withdraw_parent_intent_key(
            person_id=person_id,
            bundle_id=bundle_id,
            batch_id=batch_id,
        ),
    )


def update_bundle_withdraw_phase(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
    withdraw_phase: str,
    status: Optional[str] = None,
) -> dict[str, Any] | None:
    try:
        row = _find_withdraw_parent(
            db, person_id=person_id, bundle_id=bundle_id, batch_id=batch_id,
        )
        if row is None:
            return None
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        row.metadata_json = {**meta, "withdraw_phase": withdraw_phase}
        legs = _normalize_legs(meta.get("legs"))
        return _save_parent(db, row, legs=legs, status=status or row.status)
    except Exception as exc:
        logger.warning("intent.bundle_withdraw.phase_update_failed", extra={"error": str(exc)})
        return None


def mark_bundle_withdraw_released(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
    released_amount: str,
) -> dict[str, Any] | None:
    try:
        row = _find_withdraw_parent(
            db, person_id=person_id, bundle_id=bundle_id, batch_id=batch_id,
        )
        if row is None:
            return None
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        row.metadata_json = {
            **meta,
            "withdraw_phase": "RELEASED",
            "released_amount": released_amount,
        }
        legs = _normalize_legs(meta.get("legs"))
        return _save_parent(db, row, legs=legs, status=IntentStatus.CONFIRMED.value)
    except Exception as exc:
        logger.warning("intent.bundle_withdraw.released_failed", extra={"error": str(exc)})
        return None


def register_bundle_withdraw_leg(
    db: Session,
    *,
    person_id: UUID,
    bundle_id: str,
    batch_id: str,
    leg_id: str,
    swap_id: str,
    asset: str,
) -> dict[str, Any] | None:
    parent = ensure_bundle_withdraw_parent_intent(
        db,
        person_id=person_id,
        bundle_id=bundle_id,
        batch_id=batch_id,
        withdraw_phase="UNWINDING",
        requested_amount="0",
        full_withdraw=False,
    )
    if parent is None:
        return register_bundle_leg(
            db,
            person_id=person_id,
            bundle_id=bundle_id,
            batch_id=batch_id,
            leg_id=leg_id,
            swap_id=swap_id,
            asset=asset,
        )
    return register_bundle_leg(
        db,
        person_id=person_id,
        bundle_id=bundle_id,
        batch_id=batch_id,
        leg_id=leg_id,
        swap_id=swap_id,
        asset=asset,
    )
