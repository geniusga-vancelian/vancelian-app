"""Lien intent ↔ raw_onchain_events (lecture seule)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.onchain_indexer.models import RawOnChainEvent

from services.onchain_indexer.models import TransactionIntent


def find_raw_event_for_tx(
    db: Session,
    *,
    chain_id: int | None,
    tx_hash: str,
    wallet_address: str | None = None,
) -> RawOnChainEvent | None:
    normalized = str(tx_hash or "").strip().lower()
    if not normalized:
        return None
    q = db.query(RawOnChainEvent).filter(RawOnChainEvent.tx_hash == normalized)
    if chain_id is not None:
        q = q.filter(RawOnChainEvent.chain_id == chain_id)
    if wallet_address:
        q = q.filter(RawOnChainEvent.wallet_address == wallet_address.strip().lower())
    return q.order_by(RawOnChainEvent.parsed_at.desc()).first()


def try_link_raw_event_to_intent(db: Session, intent: TransactionIntent) -> UUID | None:
    if intent.raw_onchain_event_id or not intent.tx_hash:
        return intent.raw_onchain_event_id

    row = find_raw_event_for_tx(
        db,
        chain_id=intent.chain_id,
        tx_hash=intent.tx_hash,
        wallet_address=intent.wallet_address,
    )
    if row is None:
        return None

    intent.raw_onchain_event_id = row.id
    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    intent.metadata_json = {**meta, "raw_event_linked_at": "auto"}
    db.add(intent)
    db.flush()
    return row.id
