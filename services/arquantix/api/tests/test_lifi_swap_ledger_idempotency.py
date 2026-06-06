"""Tests idempotence jambes ledger swap LI.FI — collision tx_hash/log_index."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from services.auth.person_identity_bridge import PROVIDER_PRIVY, link_external_identity_to_person, upsert_person_crypto_wallet
from services.lifi.lifi_swap_settlement import (
    SWAP_LEDGER_LOG_INDEX_DEBIT_SYNTHETIC,
    _create_swap_ledger_entry,
    swap_debit_idempotency_key,
)
from services.lifi.models import PersonWalletSwap
from services.privy_wallet.enums import PersonWalletDirection
from services.privy_wallet.models import PersonWalletDeposit
from services.privy_wallet.repository import PersonWalletDepositRepository
from tests.conftest import make_linked_client

EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
TX = "0xabc123collision000000000000000000000000000000000000000000000001"


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


def _wallet(db: Session, pe):
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject="did:privy:ledgeridem001",
        external_email="ledgeridem@test.local",
    )
    return upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        address=EVM_ADDR,
        metadata_json={"privy_wallet_id": "w-ledgeridem"},
    )


def _swap(person_id):
    swap_id = uuid4()
    return PersonWalletSwap(
        id=swap_id,
        person_id=person_id,
        status="SUBMITTED",
        from_asset="AAVE",
        to_asset="EURC",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("1"),
        estimated_receive=Decimal("10"),
        tx_hash=TX,
        audit_log=[{"event": "quote_requested", "signing_wallet_address": EVM_ADDR}],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


def test_create_swap_ledger_entry_uses_synthetic_log_index_on_collision(db: Session):
    pe = make_linked_client(db)
    wallet = _wallet(db, pe)
    swap = _swap(pe.person_id)
    db.add(swap)
    db.flush()

    PersonWalletDepositRepository().create(
        db,
        data={
            "person_crypto_wallet_id": wallet.id,
            "person_id": pe.person_id,
            "pe_client_id": wallet.pe_client_id,
            "transaction_kind": "privy_deposit_in",
            "direction": PersonWalletDirection.CREDIT.value,
            "asset": "EURC",
            "amount": Decimal("10"),
            "chain_type": "ethereum",
            "chain_id": 8453,
            "tx_hash": TX,
            "log_index": 0,
            "from_address": "0xrouter",
            "to_address": EVM_ADDR,
            "confirmations": 1,
            "status": "confirmed",
            "idempotency_key": f"{TX}-0_webhook",
            "title": "Dépôt EURC",
            "subtitle": "+10 EURC",
            "metadata_json": {"event_source": "privy_webhook"},
            "confirmed_at": datetime.now(timezone.utc),
        },
    )
    db.commit()

    created = _create_swap_ledger_entry(
        db,
        swap=swap,
        wallet=wallet,
        direction=PersonWalletDirection.DEBIT.value,
        asset="AAVE",
        amount=Decimal("1"),
        chain_id=8453,
        log_index=0,
        idempotency_key=swap_debit_idempotency_key(str(swap.id)),
        sync_source="test",
    )
    assert created is True

    debit = (
        db.query(PersonWalletDeposit)
        .filter(PersonWalletDeposit.idempotency_key == swap_debit_idempotency_key(str(swap.id)))
        .one()
    )
    assert debit.log_index == SWAP_LEDGER_LOG_INDEX_DEBIT_SYNTHETIC
    assert debit.asset == "AAVE"

    again = _create_swap_ledger_entry(
        db,
        swap=swap,
        wallet=wallet,
        direction=PersonWalletDirection.DEBIT.value,
        asset="AAVE",
        amount=Decimal("1"),
        chain_id=8453,
        log_index=0,
        idempotency_key=swap_debit_idempotency_key(str(swap.id)),
        sync_source="test",
    )
    assert again is False
