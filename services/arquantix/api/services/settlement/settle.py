"""settle_transaction_intent_idempotently — Settlement Layer (S2.5 skeleton / S3b ledger)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.config import lifi_settlement_layer_ledger_enabled
from services.lifi.lifi_validation_service import SwapValidationError
from services.onchain_indexer.models import TransactionIntent
from services.settlement.constants import SETTLEMENT_RECEIPT_METADATA_KEY
from services.settlement.lifi_ledger import (
    LifiStandaloneSettlementError,
    apply_lifi_standalone_ledger_settlement,
)
from services.settlement.preconditions import _resolve_linked_entity, validate_preconditions
from services.settlement.receipt import compute_settlement_receipt_hash, linked_entity_snapshot
from services.settlement.result import SettlementOutcome, SettlementResult


def _persist_settlement_marker(intent: TransactionIntent, receipt_hash: str) -> None:
    meta = dict(intent.metadata_json) if isinstance(intent.metadata_json, dict) else {}
    meta[SETTLEMENT_RECEIPT_METADATA_KEY] = receipt_hash
    intent.metadata_json = meta


def _rollback_savepoint(savepoint) -> None:
    if savepoint.is_active:
        savepoint.rollback()


def _apply_ledger_settlement_atomic(
    db: Session,
    *,
    intent: TransactionIntent,
    linked,
    snapshot: dict,
) -> tuple[dict, str]:
    """Projection ledger + marker dans un savepoint — rollback total si échec intermédiaire."""
    savepoint = db.begin_nested()
    try:
        ledger_result = apply_lifi_standalone_ledger_settlement(
            db,
            intent=intent,
            swap=linked,
        )
        merged_snapshot = {**snapshot, "ledger": ledger_result}
        receipt_hash = compute_settlement_receipt_hash(
            intent,
            linked_snapshot=merged_snapshot,
            projection="s3b-ledger",
        )
        _persist_settlement_marker(intent, receipt_hash)
    except (LifiStandaloneSettlementError, SwapValidationError):
        _rollback_savepoint(savepoint)
        raise
    except Exception:
        _rollback_savepoint(savepoint)
        raise
    else:
        savepoint.commit()
        return merged_snapshot, receipt_hash


def settle_transaction_intent_idempotently(
    db: Session,
    *,
    intent_id: UUID,
) -> SettlementResult:
    """Settlement Layer — squelette NOOP (S2.5/S3a) ou projection ledger LI.FI (S3b, flag ON)."""
    intent = db.query(TransactionIntent).filter(TransactionIntent.id == intent_id).first()

    precond = validate_preconditions(db, intent, intent_id=intent_id)
    if precond is not None:
        return precond

    assert intent is not None
    linked = _resolve_linked_entity(db, intent)
    snapshot = linked_entity_snapshot(linked)
    ledger_enabled = lifi_settlement_layer_ledger_enabled()
    projection = "s3b-ledger" if ledger_enabled else "s2.5-noop"

    if ledger_enabled:
        if linked is None:
            return SettlementResult(
                outcome=SettlementOutcome.TERMINAL_FAILURE,
                intent_id=intent.id,
                error_code="intent.linked_entity_not_found",
                error_message="Entité liée introuvable",
            )
        try:
            _snapshot, receipt_hash = _apply_ledger_settlement_atomic(
                db,
                intent=intent,
                linked=linked,
                snapshot=snapshot,
            )
        except LifiStandaloneSettlementError as exc:
            return SettlementResult(
                outcome=SettlementOutcome.TERMINAL_FAILURE,
                intent_id=intent.id,
                error_code=exc.code,
                error_message=str(exc),
            )
        except SwapValidationError as exc:
            return SettlementResult(
                outcome=SettlementOutcome.TERMINAL_FAILURE,
                intent_id=intent.id,
                error_code=getattr(exc, "code", "settlement.swap_validation"),
                error_message=str(exc),
            )
        except Exception as exc:
            return SettlementResult(
                outcome=SettlementOutcome.TERMINAL_FAILURE,
                intent_id=intent.id,
                error_code="settlement.ledger_projection_failed",
                error_message=str(exc),
            )
        return SettlementResult(
            outcome=SettlementOutcome.SUCCESS,
            intent_id=intent.id,
            settlement_receipt_hash=receipt_hash,
        )

    receipt_hash = compute_settlement_receipt_hash(
        intent,
        linked_snapshot=snapshot,
        projection=projection,
    )

    return SettlementResult(
        outcome=SettlementOutcome.SUCCESS,
        intent_id=intent.id,
        settlement_receipt_hash=receipt_hash,
    )
