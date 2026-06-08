"""Planification des legs d'allocation bundle (Phase 5A)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.allocations.models import TargetAllocation
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument

from .allocation_config import compute_allocatable_amount
from .lifi_base_config import normalize_bundle_asset


@dataclass(frozen=True)
class PlannedAllocationLeg:
    target_asset: str
    lifi_target: str
    target_instrument_id: UUID
    target_weight: Decimal
    alloc_entry_amount: Decimal
    ext_ref: str


def plan_allocation_legs(
    db: Session,
    *,
    allocations: list[TargetAllocation],
    fund_amount: Decimal,
    batch_id: str,
    normalize_asset_fn,
) -> tuple[list[PlannedAllocationLeg], Decimal, Decimal, Decimal]:
    """Calcule les montants legs après buffer d'exécution.

    Returns:
        (planned_legs, allocatable_amount, execution_buffer, cash_available_for_plan)
    """
    allocatable, buffer = compute_allocatable_amount(fund_amount)
    cash_available = allocatable
    planned: list[PlannedAllocationLeg] = []

    for alloc in allocations:
        instrument = alloc.instrument
        if instrument is None:
            instrument = db.query(Instrument).filter(
                Instrument.id == alloc.instrument_id
            ).first()
        if instrument is None:
            continue
        asset_obj = db.query(Asset).filter(Asset.id == instrument.asset_id).first()
        if asset_obj is None:
            continue

        target_asset = normalize_asset_fn(asset_obj.symbol.upper())
        lifi_target = normalize_bundle_asset(target_asset)

        alloc_entry_amount = (allocatable * alloc.target_weight).quantize(
            Decimal("0.000001"), rounding=ROUND_DOWN,
        )
        if alloc_entry_amount <= 0 or alloc_entry_amount > cash_available:
            continue

        ext_ref = f"bundle-alloc-{batch_id}-{lifi_target}"
        planned.append(
            PlannedAllocationLeg(
                target_asset=target_asset,
                lifi_target=lifi_target,
                target_instrument_id=alloc.instrument_id,
                target_weight=alloc.target_weight,
                alloc_entry_amount=alloc_entry_amount,
                ext_ref=ext_ref,
            )
        )
        cash_available -= alloc_entry_amount

    return planned, allocatable, buffer, cash_available


def plan_recovery_allocation_legs(
    db: Session,
    *,
    allocations: list[TargetAllocation],
    fund_amount: Decimal,
    batch_id: str,
    normalize_asset_fn,
    skip_lifi_targets: set[str],
    only_lifi_targets: set[str] | None = None,
) -> tuple[list[PlannedAllocationLeg], Decimal, Decimal, Decimal]:
    """Plan buy-only recovery legs — cash restant vers cibles non encore confirmées.

    ``skip_lifi_targets`` : assets déjà alloués (swaps CONFIRMED) — jamais re-quotés.
    ``only_lifi_targets`` : si fourni, limite aux legs expirés / manquants (ex. CBETH seul).
    """
    eligible: list[tuple[TargetAllocation, str, str]] = []
    for alloc in allocations:
        instrument = alloc.instrument
        if instrument is None:
            instrument = db.query(Instrument).filter(
                Instrument.id == alloc.instrument_id
            ).first()
        if instrument is None:
            continue
        asset_obj = db.query(Asset).filter(Asset.id == instrument.asset_id).first()
        if asset_obj is None:
            continue

        target_asset = normalize_asset_fn(asset_obj.symbol.upper())
        lifi_target = normalize_bundle_asset(target_asset)
        if lifi_target in skip_lifi_targets:
            continue
        if only_lifi_targets is not None and lifi_target not in only_lifi_targets:
            continue
        eligible.append((alloc, target_asset, lifi_target))

    if not eligible:
        return [], Decimal("0"), Decimal("0"), Decimal("0")

    weight_sum = sum((a.target_weight for a, _, _ in eligible), Decimal("0"))
    if weight_sum <= 0:
        return [], Decimal("0"), Decimal("0"), Decimal("0")

    allocatable, buffer = compute_allocatable_amount(fund_amount)
    cash_available = allocatable
    planned: list[PlannedAllocationLeg] = []

    for alloc, target_asset, lifi_target in eligible:
        normalized_weight = (alloc.target_weight / weight_sum).quantize(
            Decimal("0.000001"), rounding=ROUND_DOWN,
        )
        alloc_entry_amount = (allocatable * normalized_weight).quantize(
            Decimal("0.000001"), rounding=ROUND_DOWN,
        )
        if alloc_entry_amount <= 0 or alloc_entry_amount > cash_available:
            continue

        ext_ref = f"bundle-recovery-{batch_id}-{lifi_target}"
        planned.append(
            PlannedAllocationLeg(
                target_asset=target_asset,
                lifi_target=lifi_target,
                target_instrument_id=alloc.instrument_id,
                target_weight=normalized_weight,
                alloc_entry_amount=alloc_entry_amount,
                ext_ref=ext_ref,
            )
        )
        cash_available -= alloc_entry_amount

    return planned, allocatable, buffer, cash_available
