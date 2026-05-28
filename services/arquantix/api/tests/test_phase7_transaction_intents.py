"""Tests Phase 7 — transaction_intents / LI.FI."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_swap_settlement import swap_settlement_already_applied
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import RawOnChainEvent, TransactionIntent
from services.onchain_indexer.repository import RawOnChainEventRepository
from services.onchain_reconciliation.discrepancy_models import ReconciliationDiscrepancy
from services.onchain_reconciliation.discrepancy_repository import DiscrepancyRepository
from services.privy_wallet.repository import PersonWalletBalanceRepository, PersonWalletDepositRepository
from services.transaction_intents.enums import IntentProductType, IntentStatus
from services.transaction_intents.lifi_intent_sync import LINKED_TABLE, sync_lifi_swap_intent
from services.transaction_intents.repository import TransactionIntentRepository
from services.transaction_intents.transaction_intent_reconciliation import (
    persist_intent_discrepancies,
    scan_intent_gaps_for_person,
)
from tests.conftest import make_linked_client
from tests.test_phase4_reconciliation import _seed_wallet


def _migration_166_ready() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'transaction_intents' "
                    "AND column_name = 'product_type'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_166_ready(),
    reason="Migration 166 requise.",
)


def _seed_swap(db: Session, pe, *, status: str = "QUOTE_RECEIVED") -> PersonWalletSwap:
    swap = PersonWalletSwap(
        person_id=pe.person_id,
        status=status,
        from_asset="USDC",
        to_asset="EURC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        estimated_receive=Decimal("9"),
        tx_hash=None,
        audit_log=[],
    )
    db.add(swap)
    db.flush()
    return swap


def test_lifi_swap_create_triggers_intent(db: Session):
    from services.transaction_intents.lifi_intent_sync import on_swap_created

    pe = make_linked_client(db)
    swap = _seed_swap(db, pe)
    on_swap_created(db, swap)
    db.commit()

    intent = TransactionIntentRepository.find_by_linked(
        db,
        linked_table=LINKED_TABLE,
        linked_id=swap.id,
    )
    assert intent is not None
    assert intent.product_type == IntentProductType.LIFI_SWAP.value
    assert intent.status == IntentStatus.CREATED.value


def test_lifi_submit_updates_tx_hash(db: Session):
    from services.transaction_intents.lifi_intent_sync import on_swap_submitted

    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    swap = _seed_swap(db, pe, status=SwapSessionStatus.SUBMITTED.value)
    tx = "0x" + uuid.uuid4().hex + uuid.uuid4().hex[:24]
    swap.tx_hash = tx
    on_swap_submitted(db, swap, tx_hash=tx)
    db.commit()

    intent = TransactionIntentRepository.find_by_linked(
        db, linked_table=LINKED_TABLE, linked_id=swap.id
    )
    assert intent.status == IntentStatus.SUBMITTED.value
    assert intent.tx_hash == tx.lower()


def test_lifi_partial_sets_partial_status(db: Session):
    pe = make_linked_client(db)
    swap = _seed_swap(db, pe, status=SwapSessionStatus.SUBMITTED.value)
    swap.tx_hash = "0xabc"
    swap.audit_log = [{"event": "partial_confirmed", "substatus": "PARTIAL"}]
    sync_lifi_swap_intent(db, swap)
    db.commit()

    intent = TransactionIntentRepository.find_by_linked(
        db, linked_table=LINKED_TABLE, linked_id=swap.id
    )
    assert intent.status == IntentStatus.PARTIAL.value


def test_lifi_settlement_blocked_sets_reconciliation_required(db: Session):
    pe = make_linked_client(db)
    swap = _seed_swap(db, pe, status=SwapSessionStatus.CONFIRMED.value)
    swap.audit_log = [{"event": "settlement_blocked", "reason": "actual_amount_missing"}]
    sync_lifi_swap_intent(db, swap)
    db.commit()

    intent = TransactionIntentRepository.find_by_linked(
        db, linked_table=LINKED_TABLE, linked_id=swap.id
    )
    assert intent.status == IntentStatus.RECONCILIATION_REQUIRED.value


def test_idempotency_prevents_duplicate_intents(db: Session):
    pe = make_linked_client(db)
    swap = _seed_swap(db, pe)
    sync_lifi_swap_intent(db, swap, status=IntentStatus.CREATED.value)
    sync_lifi_swap_intent(db, swap, status=IntentStatus.SUBMITTED.value)
    db.commit()

    count = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.person_id == pe.person_id,
            TransactionIntent.linked_id == swap.id,
        )
        .count()
    )
    assert count == 1


def test_intent_confirmed_without_ledger_creates_discrepancy(db: Session):
    pe = make_linked_client(db)
    swap = _seed_swap(db, pe, status=SwapSessionStatus.CONFIRMED.value)
    swap.audit_log = []
    TransactionIntentRepository.upsert(
        db,
        person_id=pe.person_id,
        product_type=IntentProductType.LIFI_SWAP.value,
        operation_type="swap",
        idempotency_key=f"lifi_swap:{swap.id}",
        status=IntentStatus.CONFIRMED.value,
        linked_table=LINKED_TABLE,
        linked_id=swap.id,
    )
    db.commit()
    assert not swap_settlement_already_applied(swap)

    gaps = scan_intent_gaps_for_person(db, pe.person_id)
    assert any(g["discrepancy_type"] == "intent_confirmed_without_ledger" for g in gaps)


def test_raw_event_without_intent_creates_discrepancy(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    RawOnChainEventRepository.insert_if_absent(
        db,
        data={
            "chain_id": 8453,
            "tx_hash": f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}",
            "log_index": 0,
            "wallet_address": wallet.address,
            "asset": "USDC",
            "amount_raw": 1_000_000,
        },
    )
    db.commit()

    gaps = scan_intent_gaps_for_person(db, pe.person_id)
    assert any(g["discrepancy_type"] == "raw_event_without_intent" for g in gaps)


def test_no_balance_modification_on_intent_sync(db: Session, monkeypatch):
    pe = make_linked_client(db)
    swap = _seed_swap(db, pe)
    monkeypatch.setattr(PersonWalletBalanceRepository, "increment_balance", MagicMock())
    monkeypatch.setattr(PersonWalletDepositRepository, "create", MagicMock())

    sync_lifi_swap_intent(db, swap, status=IntentStatus.CONFIRMED.value)
    PersonWalletBalanceRepository.increment_balance.assert_not_called()
    PersonWalletDepositRepository.create.assert_not_called()


def test_lifi_failed_status(db: Session):
    pe = make_linked_client(db)
    swap = _seed_swap(db, pe, status=SwapSessionStatus.FAILED.value)
    sync_lifi_swap_intent(db, swap)
    db.commit()

    intent = TransactionIntentRepository.find_by_linked(
        db, linked_table=LINKED_TABLE, linked_id=swap.id
    )
    assert intent.status == IntentStatus.FAILED.value
