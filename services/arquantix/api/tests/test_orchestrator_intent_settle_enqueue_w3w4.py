"""W3/W4 — auto-enqueue ``intent.settle`` on orchestrator swap CONFIRMED."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.cost_basis.models import CostBasisExecution
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_execute_service import LifiExecuteService
from services.lifi.lifi_swap_settlement import apply_swap_settlement
from services.portfolio_engine.positions.models import PositionAtom
from services.onchain_indexer.models import TransactionIntent
from services.privy_wallet.models import PersonWalletBalance, PersonWalletDeposit
from services.lifi.models import PersonWalletSwap
from services.settlement.constants import SETTLEMENT_RECEIPT_METADATA_KEY
from services.transaction_outbox.atomic import attach_orchestrator_intent_to_swap_atomic
from services.transaction_outbox.enums import OutboxEventType
from services.transaction_outbox.intent_phases import IntentOrchestratorPhase
from services.transaction_outbox.orchestrator_settle_enqueue import (
    ENQUEUE_SOURCE,
    maybe_enqueue_orchestrator_intent_settle,
)
from services.transaction_outbox.repository import TransactionOutboxRepository
from services.transaction_outbox.worker import handle_intent_created_event
from tests.conftest import make_linked_client
from tests.lifi_orchestrator_test_utils import enable_lifi_orchestrator_allowlist
from tests.test_lifi_swap_routes import _seed_wallet

EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
TX_HASH = "0xw3w4test1234567890abcdef1234567890abcdef1234567890abcdef123456"


def _migration_outbox_ready() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM pg_indexes "
                    "WHERE schemaname = 'public' AND indexname = 'uq_outbox_intent_event_type'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_outbox_ready(),
    reason="Migration 174 (uq_outbox_intent_event_type) requise.",
)


def _economic_counts(db: Session, person_id) -> dict[str, int]:
    return {
        "deposits": db.query(PersonWalletDeposit)
        .filter(PersonWalletDeposit.person_id == person_id)
        .count(),
        "balances": db.query(PersonWalletBalance)
        .filter(PersonWalletBalance.person_id == person_id)
        .count(),
        "pe_atoms": db.query(PositionAtom).count(),
        "cost_basis": db.query(CostBasisExecution).count(),
    }


def _enable_orchestrator(monkeypatch, pe) -> None:
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")


def _seed_orchestrator_queued_swap(db: Session, monkeypatch, *, phase: str = "QUEUED"):
    pe = make_linked_client(db)
    _enable_orchestrator(monkeypatch, pe)
    _seed_wallet(db, pe)

    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="AAVE",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1"),
        slippage_bps=50,
        expires_at=datetime.now(timezone.utc),
        tx_hash=TX_HASH,
        confirmed_at=datetime.now(timezone.utc),
        estimated_receive=Decimal("0.05"),
        audit_log=[{"event": "quote_requested", "signing_wallet_address": EVM_ADDR}],
    )
    db.add(swap)
    db.flush()

    attach_orchestrator_intent_to_swap_atomic(
        db,
        person_id=pe.person_id,
        swap_id=swap.id,
    )
    intent = db.query(TransactionIntent).filter(TransactionIntent.linked_id == swap.id).one()
    intent.current_phase = phase
    db.commit()
    db.refresh(swap)
    db.refresh(intent)
    return pe, swap, intent


def _settle_outbox_count(db: Session, intent_id) -> int:
    return len(
        TransactionOutboxRepository.find_by_intent(
            db, intent_id, event_type=OutboxEventType.INTENT_SETTLE.value
        )
    )


def test_w3w4_confirmed_orchestrator_enqueues_one_intent_settle(db: Session, monkeypatch):
    pe, swap, intent = _seed_orchestrator_queued_swap(db, monkeypatch)
    before = _economic_counts(db, pe.person_id)

    result = maybe_enqueue_orchestrator_intent_settle(db, swap)
    db.commit()

    assert result.enqueued is True
    assert result.outbox is not None
    assert result.outbox.event_type == OutboxEventType.INTENT_SETTLE.value
    assert result.outbox.status == "pending"
    assert (result.outbox.payload_json or {}).get("source") == ENQUEUE_SOURCE
    assert (result.outbox.payload_json or {}).get("tx_hash") == TX_HASH
    assert _settle_outbox_count(db, intent.id) == 1

    after = _economic_counts(db, pe.person_id)
    assert after["deposits"] == before["deposits"]
    assert after["pe_atoms"] == before["pe_atoms"]
    assert after["cost_basis"] == before["cost_basis"]


def test_w3w4_rerun_no_duplicate_intent_settle(db: Session, monkeypatch):
    _, swap, intent = _seed_orchestrator_queued_swap(db, monkeypatch)

    first = maybe_enqueue_orchestrator_intent_settle(db, swap)
    db.commit()
    second = maybe_enqueue_orchestrator_intent_settle(db, swap)

    assert first.enqueued is True
    assert second.enqueued is False
    assert second.reason == "intent_settle_already_enqueued"
    assert _settle_outbox_count(db, intent.id) == 1


def test_w3w4_legacy_non_orchestrator_no_enqueue(db: Session, monkeypatch):
    monkeypatch.delenv("LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS", raising=False)
    monkeypatch.delenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", raising=False)
    pe = make_linked_client(db)
    _seed_wallet(db, pe)

    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1"),
        slippage_bps=50,
        expires_at=datetime.now(timezone.utc),
        tx_hash=TX_HASH,
        audit_log=[],
    )
    db.add(swap)
    db.commit()

    result = maybe_enqueue_orchestrator_intent_settle(db, swap)
    assert result.enqueued is False
    assert result.reason == "no_phase2_orchestrator_intent"


def test_w3w4_bundle_internal_swap_no_enqueue(db: Session, monkeypatch):
    _, swap, intent = _seed_orchestrator_queued_swap(db, monkeypatch)
    swap.audit_log = [
        {
            "event": "bundle_leg_context",
            "bundle_execution": True,
            "bundle_action": "rebalance",
            "batch_id": "batch-1",
        }
    ]
    db.commit()

    result = maybe_enqueue_orchestrator_intent_settle(db, swap)
    assert result.enqueued is False
    assert result.reason == "bundle_internal_swap"
    assert _settle_outbox_count(db, intent.id) == 0


def test_w3w4_confirmed_without_tx_hash_no_enqueue(db: Session, monkeypatch):
    _, swap, intent = _seed_orchestrator_queued_swap(db, monkeypatch)
    swap.tx_hash = None
    db.commit()

    result = maybe_enqueue_orchestrator_intent_settle(db, swap)
    assert result.enqueued is False
    assert result.reason == "missing_tx_hash"
    assert _settle_outbox_count(db, intent.id) == 0


@pytest.mark.parametrize(
    "status",
    [SwapSessionStatus.FAILED.value, SwapSessionStatus.EXPIRED.value, SwapSessionStatus.SUBMITTED.value],
)
def test_w3w4_non_confirmed_status_no_enqueue(db: Session, monkeypatch, status: str):
    _, swap, intent = _seed_orchestrator_queued_swap(db, monkeypatch)
    swap.status = status
    db.commit()

    result = maybe_enqueue_orchestrator_intent_settle(db, swap)
    assert result.enqueued is False
    assert result.reason.startswith("swap_status:")
    assert _settle_outbox_count(db, intent.id) == 0


def test_w3w4_intent_already_settled_no_enqueue(db: Session, monkeypatch):
    _, swap, intent = _seed_orchestrator_queued_swap(db, monkeypatch)
    intent.current_phase = IntentOrchestratorPhase.LEDGER_SETTLED.value
    intent.metadata_json = {**(intent.metadata_json or {}), SETTLEMENT_RECEIPT_METADATA_KEY: "abc123"}
    db.commit()

    result = maybe_enqueue_orchestrator_intent_settle(db, swap)
    assert result.enqueued is False
    assert result.reason.startswith("intent_phase_settled:")
    assert _settle_outbox_count(db, intent.id) == 0


def test_w3w4_intent_phase_created_not_ready(db: Session, monkeypatch):
    _, swap, intent = _seed_orchestrator_queued_swap(db, monkeypatch, phase="CREATED")
    db.commit()

    result = maybe_enqueue_orchestrator_intent_settle(db, swap)
    assert result.enqueued is False
    assert result.reason == "intent_phase_not_ready:CREATED"
    assert _settle_outbox_count(db, intent.id) == 0


def test_w3w4_onchain_confirmed_phase_allowed(db: Session, monkeypatch):
    _, swap, intent = _seed_orchestrator_queued_swap(db, monkeypatch, phase="ONCHAIN_CONFIRMED")
    db.commit()

    result = maybe_enqueue_orchestrator_intent_settle(db, swap)
    db.commit()

    assert result.enqueued is True
    assert _settle_outbox_count(db, intent.id) == 1


def test_w3w4_dual_path_serial_no_duplicate(db: Session, monkeypatch):
    """Simule refresh + reconciliation séquentiels sur le même CONFIRMED."""
    _, swap, intent = _seed_orchestrator_queued_swap(db, monkeypatch)

    first = maybe_enqueue_orchestrator_intent_settle(db, swap)
    second = maybe_enqueue_orchestrator_intent_settle(db, swap)
    db.commit()

    assert first.enqueued is True
    assert second.enqueued is False
    assert second.reason == "intent_settle_already_enqueued"
    assert _settle_outbox_count(db, intent.id) == 1


def test_w3w4_confirmed_before_queued_recovered_by_worker(db: Session, monkeypatch):
    """Swap CONFIRMED avant worker intent.created → enqueue au passage QUEUED."""
    _, swap, intent = _seed_orchestrator_queued_swap(db, monkeypatch, phase="CREATED")
    created_outbox = TransactionOutboxRepository.find_by_intent(
        db, intent.id, event_type=OutboxEventType.INTENT_CREATED.value
    )[0]

    blocked = maybe_enqueue_orchestrator_intent_settle(db, swap)
    assert blocked.enqueued is False
    assert blocked.reason == "intent_phase_not_ready:CREATED"
    assert _settle_outbox_count(db, intent.id) == 0

    handle_intent_created_event(db, created_outbox)
    db.commit()

    assert intent.current_phase == "QUEUED"
    assert _settle_outbox_count(db, intent.id) == 1
    settle_rows = TransactionOutboxRepository.find_by_intent(
        db, intent.id, event_type=OutboxEventType.INTENT_SETTLE.value
    )
    assert settle_rows[0].status == "pending"
    assert (settle_rows[0].payload_json or {}).get("source") == ENQUEUE_SOURCE


def test_w3w4_processed_settle_silent_rerun(db: Session, monkeypatch, caplog):
    """intent.settle déjà processed → 0 nouvelle ligne, 0 log enqueue."""
    _, swap, intent = _seed_orchestrator_queued_swap(db, monkeypatch)
    first = maybe_enqueue_orchestrator_intent_settle(db, swap)
    db.commit()
    assert first.enqueued is True

    processed = TransactionOutboxRepository.find_by_intent(
        db, intent.id, event_type=OutboxEventType.INTENT_SETTLE.value
    )[0]
    TransactionOutboxRepository.mark_processed(db, processed)
    db.commit()

    caplog.set_level("INFO")
    caplog.clear()
    second = maybe_enqueue_orchestrator_intent_settle(db, swap)

    assert second.enqueued is False
    assert second.reason == "intent_settle_already_enqueued"
    assert _settle_outbox_count(db, intent.id) == 1
    assert "orchestrator_intent_settle_enqueued" not in caplog.text


def test_w3w4_apply_swap_settlement_skipped_for_orchestrator(db: Session, monkeypatch):
    pe, swap, _ = _seed_orchestrator_queued_swap(db, monkeypatch)
    before_deposits = (
        db.query(PersonWalletDeposit).filter(PersonWalletDeposit.person_id == pe.person_id).count()
    )

    apply_swap_settlement(db, swap, sync_source="lifi_swap", allow_mock_quote_amount=True)
    db.commit()

    after_deposits = (
        db.query(PersonWalletDeposit).filter(PersonWalletDeposit.person_id == pe.person_id).count()
    )
    assert after_deposits == before_deposits


def test_w3w4_refresh_lifi_status_done_enqueues_via_execute_service(db: Session, monkeypatch):
    from unittest.mock import MagicMock

    from services.lifi.lifi_actual_receive import LifiActualReceiveResult

    pe, swap, intent = _seed_orchestrator_queued_swap(db, monkeypatch)
    swap.status = SwapSessionStatus.SUBMITTED.value
    swap.lifi_tool = "stargateV2"
    swap.lifi_quote_raw = {
        "action": {"fromChainId": 8453, "toChainId": 8453},
        "estimate": {"toAmount": "50000000000000000"},
    }
    db.commit()

    svc = LifiExecuteService(lifi_client=MagicMock())
    svc._lifi.get_status = MagicMock(
        return_value={
            "status": "DONE",
            "substatus": "COMPLETED",
            "substatusMessage": "ok",
        }
    )
    monkeypatch.setattr(
        "services.lifi.lifi_execute_service.resolve_lifi_actual_receive_amount",
        lambda db, swap, **kw: LifiActualReceiveResult(
            amount=Decimal("0.05"),
            source="test",
            receive_tx_hash=TX_HASH,
        ),
    )

    svc.refresh_lifi_status(db, swap)
    db.commit()

    rows = TransactionOutboxRepository.find_by_intent(
        db, intent.id, event_type=OutboxEventType.INTENT_SETTLE.value
    )
    assert len(rows) == 1
    assert rows[0].status == "pending"
    assert (rows[0].payload_json or {}).get("source") == ENQUEUE_SOURCE
