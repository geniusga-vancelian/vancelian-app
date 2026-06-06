"""Phase 2 S3b — premier settlement réel LI.FI standalone (ledger debit + credit uniquement)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.auth.person_identity_bridge import (
    PROVIDER_PRIVY,
    link_external_identity_to_person,
    upsert_person_crypto_wallet,
)
from services.cost_basis.models import CostBasisExecution
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_swap_settlement import (
    apply_swap_settlement,
    swap_credit_idempotency_key,
    swap_debit_idempotency_key,
)
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundle_ledger.models import BundleLedgerEntry
from services.portfolio_engine.positions.models import PositionAtom
from services.privy_wallet.admin_service import PrivyWalletAdminService
from services.privy_wallet.enums import PersonWalletDirection
from services.privy_wallet.models import PersonWalletBalance, PersonWalletDeposit
from services.privy_wallet.schemas import PrivySimulateDepositRequest
from services.settlement.constants import SETTLEMENT_RECEIPT_METADATA_KEY
from services.settlement.lifi_ledger import count_swap_settlement_legs
from services.settlement.preconditions import settlement_marker_present
from services.settlement.result import SettlementOutcome
from services.settlement.settle import settle_transaction_intent_idempotently
from services.transaction_intents.enums import IntentStatus
from services.transaction_outbox.atomic import persist_intent_swap_outbox_atomic
from services.transaction_outbox.enums import OutboxEventType
from services.transaction_outbox.intent_phases import IntentOrchestratorPhase
from services.transaction_outbox.repository import TransactionOutboxRepository
from services.transaction_outbox.settlement_worker import process_transaction_outbox_intent_settle
from tests.conftest import make_linked_client

EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
TX_HASH = "0xs3btest1234567890abcdef1234567890abcdef1234567890abcdef123456"


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


@pytest.fixture(autouse=True)
def _s3b_ledger_flag_off_by_default(monkeypatch):
    monkeypatch.delenv("LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED", raising=False)


def _economic_counts(db: Session, person_id) -> dict[str, int]:
    return {
        "deposits": db.query(PersonWalletDeposit)
        .filter(PersonWalletDeposit.person_id == person_id)
        .count(),
        "balances": db.query(PersonWalletBalance)
        .filter(PersonWalletBalance.person_id == person_id)
        .count(),
        "pe_atoms": db.query(PositionAtom).count(),
        "bundle_ledger": db.query(BundleLedgerEntry).count(),
        "cost_basis": db.query(CostBasisExecution).count(),
    }


def _seed_wallet(db: Session, pe):
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject="did:privy:s3btest001",
        external_email="s3b@test.local",
    )
    return upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        address=EVM_ADDR,
        metadata_json={"privy_wallet_id": "w-s3b"},
    )


def _seed_confirmed_swap_bundle(db: Session):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    PrivyWalletAdminService().simulate_deposit(
        db,
        PrivySimulateDepositRequest(
            person_id=pe.person_id,
            wallet_address=EVM_ADDR,
            asset="USDC",
            amount="50",
            chain_id=8453,
        ),
    )

    bundle = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
    )
    bundle.swap.status = SwapSessionStatus.CONFIRMED.value
    bundle.swap.tx_hash = TX_HASH
    bundle.swap.estimated_receive = Decimal("0.00475")
    bundle.swap.confirmed_at = datetime.now(timezone.utc)
    bundle.swap.audit_log = [
        {"event": "quote_requested", "signing_wallet_address": EVM_ADDR},
    ]
    bundle.intent.current_phase = IntentOrchestratorPhase.QUEUED.value
    bundle.intent.assets_json = {
        "from": {"asset": "USDC", "amount": "10"},
        "to": {"asset": "ETH", "amount": "0.00475"},
    }

    settle_outbox = TransactionOutboxRepository.insert_event(
        db,
        intent_id=bundle.intent.id,
        event_type=OutboxEventType.INTENT_SETTLE.value,
    )
    db.commit()
    return pe, bundle, settle_outbox


def test_s3b_success_one_debit_one_credit(db: Session, monkeypatch):
    monkeypatch.setenv("LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED", "true")
    pe, bundle, _ = _seed_confirmed_swap_bundle(db)
    pe_before = _economic_counts(db, pe.person_id)

    result = settle_transaction_intent_idempotently(db, intent_id=bundle.intent.id)
    db.commit()

    assert result.outcome == SettlementOutcome.SUCCESS
    legs = count_swap_settlement_legs(db, swap_id=bundle.swap.id, person_id=pe.person_id)
    assert legs == {"debit": 1, "credit": 1}
    db.refresh(bundle.intent)
    assert settlement_marker_present(bundle.intent)
    assert bundle.intent.status not in {"COMPLETED", "completed"}
    assert _economic_counts(db, pe.person_id)["pe_atoms"] == pe_before["pe_atoms"]
    assert _economic_counts(db, pe.person_id)["cost_basis"] == pe_before["cost_basis"]


def test_s3b_second_passage_noop_already_settled(db: Session, monkeypatch):
    monkeypatch.setenv("LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED", "true")
    pe, bundle, _ = _seed_confirmed_swap_bundle(db)

    first = settle_transaction_intent_idempotently(db, intent_id=bundle.intent.id)
    db.commit()
    assert first.outcome == SettlementOutcome.SUCCESS
    counts_after_first = count_swap_settlement_legs(
        db, swap_id=bundle.swap.id, person_id=pe.person_id
    )

    second = settle_transaction_intent_idempotently(db, intent_id=bundle.intent.id)
    assert second.outcome == SettlementOutcome.NOOP_ALREADY_SETTLED
    assert count_swap_settlement_legs(db, swap_id=bundle.swap.id, person_id=pe.person_id) == (
        counts_after_first
    )


def test_s3b_credit_already_present_no_double_credit(db: Session, monkeypatch):
    monkeypatch.setenv("LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED", "true")
    pe, bundle, _ = _seed_confirmed_swap_bundle(db)
    wallet = _seed_wallet(db, pe)

    from services.lifi.lifi_swap_settlement import _create_swap_ledger_entry

    _create_swap_ledger_entry(
        db,
        swap=bundle.swap,
        wallet=wallet,
        direction=PersonWalletDirection.CREDIT.value,
        asset="ETH",
        amount=Decimal("0.00475"),
        chain_id=8453,
        log_index=1,
        idempotency_key=swap_credit_idempotency_key(str(bundle.swap.id)),
        sync_source="privy_webhook_sim",
        settlement_meta={"event_source": "privy_webhook"},
    )
    db.commit()

    result = settle_transaction_intent_idempotently(db, intent_id=bundle.intent.id)
    db.commit()
    assert result.outcome == SettlementOutcome.SUCCESS

    legs = count_swap_settlement_legs(db, swap_id=bundle.swap.id, person_id=pe.person_id)
    assert legs["credit"] == 1
    assert legs["debit"] == 1

    credits = (
        db.query(PersonWalletDeposit)
        .filter(
            PersonWalletDeposit.idempotency_key
            == swap_credit_idempotency_key(str(bundle.swap.id))
        )
        .count()
    )
    assert credits == 1


def test_s3b_debit_already_present_no_double_debit(db: Session, monkeypatch):
    monkeypatch.setenv("LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED", "true")
    pe, bundle, _ = _seed_confirmed_swap_bundle(db)
    wallet = _seed_wallet(db, pe)

    from services.lifi.lifi_swap_settlement import _create_swap_ledger_entry

    _create_swap_ledger_entry(
        db,
        swap=bundle.swap,
        wallet=wallet,
        direction=PersonWalletDirection.DEBIT.value,
        asset="USDC",
        amount=Decimal("10"),
        chain_id=8453,
        log_index=0,
        idempotency_key=swap_debit_idempotency_key(str(bundle.swap.id)),
        sync_source="partial_settlement",
    )
    db.commit()

    result = settle_transaction_intent_idempotently(db, intent_id=bundle.intent.id)
    db.commit()
    assert result.outcome == SettlementOutcome.SUCCESS

    debits = (
        db.query(PersonWalletDeposit)
        .filter(
            PersonWalletDeposit.idempotency_key
            == swap_debit_idempotency_key(str(bundle.swap.id))
        )
        .count()
    )
    assert debits == 1
    assert count_swap_settlement_legs(db, swap_id=bundle.swap.id, person_id=pe.person_id) == {
        "debit": 1,
        "credit": 1,
    }


def test_s3b_failure_between_debit_and_credit_rolls_back(db: Session, monkeypatch):
    monkeypatch.setenv("LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED", "true")
    pe, bundle, _ = _seed_confirmed_swap_bundle(db)
    before = _economic_counts(db, pe.person_id)

    from services.lifi.lifi_swap_settlement import _create_swap_ledger_entry as original_create
    import services.settlement.lifi_ledger as lifi_ledger_mod

    def _fail_on_credit(*args, **kwargs):
        if kwargs.get("direction") == PersonWalletDirection.CREDIT.value:
            raise RuntimeError("simulated_credit_failure")
        return original_create(*args, **kwargs)

    with patch.object(lifi_ledger_mod, "_create_swap_ledger_entry", side_effect=_fail_on_credit):
        result = settle_transaction_intent_idempotently(db, intent_id=bundle.intent.id)

    assert result.outcome == SettlementOutcome.TERMINAL_FAILURE
    db.rollback()

    db.refresh(bundle.intent)
    assert settlement_marker_present(bundle.intent) is None
    assert count_swap_settlement_legs(db, swap_id=bundle.swap.id, person_id=pe.person_id) == {
        "debit": 0,
        "credit": 0,
    }
    assert _economic_counts(db, pe.person_id) == before


def test_s3b_no_pe_atoms_written(db: Session, monkeypatch):
    monkeypatch.setenv("LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED", "true")
    pe, bundle, _ = _seed_confirmed_swap_bundle(db)
    pe_atoms_before = db.query(PositionAtom).count()

    settle_transaction_intent_idempotently(db, intent_id=bundle.intent.id)
    db.commit()

    assert db.query(PositionAtom).count() == pe_atoms_before


def test_s3b_no_completed_produced(db: Session, monkeypatch):
    monkeypatch.setenv("LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED", "true")
    monkeypatch.setenv("LIFI_OUTBOX_WORKER_ENABLED", "true")
    _pe, bundle, _ = _seed_confirmed_swap_bundle(db)

    process_transaction_outbox_intent_settle(db)
    db.refresh(bundle.intent)

    assert bundle.intent.status == IntentStatus.CREATED.value
    assert bundle.intent.status not in {"COMPLETED", "completed"}
    assert bundle.intent.current_phase == IntentOrchestratorPhase.LEDGER_SETTLED.value
    assert (bundle.intent.metadata_json or {}).get(SETTLEMENT_RECEIPT_METADATA_KEY)


def test_s3b_flag_off_legacy_apply_swap_unchanged(db: Session, monkeypatch):
    monkeypatch.delenv("LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED", raising=False)
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    PrivyWalletAdminService().simulate_deposit(
        db,
        PrivySimulateDepositRequest(
            person_id=pe.person_id,
            wallet_address=EVM_ADDR,
            asset="USDC",
            amount="30",
            chain_id=8453,
        ),
    )

    swap = PersonWalletSwap(
        id=uuid4(),
        person_id=pe.person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("5"),
        estimated_receive=Decimal("0.002"),
        tx_hash="0xlegacyflagoffabcdef1234567890abcdef1234567890abcdef1234567890",
        audit_log=[{"event": "quote_requested", "signing_wallet_address": EVM_ADDR}],
        confirmed_at=datetime.now(timezone.utc),
    )
    db.add(swap)
    db.flush()

    bundle = persist_intent_swap_outbox_atomic(
        db,
        person_id=pe.person_id,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("5"),
    )
    bundle.intent.current_phase = IntentOrchestratorPhase.QUEUED.value
    db.commit()

    noop_result = settle_transaction_intent_idempotently(db, intent_id=bundle.intent.id)
    db.commit()
    assert noop_result.outcome == SettlementOutcome.SUCCESS
    assert count_swap_settlement_legs(db, swap_id=bundle.swap.id, person_id=pe.person_id) == {
        "debit": 0,
        "credit": 0,
    }

    apply_swap_settlement(db, swap, sync_source="lifi_swap", amount_actual=Decimal("0.002"))
    db.commit()
    assert count_swap_settlement_legs(db, swap_id=swap.id, person_id=pe.person_id) == {
        "debit": 1,
        "credit": 1,
    }
