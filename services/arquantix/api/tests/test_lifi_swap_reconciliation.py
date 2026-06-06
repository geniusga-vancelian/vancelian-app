"""Tests réconciliation idempotente swap LI.FI — settlement partiel ledger."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from services.auth.person_identity_bridge import PROVIDER_PRIVY, link_external_identity_to_person, upsert_person_crypto_wallet
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_actual_receive import LifiActualReceiveResult
from services.lifi.lifi_swap_reconciliation import (
    build_reconciliation_dry_run_summary,
    detect_swap_ledger_legs,
    settle_lifi_swap_idempotently,
)
from services.lifi.models import PersonWalletSwap
from services.privy_wallet.admin_service import PrivyWalletAdminService
from services.privy_wallet.enums import PersonWalletDirection
from services.privy_wallet.models import PersonWalletDeposit
from services.privy_wallet.repository import PersonWalletBalanceRepository, PersonWalletDepositRepository
from services.privy_wallet.schemas import PrivySimulateDepositRequest
from tests.conftest import make_linked_client

EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
PRIVY_USER = "did:privy:testreconcile001"
TX = "0x6aabacfbac0f92c9007cb070bc2c744dbb52c0317e8dd38eab75a7072f35f8bb"


def _migration_159_applied() -> bool:
    try:
        from sqlalchemy import inspect

        from database import engine

        return inspect(engine).has_table("person_wallet_swaps")
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_159_applied(),
    reason="Appliquer `alembic upgrade head` (159) pour les tests swap LI.FI.",
)


def _seed_wallet(db: Session, pe):
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=PRIVY_USER,
        external_email="reconcile@test.local",
    )
    wallet = upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        address=EVM_ADDR,
        metadata_json={"privy_wallet_id": "w-reconcile"},
    )
    db.commit()
    return wallet


def _submitted_swap(person_id) -> PersonWalletSwap:
    return PersonWalletSwap(
        id=uuid4(),
        person_id=person_id,
        status=SwapSessionStatus.SUBMITTED.value,
        from_asset="AAVE",
        to_asset="EURC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("0.2115547"),
        estimated_receive=Decimal("11.17"),
        tx_hash=TX,
        audit_log=[{"event": "quote_requested", "signing_wallet_address": EVM_ADDR}],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def _seed_aave_balance(db: Session, wallet, person_id):
    PrivyWalletAdminService().simulate_deposit(
        db,
        PrivySimulateDepositRequest(
            person_id=person_id,
            wallet_address=EVM_ADDR,
            asset="AAVE",
            amount="0.211554657",
            chain_id=8453,
        ),
    )
    db.commit()


def _seed_webhook_eurc_credit(db: Session, wallet, person_id):
    PersonWalletDepositRepository().create(
        db,
        data={
            "person_crypto_wallet_id": wallet.id,
            "person_id": person_id,
            "pe_client_id": wallet.pe_client_id,
            "privy_webhook_event_id": None,
            "transaction_kind": "privy_deposit_in",
            "direction": PersonWalletDirection.CREDIT.value,
            "asset": "EURC",
            "amount": Decimal("11.153851"),
            "chain_type": "ethereum",
            "chain_id": 8453,
            "tx_hash": TX,
            "log_index": 444,
            "from_address": "0xrouter",
            "to_address": EVM_ADDR,
            "confirmations": 1,
            "status": "confirmed",
            "idempotency_key": f"{TX}-444_wallet.funds_deposited",
            "title": "Dépôt Euro Coin",
            "subtitle": "+11.153851 EURC",
            "metadata_json": {
                "event_source": "privy_webhook",
                "privy_event_type": "wallet.funds_deposited",
            },
            "confirmed_at": datetime.now(timezone.utc),
        },
    )
    balance_repo = PersonWalletBalanceRepository()
    row = balance_repo.get_or_create_for_update(db, wallet_id=wallet.id, person_id=person_id, asset="EURC")
    balance_repo.increment_balance(db, row, delta=Decimal("11.153851"), sync_source="test")
    db.commit()


def _seed_swap_debit_only(db: Session, wallet, person_id, swap_id: str):
    PersonWalletDepositRepository().create(
        db,
        data={
            "person_crypto_wallet_id": wallet.id,
            "person_id": person_id,
            "pe_client_id": wallet.pe_client_id,
            "transaction_kind": "crypto_swap",
            "direction": PersonWalletDirection.DEBIT.value,
            "asset": "USDC",
            "amount": Decimal("12"),
            "chain_type": "ethereum",
            "chain_id": 8453,
            "tx_hash": "0xswapbaseeth1234567890abcdef1234567890abcdef1234567890abcdef12",
            "log_index": 0,
            "from_address": EVM_ADDR,
            "to_address": EVM_ADDR,
            "confirmations": 1,
            "status": "confirmed",
            "idempotency_key": f"lifi-swap:{swap_id}:debit",
            "title": "Échange USDC → ETH",
            "subtitle": "−12 USDC",
            "metadata_json": {"swap_id": swap_id, "source": "lifi_swap"},
            "confirmed_at": datetime.now(timezone.utc),
        },
    )
    db.commit()


@patch("services.lifi.lifi_swap_reconciliation.is_tx_confirmed_on_chain", return_value=True)
@patch(
    "services.lifi.lifi_swap_reconciliation.resolve_lifi_actual_receive_amount",
    return_value=LifiActualReceiveResult(amount=Decimal("11.153851"), source="test"),
)
def test_partial_settlement_credit_exists_debit_missing(mock_amount, mock_rpc, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    _seed_aave_balance(db, wallet, pe.person_id)
    swap = _submitted_swap(pe.person_id)
    db.add(swap)
    db.flush()
    _seed_webhook_eurc_credit(db, wallet, pe.person_id)

    legs = detect_swap_ledger_legs(db, swap)
    assert legs.credit_exists is True
    assert legs.debit_exists is False

    preview = build_reconciliation_dry_run_summary(db, swap)
    assert preview["would_create_debit_AAVE"] is True
    assert preview["would_create_credit_EURC"] is False
    assert preview["would_link_existing_credit_EURC"] is True
    assert preview["no_double_write_risk"] is True

    result = settle_lifi_swap_idempotently(db, swap.id, dry_run=False)
    db.refresh(swap)

    assert result.debit_applied is True
    assert result.credit_applied is False
    assert swap.status == SwapSessionStatus.CONFIRMED.value


@patch("services.lifi.lifi_swap_reconciliation.is_tx_confirmed_on_chain", return_value=True)
@patch(
    "services.lifi.lifi_swap_reconciliation.resolve_lifi_actual_receive_amount",
    return_value=LifiActualReceiveResult(amount=Decimal("11.153851"), source="test"),
)
def test_partial_settlement_idempotent_no_double_debit(mock_amount, mock_rpc, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    _seed_aave_balance(db, wallet, pe.person_id)
    swap = _submitted_swap(pe.person_id)
    db.add(swap)
    db.flush()
    _seed_webhook_eurc_credit(db, wallet, pe.person_id)

    settle_lifi_swap_idempotently(db, swap.id, dry_run=False)
    db.refresh(swap)

    result2 = settle_lifi_swap_idempotently(db, swap.id, dry_run=False)
    assert result2.action == "noop_already_settled"


@patch("services.lifi.lifi_swap_reconciliation.is_tx_confirmed_on_chain", return_value=True)
@patch(
    "services.lifi.lifi_swap_reconciliation.resolve_lifi_actual_receive_amount",
    return_value=LifiActualReceiveResult(amount=Decimal("0.00475"), source="test"),
)
def test_full_settlement_creates_debit_and_credit(mock_amount, mock_rpc, db: Session):
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
        tx_hash="0xswapbaseeth1234567890abcdef1234567890abcdef1234567890abcdef12",
        audit_log=[{"event": "quote_requested", "signing_wallet_address": EVM_ADDR}],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(swap)
    db.commit()

    result = settle_lifi_swap_idempotently(db, swap.id, dry_run=False)
    db.refresh(swap)
    assert result.debit_applied is True
    assert result.credit_applied is True
    assert swap.status == SwapSessionStatus.CONFIRMED.value


@patch("services.lifi.lifi_swap_reconciliation.is_tx_confirmed_on_chain", return_value=True)
@patch(
    "services.lifi.lifi_swap_reconciliation.resolve_lifi_actual_receive_amount",
    return_value=LifiActualReceiveResult(amount=Decimal("0.00475"), source="rpc_only"),
)
def test_debit_exists_credit_missing_only_credit_added(mock_amount, mock_rpc, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
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
        tx_hash="0xswapbaseeth1234567890abcdef1234567890abcdef1234567890abcdef12",
        audit_log=[{"event": "quote_requested", "signing_wallet_address": EVM_ADDR}],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(swap)
    db.flush()
    _seed_swap_debit_only(db, wallet, pe.person_id, str(swap.id))

    result = settle_lifi_swap_idempotently(db, swap.id, dry_run=False)
    db.refresh(swap)
    assert result.debit_applied is False
    assert result.credit_applied is True


@patch("services.lifi.lifi_swap_reconciliation.is_tx_confirmed_on_chain", return_value=True)
@patch(
    "services.lifi.lifi_swap_reconciliation.resolve_lifi_actual_receive_amount",
    return_value=LifiActualReceiveResult(amount=Decimal("0.00475"), source="test"),
)
def test_both_legs_exist_noop_until_settled_marker(mock_amount, mock_rpc, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    swap = PersonWalletSwap(
        id=uuid4(),
        person_id=pe.person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("12"),
        estimated_receive=Decimal("0.00475"),
        tx_hash="0xswapbaseeth1234567890abcdef1234567890abcdef1234567890abcdef12",
        audit_log=[{"event": "swap_settled"}],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        confirmed_at=datetime.now(timezone.utc),
    )
    db.add(swap)
    db.flush()
    _seed_swap_debit_only(db, wallet, pe.person_id, str(swap.id))
    PersonWalletDepositRepository().create(
        db,
        data={
            "person_crypto_wallet_id": wallet.id,
            "person_id": pe.person_id,
            "pe_client_id": wallet.pe_client_id,
            "transaction_kind": "crypto_swap",
            "direction": PersonWalletDirection.CREDIT.value,
            "asset": "ETH",
            "amount": Decimal("0.00475"),
            "chain_type": "ethereum",
            "chain_id": 8453,
            "tx_hash": swap.tx_hash,
            "log_index": 1,
            "from_address": EVM_ADDR,
            "to_address": EVM_ADDR,
            "confirmations": 1,
            "status": "confirmed",
            "idempotency_key": f"lifi-swap:{swap.id}:credit",
            "title": "Échange USDC → ETH",
            "subtitle": "+0.00475 ETH",
            "metadata_json": {"swap_id": str(swap.id), "source": "lifi_swap"},
            "confirmed_at": datetime.now(timezone.utc),
        },
    )
    db.commit()

    result = settle_lifi_swap_idempotently(db, swap.id, dry_run=True)
    assert result.action == "noop_already_settled"


@patch("services.lifi.lifi_swap_reconciliation.is_tx_confirmed_on_chain", return_value=True)
@patch(
    "services.lifi.lifi_swap_reconciliation.resolve_lifi_actual_receive_amount",
    return_value=None,
)
def test_rpc_confirms_uses_existing_credit_amount(mock_resolve, mock_rpc, db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    _seed_aave_balance(db, wallet, pe.person_id)
    swap = _submitted_swap(pe.person_id)
    db.add(swap)
    db.flush()
    _seed_webhook_eurc_credit(db, wallet, pe.person_id)

    dry = settle_lifi_swap_idempotently(db, swap.id, dry_run=True)
    assert dry.preview is not None
    assert dry.preview["would_create_debit_AAVE"] is True
    assert dry.preview["would_create_credit_EURC"] is False
