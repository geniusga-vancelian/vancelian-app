"""Tests Phase 7B — transaction_intents / Morpho Earn."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.privy_wallet.repository import PersonWalletBalanceRepository, PersonWalletDepositRepository
from services.transaction_intents.enums import IntentProductType, IntentStatus
from services.transaction_intents.morpho_intent_sync import (
    MORPHO_LINKED_TABLE,
    ensure_morpho_intent_for_vault_transaction,
    mark_morpho_intent_confirmed,
    mark_morpho_intent_failed,
    morpho_intent_key,
)
from services.transaction_intents.repository import TransactionIntentRepository
from services.transaction_intents.transaction_intent_reconciliation import scan_intent_gaps_for_person
from tests.conftest import make_linked_client
from tests.test_phase4_reconciliation import _seed_wallet
from tests.test_phase7_transaction_intents import _migration_166_ready


def _migration_167_ready() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND table_name = 'transaction_intents' "
                    "AND column_name = 'linked_reference_id'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


def _vault_table_ready() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'onchain_vault_transactions'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = [
    pytest.mark.skipif(not _migration_166_ready(), reason="Migration 166 requise."),
    pytest.mark.skipif(not _migration_167_ready(), reason="Migration 167 requise."),
]


def _vault_tx_id() -> str:
    return f"cl{uuid.uuid4().hex[:22]}"


def _morpho_prepare(
    db: Session,
    pe,
    *,
    operation: str = "deposit",
    vault_tx_id: str | None = None,
    idempotency_key: str | None = None,
) -> str:
    wallet = _seed_wallet(db, pe)
    vid = vault_tx_id or _vault_tx_id()
    idem = idempotency_key or f"morpho-test-{uuid.uuid4().hex[:12]}"
    result = ensure_morpho_intent_for_vault_transaction(
        db,
        person_id=pe.person_id,
        vault_transaction_id=vid,
        vault_address="0xvault0000000000000000000000000000000001",
        chain_id=8453,
        wallet_address=wallet.address,
        operation=operation,
        idempotency_key=idem,
        tx_index=0,
        vault_status="pending",
    )
    db.commit()
    assert result is not None
    return vid


def test_morpho_prepare_deposit_creates_awaiting_signature(db: Session):
    pe = make_linked_client(db)
    vid = _morpho_prepare(db, pe, operation="deposit")

    intent = TransactionIntentRepository.find_by_vault_transaction(
        db, vault_transaction_id=vid, person_id=pe.person_id
    )
    assert intent is not None
    assert intent.product_type == IntentProductType.MORPHO_EARN.value
    assert intent.operation_type == "deposit"
    assert intent.status == IntentStatus.AWAITING_SIGNATURE.value
    assert intent.linked_table == MORPHO_LINKED_TABLE
    assert intent.linked_reference_id == vid


def test_morpho_prepare_withdraw_creates_awaiting_signature(db: Session):
    pe = make_linked_client(db)
    vid = _morpho_prepare(db, pe, operation="withdraw")

    intent = TransactionIntentRepository.find_by_vault_transaction(
        db, vault_transaction_id=vid, person_id=pe.person_id
    )
    assert intent.operation_type == "withdraw"
    assert intent.status == IntentStatus.AWAITING_SIGNATURE.value


def test_morpho_confirm_success_sets_confirmed(db: Session):
    pe = make_linked_client(db)
    vid = _morpho_prepare(db, pe)
    tx = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"
    mark_morpho_intent_confirmed(
        db,
        person_id=pe.person_id,
        vault_transaction_id=vid,
        tx_hash=tx,
    )
    db.commit()

    intent = TransactionIntentRepository.find_by_vault_transaction(db, vault_transaction_id=vid)
    assert intent.status == IntentStatus.CONFIRMED.value
    assert intent.tx_hash == tx.lower()


def test_morpho_confirm_reverted_sets_failed(db: Session):
    pe = make_linked_client(db)
    vid = _morpho_prepare(db, pe)
    mark_morpho_intent_failed(
        db,
        person_id=pe.person_id,
        vault_transaction_id=vid,
        reason="reverted",
    )
    db.commit()

    intent = TransactionIntentRepository.find_by_vault_transaction(db, vault_transaction_id=vid)
    assert intent.status == IntentStatus.FAILED.value


def test_morpho_idempotency_same_vault_tx(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    vid = _vault_tx_id()
    vault = "0xvault0000000000000000000000000000000002"
    idem = f"idem-{uuid.uuid4().hex[:8]}"
    kwargs = dict(
        person_id=pe.person_id,
        vault_transaction_id=vid,
        vault_address=vault,
        chain_id=8453,
        wallet_address=wallet.address,
        operation="deposit",
        idempotency_key=idem,
        tx_index=0,
    )
    ensure_morpho_intent_for_vault_transaction(db, **kwargs)
    ensure_morpho_intent_for_vault_transaction(db, **kwargs)
    db.commit()

    from services.onchain_indexer.models import TransactionIntent

    key = morpho_intent_key(
        person_id=pe.person_id,
        vault_address=vault,
        operation="deposit",
        idempotency_key=idem,
        tx_index=0,
    )
    count = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.person_id == pe.person_id,
            TransactionIntent.idempotency_key == key,
        )
        .count()
    )
    assert count == 1


def test_morpho_intent_sync_failure_does_not_raise(db: Session, monkeypatch):
    pe = make_linked_client(db)
    monkeypatch.setattr(
        TransactionIntentRepository,
        "upsert",
        MagicMock(side_effect=RuntimeError("intent db down")),
    )
    result = ensure_morpho_intent_for_vault_transaction(
        db,
        person_id=pe.person_id,
        vault_transaction_id=_vault_tx_id(),
        vault_address="0xvault",
        chain_id=8453,
        wallet_address="0xwallet",
        operation="deposit",
        idempotency_key="k",
        tx_index=0,
    )
    assert result is None


def test_morpho_no_balance_modification_on_intent_sync(db: Session, monkeypatch):
    pe = make_linked_client(db)
    monkeypatch.setattr(PersonWalletBalanceRepository, "increment_balance", MagicMock())
    monkeypatch.setattr(PersonWalletDepositRepository, "create", MagicMock())

    _morpho_prepare(db, pe)
    PersonWalletBalanceRepository.increment_balance.assert_not_called()
    PersonWalletDepositRepository.create.assert_not_called()


@pytest.mark.skipif(not _vault_table_ready(), reason="Table onchain_vault_transactions absente.")
def test_reconciliation_vault_success_without_intent(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    vid = _vault_tx_id()
    db.execute(
        sa.text(
            """
            INSERT INTO onchain_vault_transactions (
                id, person_id, vault_address, chain_id, chain_type, wallet_address,
                operation, amount_raw, asset_symbol, asset_decimals, status,
                idempotency_key, integration_mode, tx_index, created_at, updated_at
            ) VALUES (
                :id, :person_id, :vault, 8453, 'evm', :wallet,
                'deposit', '1000000', 'USDC', 6, 'success',
                :idem, 'direct_morpho', 0, NOW(), NOW()
            )
            """
        ),
        {
            "id": vid,
            "person_id": str(pe.person_id),
            "vault": "0xvault0000000000000000000000000000000003",
            "wallet": wallet.address.lower(),
            "idem": f"rec-{uuid.uuid4().hex[:10]}",
        },
    )
    db.commit()

    gaps = scan_intent_gaps_for_person(db, pe.person_id)
    assert any(g["discrepancy_type"] == "vault_tx_success_without_intent" for g in gaps)


@pytest.mark.skipif(not _vault_table_ready(), reason="Table onchain_vault_transactions absente.")
def test_reconciliation_intent_confirmed_vault_not_success(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    vid = _vault_tx_id()
    db.execute(
        sa.text(
            """
            INSERT INTO onchain_vault_transactions (
                id, person_id, vault_address, chain_id, chain_type, wallet_address,
                operation, amount_raw, asset_symbol, asset_decimals, status,
                idempotency_key, integration_mode, tx_index, created_at, updated_at
            ) VALUES (
                :id, :person_id, :vault, 8453, 'evm', :wallet,
                'deposit', '1000000', 'USDC', 6, 'pending',
                :idem, 'direct_morpho', 0, NOW(), NOW()
            )
            """
        ),
        {
            "id": vid,
            "person_id": str(pe.person_id),
            "vault": "0xvault0000000000000000000000000000000004",
            "wallet": wallet.address.lower(),
            "idem": f"rec2-{uuid.uuid4().hex[:10]}",
        },
    )
    ensure_morpho_intent_for_vault_transaction(
        db,
        person_id=pe.person_id,
        vault_transaction_id=vid,
        vault_address="0xvault0000000000000000000000000000000004",
        chain_id=8453,
        wallet_address=wallet.address,
        operation="deposit",
        idempotency_key=f"rec2-{uuid.uuid4().hex[:10]}",
        tx_index=0,
    )
    intent = TransactionIntentRepository.find_by_vault_transaction(db, vault_transaction_id=vid)
    intent.status = IntentStatus.CONFIRMED.value
    db.add(intent)
    db.commit()

    gaps = scan_intent_gaps_for_person(db, pe.person_id)
    assert any(
        g["discrepancy_type"] == "intent_confirmed_vault_tx_not_success" for g in gaps
    )
