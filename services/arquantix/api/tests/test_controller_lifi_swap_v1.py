"""S3 Controller v1 — réconciliation LI.FI standalone post LEDGER_SETTLED."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
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
from services.controller.constants import (
    CHAIN_DIMENSION_MISSING_BALANCE,
    CHAIN_DIMENSION_MISSING_LEDGER,
    PE_SNAPSHOT_WALLET_CHECK_SKIPPED,
    RECONCILIATION_REPORT_METADATA_KEY,
)
from services.controller.lifi_swap_controller import (
    _compute_report_hash,
    reconcile_lifi_swap_intent,
)
from services.controller.result import ReconciliationOutcome
from services.cost_basis.models import CostBasisExecution
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_swap_settlement import swap_credit_idempotency_key, swap_debit_idempotency_key
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundle_ledger.models import BundleLedgerEntry
from services.portfolio_engine.positions.models import PositionAtom
from services.privy_wallet.admin_service import PrivyWalletAdminService
from services.privy_wallet.enums import PersonWalletDirection
from services.privy_wallet.models import PersonWalletBalance, PersonWalletDeposit
from services.privy_wallet.repository import PersonWalletBalanceRepository, PersonWalletDepositRepository
from services.privy_wallet.schemas import PrivySimulateDepositRequest
from services.settlement.constants import SETTLEMENT_RECEIPT_METADATA_KEY
from services.settlement.lifi_ledger import count_swap_settlement_legs
from services.settlement.settle import settle_transaction_intent_idempotently
from services.transaction_outbox.atomic import persist_intent_swap_outbox_atomic
from services.transaction_outbox.enums import OutboxEventType
from services.transaction_outbox.intent_phases import IntentOrchestratorPhase
from services.transaction_outbox.repository import (
    TransactionIntentTransitionRepository,
    TransactionOutboxRepository,
)
from services.transaction_outbox.settlement_worker import process_transaction_outbox_intent_settle
from tests.conftest import make_linked_client
from tests.lifi_orchestrator_test_utils import enable_lifi_orchestrator_allowlist

EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
TX_HASH = "0xctrltest1234567890abcdef1234567890abcdef1234567890abcdef123456"


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
def _controller_flags(monkeypatch):
    monkeypatch.setenv("LIFI_SETTLEMENT_LAYER_LEDGER_ENABLED", "true")
    monkeypatch.setenv("LIFI_OUTBOX_WORKER_ENABLED", "true")


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
        external_subject="did:privy:ctrltest001",
        external_email="ctrl@test.local",
    )
    return upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        address=EVM_ADDR,
        metadata_json={"privy_wallet_id": "w-ctrl"},
    )


def _seed_confirmed_swap_bundle(db: Session, monkeypatch=None):
    pe = make_linked_client(db)
    if monkeypatch is not None:
        enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    wallet = _seed_wallet(db, pe)
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
    TransactionOutboxRepository.insert_event(
        db,
        intent_id=bundle.intent.id,
        event_type=OutboxEventType.INTENT_SETTLE.value,
    )
    db.commit()
    return pe, bundle, wallet


def _advance_to_ledger_settled(db: Session, bundle) -> None:
    process_transaction_outbox_intent_settle(db)
    db.refresh(bundle.intent)
    assert bundle.intent.current_phase == IntentOrchestratorPhase.LEDGER_SETTLED.value
    assert (bundle.intent.metadata_json or {}).get(SETTLEMENT_RECEIPT_METADATA_KEY)


def _webhook_credit_idempotency_key(tx_hash: str) -> str:
    return f"call_{tx_hash}_wallet.funds_deposited"


def _seed_webhook_destination_credit(db: Session, *, wallet, swap, amount: Decimal) -> None:
    tx_hash = str(swap.tx_hash or "").strip().lower()
    PersonWalletDepositRepository().create(
        db,
        data={
            "person_crypto_wallet_id": wallet.id,
            "person_id": wallet.person_id,
            "pe_client_id": wallet.pe_client_id,
            "privy_webhook_event_id": None,
            "transaction_kind": "privy_deposit_in",
            "direction": PersonWalletDirection.CREDIT.value,
            "asset": str(swap.to_asset).upper(),
            "amount": amount,
            "chain_type": "ethereum",
            "chain_id": 8453,
            "tx_hash": tx_hash,
            "log_index": 1,
            "from_address": "0xrouter",
            "to_address": EVM_ADDR,
            "confirmations": 1,
            "status": "confirmed",
            "idempotency_key": _webhook_credit_idempotency_key(tx_hash),
            "title": "Dépôt ETH",
            "subtitle": f"+{amount} ETH",
            "metadata_json": {"event_source": "privy_webhook"},
            "confirmed_at": datetime.now(timezone.utc),
        },
    )
    balance_repo = PersonWalletBalanceRepository()
    row = balance_repo.get_or_create_for_update(
        db, wallet_id=wallet.id, person_id=wallet.person_id, asset=str(swap.to_asset).upper()
    )
    balance_repo.increment_balance(db, row, delta=amount, sync_source="privy_webhook_sim")
    db.commit()


def _inject_balance_snapshot(intent, *, available: str = "50") -> None:
    meta = dict(intent.metadata_json or {})
    meta["balance_snapshot"] = {
        "asset": "USDC",
        "available": available,
        "version": 1,
        "hash": "sha256:pe-product-lock-test-snapshot",
    }
    intent.metadata_json = meta


def _inject_wallet_balance_snapshot(intent, *, available: str = "50") -> None:
    meta = dict(intent.metadata_json or {})
    meta["balance_snapshot"] = {
        "asset": "USDC",
        "available": available,
        "version": 1,
        "source": "wallet",
        "hash": "sha256:wallet-dedicated-test-snapshot",
    }
    intent.metadata_json = meta


def test_controller_nominal_one_debit_one_credit_reconciled(db: Session, monkeypatch):
    pe, bundle, _wallet = _seed_confirmed_swap_bundle(db, monkeypatch)
    _advance_to_ledger_settled(db, bundle)
    before = _economic_counts(db, pe.person_id)

    result = reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()
    db.refresh(bundle.intent)

    assert result.outcome == ReconciliationOutcome.RECONCILED
    assert result.reconciliation_report_hash
    assert len(result.reconciliation_report_hash) == 64
    assert bundle.intent.current_phase == IntentOrchestratorPhase.RECONCILED.value
    assert (bundle.intent.metadata_json or {}).get(RECONCILIATION_REPORT_METADATA_KEY)
    assert bundle.intent.status not in {"completed", "COMPLETED"}
    assert _economic_counts(db, pe.person_id) == before
    legs = count_swap_settlement_legs(db, swap_id=bundle.swap.id, person_id=pe.person_id)
    assert legs == {"debit": 1, "credit": 1}


def test_controller_webhook_credit_reused_reconciled(db: Session, monkeypatch):
    pe, bundle, wallet = _seed_confirmed_swap_bundle(db, monkeypatch)
    _seed_webhook_destination_credit(db, wallet=wallet, swap=bundle.swap, amount=Decimal("0.00475"))
    _advance_to_ledger_settled(db, bundle)

    result = reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()

    assert result.outcome == ReconciliationOutcome.RECONCILED
    credits = (
        db.query(PersonWalletDeposit)
        .filter(
            PersonWalletDeposit.person_id == pe.person_id,
            PersonWalletDeposit.direction == PersonWalletDirection.CREDIT.value,
            PersonWalletDeposit.asset == "ETH",
        )
        .count()
    )
    assert credits == 1


def test_controller_external_deposit_during_window_reconciled(db: Session, monkeypatch):
    pe, bundle, wallet = _seed_confirmed_swap_bundle(db, monkeypatch)
    _inject_balance_snapshot(bundle.intent, available="50")
    db.commit()

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
    _advance_to_ledger_settled(db, bundle)

    result = reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()

    assert result.outcome == ReconciliationOutcome.RECONCILED
    assert result.projection is not None
    assert len(result.projection.get("external_movements") or []) >= 1


def test_controller_pe_snapshot_wallet_mismatch_reconciled_with_warning(
    db: Session, monkeypatch
):
    """PE Product Lock snapshot ≠ wallet balance — warning only (v1.2)."""
    pe, bundle, _wallet = _seed_confirmed_swap_bundle(db, monkeypatch)
    _inject_balance_snapshot(bundle.intent, available="100")
    db.commit()
    _advance_to_ledger_settled(db, bundle)

    result = reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()
    db.refresh(bundle.intent)

    assert result.outcome == ReconciliationOutcome.RECONCILED
    assert result.reconciliation_report_hash
    assert bundle.intent.current_phase == IntentOrchestratorPhase.RECONCILED.value
    assert result.projection is not None
    assert PE_SNAPSHOT_WALLET_CHECK_SKIPPED in (result.projection.get("warnings") or [])
    balance_debug = result.projection.get("balance_reconciliation") or {}
    assert balance_debug.get("check_mode") == "pe_snapshot_wallet_check_skipped"


def test_controller_report_hash_differs_by_chain(db: Session):
    """Même asset/montant — hash différent si from_chain/to_chain diffèrent."""
    from uuid import uuid4

    intent_id = uuid4()
    common = {
        "tx_hash": "0xabc",
        "from_asset": "USDC",
        "to_asset": "ETH",
        "expected_debit": {"asset": "USDC", "amount": "10", "chain": "base"},
        "expected_credit": {"asset": "ETH", "amount": "0.01", "chain": "base"},
    }
    base_proj = {**common, "from_chain": "base", "to_chain": "base"}
    eth_proj = {**common, "from_chain": "ethereum", "to_chain": "ethereum"}
    assert _compute_report_hash(intent_id, base_proj) != _compute_report_hash(
        intent_id, eth_proj
    )


def test_controller_projection_includes_from_chain_and_to_chain(db: Session, monkeypatch):
    pe, bundle, _wallet = _seed_confirmed_swap_bundle(db, monkeypatch)
    _advance_to_ledger_settled(db, bundle)

    result = reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()

    assert result.outcome == ReconciliationOutcome.RECONCILED
    proj = result.projection or {}
    assert proj.get("from_chain") == "base"
    assert proj.get("to_chain") == "base"
    assert proj.get("from_asset") == "USDC"
    assert proj.get("to_asset") == "ETH"
    assert proj.get("expected_debit", {}).get("chain") == "base"
    assert proj.get("expected_credit", {}).get("chain") == "base"


def test_controller_legacy_missing_chain_id_warning_not_blocking(db: Session, monkeypatch):
    _pe, bundle, _wallet = _seed_confirmed_swap_bundle(db, monkeypatch)
    _advance_to_ledger_settled(db, bundle)

    for dep in (
        db.query(PersonWalletDeposit)
        .filter(
            PersonWalletDeposit.idempotency_key.in_(
                [
                    swap_debit_idempotency_key(str(bundle.swap.id)),
                    swap_credit_idempotency_key(str(bundle.swap.id)),
                ]
            )
        )
        .all()
    ):
        dep.chain_id = None
    db.commit()

    result = reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()

    assert result.outcome == ReconciliationOutcome.RECONCILED
    warnings = result.projection.get("warnings") or []
    assert CHAIN_DIMENSION_MISSING_LEDGER in warnings
    assert CHAIN_DIMENSION_MISSING_BALANCE in warnings


def test_controller_wallet_dedicated_snapshot_strict_balance_terminal(
    db: Session, monkeypatch
):
    """Snapshot wallet explicite — check stricte conservée."""
    _pe, bundle, _wallet = _seed_confirmed_swap_bundle(db, monkeypatch)
    _inject_wallet_balance_snapshot(bundle.intent, available="100")
    db.commit()
    _advance_to_ledger_settled(db, bundle)

    result = reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()

    assert result.outcome == ReconciliationOutcome.RECONCILIATION_TERMINAL_FAILURE
    assert result.error_code == "controller.balance_unexplained"


def test_controller_debit_missing_retryable(db: Session, monkeypatch):
    pe, bundle, wallet = _seed_confirmed_swap_bundle(db, monkeypatch)
    _advance_to_ledger_settled(db, bundle)

    debit = (
        db.query(PersonWalletDeposit)
        .filter(
            PersonWalletDeposit.idempotency_key
            == swap_debit_idempotency_key(str(bundle.swap.id))
        )
        .one()
    )
    db.delete(debit)
    db.commit()

    result = reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()
    db.refresh(bundle.intent)

    assert result.outcome == ReconciliationOutcome.RECONCILIATION_RETRYABLE_FAILURE
    assert result.error_code == "controller.debit_missing"
    assert bundle.intent.current_phase == IntentOrchestratorPhase.RECONCILIATION_RETRYABLE_FAILURE.value


def test_controller_credit_missing_retryable(db: Session, monkeypatch):
    pe, bundle, _wallet = _seed_confirmed_swap_bundle(db, monkeypatch)
    _advance_to_ledger_settled(db, bundle)

    credit = (
        db.query(PersonWalletDeposit)
        .filter(
            PersonWalletDeposit.idempotency_key
            == swap_credit_idempotency_key(str(bundle.swap.id))
        )
        .one()
    )
    db.delete(credit)
    db.commit()

    result = reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()

    assert result.outcome == ReconciliationOutcome.RECONCILIATION_RETRYABLE_FAILURE
    assert result.error_code == "controller.credit_missing"


def test_controller_double_credit_terminal(db: Session, monkeypatch):
    _pe, bundle, wallet = _seed_confirmed_swap_bundle(db, monkeypatch)
    _advance_to_ledger_settled(db, bundle)

    PersonWalletDepositRepository().create(
        db,
        data={
            "person_crypto_wallet_id": wallet.id,
            "person_id": wallet.person_id,
            "pe_client_id": wallet.pe_client_id,
            "transaction_kind": "crypto_swap",
            "direction": PersonWalletDirection.CREDIT.value,
            "asset": "ETH",
            "amount": Decimal("0.00475"),
            "chain_type": "ethereum",
            "chain_id": 8453,
            "tx_hash": TX_HASH.lower(),
            "log_index": 3,
            "from_address": "0xrouter",
            "to_address": EVM_ADDR,
            "confirmations": 1,
            "status": "confirmed",
            "idempotency_key": f"dup-credit-{uuid4()}",
            "title": "Crédit ETH duplicate",
            "subtitle": "+0.00475 ETH",
            "metadata_json": {"swap_id": str(bundle.swap.id)},
            "confirmed_at": datetime.now(timezone.utc),
        },
    )
    db.commit()

    result = reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()

    assert result.outcome == ReconciliationOutcome.RECONCILIATION_TERMINAL_FAILURE
    assert result.error_code == "controller.double_credit"


def test_controller_wrong_asset_terminal(db: Session, monkeypatch):
    pe, bundle, wallet = _seed_confirmed_swap_bundle(db, monkeypatch)
    _advance_to_ledger_settled(db, bundle)

    credit = (
        db.query(PersonWalletDeposit)
        .filter(
            PersonWalletDeposit.idempotency_key
            == swap_credit_idempotency_key(str(bundle.swap.id))
        )
        .one()
    )
    credit.asset = "USDC"
    db.commit()

    result = reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()

    assert result.outcome == ReconciliationOutcome.RECONCILIATION_TERMINAL_FAILURE
    assert result.error_code == "controller.credit_asset_mismatch"


def test_controller_wrong_amount_terminal(db: Session, monkeypatch):
    pe, bundle, _wallet = _seed_confirmed_swap_bundle(db, monkeypatch)
    _advance_to_ledger_settled(db, bundle)

    debit = (
        db.query(PersonWalletDeposit)
        .filter(
            PersonWalletDeposit.idempotency_key
            == swap_debit_idempotency_key(str(bundle.swap.id))
        )
        .one()
    )
    debit.amount = Decimal("99")
    db.commit()

    result = reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()

    assert result.outcome == ReconciliationOutcome.RECONCILIATION_TERMINAL_FAILURE
    assert result.error_code == "controller.debit_amount_mismatch"


def test_controller_no_tx_hash_retryable(db: Session, monkeypatch):
    pe, bundle, _wallet = _seed_confirmed_swap_bundle(db, monkeypatch)
    _advance_to_ledger_settled(db, bundle)
    bundle.swap.tx_hash = None
    db.commit()

    result = reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()

    assert result.outcome == ReconciliationOutcome.RECONCILIATION_RETRYABLE_FAILURE
    assert result.error_code == "controller.missing_tx_hash"


def test_controller_already_reconciled_idempotent(db: Session, monkeypatch):
    pe, bundle, _wallet = _seed_confirmed_swap_bundle(db, monkeypatch)
    _advance_to_ledger_settled(db, bundle)

    first = reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()
    transitions_after_first = TransactionIntentTransitionRepository.count_for_intent(
        db, bundle.intent.id
    )

    second = reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()

    assert first.outcome == ReconciliationOutcome.RECONCILED
    assert second.outcome == ReconciliationOutcome.NOOP_ALREADY_RECONCILED
    assert second.reconciliation_report_hash == first.reconciliation_report_hash
    assert TransactionIntentTransitionRepository.count_for_intent(db, bundle.intent.id) == (
        transitions_after_first
    )


def test_controller_pe_and_cost_basis_unchanged(db: Session, monkeypatch):
    pe, bundle, _wallet = _seed_confirmed_swap_bundle(db, monkeypatch)
    _advance_to_ledger_settled(db, bundle)
    before = _economic_counts(db, pe.person_id)

    reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()

    after = _economic_counts(db, pe.person_id)
    assert after["pe_atoms"] == before["pe_atoms"]
    assert after["cost_basis"] == before["cost_basis"]
    assert after["deposits"] == before["deposits"]
    assert after["balances"] == before["balances"]


def test_controller_no_completed_status(db: Session, monkeypatch):
    _pe, bundle, _wallet = _seed_confirmed_swap_bundle(db, monkeypatch)
    _advance_to_ledger_settled(db, bundle)

    reconcile_lifi_swap_intent(db, intent_id=bundle.intent.id)
    db.commit()
    db.refresh(bundle.intent)

    assert bundle.intent.status not in {"completed", "COMPLETED"}
    assert bundle.intent.current_phase == IntentOrchestratorPhase.RECONCILED.value
    assert bundle.intent.current_phase != "COMPLETED"
