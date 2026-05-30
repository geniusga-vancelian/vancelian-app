"""Tests transaction trace logging — observabilité (pas source of truth)."""
from __future__ import annotations

import json
import logging
import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from services.transaction_attempts.enums import AttemptProtocol, AttemptStepType
from services.transaction_attempts.schemas import AttemptCreateInput, AttemptTransitionInput
from services.transaction_attempts.service import OnchainTransactionAttemptService
from services.transaction_trace.enums import TraceEventType
from services.transaction_trace.transaction_trace_logger import (
    log_attempt_transition_trace,
    log_transaction_trace,
)
from services.transaction_attempts.reconciliation import group_legacy_records_by_chain_tx
from tests.conftest import make_linked_client
from tests.test_phase2_transaction_attempts import _migration_171_ready
from tests.test_phase7_transaction_intents import _migration_166_ready

pytestmark = [
    pytest.mark.skipif(not _migration_166_ready(), reason="Migration 166 requise."),
]


def _parse_trace_log(caplog) -> dict:
    records = [
        r
        for r in caplog.records
        if r.name == "arquantix.transaction_trace" and r.levelno == logging.INFO
    ]
    assert records, "aucun log transaction_trace capturé"
    return json.loads(records[-1].message)


def test_attempt_confirmed_emits_structured_trace(caplog, db: Session):
    caplog.set_level(logging.INFO, logger="arquantix.transaction_trace")
    pe = make_linked_client(db)
    idem = f"trace-confirmed-{uuid.uuid4().hex[:12]}"
    tx_hash = f"0x{'a' * 64}"

    OnchainTransactionAttemptService.create_prepared_attempt(
        db,
        AttemptCreateInput(
            person_id=pe.person_id,
            chain_id=8453,
            protocol=AttemptProtocol.LIFI.value,
            operation_type="swap",
            step_type=AttemptStepType.SWAP.value,
            idempotency_key=idem,
            group_key="g-trace",
        ),
    )
    caplog.clear()

    OnchainTransactionAttemptService.mark_submitted(
        db,
        idempotency_key=idem,
        step_type=AttemptStepType.SWAP.value,
        transition=AttemptTransitionInput(tx_hash=tx_hash),
    )
    OnchainTransactionAttemptService.mark_confirmed(
        db,
        idempotency_key=idem,
        step_type=AttemptStepType.SWAP.value,
        transition=AttemptTransitionInput(tx_hash=tx_hash),
    )

    payload = _parse_trace_log(caplog)
    assert payload["event_type"] == TraceEventType.ATTEMPT_CONFIRMED.value
    assert payload["person_id"] == str(pe.person_id)
    assert payload["idempotency_key"] == idem
    assert payload["step_type"] == AttemptStepType.SWAP.value
    assert payload["status_from"] == "submitted"
    assert payload["status_to"] == "confirmed"
    assert payload["tx_hash"] == tx_hash.lower()
    assert payload["chain_id"] == 8453
    assert payload["trace_id"]
    assert payload["timestamp"]


def test_failed_attempt_trace_includes_error_code(caplog):
    caplog.set_level(logging.INFO, logger="arquantix.transaction_trace")
    person_id = uuid.uuid4()
    attempt_id = uuid.uuid4()
    row = SimpleNamespace(
        person_id=person_id,
        intent_id=None,
        id=attempt_id,
        group_key="g-fail",
        idempotency_key="lifi:swap-1:swap",
        protocol=AttemptProtocol.LIFI.value,
        operation_type="swap",
        step_type=AttemptStepType.SWAP.value,
        tx_hash="0x" + "b" * 64,
        chain_id=8453,
        linked_table="person_wallet_swaps",
        linked_id=uuid.uuid4(),
        linked_reference_id=None,
    )
    transition = SimpleNamespace(
        error_code="REVERTED",
        error_message="execution reverted",
    )

    log_attempt_transition_trace(
        None,
        row=row,
        status_from="submitted",
        status_to="failed",
        source="test",
        transition=transition,
    )

    payload = _parse_trace_log(caplog)
    assert payload["event_type"] == TraceEventType.ATTEMPT_FAILED.value
    assert payload["status_to"] == "failed"
    assert payload["metadata_json"]["error_code"] == "REVERTED"
    assert "reverted" in payload["metadata_json"]["error_message"]


