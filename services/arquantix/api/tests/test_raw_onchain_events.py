"""Tests raw_onchain_events + indexer idempotent (Phase 3)."""
from __future__ import annotations

import uuid

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session

from database import engine
from services.onchain_indexer.repository import RawOnChainEventRepository


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
    not _migration_161_applied(),
    reason="Appliquer `alembic upgrade head` (révision 161) pour raw_onchain_events.",
)


def _sample_event_data(*, tx_hash: str | None = None, log_index: int = 0) -> dict:
    tx = tx_hash or f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"
    return {
        "chain_id": 8453,
        "block_number": 12_345_678,
        "tx_hash": tx,
        "log_index": log_index,
        "contract_address": "0x833589fcd6ede6e08f4c7c32d4f71b54bda02913",
        "event_type": "erc20_transfer",
        "wallet_address": "0x742d35cc6634c0532925a3b844bc454e4438f44e",
        "asset": "USDC",
        "amount_raw": 1_000_000,
        "payload_json": {"test": True},
    }


def test_insert_raw_onchain_event_idempotent(db: Session):
    data = _sample_event_data()
    row1, created1 = RawOnChainEventRepository.insert_if_absent(db, data=data)
    row2, created2 = RawOnChainEventRepository.insert_if_absent(db, data=data)

    assert created1 is True
    assert created2 is False
    assert row1.id == row2.id
    assert row1.tx_hash == data["tx_hash"].lower()


def test_same_tx_hash_log_index_single_row(db: Session):
    tx_hash = f"0x{uuid.uuid4().hex}{uuid.uuid4().hex[:24]}"
    _, c1 = RawOnChainEventRepository.insert_if_absent(
        db,
        data=_sample_event_data(tx_hash=tx_hash, log_index=2),
    )
    _, c2 = RawOnChainEventRepository.insert_if_absent(
        db,
        data=_sample_event_data(tx_hash=tx_hash, log_index=2),
    )
    assert c1 is True
    assert c2 is False
