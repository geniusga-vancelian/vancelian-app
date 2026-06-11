"""Trade primitive contracts (ADR 008)."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

TradeExecutionStatus = Literal[
    "awaiting_signature",
    "submitted",
    "confirmed",
    "pending",
    "failed",
]


@dataclass(frozen=True)
class TradeReviewSnapshot:
    review_amount_in: str
    review_estimated_receive: str


@dataclass(frozen=True)
class TradeRequest:
    wallet_from_id: UUID
    wallet_to_id: UUID
    instrument_from_id: UUID
    instrument_to_id: UUID
    quantity_from: Decimal
    correlation_id: UUID
    client_id: UUID
    portfolio_id: UUID
    from_asset: str
    to_asset: str
    leg_id: str
    batch_id: str
    bundle_action: str
    leg_action: str
    chain: str | None = "base"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TradeExecutionResult:
    swap_id: UUID
    leg_id: str
    status: TradeExecutionStatus
    from_asset: str
    to_asset: str
    amount_from: Decimal
    amount_to: Decimal | None = None
    tx_hash: str | None = None
    requires_client_signature: bool = False
    raw: dict[str, Any] = field(default_factory=dict)
