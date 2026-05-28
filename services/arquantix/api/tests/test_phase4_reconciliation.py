"""Tests Phase 4 — replay block range, reconcile:user, discrepancies."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.auth.person_identity_bridge import PROVIDER_PRIVY, link_external_identity_to_person, upsert_person_crypto_wallet
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.block_range_replay import replay_block_range
from services.onchain_indexer.repository import RawOnChainEventRepository
from services.onchain_reconciliation.discrepancy_models import ReconciliationDiscrepancy
from services.onchain_reconciliation.discrepancy_repository import DiscrepancyRepository
from services.onchain_reconciliation.user_reconcile import build_user_reconcile_report
from services.onchain_indexer.models import RawOnChainEvent
from services.privy_wallet.enums import PersonWalletDepositStatus, PersonWalletDirection
from services.privy_wallet.models import PersonWalletDeposit
from services.privy_wallet.repository import PersonWalletBalanceRepository
from tests.conftest import make_linked_client

CHAIN_ID = 8453


def _unique_evm_address() -> str:
    return "0x" + (uuid.uuid4().hex + uuid.uuid4().hex)[:40]


def _migration_162_applied() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = 'reconciliation_discrepancies'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


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


pytestmark = pytest.mark.skipif(
    not (_migration_161_applied() and _migration_162_applied()),
    reason="Migrations 161+162 requises.",
)


def _seed_wallet(db: Session, pe, *, address: str | None = None):
    addr = address or _unique_evm_address()
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=f"did:privy:{uuid.uuid4().hex[:12]}",
        external_email=f"phase4-{uuid.uuid4().hex[:8]}@test.local",
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
    )


# USDC native Base (EVM_ERC20_CONTRACTS[8453]) — doit matcher ERC20_CONTRACT_TO_ASSET.
_BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"


def _mock_transfer_log(*, tx_hash: str, log_index: int, to_wallet: str) -> dict:
    to_topic = "0x" + to_wallet.lower().replace("0x", "").rjust(64, "0")
    from_topic = "0x" + "1" * 64
    return {
        "address": _BASE_USDC,
        "topics": [
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
            from_topic,
            to_topic,
        ],
        "data": "0x" + format(1_000_000, "x"),
        "transactionHash": tx_hash,
        "blockNumber": "0x1",
        "logIndex": hex(log_index),
    }


def test_replay_block_range_dry_run_writes_nothing(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    db.commit()

    tx_hash = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"
    mock_log = _mock_transfer_log(tx_hash=tx_hash, log_index=3, to_wallet=wallet.address)

    with patch(
        "services.onchain_indexer.block_range_replay.resolve_chain_rpc_url",
        return_value="http://mock-rpc",
    ):
        with patch(
            "services.onchain_indexer.block_range_replay._fetch_transfer_logs",
            return_value=[mock_log],
        ):
            before = db.query(RawOnChainEvent).count()
            result = replay_block_range(
                db,
                chain_id=CHAIN_ID,
                from_block=100,
                to_block=101,
                dry_run=True,
            )
            db.rollback()
            after = db.query(RawOnChainEvent).count()

    assert result.dry_run is True
    assert result.events_prepared >= 1
    assert after == before


def test_replay_block_range_no_dry_run_inserts_only_raw_events(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    db.commit()

    tx_hash = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"
    mock_log = _mock_transfer_log(tx_hash=tx_hash, log_index=7, to_wallet=wallet.address)

    with patch(
        "services.onchain_indexer.block_range_replay.resolve_chain_rpc_url",
        return_value="http://mock-rpc",
    ):
        with patch(
            "services.onchain_indexer.block_range_replay._fetch_transfer_logs",
            return_value=[mock_log],
        ):
            result = replay_block_range(
                db,
                chain_id=CHAIN_ID,
                from_block=200,
                to_block=201,
                dry_run=False,
            )
            db.commit()

    assert result.events_inserted >= 1
    row = RawOnChainEventRepository.find_by_chain_tx_log(
        db, chain_id=CHAIN_ID, tx_hash=tx_hash.lower(), log_index=7
    )
    assert row is not None

    with patch(
        "services.onchain_indexer.block_range_replay.resolve_chain_rpc_url",
        return_value="http://mock-rpc",
    ):
        with patch(
            "services.onchain_indexer.block_range_replay._fetch_transfer_logs",
            return_value=[mock_log],
        ):
            result2 = replay_block_range(
                db,
                chain_id=CHAIN_ID,
                from_block=200,
                to_block=201,
                dry_run=False,
            )
            db.commit()
    assert result2.events_skipped_existing >= 1


def test_reconcile_user_detects_admin_sim(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    db.add(
        PersonWalletDeposit(
            person_crypto_wallet_id=wallet.id,
            person_id=pe.person_id,
            pe_client_id=pe.id,
            transaction_kind="privy_deposit_in",
            direction=PersonWalletDirection.CREDIT.value,
            asset="USDC",
            amount=Decimal("100"),
            chain_type="ethereum",
            chain_id=CHAIN_ID,
            tx_hash=f"0xsim{uuid.uuid4().hex}",
            log_index=0,
            to_address=wallet.address,
            status=PersonWalletDepositStatus.CONFIRMED.value,
            idempotency_key=f"admin_sim_{uuid.uuid4().hex}",
            title="Sim",
            subtitle="+100",
        )
    )
    db.flush()

    with patch(
        "services.onchain_reconciliation.wallet_dry_run.fetch_aggregated_on_chain_balances",
        lambda **kwargs: {(CHAIN_ID, "USDC"): Decimal("0")},
    ):
        report = build_user_reconcile_report(db, person_id=pe.person_id, dry_run=True)

    assert any(a.get("discrepancy_type") == "admin_sim_deposit" for a in report.anomalies)


def test_reconcile_user_detects_swap_without_settlement(db: Session):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    swap = PersonWalletSwap(
        id=uuid.uuid4(),
        person_id=pe.person_id,
        status=SwapSessionStatus.CONFIRMED.value,
        from_asset="USDC",
        to_asset="ETH",
        from_chain="base",
        to_chain="base",
        amount_in=Decimal("10"),
        estimated_receive=Decimal("0.01"),
        tx_hash="0xabc",
        audit_log=[{"event": "settlement_blocked", "reason": "actual_amount_missing"}],
    )
    db.add(swap)
    db.flush()

    with patch(
        "services.onchain_reconciliation.wallet_dry_run.fetch_aggregated_on_chain_balances",
        lambda **kwargs: {},
    ):
        report = build_user_reconcile_report(db, person_id=pe.person_id, dry_run=True)

    assert any(
        a.get("discrepancy_type") == "swap_confirmed_without_settlement" for a in report.anomalies
    )


def test_reconcile_user_detects_onchain_without_ledger(db: Session):
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
            "amount_raw": 1_000_000,
        },
    )
    db.flush()

    with patch(
        "services.onchain_reconciliation.wallet_dry_run.fetch_aggregated_on_chain_balances",
        lambda **kwargs: {(CHAIN_ID, "USDC"): Decimal("1")},
    ):
        report = build_user_reconcile_report(db, person_id=pe.person_id, dry_run=True)

    assert any(
        a.get("discrepancy_type") == "onchain_event_without_db_ledger" for a in report.anomalies
    )


def test_reconcile_user_no_dry_run_writes_discrepancies_only(db: Session, monkeypatch):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    db.add(
        PersonWalletDeposit(
            person_crypto_wallet_id=wallet.id,
            person_id=pe.person_id,
            pe_client_id=pe.id,
            transaction_kind="privy_deposit_in",
            direction=PersonWalletDirection.CREDIT.value,
            asset="USDC",
            amount=Decimal("5"),
            chain_type="ethereum",
            chain_id=CHAIN_ID,
            tx_hash=f"0xsim{uuid.uuid4().hex}",
            log_index=0,
            to_address=wallet.address,
            status=PersonWalletDepositStatus.CONFIRMED.value,
            idempotency_key=f"admin_sim_{uuid.uuid4().hex}",
            title="Sim",
            subtitle="+5",
        )
    )
    db.flush()

    balance_row = PersonWalletBalanceRepository.get_or_create_for_update(
        db,
        wallet_id=wallet.id,
        person_id=pe.person_id,
        asset="USDC",
    )
    balance_row.balance = Decimal("99")
    balance_row.available_balance = Decimal("99")
    db.flush()
    before_balance = Decimal(str(balance_row.balance))

    def _fail_increment(*args, **kwargs):
        raise AssertionError("balance increment forbidden")

    monkeypatch.setattr(PersonWalletBalanceRepository, "increment_balance", _fail_increment)

    with patch(
        "services.onchain_reconciliation.wallet_dry_run.fetch_aggregated_on_chain_balances",
        lambda **kwargs: {(CHAIN_ID, "USDC"): Decimal("99")},
    ):
        report = build_user_reconcile_report(
            db,
            person_id=pe.person_id,
            dry_run=False,
            persist_discrepancies=True,
        )
        db.commit()

    db.refresh(balance_row)
    assert Decimal(str(balance_row.balance)) == before_balance
    assert report.discrepancies_written >= 1
    assert (
        db.query(ReconciliationDiscrepancy)
        .filter(ReconciliationDiscrepancy.person_id == pe.person_id)
        .count()
        >= 1
    )
