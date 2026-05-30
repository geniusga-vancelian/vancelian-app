"""Typed structures for dry-run scope movement audit."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any
from uuid import UUID


def _dec(v: Decimal | float | str | int) -> str:
    return str(v)


@dataclass(frozen=True)
class ScopeBalance:
    scope: str
    asset: str
    quantity: Decimal

    def to_dict(self) -> dict[str, Any]:
        return {"scope": self.scope, "asset": self.asset.upper(), "quantity": _dec(self.quantity)}


@dataclass(frozen=True)
class ScopeMovement:
    movement_type: str
    source_scope: str
    destination_scope: str
    asset: str
    quantity: Decimal
    reference_id: str
    source_system: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "movement_type": self.movement_type,
            "source_scope": self.source_scope,
            "destination_scope": self.destination_scope,
            "asset": self.asset.upper(),
            "quantity": _dec(self.quantity),
            "reference_id": self.reference_id,
            "source_system": self.source_system,
            "metadata": self.metadata,
        }


@dataclass
class ScopeMovementSet:
    person_id: UUID
    product: str
    movements: list[ScopeMovement] = field(default_factory=list)
    net_by_scope: dict[tuple[str, str], Decimal] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        net = [
            {"scope": scope, "asset": asset.upper(), "quantity": _dec(qty)}
            for (scope, asset), qty in sorted(self.net_by_scope.items())
        ]
        return {
            "person_id": str(self.person_id),
            "product": self.product,
            "movement_count": len(self.movements),
            "movements": [m.to_dict() for m in self.movements],
            "net_by_scope": net,
            "notes": self.notes,
        }


@dataclass
class CurrentPeScopeSnapshot:
    person_id: UUID
    client_id: UUID | None
    trading_available: dict[str, Decimal] = field(default_factory=dict)
    trading_locked_collateral: dict[str, Decimal] = field(default_factory=dict)
    bundle_cash: dict[str, Decimal] = field(default_factory=dict)
    bundle_position: dict[str, Decimal] = field(default_factory=dict)
    vault_position: dict[str, Decimal] = field(default_factory=dict)
    liability: dict[str, Decimal] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        def _scope(d: dict[str, Decimal]) -> dict[str, str]:
            return {k.upper(): _dec(v) for k, v in sorted(d.items())}

        return {
            "person_id": str(self.person_id),
            "client_id": str(self.client_id) if self.client_id else None,
            "trading_available": _scope(self.trading_available),
            "trading_locked_collateral": _scope(self.trading_locked_collateral),
            "bundle_cash": _scope(self.bundle_cash),
            "bundle_position": _scope(self.bundle_position),
            "vault_position": _scope(self.vault_position),
            "liability": _scope(self.liability),
        }


@dataclass
class ScopeGap:
    gap_type: str
    asset: str
    expected_scope: str
    expected_quantity: Decimal
    current_quantity: Decimal
    severity: str = "gap"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_type": self.gap_type,
            "asset": self.asset.upper(),
            "expected_scope": self.expected_scope,
            "expected_quantity": _dec(self.expected_quantity),
            "current_quantity": _dec(self.current_quantity),
            "severity": self.severity,
            "metadata": self.metadata,
        }


@dataclass
class DoubleCountingRisk:
    risk_type: str
    asset: str
    message: str
    severity: str = "warning"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self) | {"asset": self.asset.upper()}
