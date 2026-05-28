"""Execution leg contracts for bundle invest / rebalance."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

ExecutionAction = Literal[
    "funding",
    "allocation",
    "rebalance_sell",
    "rebalance_buy",
    "withdraw_sell",
]

ExecutionStatus = Literal["completed", "partial", "failed", "pending"]


@dataclass(frozen=True)
class ExecutionLeg:
    leg_id: str
    portfolio_id: UUID
    client_id: UUID
    action: ExecutionAction
    from_asset: str
    to_asset: str
    amount_from: Decimal
    batch_id: str
    bundle_action: str
    chain: str | None = None
    currency: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionQuote:
    leg_id: str
    from_asset: str
    to_asset: str
    amount_from: Decimal
    estimated_amount_to: Decimal
    reference_value_net: Decimal | None = None
    fees: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionResult:
    leg_id: str
    status: ExecutionStatus
    from_asset: str
    to_asset: str
    amount_from: Decimal
    amount_to: Decimal | None = None
    tx_hash: str | None = None
    provider_order_id: str | None = None
    fees: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    def to_buy_legacy_dict(self) -> dict[str, Any]:
        """Shape expected by ``BundleOrchestrator`` after fiat funding."""
        out = dict(self.raw)
        out.setdefault("amount_crypto", self.amount_to)
        out.setdefault("order_id", self.provider_order_id)
        out.setdefault("status", self.status)
        return out

    def to_swap_legacy_dict(self) -> dict[str, Any]:
        """Shape expected by orchestrators after a swap leg."""
        out = dict(self.raw)
        if self.amount_to is not None:
            out.setdefault("amount_to", self.amount_to)
        out.setdefault("status", self.status)
        return out
