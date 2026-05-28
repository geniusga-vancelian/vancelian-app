"""Indexer continu Base — raw_onchain_events uniquement (Phase 6)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from services.privy_wallet.evm_chain_config import resolve_chain_rpc_url
from services.privy_wallet.evm_rpc_client import fetch_block_number

from .block_range_replay import (
    MAX_BLOCK_RANGE,
    effective_block_chunk,
    load_monitored_wallet_addresses,
    replay_block_range,
)
from .checkpoint_repository import CheckpointRepository
from .indexer_config import (
    INDEXER_NAME_BASE_CONTINUOUS,
    BaseIndexerConfig,
)
from .native_block_scan import scan_native_incoming_transfers

logger = logging.getLogger(__name__)


class IndexerNotEnabledError(RuntimeError):
    """Écriture refusée : ONCHAIN_INDEXER_BASE_ENABLED=false."""


class IndexerConfigError(ValueError):
    pass


@dataclass
class ContinuousIndexerRunResult:
    chain_id: int
    dry_run: bool
    enabled: bool
    from_block: int | None = None
    to_block: int | None = None
    head_block: int | None = None
    confirmations: int = 0
    wallets_monitored: int = 0
    chunks_processed: int = 0
    erc20: dict[str, Any] = field(default_factory=dict)
    native: dict[str, Any] | None = None
    checkpoint_before: int | None = None
    checkpoint_after: int | None = None
    status: str = "idle"
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "dry_run": self.dry_run,
            "enabled": self.enabled,
            "from_block": self.from_block,
            "to_block": self.to_block,
            "head_block": self.head_block,
            "confirmations": self.confirmations,
            "wallets_monitored": self.wallets_monitored,
            "chunks_processed": self.chunks_processed,
            "erc20": self.erc20,
            "native": self.native,
            "checkpoint_before": self.checkpoint_before,
            "checkpoint_after": self.checkpoint_after,
            "status": self.status,
            "errors": self.errors,
        }


def _resolve_from_block(
    checkpoint_last: int | None,
    *,
    start_block: int | None,
) -> int:
    if checkpoint_last is not None:
        return int(checkpoint_last) + 1
    if start_block is not None:
        return int(start_block)
    raise IndexerConfigError(
        "ONCHAIN_INDEXER_BASE_START_BLOCK requis si aucun checkpoint existant",
    )


def run_base_indexer_once(
    db: Session,
    *,
    chain_id: int,
    dry_run: bool = True,
    config: BaseIndexerConfig | None = None,
    force_write: bool = False,
) -> ContinuousIndexerRunResult:
    """
    Un passage indexer : scan ERC20 (+ natif optionnel), checkpoint par chunk réussi.

    N'écrit jamais dans person_wallet_* ni reconciliation apply.
    """
    cfg = config or BaseIndexerConfig.from_env()
    out = ContinuousIndexerRunResult(
        chain_id=chain_id,
        dry_run=dry_run,
        enabled=cfg.enabled,
        confirmations=cfg.confirmations,
    )

    if not dry_run and not cfg.enabled and not force_write:
        raise IndexerNotEnabledError(
            "ONCHAIN_INDEXER_BASE_ENABLED=false — utilisez --dry-run ou activez l'indexer",
        )

    rpc_url = resolve_chain_rpc_url(chain_id)
    if not rpc_url:
        raise IndexerConfigError(f"RPC non configuré pour chain_id={chain_id}")

    rpc_chunk = effective_block_chunk(rpc_url, cfg.chunk_size)
    monitored = load_monitored_wallet_addresses(db, chain_id=chain_id)
    out.wallets_monitored = len(monitored)

    checkpoint = CheckpointRepository.get(
        db,
        chain_id=chain_id,
        indexer_name=INDEXER_NAME_BASE_CONTINUOUS,
    )
    checkpoint_before = int(checkpoint.last_scanned_block) if checkpoint else None
    out.checkpoint_before = checkpoint_before

    try:
        head_block = fetch_block_number(rpc_url)
    except Exception as exc:
        out.errors.append(f"eth_blockNumber: {exc}")
        out.status = "error"
        if checkpoint and not dry_run:
            CheckpointRepository.mark_error(db, checkpoint, error=str(exc))
        return out

    out.head_block = head_block
    safe_head = max(0, head_block - cfg.confirmations)

    try:
        from_block = _resolve_from_block(checkpoint_before, start_block=cfg.start_block)
    except IndexerConfigError as exc:
        out.errors.append(str(exc))
        out.status = "error"
        return out

    if from_block > safe_head:
        out.status = "idle"
        out.from_block = from_block
        out.to_block = safe_head
        logger.info(
            "indexer.base.idle chain_id=%s from=%s head=%s confirmations=%s",
            chain_id,
            from_block,
            safe_head,
            cfg.confirmations,
        )
        return out

    block_span = safe_head - from_block + 1
    if block_span > cfg.max_blocks_per_run:
        to_block = from_block + cfg.max_blocks_per_run - 1
    else:
        to_block = safe_head

    if to_block - from_block + 1 > MAX_BLOCK_RANGE:
        raise IndexerConfigError(
            f"Plage {to_block - from_block + 1} blocs > max {MAX_BLOCK_RANGE} par exécution",
        )

    out.from_block = from_block
    out.to_block = to_block

    if not checkpoint and not dry_run:
        initial = (cfg.start_block or from_block) - 1
        checkpoint = CheckpointRepository.get_or_create(
            db,
            chain_id=chain_id,
            indexer_name=INDEXER_NAME_BASE_CONTINUOUS,
            initial_block=initial,
        )
        checkpoint_before = initial
        out.checkpoint_before = checkpoint_before
    elif not checkpoint and dry_run:
        checkpoint = None

    erc20_totals = {
        "events_prepared": 0,
        "events_inserted": 0,
        "events_skipped_existing": 0,
        "logs_scanned": 0,
    }
    native_totals: dict[str, Any] | None = None

    cursor = from_block
    while cursor <= to_block:
        chunk_end = min(cursor + rpc_chunk - 1, to_block)
        logger.info(
            "indexer.base.chunk chain_id=%s blocks=%s-%s dry_run=%s wallets=%s",
            chain_id,
            cursor,
            chunk_end,
            dry_run,
            len(monitored),
        )

        try:
            erc20_result = replay_block_range(
                db,
                chain_id=chain_id,
                from_block=cursor,
                to_block=chunk_end,
                dry_run=dry_run,
                block_chunk=rpc_chunk,
                wallet_addresses=monitored if monitored else None,
            )
        except Exception as exc:
            out.errors.append(f"erc20 [{cursor}-{chunk_end}]: {exc}")
            if checkpoint and not dry_run:
                CheckpointRepository.mark_error(
                    db,
                    checkpoint,
                    error=str(exc),
                    failed_block=cursor,
                )
            out.status = "error"
            break

        if erc20_result.errors:
            out.errors.extend(erc20_result.errors)
            if checkpoint and not dry_run:
                CheckpointRepository.mark_error(
                    db,
                    checkpoint,
                    error=erc20_result.errors[0],
                    failed_block=cursor,
                )
            out.status = "error"
            break

        erc20_totals["events_prepared"] += erc20_result.events_prepared
        erc20_totals["events_inserted"] += erc20_result.events_inserted
        erc20_totals["events_skipped_existing"] += erc20_result.events_skipped_existing
        erc20_totals["logs_scanned"] += erc20_result.logs_scanned

        native_result = None
        if cfg.native_enabled:
            native_result = scan_native_incoming_transfers(
                db,
                chain_id=chain_id,
                rpc_url=rpc_url,
                from_block=cursor,
                to_block=chunk_end,
                monitored_wallets=monitored,
                dry_run=dry_run,
            )
            if native_result.errors:
                out.errors.extend(native_result.errors)
                if checkpoint and not dry_run:
                    CheckpointRepository.mark_error(
                        db,
                        checkpoint,
                        error=native_result.errors[0],
                        failed_block=cursor,
                    )
                out.status = "error"
                break
            if native_totals is None:
                native_totals = {
                    "events_prepared": 0,
                    "events_inserted": 0,
                    "events_skipped_existing": 0,
                    "blocks_scanned": 0,
                }
            native_totals["events_prepared"] += native_result.events_prepared
            native_totals["events_inserted"] += native_result.events_inserted
            native_totals["events_skipped_existing"] += native_result.events_skipped_existing
            native_totals["blocks_scanned"] += native_result.blocks_scanned

        if not dry_run:
            if checkpoint is None:
                checkpoint = CheckpointRepository.get_or_create(
                    db,
                    chain_id=chain_id,
                    indexer_name=INDEXER_NAME_BASE_CONTINUOUS,
                    initial_block=(cfg.start_block or from_block) - 1,
                )
            CheckpointRepository.advance_after_chunk(
                db,
                checkpoint,
                last_scanned_block=chunk_end,
                status="ok",
                run_metadata={
                    "last_chunk": {"from": cursor, "to": chunk_end},
                    "erc20_inserted": erc20_result.events_inserted,
                    "native_inserted": (
                        native_result.events_inserted if native_result else 0
                    ),
                },
            )
            out.checkpoint_after = chunk_end

        out.chunks_processed += 1
        cursor = chunk_end + 1

    out.erc20 = erc20_totals
    out.native = native_totals
    if out.status != "error":
        out.status = "ok" if out.chunks_processed > 0 else "idle"
        if checkpoint and not dry_run and out.checkpoint_after is None:
            out.checkpoint_after = int(checkpoint.last_scanned_block)

    return out
