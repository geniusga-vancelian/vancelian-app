"""Repository checkpoints indexer (Phase 6)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .indexer_config import INDEXER_NAME_BASE_CONTINUOUS
from .models import OnchainIndexerCheckpoint


class CheckpointRepository:

    @staticmethod
    def get(
        db: Session,
        *,
        chain_id: int,
        indexer_name: str = INDEXER_NAME_BASE_CONTINUOUS,
    ) -> OnchainIndexerCheckpoint | None:
        return (
            db.query(OnchainIndexerCheckpoint)
            .filter(
                OnchainIndexerCheckpoint.chain_id == chain_id,
                OnchainIndexerCheckpoint.indexer_name == indexer_name,
            )
            .first()
        )

    @staticmethod
    def get_or_create(
        db: Session,
        *,
        chain_id: int,
        indexer_name: str = INDEXER_NAME_BASE_CONTINUOUS,
        initial_block: int = 0,
    ) -> OnchainIndexerCheckpoint:
        row = CheckpointRepository.get(db, chain_id=chain_id, indexer_name=indexer_name)
        if row is not None:
            return row
        row = OnchainIndexerCheckpoint(
            chain_id=chain_id,
            indexer_name=indexer_name,
            last_scanned_block=initial_block,
            status="idle",
            metadata_json={},
        )
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def advance_after_chunk(
        db: Session,
        row: OnchainIndexerCheckpoint,
        *,
        last_scanned_block: int,
        status: str = "ok",
        run_metadata: dict[str, Any] | None = None,
    ) -> OnchainIndexerCheckpoint:
        row.last_scanned_block = int(last_scanned_block)
        row.status = status
        base = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        row.metadata_json = {
            **base,
            **(run_metadata or {}),
            "last_run_at": datetime.now(timezone.utc).isoformat(),
        }
        row.updated_at = datetime.now(timezone.utc)
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def mark_error(
        db: Session,
        row: OnchainIndexerCheckpoint,
        *,
        error: str,
        failed_block: int | None = None,
    ) -> None:
        base = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        row.status = "error"
        row.metadata_json = {
            **base,
            "last_error": error,
            "last_error_at": datetime.now(timezone.utc).isoformat(),
            "failed_block": failed_block,
        }
        row.updated_at = datetime.now(timezone.utc)
        db.add(row)
        db.flush()
