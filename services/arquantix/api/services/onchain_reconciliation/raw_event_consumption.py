"""Consommation unique des raw_onchain_events (Phase 5C)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.onchain_indexer.models import RawOnChainEvent

from .correction_policy import CORRECTION_STATUS_APPLIED
from .discrepancy_models import ReconciliationCorrection


class RawEventConsumptionError(ValueError):
    """Raw event déjà consommé par une correction appliquée."""


def get_consumed_correction_id(db: Session, raw_event: RawOnChainEvent) -> UUID | None:
    """Retourne l'id de correction ayant consommé l'événement, si présent."""
    consumed = getattr(raw_event, "consumed_by_correction_id", None)
    if consumed is not None:
        return consumed

    row = (
        db.query(ReconciliationCorrection.id)
        .filter(
            ReconciliationCorrection.status == CORRECTION_STATUS_APPLIED,
            ReconciliationCorrection.metadata_json["raw_onchain_event_id"].as_string()
            == str(raw_event.id),
        )
        .order_by(ReconciliationCorrection.applied_at.desc())
        .first()
    )
    return row[0] if row else None


def assert_raw_event_available(
    db: Session,
    raw_event: RawOnChainEvent,
    *,
    for_correction_id: UUID | None = None,
) -> None:
    consumer = get_consumed_correction_id(db, raw_event)
    if consumer is None:
        return
    if for_correction_id and consumer == for_correction_id:
        return
    raise RawEventConsumptionError("raw_onchain_event_already_consumed")


def lock_raw_event_for_apply(db: Session, raw_event_id: UUID) -> RawOnChainEvent:
    row = (
        db.query(RawOnChainEvent)
        .filter(RawOnChainEvent.id == raw_event_id)
        .with_for_update()
        .first()
    )
    if row is None:
        raise LookupError("raw_onchain_event_not_found")
    return row


def mark_raw_event_consumed(
    db: Session,
    raw_event: RawOnChainEvent,
    *,
    correction_id: UUID,
) -> None:
    assert_raw_event_available(db, raw_event, for_correction_id=correction_id)
    raw_event.consumed_by_correction_id = correction_id
    db.add(raw_event)
    db.flush()
