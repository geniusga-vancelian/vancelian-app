"""Configuration indexer continu Base (Phase 6)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from .chain_config import CHAIN_BASE

INDEXER_NAME_BASE_CONTINUOUS = "base_continuous"

DEFAULT_CHUNK_SIZE = 10
DEFAULT_CONFIRMATIONS = 12
DEFAULT_MAX_BLOCKS_PER_RUN = 500


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name, "").strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return int(raw)


@dataclass(frozen=True)
class BaseIndexerConfig:
    enabled: bool
    start_block: int | None
    chunk_size: int
    confirmations: int
    max_blocks_per_run: int
    native_enabled: bool

    @classmethod
    def from_env(cls) -> BaseIndexerConfig:
        start_raw = os.getenv("ONCHAIN_INDEXER_BASE_START_BLOCK", "").strip()
        start_block = int(start_raw) if start_raw else None
        return cls(
            enabled=_env_bool("ONCHAIN_INDEXER_BASE_ENABLED", default=False),
            start_block=start_block,
            chunk_size=max(1, _env_int("ONCHAIN_INDEXER_BASE_CHUNK_SIZE", DEFAULT_CHUNK_SIZE)),
            confirmations=max(0, _env_int("ONCHAIN_INDEXER_BASE_CONFIRMATIONS", DEFAULT_CONFIRMATIONS)),
            max_blocks_per_run=max(
                1,
                _env_int("ONCHAIN_INDEXER_BASE_MAX_BLOCKS_PER_RUN", DEFAULT_MAX_BLOCKS_PER_RUN),
            ),
            native_enabled=_env_bool("ONCHAIN_INDEXER_BASE_NATIVE_ENABLED", default=False),
        )


def default_chain_id() -> int:
    return CHAIN_BASE
