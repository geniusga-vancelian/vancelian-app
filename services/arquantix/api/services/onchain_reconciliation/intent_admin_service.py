"""Admin — liste / détail transaction_intents."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.transaction_intents.repository import TransactionIntentRepository, intent_to_dict


def list_intents_admin(
    db: Session,
    *,
    filters: dict[str, Any],
    skip: int,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    rows, total = TransactionIntentRepository.list_filtered(db, skip=skip, limit=limit, **filters)
    return [intent_to_dict(r) for r in rows], total


def get_intent_for_discrepancy(
    db: Session,
    *,
    reference_type: str | None,
    reference_id: str | None,
    metadata_json: dict[str, Any] | None,
) -> dict[str, Any] | None:
    meta = metadata_json if isinstance(metadata_json, dict) else {}

    if reference_type == "swap" and reference_id:
        from services.transaction_intents.lifi_intent_sync import LINKED_TABLE

        row = TransactionIntentRepository.find_by_linked(
            db,
            linked_table=LINKED_TABLE,
            linked_id=UUID(reference_id),
        )
        if row:
            return intent_to_dict(row)

    intent_id = meta.get("transaction_intent_id")
    if intent_id:
        from services.onchain_indexer.models import TransactionIntent

        row = db.query(TransactionIntent).filter(TransactionIntent.id == UUID(str(intent_id))).first()
        if row:
            return intent_to_dict(row)

    swap_id = meta.get("linked_swap_id") or meta.get("swap_id")
    if swap_id:
        from services.transaction_intents.lifi_intent_sync import LINKED_TABLE

        row = TransactionIntentRepository.find_by_linked(
            db,
            linked_table=LINKED_TABLE,
            linked_id=UUID(str(swap_id)),
        )
        if row:
            return intent_to_dict(row)

    vault_tx_id = meta.get("vault_transaction_id") or (
        reference_id if reference_type == "vault_tx" else None
    )
    if vault_tx_id:
        row = TransactionIntentRepository.find_by_vault_transaction(
            db,
            vault_transaction_id=str(vault_tx_id),
        )
        if row:
            return intent_to_dict(row)

    batch_id = meta.get("batch_id") or (
        reference_id if reference_type in ("bundle_batch", "bundle_invest_lock") else None
    )
    if batch_id:
        person_raw = meta.get("person_id")
        bundle_id = meta.get("bundle_id") or meta.get("portfolio_id")
        person_id = UUID(str(person_raw)) if person_raw else None
        if person_id is not None and bundle_id:
            row = TransactionIntentRepository.find_by_bundle_batch(
                db,
                person_id=person_id,
                bundle_id=str(bundle_id),
                batch_id=str(batch_id),
            )
            if row:
                return intent_to_dict(row)

    group_key = meta.get("group_key") or (
        reference_id if reference_type in ("lombard_group", "vault_group") else None
    )
    if group_key:
        person_raw = meta.get("person_id")
        market = meta.get("market_id") or meta.get("vault_address")
        person_id = UUID(str(person_raw)) if person_raw else None
        if person_id is not None:
            row = TransactionIntentRepository.find_by_lombard_group(
                db,
                person_id=person_id,
                group_key=str(group_key),
                market_or_vault=str(market) if market else None,
            )
            if row:
                return intent_to_dict(row)

    return None
