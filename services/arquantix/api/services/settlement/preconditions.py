"""Pré-conditions Settlement Layer Contract v1 (P1–P6) — validation lecture seule."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.settlement.constants import SETTLEMENT_READY_PHASES
from services.settlement.result import SettlementOutcome, SettlementResult


def _terminal(intent_id: UUID, code: str, message: str) -> SettlementResult:
    return SettlementResult(
        outcome=SettlementOutcome.TERMINAL_FAILURE,
        intent_id=intent_id,
        error_code=code,
        error_message=message,
    )


def _noop_already_settled(intent_id: UUID, receipt_hash: str) -> SettlementResult:
    return SettlementResult(
        outcome=SettlementOutcome.NOOP_ALREADY_SETTLED,
        intent_id=intent_id,
        settlement_receipt_hash=receipt_hash,
    )


def settlement_marker_present(intent: TransactionIntent) -> str | None:
    meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
    raw = meta.get("settlement_receipt_hash")
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def validate_preconditions(
    db: Session,
    intent: TransactionIntent | None,
    *,
    intent_id: UUID,
) -> SettlementResult | None:
    """Retourne un SettlementResult terminal/noop si pré-condition échoue, sinon None."""
    # P1
    if intent is None:
        return _terminal(intent_id, "intent.not_found", "Intent introuvable")

    # P5 — déjà settled (lecture marker existant uniquement)
    existing_hash = settlement_marker_present(intent)
    if existing_hash:
        return _noop_already_settled(intent.id, existing_hash)

    # P4
    key = (intent.idempotency_key or "").strip()
    if not key:
        return _terminal(intent.id, "intent.missing_idempotency_key", "idempotency_key requis")

    # P3 — linked entity
    if not intent.linked_table or not intent.linked_id:
        return _terminal(intent.id, "intent.missing_linked_entity", "linked_table/linked_id requis")

    linked = _resolve_linked_entity(db, intent)
    if linked is None:
        return _terminal(intent.id, "intent.linked_entity_not_found", "Entité liée introuvable")

    # P2 — phase autorisée pour settlement
    phase = (intent.current_phase or "").strip().upper()
    if phase not in SETTLEMENT_READY_PHASES:
        return _terminal(
            intent.id,
            "intent.phase_not_settlement_ready",
            f"Phase {phase or '?'} non autorisée pour settlement",
        )

    # P6 — données de projection présentes (intent + linked, pas de fetch provider)
    if not _projection_data_present(intent, linked):
        return _terminal(
            intent.id,
            "intent.projection_data_missing",
            "Données de projection insuffisantes sur intent/linked entity",
        )

    return None


def _resolve_linked_entity(db: Session, intent: TransactionIntent) -> Any | None:
    table = (intent.linked_table or "").strip()
    if table == "person_wallet_swaps":
        return (
            db.query(PersonWalletSwap)
            .filter(PersonWalletSwap.id == intent.linked_id)
            .first()
        )
    return None


def _projection_data_present(intent: TransactionIntent, linked: Any) -> bool:
    assets = intent.assets_json if isinstance(intent.assets_json, dict) else {}
    from_block = assets.get("from")
    if not isinstance(from_block, dict):
        return False
    amount = from_block.get("amount")
    asset = from_block.get("asset")
    if not amount or not asset:
        return False
    if linked is None:
        return False
    if hasattr(linked, "amount_in") and linked.amount_in is None:
        return False
    return True
