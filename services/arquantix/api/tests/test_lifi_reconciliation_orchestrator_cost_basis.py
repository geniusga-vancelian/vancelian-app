"""Legacy reconciliation — skip cost basis ingest for orchestrator-active swaps."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.cost_basis.models import CostBasisExecution
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_actual_receive import LifiActualReceiveResult
from services.lifi.lifi_swap_reconciliation import (
    build_reconciliation_dry_run_summary,
    settle_lifi_swap_idempotently,
)
from services.lifi.models import PersonWalletSwap
from services.privy_wallet.admin_service import PrivyWalletAdminService
from services.privy_wallet.enums import PersonWalletDirection
from services.privy_wallet.repository import PersonWalletBalanceRepository, PersonWalletDepositRepository
from services.privy_wallet.schemas import PrivySimulateDepositRequest
from services.transaction_outbox.atomic import attach_orchestrator_intent_to_swap_atomic
from services.transaction_outbox.orchestrator_settle_enqueue import (
    skip_legacy_cost_basis_for_orchestrator,
)
from tests.conftest import make_linked_client
from tests.lifi_orchestrator_test_utils import enable_lifi_orchestrator_allowlist
from services.auth.person_identity_bridge import PROVIDER_PRIVY, link_external_identity_to_person, upsert_person_crypto_wallet

EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
TX_ORCH = "0xorchreconcil1234567890abcdef1234567890abcdef1234567890abcdef12"
TX_LEGACY = "0xlegacyreconcil1234567890abcdef1234567890abcdef1234567890abcdef"


def _migration_ready() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'person_wallet_swaps'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_ready(),
    reason="Tables swap LI.FI requises.",
)


def _cb_count(db: Session) -> int:
    return db.query(CostBasisExecution).count()


def _seed_webhook_eth_credit(db: Session, *, wallet, person_id, tx_hash: str, amount: str) -> None:
    PersonWalletDepositRepository().create(
        db,
        data={
            "person_crypto_wallet_id": wallet.id,
            "person_id": person_id,
            "pe_client_id": wallet.pe_client_id,
            "transaction_kind": "privy_deposit_in",
            "direction": PersonWalletDirection.CREDIT.value,
            "asset": "ETH",
            "amount": Decimal(amount),
            "chain_type": "ethereum",
            "chain_id": 8453,
            "tx_hash": tx_hash.lower(),
            "log_index": 1,
            "from_address": "0xrouter",
            "to_address": EVM_ADDR,
            "confirmations": 1,
            "status": "confirmed",
            "idempotency_key": f"call_{tx_hash.lower()}_wallet.funds_deposited",
            "title": "Dépôt ETH",
            "subtitle": f"+{amount} ETH",
            "metadata_json": {"event_source": "privy_webhook"},
            "confirmed_at": datetime.now(timezone.utc),
        },
    )
    row = PersonWalletBalanceRepository().get_or_create_for_update(
        db, wallet_id=wallet.id, person_id=person_id, asset="ETH"
    )
    PersonWalletBalanceRepository().increment_balance(
        db, row, delta=Decimal(amount), sync_source="test"
    )
    db.commit()


def _seed_wallet(db: Session, pe):
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject="did:privy:reconorch001",
        external_email="recon-orch@test.local",
    )
    return upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        address=EVM_ADDR,
        metadata_json={"privy_wallet_id": "w-recon-orch"},
    )


def _seed_orchestrator_confirmed_swap(db: Session, monkeypatch, *, tx_hash: str = TX_ORCH):
    pe = make_linked_client(db)
    enable_lifi_orchestrator_allowlist(monkeypatch, pe)
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
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
    db.commit()

    swap = PersonWalletSwap(
        id=uuid4(),
        person_id=pe.person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1"),
        estimated_receive=Decimal("0.000614"),
        tx_hash=tx_hash,
        confirmed_at=datetime.now(timezone.utc),
        audit_log=[{"event": "quote_requested", "signing_wallet_address": EVM_ADDR}],
    )
    db.add(swap)
    db.flush()
    attach_orchestrator_intent_to_swap_atomic(db, person_id=pe.person_id, swap_id=swap.id)
    db.commit()
    db.refresh(swap)
    return pe, swap, wallet


@patch("services.lifi.lifi_swap_reconciliation.is_tx_confirmed_on_chain", return_value=True)
@patch(
    "services.lifi.lifi_swap_reconciliation.resolve_lifi_actual_receive_amount",
    return_value=LifiActualReceiveResult(amount=Decimal("0.000614"), source="test"),
)
def test_reconciliation_orchestrator_skips_cost_basis_writes_debit(mock_amount, mock_rpc, db, monkeypatch):
    pe, swap, wallet = _seed_orchestrator_confirmed_swap(db, monkeypatch)
    _seed_webhook_eth_credit(
        db, wallet=wallet, person_id=pe.person_id, tx_hash=TX_ORCH, amount="0.000614"
    )

    assert skip_legacy_cost_basis_for_orchestrator(db, swap) is True
    preview = build_reconciliation_dry_run_summary(db, swap)
    assert preview["would_create_cost_basis"] is False
    assert preview["would_create_debit_USDC"] is True

    cb_before = _cb_count(db)
    result = settle_lifi_swap_idempotently(db, swap.id, dry_run=False)
    db.commit()

    assert result.debit_applied is True
    assert result.credit_applied is False
    assert result.cost_basis_applied is False
    assert _cb_count(db) == cb_before


@patch("services.lifi.lifi_swap_reconciliation.is_tx_confirmed_on_chain", return_value=True)
@patch(
    "services.lifi.lifi_swap_reconciliation.resolve_lifi_actual_receive_amount",
    return_value=LifiActualReceiveResult(amount=Decimal("0.00475"), source="test"),
)
def test_reconciliation_legacy_non_orchestrator_creates_cost_basis(mock_amount, mock_rpc, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    PrivyWalletAdminService().simulate_deposit(
        db,
        PrivySimulateDepositRequest(
            person_id=pe.person_id,
            wallet_address=EVM_ADDR,
            asset="USDC",
            amount="20",
            chain_id=8453,
        ),
    )
    db.commit()

    swap = PersonWalletSwap(
        id=uuid4(),
        person_id=pe.person_id,
        status=SwapSessionStatus.SUBMITTED.value,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("12"),
        estimated_receive=Decimal("0.00475"),
        tx_hash=TX_LEGACY,
        audit_log=[{"event": "quote_requested", "signing_wallet_address": EVM_ADDR}],
    )
    db.add(swap)
    db.commit()

    assert skip_legacy_cost_basis_for_orchestrator(db, swap) is False
    cb_before = _cb_count(db)
    result = settle_lifi_swap_idempotently(db, swap.id, dry_run=False)
    db.commit()

    assert result.debit_applied is True
    assert result.credit_applied is True
    assert result.cost_basis_applied is True
    assert _cb_count(db) > cb_before


@patch("services.lifi.lifi_swap_reconciliation.is_tx_confirmed_on_chain", return_value=True)
@patch(
    "services.lifi.lifi_swap_reconciliation.resolve_lifi_actual_receive_amount",
    return_value=LifiActualReceiveResult(amount=Decimal("0.000614"), source="test"),
)
def test_reconciliation_orchestrator_allowlist_off_ingests_cost_basis(mock_amount, mock_rpc, db, monkeypatch):
    """Intent Phase 2 résiduel hors allowlist → cost basis legacy autorisé."""
    monkeypatch.setenv("LIFI_INTENT_ORCHESTRATOR_ENABLED", "true")
    monkeypatch.setenv("LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS", "other-pilot@example.com")
    pe = make_linked_client(db)
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
    db.commit()

    swap = PersonWalletSwap(
        id=uuid4(),
        person_id=pe.person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1"),
        estimated_receive=Decimal("0.000614"),
        tx_hash="0xallowlistoff1234567890abcdef1234567890abcdef1234567890abcdef",
        confirmed_at=datetime.now(timezone.utc),
        audit_log=[{"event": "quote_requested", "signing_wallet_address": EVM_ADDR}],
    )
    db.add(swap)
    db.flush()
    attach_orchestrator_intent_to_swap_atomic(db, person_id=pe.person_id, swap_id=swap.id)
    _seed_webhook_eth_credit(
        db,
        wallet=wallet,
        person_id=pe.person_id,
        tx_hash=str(swap.tx_hash),
        amount="0.000614",
    )

    assert skip_legacy_cost_basis_for_orchestrator(db, swap) is False
    preview = build_reconciliation_dry_run_summary(db, swap)
    assert preview["would_create_cost_basis"] is True

    cb_before = _cb_count(db)
    result = settle_lifi_swap_idempotently(db, swap.id, dry_run=False)
    db.commit()

    assert result.debit_applied is True
    assert result.cost_basis_applied is True
    assert _cb_count(db) > cb_before


def test_skip_legacy_cost_basis_matches_swap_settlement_guard(db: Session, monkeypatch):
    from services.transaction_outbox.orchestrator_settle_enqueue import (
        skip_legacy_swap_settlement_for_orchestrator,
    )

    pe, swap, _ = _seed_orchestrator_confirmed_swap(db, monkeypatch)
    assert skip_legacy_cost_basis_for_orchestrator(db, swap) == skip_legacy_swap_settlement_for_orchestrator(
        db, swap
    )
