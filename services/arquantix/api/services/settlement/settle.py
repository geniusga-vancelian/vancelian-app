"""settle_transaction_intent_idempotently — S2.5 skeleton NOOP (Contract v1)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.onchain_indexer.models import TransactionIntent
from services.settlement.preconditions import _resolve_linked_entity, validate_preconditions
from services.settlement.receipt import compute_settlement_receipt_hash, linked_entity_snapshot
from services.settlement.result import SettlementOutcome, SettlementResult


def settle_transaction_intent_idempotently(
    db: Session,
    *,
    intent_id: UUID,
) -> SettlementResult:
    """Settlement Layer skeleton — valide le contrat v1, **aucune écriture économique** (S2.5).

    Pas de ledger, PE, cost basis, provider, COMPLETED, ni persistance marker en S2.5.
    """
    intent = db.query(TransactionIntent).filter(TransactionIntent.id == intent_id).first()

    precond = validate_preconditions(db, intent, intent_id=intent_id)
    if precond is not None:
        return precond

    assert intent is not None
    linked = _resolve_linked_entity(db, intent)
    receipt_hash = compute_settlement_receipt_hash(
        intent,
        linked_snapshot=linked_entity_snapshot(linked),
    )

    return SettlementResult(
        outcome=SettlementOutcome.SUCCESS,
        intent_id=intent.id,
        settlement_receipt_hash=receipt_hash,
    )
