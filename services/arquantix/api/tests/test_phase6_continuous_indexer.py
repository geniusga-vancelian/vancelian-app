"""Tests Phase 6 — indexer continu Base."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.onchain_indexer.checkpoint_repository import CheckpointRepository
from services.onchain_indexer.continuous_base_indexer import (
    IndexerConfigError,
    IndexerNotEnabledError,
    run_base_indexer_once,
)
from services.onchain_indexer.indexer_config import (
    INDEXER_NAME_BASE_CONTINUOUS,
    BaseIndexerConfig,
)
from services.onchain_indexer.models import OnchainIndexerCheckpoint, RawOnChainEvent
from services.onchain_indexer.repository import RawOnChainEventRepository
from services.onchain_reconciliation.discrepancy_models import ReconciliationCorrection
from services.privy_wallet.repository import (
    PersonWalletBalanceRepository,
    PersonWalletDepositRepository,
)
from tests.conftest import make_linked_client
from tests.test_phase4_reconciliation import CHAIN_ID, _mock_transfer_log, _seed_wallet

RPC = "http://mock-rpc"


def _migration_165_ready() -> bool:
    try:
        with engine.connect() as conn:
            r = conn.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' "
                    "AND table_name = 'onchain_indexer_checkpoints'"
                )
            )
            return r.fetchone() is not None
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_165_ready(),
    reason="Migration 165 requise.",
)


def _cfg(**overrides) -> BaseIndexerConfig:
    base = {
        "enabled": True,
        "start_block": 1000,
        "chunk_size": 10,
        "confirmations": 12,
        "max_blocks_per_run": 50,
        "native_enabled": False,
    }
    base.update(overrides)
    return BaseIndexerConfig(**base)


def _patch_rpc(mock_log, *, head: int = 1050):
    return patch.multiple(
        "services.onchain_indexer.continuous_base_indexer",
        resolve_chain_rpc_url=MagicMock(return_value=RPC),
        fetch_block_number=MagicMock(return_value=head),
        effective_block_chunk=MagicMock(return_value=10),
        replay_block_range=MagicMock(
            return_value=MagicMock(
                errors=[],
                events_prepared=1,
                events_inserted=1,
                events_skipped_existing=0,
                logs_scanned=1,
                to_dict=MagicMock(return_value={}),
            )
        ),
    )


def test_dry_run_writes_nothing(db: Session):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    db.commit()

    with _patch_rpc(_mock_transfer_log(tx_hash="0x1", log_index=0, to_wallet="0x" + "a" * 40)):
        before = db.query(RawOnChainEvent).count()
        result = run_base_indexer_once(
            db,
            chain_id=CHAIN_ID,
            dry_run=True,
            config=_cfg(),
        )
        db.rollback()
        after = db.query(RawOnChainEvent).count()

    assert result.dry_run is True
    assert after == before
    assert db.query(OnchainIndexerCheckpoint).count() == 0


def test_no_dry_run_inserts_raw_and_advances_checkpoint(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    tx_hash = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"
    mock_log = _mock_transfer_log(tx_hash=tx_hash, log_index=2, to_wallet=wallet.address)

    def _real_replay(db_sess, **kwargs):
        from services.onchain_indexer.block_range_replay import replay_block_range

        return replay_block_range(db_sess, **kwargs)

    with patch(
        "services.onchain_indexer.continuous_base_indexer.resolve_chain_rpc_url",
        return_value=RPC,
    ):
        with patch(
            "services.onchain_indexer.continuous_base_indexer.fetch_block_number",
            return_value=1020,
        ):
            with patch(
                "services.onchain_indexer.block_range_replay._fetch_transfer_logs",
                return_value=[mock_log],
            ):
                with patch(
                    "services.onchain_indexer.continuous_base_indexer.replay_block_range",
                    side_effect=_real_replay,
                ):
                    result = run_base_indexer_once(
                        db,
                        chain_id=CHAIN_ID,
                        dry_run=False,
                        config=_cfg(start_block=1000, max_blocks_per_run=20),
                    )
                    db.commit()

    assert result.status == "ok"
    assert result.erc20.get("events_inserted", 0) >= 1
    row = RawOnChainEventRepository.find_by_chain_tx_log(
        db, chain_id=CHAIN_ID, tx_hash=tx_hash.lower(), log_index=2
    )
    assert row is not None

    cp = CheckpointRepository.get(db, chain_id=CHAIN_ID, indexer_name=INDEXER_NAME_BASE_CONTINUOUS)
    assert cp is not None
    assert cp.last_scanned_block >= 1000


def test_idempotent_replay_skips_existing(db: Session):
    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    tx_hash = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"
    mock_log = _mock_transfer_log(tx_hash=tx_hash, log_index=4, to_wallet=wallet.address)

    def _real_replay(db_sess, **kwargs):
        from services.onchain_indexer.block_range_replay import replay_block_range

        return replay_block_range(db_sess, **kwargs)

    patches = [
        patch("services.onchain_indexer.continuous_base_indexer.resolve_chain_rpc_url", return_value=RPC),
        patch("services.onchain_indexer.continuous_base_indexer.fetch_block_number", return_value=1015),
        patch("services.onchain_indexer.block_range_replay._fetch_transfer_logs", return_value=[mock_log]),
        patch("services.onchain_indexer.continuous_base_indexer.replay_block_range", side_effect=_real_replay),
    ]
    for p in patches:
        p.start()
    try:
        run_base_indexer_once(
            db,
            chain_id=CHAIN_ID,
            dry_run=False,
            config=_cfg(start_block=1000, max_blocks_per_run=15),
        )
        db.commit()
        count1 = db.query(RawOnChainEvent).filter(RawOnChainEvent.tx_hash == tx_hash.lower()).count()

        CheckpointRepository.get_or_create(
            db,
            chain_id=CHAIN_ID,
            indexer_name=INDEXER_NAME_BASE_CONTINUOUS,
            initial_block=999,
        )
        cp = CheckpointRepository.get(db, chain_id=CHAIN_ID)
        cp.last_scanned_block = 999
        db.commit()

        run_base_indexer_once(
            db,
            chain_id=CHAIN_ID,
            dry_run=False,
            config=_cfg(start_block=1000, max_blocks_per_run=15),
        )
        db.commit()
        count2 = db.query(RawOnChainEvent).filter(RawOnChainEvent.tx_hash == tx_hash.lower()).count()
    finally:
        for p in patches:
            p.stop()

    assert count1 == 1
    assert count2 == 1


def test_checkpoint_not_advanced_on_rpc_error(db: Session):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    CheckpointRepository.get_or_create(
        db,
        chain_id=CHAIN_ID,
        indexer_name=INDEXER_NAME_BASE_CONTINUOUS,
        initial_block=5000,
    )
    db.commit()

    with patch(
        "services.onchain_indexer.continuous_base_indexer.resolve_chain_rpc_url",
        return_value=RPC,
    ):
        with patch(
            "services.onchain_indexer.continuous_base_indexer.fetch_block_number",
            return_value=5100,
        ):
            with patch(
                "services.onchain_indexer.continuous_base_indexer.replay_block_range",
                return_value=MagicMock(
                    errors=["eth_getLogs failed"],
                    events_prepared=0,
                    events_inserted=0,
                    events_skipped_existing=0,
                    logs_scanned=0,
                ),
            ):
                result = run_base_indexer_once(
                    db,
                    chain_id=CHAIN_ID,
                    dry_run=False,
                    config=_cfg(start_block=1000, max_blocks_per_run=30),
                )
                db.commit()

    cp = CheckpointRepository.get(db, chain_id=CHAIN_ID)
    assert result.status == "error"
    assert cp.last_scanned_block == 5000


def test_confirmations_respected(db: Session):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    db.commit()

    captured: dict[str, int] = {}

    def _replay(db_sess, *, from_block, to_block, **kwargs):
        captured["to_block"] = to_block
        return MagicMock(
            errors=[],
            events_prepared=0,
            events_inserted=0,
            events_skipped_existing=0,
            logs_scanned=0,
        )

    with patch(
        "services.onchain_indexer.continuous_base_indexer.resolve_chain_rpc_url",
        return_value=RPC,
    ):
        with patch(
            "services.onchain_indexer.continuous_base_indexer.fetch_block_number",
            return_value=2000,
        ):
            with patch(
                "services.onchain_indexer.continuous_base_indexer.replay_block_range",
                side_effect=_replay,
            ):
                run_base_indexer_once(
                    db,
                    chain_id=CHAIN_ID,
                    dry_run=True,
                    config=_cfg(start_block=1000, confirmations=12, max_blocks_per_run=5000),
                )

    assert captured["to_block"] == 2000 - 12


def test_max_blocks_per_run_caps_range(db: Session):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    db.query(OnchainIndexerCheckpoint).filter(
        OnchainIndexerCheckpoint.chain_id == CHAIN_ID
    ).delete()
    db.commit()

    captured: dict[str, int] = {}

    def _replay(db_sess, *, from_block, to_block, **kwargs):
        captured["from_block"] = from_block
        captured["to_block"] = to_block
        return MagicMock(
            errors=[],
            events_prepared=0,
            events_inserted=0,
            events_skipped_existing=0,
            logs_scanned=0,
        )

    with patch(
        "services.onchain_indexer.continuous_base_indexer.resolve_chain_rpc_url",
        return_value=RPC,
    ):
        with patch(
            "services.onchain_indexer.continuous_base_indexer.fetch_block_number",
            return_value=10000,
        ):
            with patch(
                "services.onchain_indexer.continuous_base_indexer.replay_block_range",
                side_effect=_replay,
            ):
                run_base_indexer_once(
                    db,
                    chain_id=CHAIN_ID,
                    dry_run=True,
                    config=_cfg(start_block=1000, max_blocks_per_run=25, confirmations=0),
                )

    span = captured["to_block"] - captured["from_block"] + 1
    assert span <= 25
    assert captured["to_block"] <= 10000


def test_chunk_too_large_refused(db: Session):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    db.commit()

    with patch(
        "services.onchain_indexer.continuous_base_indexer.fetch_block_number",
        return_value=200_000,
    ):
        with pytest.raises(IndexerConfigError):
            run_base_indexer_once(
                db,
                chain_id=CHAIN_ID,
                dry_run=True,
                config=_cfg(start_block=0, max_blocks_per_run=60_000, confirmations=0),
            )


def test_disabled_without_force_raises(db: Session):
    with pytest.raises(IndexerNotEnabledError):
        run_base_indexer_once(
            db,
            chain_id=CHAIN_ID,
            dry_run=False,
            config=_cfg(enabled=False),
        )


def test_no_financial_side_effects(db: Session, monkeypatch):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    db.commit()

    monkeypatch.setattr(PersonWalletBalanceRepository, "increment_balance", MagicMock())
    monkeypatch.setattr(PersonWalletDepositRepository, "create", MagicMock())
    monkeypatch.setattr(ReconciliationCorrection, "status", "preview")

    with patch(
        "services.onchain_indexer.continuous_base_indexer.resolve_chain_rpc_url",
        return_value=RPC,
    ):
        with patch(
            "services.onchain_indexer.continuous_base_indexer.fetch_block_number",
            return_value=1010,
        ):
            with patch(
                "services.onchain_indexer.continuous_base_indexer.replay_block_range",
                return_value=MagicMock(
                    errors=[],
                    events_prepared=0,
                    events_inserted=0,
                    events_skipped_existing=0,
                    logs_scanned=0,
                ),
            ):
                run_base_indexer_once(
                    db,
                    chain_id=CHAIN_ID,
                    dry_run=False,
                    config=_cfg(),
                )

    PersonWalletBalanceRepository.increment_balance.assert_not_called()
    PersonWalletDepositRepository.create.assert_not_called()


def test_consumed_raw_event_not_mutated_on_reindex(db: Session):
    from services.onchain_reconciliation.discrepancy_models import (
        ReconciliationCorrection,
        ReconciliationDiscrepancy,
    )
    from services.onchain_reconciliation.discrepancy_repository import DiscrepancyRepository

    pe = make_linked_client(db)
    wallet = _seed_wallet(db, pe)
    tx_hash = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"

    disc, _ = DiscrepancyRepository.upsert_open(
        db,
        person_id=pe.person_id,
        layer="privy",
        discrepancy_type="balance_ledger_vs_onchain",
        severity="P1",
        wallet_address=wallet.address,
        asset="USDC",
    )
    correction = ReconciliationCorrection(
        discrepancy_id=disc.id,
        action="create_missing_deposit_from_raw_event",
        status="applied",
        dry_run=False,
        metadata_json={"raw_onchain_event_id": None},
    )
    db.add(correction)
    db.flush()
    correction_id = correction.id

    row, _ = RawOnChainEventRepository.insert_if_absent(
        db,
        data={
            "chain_id": CHAIN_ID,
            "tx_hash": tx_hash,
            "log_index": 0,
            "wallet_address": wallet.address.lower(),
            "asset": "USDC",
            "amount_raw": 1_000_000,
            "event_type": "erc20_transfer",
        },
    )
    row.consumed_by_correction_id = correction_id
    db.flush()
    db.commit()

    mock_log = _mock_transfer_log(tx_hash=tx_hash, log_index=0, to_wallet=wallet.address)

    def _real_replay(db_sess, **kwargs):
        from services.onchain_indexer.block_range_replay import replay_block_range

        return replay_block_range(db_sess, **kwargs)

    with patch(
        "services.onchain_indexer.continuous_base_indexer.resolve_chain_rpc_url",
        return_value=RPC,
    ):
        with patch(
            "services.onchain_indexer.continuous_base_indexer.fetch_block_number",
            return_value=1012,
        ):
            with patch(
                "services.onchain_indexer.block_range_replay._fetch_transfer_logs",
                return_value=[mock_log],
            ):
                with patch(
                    "services.onchain_indexer.continuous_base_indexer.replay_block_range",
                    side_effect=_real_replay,
                ):
                    run_base_indexer_once(
                        db,
                        chain_id=CHAIN_ID,
                        dry_run=False,
                        config=_cfg(start_block=1000, max_blocks_per_run=12),
                    )
                    db.commit()

    db.refresh(row)
    assert row.consumed_by_correction_id == correction_id
    assert str(row.amount_raw) == "1000000"
