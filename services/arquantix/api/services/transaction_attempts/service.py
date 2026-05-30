"""Service onchain_transaction_attempts — transitions best-effort (Phase 2)."""
from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .enums import AttemptStatus
from .repository import OnchainTransactionAttemptRepository, attempt_to_dict
from .schemas import AttemptCreateInput, AttemptTransitionInput

logger = logging.getLogger(__name__)


def _norm_status(status: str) -> str:
    return (status or AttemptStatus.PREPARED.value).strip().lower()


class OnchainTransactionAttemptService:

    @staticmethod
    def create_prepared_attempt(
        db: Session,
        payload: AttemptCreateInput,
    ) -> dict[str, Any]:
        row, created = OnchainTransactionAttemptRepository.upsert(
            db,
            person_id=payload.person_id,
            chain_id=payload.chain_id,
            protocol=payload.protocol,
            operation_type=payload.operation_type,
            step_type=payload.step_type,
            idempotency_key=payload.idempotency_key,
            status=AttemptStatus.PREPARED.value,
            step_index=payload.step_index,
            group_key=payload.group_key,
            intent_id=payload.intent_id,
            parent_intent_id=payload.parent_intent_id,
            person_crypto_wallet_id=payload.person_crypto_wallet_id,
            wallet_address=payload.wallet_address,
            asset_in=payload.asset_in,
            asset_out=payload.asset_out,
            amount_in=payload.amount_in,
            amount_out_expected=payload.amount_out_expected,
            linked_table=payload.linked_table,
            linked_id=payload.linked_id,
            linked_reference_id=payload.linked_reference_id,
            metadata_patch=payload.metadata_patch,
            raw_request_json=payload.raw_request_json,
            raw_submission_json=payload.raw_submission_json,
        )
        if created:
            logger.info(
                "attempt.prepared",
                extra={
                    "attempt_id": str(row.id),
                    "protocol": row.protocol,
                    "step_type": row.step_type,
                },
            )
            try:
                from services.transaction_trace.enums import TraceEventType
                from services.transaction_trace.transaction_trace_logger import log_transaction_trace

                log_transaction_trace(
                    TraceEventType.ATTEMPT_PREPARED,
                    db=db,
                    person_id=row.person_id,
                    intent_id=row.intent_id,
                    attempt_id=row.id,
                    group_key=row.group_key,
                    idempotency_key=row.idempotency_key,
                    protocol=row.protocol,
                    operation_type=row.operation_type,
                    step_type=row.step_type,
                    status_to=row.status,
                    chain_id=row.chain_id,
                    linked_table=row.linked_table,
                    linked_id=row.linked_id,
                    linked_reference_id=row.linked_reference_id,
                    source="transaction_attempts.service.create_prepared_attempt",
                    message="attempt prepared",
                    metadata_json=payload.metadata_patch,
                )
            except Exception:
                pass
        return attempt_to_dict(row)

    @staticmethod
    def mark_signed(
        db: Session,
        *,
        idempotency_key: str,
        step_type: str,
        transition: AttemptTransitionInput | None = None,
    ) -> dict[str, Any] | None:
        return OnchainTransactionAttemptService._transition(
            db,
            idempotency_key=idempotency_key,
            step_type=step_type,
            status=AttemptStatus.SIGNED.value,
            transition=transition,
        )

    @staticmethod
    def mark_submitted(
        db: Session,
        *,
        idempotency_key: str,
        step_type: str,
        transition: AttemptTransitionInput | None = None,
    ) -> dict[str, Any] | None:
        return OnchainTransactionAttemptService._transition(
            db,
            idempotency_key=idempotency_key,
            step_type=step_type,
            status=AttemptStatus.SUBMITTED.value,
            transition=transition,
        )

    @staticmethod
    def mark_confirmed(
        db: Session,
        *,
        idempotency_key: str,
        step_type: str,
        transition: AttemptTransitionInput | None = None,
    ) -> dict[str, Any] | None:
        return OnchainTransactionAttemptService._transition(
            db,
            idempotency_key=idempotency_key,
            step_type=step_type,
            status=AttemptStatus.CONFIRMED.value,
            transition=transition,
        )

    @staticmethod
    def mark_failed(
        db: Session,
        *,
        idempotency_key: str,
        step_type: str,
        transition: AttemptTransitionInput | None = None,
        reverted: bool = False,
    ) -> dict[str, Any] | None:
        status = AttemptStatus.REVERTED.value if reverted else AttemptStatus.FAILED.value
        return OnchainTransactionAttemptService._transition(
            db,
            idempotency_key=idempotency_key,
            step_type=step_type,
            status=status,
            transition=transition,
        )

    @staticmethod
    def link_legacy_record(
        db: Session,
        *,
        idempotency_key: str,
        step_type: str,
        linked_table: str,
        linked_id: UUID,
        linked_reference_id: str | None = None,
        metadata_patch: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        row = OnchainTransactionAttemptRepository.find_by_composite_key(
            db,
            idempotency_key=idempotency_key,
            step_type=step_type,
        )
        if row is None:
            return None
        row.linked_table = linked_table
        row.linked_id = linked_id
        if linked_reference_id is not None:
            row.linked_reference_id = linked_reference_id
        if metadata_patch:
            base = row.metadata_json if isinstance(row.metadata_json, dict) else {}
            row.metadata_json = {**base, **metadata_patch}
        db.add(row)
        db.flush()
        try:
            from services.transaction_trace.enums import TraceEventType
            from services.transaction_trace.transaction_trace_logger import log_transaction_trace

            log_transaction_trace(
                TraceEventType.LEGACY_RECORD_LINKED,
                db=db,
                person_id=row.person_id,
                intent_id=row.intent_id,
                attempt_id=row.id,
                group_key=row.group_key,
                idempotency_key=row.idempotency_key,
                protocol=row.protocol,
                operation_type=row.operation_type,
                step_type=row.step_type,
                linked_table=linked_table,
                linked_id=linked_id,
                linked_reference_id=linked_reference_id,
                source="transaction_attempts.service.link_legacy_record",
                message="legacy record linked to attempt",
                metadata_json=metadata_patch,
            )
        except Exception:
            pass
        return attempt_to_dict(row)

    @staticmethod
    def _transition(
        db: Session,
        *,
        idempotency_key: str,
        step_type: str,
        status: str,
        transition: AttemptTransitionInput | None,
    ) -> dict[str, Any] | None:
        row = OnchainTransactionAttemptRepository.find_by_composite_key(
            db,
            idempotency_key=idempotency_key,
            step_type=step_type,
        )
        if row is None:
            return None

        status_from = row.status
        t = transition or AttemptTransitionInput()
        row.status = _norm_status(status)
        if t.tx_hash:
            row.tx_hash = t.tx_hash.strip().lower()
        if t.from_address:
            row.from_address = t.from_address.strip().lower()
        if t.to_address:
            row.to_address = t.to_address.strip().lower()
        if t.log_index is not None:
            row.log_index = t.log_index
        if t.block_number is not None:
            row.block_number = t.block_number
        if t.error_code:
            row.error_code = t.error_code
        if t.error_message:
            row.error_message = t.error_message
        if t.amount_out_actual is not None:
            row.amount_out_actual = t.amount_out_actual
        if t.raw_submission_json is not None:
            row.raw_submission_json = t.raw_submission_json
        if t.raw_receipt_json is not None:
            row.raw_receipt_json = t.raw_receipt_json
        if t.raw_revert_json is not None:
            row.raw_revert_json = t.raw_revert_json
        if t.metadata_patch:
            base = row.metadata_json if isinstance(row.metadata_json, dict) else {}
            row.metadata_json = {**base, **t.metadata_patch}

        db.add(row)
        db.flush()
        try:
            from services.transaction_trace.transaction_trace_logger import log_attempt_transition_trace

            log_attempt_transition_trace(
                db,
                row=row,
                status_from=status_from,
                status_to=row.status,
                source="transaction_attempts.service._transition",
                transition=t,
            )
        except Exception:
            pass
        return attempt_to_dict(row)
