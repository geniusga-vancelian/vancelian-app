"""WAC / P&L à partir des exécutions normalisées (FX historiques figés)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.cost_basis.repository import CostBasisExecutionRepository

D2 = Decimal("0.01")
D8 = Decimal("0.00000001")


def _dec(v: object) -> Decimal:
    return Decimal(str(v))


def _f2(v: Decimal) -> float:
    return float(v.quantize(D2, rounding=ROUND_HALF_UP))


def _f8(v: Decimal) -> float:
    return float(v.quantize(D8, rounding=ROUND_HALF_UP))


@dataclass
class CostBasisWacResult:
    avg_buy_price_eur: Decimal
    avg_buy_price_usd: Decimal
    cost_basis_eur: Decimal
    cost_basis_usd: Decimal
    unrealized_pnl_eur: Decimal
    unrealized_pnl_usd: Decimal
    realized_pnl_eur: Decimal
    realized_pnl_usd: Decimal
    total_pnl_eur: Decimal
    total_pnl_usd: Decimal
    remaining_quantity: Decimal
    trade_count: int
    buy_count: int
    sell_count: int
    first_trade_at: Optional[datetime]
    last_trade_at: Optional[datetime]
    total_bought: Decimal
    total_sold: Decimal
    avg_sell_price_eur: Optional[Decimal]
    avg_sell_price_usd: Optional[Decimal]


def compute_wac_from_executions(
    db: Session,
    client_id: UUID,
    asset: str,
    *,
    position_size: Decimal,
    current_price_eur: Decimal,
    current_price_usd: Decimal,
    portfolio_scope: Optional[str] = None,
    portfolio_id: Optional[str] = None,
) -> CostBasisWacResult:
    """Calcule PRU et P&L depuis ``cost_basis_executions`` uniquement."""
    events = CostBasisExecutionRepository().list_for_client_asset(
        db,
        client_id,
        asset,
        portfolio_scope=portfolio_scope,
        portfolio_id=portfolio_id,
    )

    remaining_qty = Decimal("0")
    remaining_cost_eur = Decimal("0")
    remaining_cost_usd = Decimal("0")
    realized_eur = Decimal("0")
    realized_usd = Decimal("0")
    buy_count = 0
    sell_count = 0
    total_bought = Decimal("0")
    total_sold = Decimal("0")
    disposal_notional_eur = Decimal("0")
    disposal_notional_usd = Decimal("0")
    first_trade_at: Optional[datetime] = None
    last_trade_at: Optional[datetime] = None

    for ev in events:
        qty = _dec(ev.quantity)
        if first_trade_at is None:
            first_trade_at = ev.executed_at
        last_trade_at = ev.executed_at

        kind = str(ev.event_kind).lower()
        if kind == "acquisition":
            buy_count += 1
            total_bought += qty
            remaining_qty += qty
            remaining_cost_eur += _dec(ev.execution_notional_eur)
            remaining_cost_usd += _dec(ev.execution_notional_usdc)
        elif kind == "disposal":
            sell_count += 1
            total_sold += qty
            disposal_notional_eur += _dec(ev.execution_notional_eur)
            disposal_notional_usd += _dec(ev.execution_notional_usdc)
            if remaining_qty <= 0:
                continue
            avg_eur = remaining_cost_eur / remaining_qty
            avg_usd = remaining_cost_usd / remaining_qty
            cost_eur = (qty * avg_eur).quantize(D2, rounding=ROUND_HALF_UP)
            cost_usd = (qty * avg_usd).quantize(D2, rounding=ROUND_HALF_UP)
            proceeds_eur = _dec(ev.execution_notional_eur)
            proceeds_usd = _dec(ev.execution_notional_usdc)
            realized_eur += proceeds_eur - cost_eur
            realized_usd += proceeds_usd - cost_usd
            remaining_cost_eur -= cost_eur
            remaining_cost_usd -= cost_usd
            remaining_qty -= qty

    qty_for_basis = position_size if position_size > 0 else remaining_qty
    avg_eur = (remaining_cost_eur / remaining_qty) if remaining_qty > 0 else Decimal("0")
    avg_usd = (remaining_cost_usd / remaining_qty) if remaining_qty > 0 else Decimal("0")

    if qty_for_basis > 0 and remaining_qty > 0:
        scale = qty_for_basis / remaining_qty
        cost_basis_eur = (remaining_cost_eur * scale).quantize(D2, rounding=ROUND_HALF_UP)
        cost_basis_usd = (remaining_cost_usd * scale).quantize(D2, rounding=ROUND_HALF_UP)
    else:
        cost_basis_eur = Decimal("0")
        cost_basis_usd = Decimal("0")

    current_value_eur = (qty_for_basis * current_price_eur).quantize(D2, rounding=ROUND_HALF_UP)
    current_value_usd = (qty_for_basis * current_price_usd).quantize(D2, rounding=ROUND_HALF_UP)
    unrealized_eur = current_value_eur - cost_basis_eur
    unrealized_usd = current_value_usd - cost_basis_usd
    total_eur = unrealized_eur + realized_eur
    total_usd = unrealized_usd + realized_usd

    avg_sell_eur = (disposal_notional_eur / total_sold) if total_sold > 0 else None
    avg_sell_usd = (disposal_notional_usd / total_sold) if total_sold > 0 else None

    return CostBasisWacResult(
        avg_buy_price_eur=avg_eur,
        avg_buy_price_usd=avg_usd,
        cost_basis_eur=cost_basis_eur,
        cost_basis_usd=cost_basis_usd,
        unrealized_pnl_eur=unrealized_eur,
        unrealized_pnl_usd=unrealized_usd,
        realized_pnl_eur=realized_eur,
        realized_pnl_usd=realized_usd,
        total_pnl_eur=total_eur,
        total_pnl_usd=total_usd,
        remaining_quantity=remaining_qty,
        trade_count=len(events),
        buy_count=buy_count,
        sell_count=sell_count,
        first_trade_at=first_trade_at,
        last_trade_at=last_trade_at,
        total_bought=total_bought,
        total_sold=total_sold,
        avg_sell_price_eur=avg_sell_eur,
        avg_sell_price_usd=avg_sell_usd,
    )