def test_backfill_grouped_tx_hash_trace_is_human_readable(caplog):
    caplog.set_level(logging.INFO, logger="arquantix.transaction_trace")
    person_id = uuid.uuid4()
    tx_hash = "0x" + "c" * 64
    chain_id = 8453
    canonical_ref = str(uuid.uuid4())
    secondary_ref = str(uuid.uuid4())

    records = [
        {
            "person_id": str(person_id),
            "chain_id": chain_id,
            "tx_hash": tx_hash,
            "reference_id": canonical_ref,
            "source": "person_wallet_swaps",
            "step_type": AttemptStepType.SWAP.value,
            "protocol": AttemptProtocol.LIFI.value,
            "legacy_idempotency_key": f"backfill:chain:{chain_id}:tx:{tx_hash}",
        },
        {
            "person_id": str(person_id),
            "chain_id": chain_id,
            "tx_hash": tx_hash,
            "reference_id": secondary_ref,
            "source": "person_wallet_swaps",
            "step_type": AttemptStepType.SWAP.value,
            "protocol": AttemptProtocol.LIFI.value,
            "legacy_idempotency_key": f"backfill:chain:{chain_id}:tx:{tx_hash}",
        },
    ]
    grouped, _, duplicate_groups = group_legacy_records_by_chain_tx(records)
    assert len(grouped) == 1
    assert duplicate_groups[0]["record_count"] == 2

    grouping = grouped[0]["grouping"]
    log_transaction_trace(
        TraceEventType.REPLAY_BACKFILL_APPLIED,
        db=None,
        person_id=person_id,
        idempotency_key=grouped[0]["idempotency_key"],
        protocol=AttemptProtocol.LIFI.value,
        operation_type="swap",
        step_type=AttemptStepType.SWAP.value,
        status_to="confirmed",
        tx_hash=tx_hash,
        chain_id=chain_id,
        linked_table="person_wallet_swaps",
        linked_id=uuid.UUID(canonical_ref),
        source="transaction_attempts.reconciliation.apply_backfill",
        message="backfill attempt applied from legacy",
        metadata_json=grouping,
        persist_db=False,
    )

    payload = _parse_trace_log(caplog)
    assert payload["event_type"] == TraceEventType.REPLAY_BACKFILL_APPLIED.value
    assert payload["tx_hash"] == tx_hash.lower()
    assert payload["metadata_json"]["backfill_grouped_by_tx_hash"] is True
    assert payload["metadata_json"]["secondary_count"] == 1
    assert payload["metadata_json"]["legacy_records_in_group"] == 2
    assert payload["message"] == "backfill attempt applied from legacy"


def test_sensitive_metadata_is_redacted(caplog):
    caplog.set_level(logging.INFO, logger="arquantix.transaction_trace")

    log_transaction_trace(
        TraceEventType.ATTEMPT_SIGNED,
        db=None,
        message="signed",
        metadata_json={
            "private_key": "0xsecret",
            "jwt": "eyJhbG",
            "note": "ok",
        },
        persist_db=False,
    )

    payload = _parse_trace_log(caplog)
    assert payload["metadata_json"]["private_key"] == "[REDACTED]"
    assert payload["metadata_json"]["jwt"] == "[REDACTED]"
    assert payload["metadata_json"]["note"] == "ok"


@pytest.mark.skipif(not _migration_171_ready(), reason="Migration 171 requise.")
def test_service_transition_logs_without_db_persist_when_table_absent(caplog, db: Session):
    """Le trace JSON applicatif est émis même si migration 172 absente."""
    caplog.set_level(logging.INFO, logger="arquantix.transaction_trace")
    pe = make_linked_client(db)
    idem = f"trace-nodb-{uuid.uuid4().hex[:12]}"

    OnchainTransactionAttemptService.create_prepared_attempt(
        db,
        AttemptCreateInput(
            person_id=pe.person_id,
            chain_id=8453,
            protocol=AttemptProtocol.MORPHO.value,
            operation_type="deposit",
            step_type=AttemptStepType.DEPOSIT.value,
            idempotency_key=idem,
        ),
    )
    caplog.clear()
    OnchainTransactionAttemptService.mark_confirmed(
        db,
        idempotency_key=idem,
        step_type=AttemptStepType.DEPOSIT.value,
        transition=AttemptTransitionInput(tx_hash="0x" + "d" * 64),
    )

    payload = _parse_trace_log(caplog)
    assert payload["event_type"] == TraceEventType.ATTEMPT_CONFIRMED.value
    assert payload["protocol"] == AttemptProtocol.MORPHO.value
