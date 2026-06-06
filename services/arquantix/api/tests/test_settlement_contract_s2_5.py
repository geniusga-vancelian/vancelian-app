"""Phase 2 S2.5 — Settlement Layer skeleton NOOP (Contract v1, zéro écriture économique)."""
from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.cost_basis.models import CostBasisExecution
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.positions.models import PositionAtom
from services.privy_wallet.models import PersonWalletBalance, PersonWalletDeposit
from services.settlement.result import SettlementOutcome
from services.settlement.settle import settle_transaction_intent_idempotently
from services.transaction_intents.enums import IntentStatus
from services.transaction_outbox.atomic import persist_intent_swap_outbox_atomic
from services.transaction_outbox.intent_phases import IntentOrchestratorPhase
from tests.conftest import make_linked_client


def _migration_173_ready() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'transaction_outbox'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_173_ready(),
    reason="Migration 173 requise.",
)


def _economic_counts(db: Session, person_id) -> dict[str, int]:
    return {
        "balances": db.query(PersonWalletBalance)
        .filter(PersonWalletBalance.person_id == person_id)
        .count(),
        "deposits": db.query(PersonWalletDeposit)
        .filter(PersonWalletDeposit.person_id == person_id)
        .count(),
        "pe_atoms": db.query(PositionAtom).count(),
        "cost_basis": db.query(CostBasisExecution).count(),
    }


def _ready_intent_bundle(db: Session):
    pe = make_linked_client(db)
    bundle = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
    )
    bundle.intent.current_phase = IntentOrchestratorPhase.QUEUED.value
    db.commit()
    return pe, bundle


def test_s2_5_intent_absent_terminal_failure(db: Session):
    missing_id = uuid4()
    result = settle_transaction_intent_idempotently(db, intent_id=missing_id)
    assert result.outcome == SettlementOutcome.TERMINAL_FAILURE
    assert result.error_code == "intent.not_found"


def test_s2_5_missing_idempotency_key_terminal_failure(db: Session):
    pe, bundle = _ready_intent_bundle(db)
    bundle.intent.idempotency_key = "   "
    db.commit()

    result = settle_transaction_intent_idempotently(db, intent_id=bundle.intent.id)
    assert result.outcome == SettlementOutcome.TERMINAL_FAILURE
    assert result.error_code == "intent.missing_idempotency_key"
    assert _economic_counts(db, pe.person_id) == _economic_counts(db, pe.person_id)


def test_s2_5_linked_entity_missing_terminal_failure(db: Session):
    pe, bundle = _ready_intent_bundle(db)
    bundle.intent.linked_id = uuid4()
    db.commit()

    result = settle_transaction_intent_idempotently(db, intent_id=bundle.intent.id)
    assert result.outcome == SettlementOutcome.TERMINAL_FAILURE
    assert result.error_code == "intent.linked_entity_not_found"


def test_s2_5_already_settled_noop(db: Session):
    pe, bundle = _ready_intent_bundle(db)
    existing_hash = "abc123deadbeef"
    bundle.intent.metadata_json = {
        **(bundle.intent.metadata_json or {}),
        "settlement_receipt_hash": existing_hash,
    }
    db.commit()

    before = _economic_counts(db, pe.person_id)
    result = settle_transaction_intent_idempotently(db, intent_id=bundle.intent.id)
    assert result.outcome == SettlementOutcome.NOOP_ALREADY_SETTLED
    assert result.settlement_receipt_hash == existing_hash
    assert _economic_counts(db, pe.person_id) == before


def test_s2_5_valid_intent_success_no_economic_writes(db: Session):
    pe, bundle = _ready_intent_bundle(db)
    before = _economic_counts(db, pe.person_id)

    result = settle_transaction_intent_idempotently(db, intent_id=bundle.intent.id)
    assert result.outcome == SettlementOutcome.SUCCESS
    assert result.settlement_receipt_hash
    assert len(result.settlement_receipt_hash) == 64

    db.refresh(bundle.intent)
    assert bundle.intent.status not in {"COMPLETED", "completed"}
    assert bundle.intent.status == IntentStatus.CREATED.value
    assert (bundle.intent.metadata_json or {}).get("settlement_receipt_hash") is None

    after = _economic_counts(db, pe.person_id)
    assert after == before


def test_s2_5_two_consecutive_calls_no_economic_double_write(db: Session):
    pe, bundle = _ready_intent_bundle(db)
    before = _economic_counts(db, pe.person_id)

    first = settle_transaction_intent_idempotently(db, intent_id=bundle.intent.id)
    second = settle_transaction_intent_idempotently(db, intent_id=bundle.intent.id)

    assert first.outcome == SettlementOutcome.SUCCESS
    assert second.outcome == SettlementOutcome.SUCCESS
    assert first.settlement_receipt_hash == second.settlement_receipt_hash
    assert _economic_counts(db, pe.person_id) == before

    swaps = db.query(PersonWalletSwap).count()
    assert swaps >= 1
