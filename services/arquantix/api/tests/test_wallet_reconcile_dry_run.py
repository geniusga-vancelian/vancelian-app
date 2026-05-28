"""Tests reconcile wallet dry-run — discrepancies sans modification balance."""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.auth.person_identity_bridge import PROVIDER_PRIVY, link_external_identity_to_person, upsert_person_crypto_wallet
from services.onchain_indexer.models import RawOnChainEvent
from services.onchain_indexer.repository import RawOnChainEventRepository
from services.onchain_reconciliation.wallet_dry_run import build_wallet_reconcile_report
from services.privy_wallet.enums import PersonWalletDepositStatus, PersonWalletDirection
from services.privy_wallet.models import PersonWalletDeposit
from services.privy_wallet.repository import PersonWalletBalanceRepository
from tests.conftest import make_linked_client


def _migration_161_applied() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'raw_onchain_events'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


def _migration_158_applied() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'person_wallet_deposits'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not (_migration_161_applied() and _migration_158_applied()),
    reason="Migrations 158 + 161 requises.",
)

CHAIN_ID = 8453


def _unique_evm_address() -> str:
    return "0x" + (uuid.uuid4().hex + uuid.uuid4().hex)[:40]


def _seed_wallet(db: Session, pe):
    addr = _unique_evm_address()
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=f"did:privy:{uuid.uuid4().hex[:12]}",
        external_email=f"reconcile-dry-{uuid.uuid4().hex[:8]}@test.local",
    )
    return upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        address=addr,
        chain_id=CHAIN_ID,
        metadata_json={"privy_wallet_id": f"w-reconcile-{uuid.uuid4().hex[:8]}"},
    )


def test_dry_run_does_not_modify_balances(db: Session, monkeypatch):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)

    balance_row = PersonWalletBalanceRepository.get_or_create_for_update(
        db,
        wallet_id=wallet.id,
        person_id=pe.person_id,
        asset="USDC",
    )
    balance_row.balance = Decimal("42.5")
    balance_row.available_balance = Decimal("42.5")
    db.flush()

    before = Decimal(str(balance_row.balance))

    monkeypatch.setattr(
        "services.onchain_reconciliation.wallet_dry_run.fetch_aggregated_on_chain_balances",
        lambda **kwargs: {(CHAIN_ID, "USDC"): Decimal("42.5")},
    )

    def _fail_increment(*args, **kwargs):
        raise AssertionError("increment_balance must not run in dry-run")

    monkeypatch.setattr(PersonWalletBalanceRepository, "increment_balance", _fail_increment)

    build_wallet_reconcile_report(
        db,
        wallet_address=wallet.address,
        chain_id=CHAIN_ID,
        dry_run=True,
        index_tx_hashes=False,
    )

    db.refresh(balance_row)
    after = Decimal(str(balance_row.balance))
    assert after == before


def test_detects_db_ledger_without_onchain_event(db: Session, monkeypatch):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    tx_hash = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"

    db.add(
        PersonWalletDeposit(
            person_crypto_wallet_id=wallet.id,
            person_id=pe.person_id,
            pe_client_id=pe.id,
            transaction_kind="privy_deposit_in",
            direction=PersonWalletDirection.CREDIT.value,
            asset="USDC",
            amount=Decimal("10"),
            chain_type="ethereum",
            chain_id=CHAIN_ID,
            tx_hash=tx_hash,
            log_index=0,
            to_address=wallet.address,
            status=PersonWalletDepositStatus.CONFIRMED.value,
            title="Test deposit",
            subtitle="+10 USDC",
        )
    )
    db.flush()

    monkeypatch.setattr(
        "services.onchain_reconciliation.wallet_dry_run.fetch_aggregated_on_chain_balances",
        lambda **kwargs: {(CHAIN_ID, "USDC"): Decimal("10")},
    )

    report = build_wallet_reconcile_report(
        db,
        wallet_address=wallet.address,
        chain_id=CHAIN_ID,
        dry_run=True,
    )

    assert any(
        row.get("reason") == "no_matching_raw_onchain_event"
        for row in report.db_without_onchain_proof
    )


def test_detects_onchain_event_without_db_ledger(db: Session, monkeypatch):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    tx_hash = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"

    RawOnChainEventRepository.insert_if_absent(
        db,
        data={
            "chain_id": CHAIN_ID,
            "tx_hash": tx_hash,
            "log_index": 1,
            "wallet_address": wallet.address,
            "asset": "USDC",
            "amount_raw": 5_000_000,
            "event_type": "erc20_transfer",
        },
    )
    db.flush()

    monkeypatch.setattr(
        "services.onchain_reconciliation.wallet_dry_run.fetch_aggregated_on_chain_balances",
        lambda **kwargs: {(CHAIN_ID, "USDC"): Decimal("5")},
    )

    report = build_wallet_reconcile_report(
        db,
        wallet_address=wallet.address,
        chain_id=CHAIN_ID,
        dry_run=True,
    )

    assert len(report.onchain_without_db_ledger) >= 1
    assert report.onchain_without_db_ledger[0]["tx_hash"] == tx_hash.lower()
