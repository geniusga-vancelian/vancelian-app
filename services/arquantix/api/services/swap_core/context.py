"""ADR 007 — Swap Core context (quote / execute)."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID


class QuotePolicy(str, Enum):
    STANDALONE = "standalone"
    BUNDLE_BASE = "bundle_base"


@dataclass(frozen=True)
class SwapQuoteContext:
    """Paramètres normalisés pour ``SwapCore.quote``."""

    person_id: UUID
    from_asset: str
    to_asset: str
    amount: str
    policy: QuotePolicy = QuotePolicy.STANDALONE
    from_chain: str | None = None
    to_chain: str | None = None
    slippage_bps: int | None = None
    signing_wallet_mode: str | None = None
    signing_wallet_address: str | None = None
    leg_action: str | None = None
    extra_audit: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ResolvedQuoteTokens:
    from_asset: str
    to_asset: str
    from_chain: str
    to_chain: str
    from_lifi_chain_id: int
    to_lifi_chain_id: int
    from_token_address: str
    to_token_address: str
    from_decimals: int
    to_decimals: int
    parsed_amount: Decimal
    slippage_bps: int
