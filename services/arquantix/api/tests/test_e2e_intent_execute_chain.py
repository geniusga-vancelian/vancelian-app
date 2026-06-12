"""Incrément 4 — intégration end-to-end de la chaîne outbox d'exécution serveur.

Parcourt le câblage réel : ``intent.created`` → QUEUED → enqueue ``intent.execute``
→ poll worker → **vraie** ``execute_prepared_swap_server_side`` (corps complet) →
``mark_processed`` + transition. Seules les frontières Privy/LI.FI sont mockées.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.trade_core import server_execution as se
from services.transaction_outbox.atomic import attach_orchestrator_intent_to_swap_atomic
from services.transaction_outbox.enums import OutboxEventType
from services.transaction_outbox.execution_worker import (
    process_transaction_outbox_intent_execute,
)
from services.transaction_outbox.repository import TransactionOutboxRepository
from services.transaction_outbox.worker import handle_intent_created_event
from tests.conftest import make_linked_client
from tests.lifi_orchestrator_test_utils import enable_lifi_orchestrator_allowlist
from tests.test_lifi_swap_routes import _seed_wallet

EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"


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


class _FakeExecuteSvc:
    def __init__(self):
        self.approval_calls = []

    def prepare_execute(self, db, *, person_id, swap_id):
        return SimpleNamespace(
            signing_wallet_address=EVM_ADDR,
            signing_wallet_mode="privy_embedded",
            transaction=SimpleNamespace(
                chain_id=8453, to="0xrouter", data="0xdead", value="0x0", gas_limit="0x5208"
            ),
            token_approval=None,
        )

    def record_token_approval(self, db, *, person_id, swap_id, tx_hash, signing_wallet_address):
        self.approval_calls.append(tx_hash)


def _seed_and_queue(db: Session, monkeypatch):
    """Crée un swap orchestrateur QUOTE_RECEIVED puis exécute le worker intent.created → QUEUED."""
    pe = make_linked_client(db)
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    monkeypatch.setenv("LIFI_EXECUTION_WORKER_ENABLED", "true")
    _seed_wallet(db, pe)

    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=SwapSessionStatus.QUOTE_RECEIVED.value,
        from_asset="USDC",
        to_asset="AAVE",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1"),
        slippage_bps=50,
        expires_at=datetime.now(timezone.utc),
        estimated_receive=Decimal("0.05"),
        audit_log=[{"event": "quote_requested", "signing_wallet_address": EVM_ADDR}],
    )
    db.add(swap)
    db.flush()

    attach_orchestrator_intent_to_swap_atomic(db, person_id=pe.person_id, swap_id=swap.id)
    intent = db.query(TransactionIntent).filter(TransactionIntent.linked_id == swap.id).one()
    db.commit()

    created = TransactionOutboxRepository.find_by_intent(
        db, intent.id, event_type=OutboxEventType.INTENT_CREATED.value
    )[0]
    handle_intent_created_event(db, created)
    db.commit()
    db.refresh(intent)

    assert intent.current_phase == "QUEUED"
    execute_rows = TransactionOutboxRepository.find_by_intent(
        db, intent.id, event_type=OutboxEventType.INTENT_EXECUTE.value
    )
    assert len(execute_rows) == 1  # le passage QUEUED a bien enqueué l'exécution serveur
    return pe, swap, intent


def _patch_privy_boundary(monkeypatch, *, delegated=True):
    monkeypatch.setattr(se, "privy_delegated_signing_configured", lambda: True)
    monkeypatch.setattr(
        se, "is_signing_wallet_delegated", lambda db, *, person_id, wallet_address: delegated
    )
    monkeypatch.setattr(
        se, "resolve_privy_wallet_id", lambda db, *, person_id, wallet_address: "wallet-rpc-id"
    )
    monkeypatch.setattr(
        "services.lifi.lifi_execute_service.LifiExecuteService", lambda *a, **k: _FakeExecuteSvc()
    )


def _execute_outbox_status(db: Session, intent_id):
    rows = TransactionOutboxRepository.find_by_intent(
        db, intent_id, event_type=OutboxEventType.INTENT_EXECUTE.value
    )
    return [r.status for r in rows]


def test_e2e_chain_signs_and_processes(db: Session, monkeypatch):
    pe, swap, intent = _seed_and_queue(db, monkeypatch)
    _patch_privy_boundary(monkeypatch, delegated=True)

    sent: list[dict] = []
    monkeypatch.setattr(
        se, "send_delegated_sponsored_transaction",
        lambda **kw: sent.append(kw) or {"hash": "0xfeed", "transaction_id": "t1"},
    )
    monkeypatch.setattr(
        se, "complete_virtual_wallet_swap",
        lambda db_arg, **kw: SimpleNamespace(
            finalize=SimpleNamespace(status="confirmed", settled=True, tx_hash=kw["tx_hash"]),
            phase="confirmed",
        ),
    )

    result = process_transaction_outbox_intent_execute(db, limit=10)

    assert result["enabled"] is True
    assert result["processed"] == 1
    assert result["signed_server_side"] == 1
    assert result["failed"] == 0
    assert len(sent) == 1  # swap signé une fois (pas d'approval)
    assert _execute_outbox_status(db, intent.id) == ["processed"]

    # transition EXECUTED écrite par le handler
    assert (
        db.execute(
            sa.text(
                "SELECT COUNT(*) FROM transaction_intent_transitions "
                "WHERE intent_id = :iid AND phase = 'EXECUTED'"
            ),
            {"iid": str(intent.id)},
        ).scalar()
        == 1
    )


def test_e2e_chain_fallback_when_not_delegated(db: Session, monkeypatch):
    _, swap, intent = _seed_and_queue(db, monkeypatch)
    _patch_privy_boundary(monkeypatch, delegated=False)

    sent: list[dict] = []
    monkeypatch.setattr(
        se, "send_delegated_sponsored_transaction",
        lambda **kw: sent.append(kw) or {"hash": "0xnope"},
    )

    result = process_transaction_outbox_intent_execute(db, limit=10)

    assert result["enabled"] is True
    assert result["processed"] == 1  # marqué traité (deferred), pas d'échec
    assert result["signed_server_side"] == 0
    assert sent == []  # aucune signature serveur
    assert _execute_outbox_status(db, intent.id) == ["processed"]
    assert (
        db.execute(
            sa.text(
                "SELECT COUNT(*) FROM transaction_intent_transitions "
                "WHERE intent_id = :iid AND phase = 'EXECUTE_DEFERRED'"
            ),
            {"iid": str(intent.id)},
        ).scalar()
        == 1
    )


def test_e2e_worker_disabled_does_not_consume_event(db: Session, monkeypatch):
    _, swap, intent = _seed_and_queue(db, monkeypatch)
    monkeypatch.setenv("LIFI_EXECUTION_WORKER_ENABLED", "false")

    result = process_transaction_outbox_intent_execute(db, limit=10)
    assert result["enabled"] is False
    assert result["skipped"] is True
    # l'événement reste pending pour un futur run
    assert _execute_outbox_status(db, intent.id) == ["pending"]
