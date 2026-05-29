"""Conversion cost_basis_executions → événements wallet_history (charts P&L)."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.cost_basis.models import CostBasisExecution
from services.cost_basis.repository import CostBasisExecutionRepository

TradeEvent = tuple[datetime, str, str, Decimal, Decimal, Optional[Decimal]]


def _normalize_ts(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts


def list_executions_for_history(
    db: Session,
    client_id: UUID,
    *,
    portfolio_scope: Optional[str] = None,
    portfolio_id: Optional[str] = None,
    asset: Optional[str] = None,
) -> list[CostBasisExecution]:
    q = db.query(CostBasisExecution).filter(CostBasisExecution.client_id == client_id)
    if asset:
        q = q.filter(CostBasisExecution.position_asset == asset.upper())
    if portfolio_scope == "bundle" and portfolio_id:
        q = q.filter(
            CostBasisExecution.portfolio_scope == "bundle",
            CostBasisExecution.portfolio_id == portfolio_id,
        )
    elif portfolio_scope == "direct":
        q = q.filter(CostBasisExecution.portfolio_scope == "direct")
    elif portfolio_scope in (None, "global"):
        q = q.filter(
            (CostBasisExecution.portfolio_scope.is_(None))
            | (CostBasisExecution.portfolio_scope.in_(("global", "direct")))
        )
    return q.order_by(CostBasisExecution.executed_at.asc()).all()


def executions_to_trade_events(
    executions: list[CostBasisExecution],
    *,
    use_eur: bool,
) -> list[TradeEvent]:
    """Mappe acquisition/disposal vers buy/sell pour ``_build_performance_value``."""
    events: list[TradeEvent] = []
    for ev in executions:
        ts = _normalize_ts(ev.executed_at)
        qty = Decimal(str(ev.quantity))
        if qty <= 0:
            continue
        kind = str(ev.event_kind).lower()
        if kind == "acquisition":
            side = "buy"
            price = Decimal(str(ev.execution_price_eur if use_eur else ev.execution_price_usdc))
            net_ref = None
        elif kind == "disposal":
            side = "sell"
            price = Decimal(str(ev.execution_price_eur if use_eur else ev.execution_price_usdc))
            net_ref = Decimal(str(ev.execution_notional_eur if use_eur else ev.execution_notional_usdc))
        else:
            continue
        events.append((ts, side, str(ev.position_asset).upper(), qty, price, net_ref))
    events.sort(key=lambda e: e[0])
    return events


def has_execution_history(
    db: Session,
    client_id: UUID,
    *,
    portfolio_scope: Optional[str] = None,
    portfolio_id: Optional[str] = None,
    asset: Optional[str] = None,
) -> bool:
    q = db.query(CostBasisExecution.id).filter(CostBasisExecution.client_id == client_id)
    if asset:
        q = q.filter(CostBasisExecution.position_asset == asset.upper())
    if portfolio_scope == "bundle" and portfolio_id:
        q = q.filter(
            CostBasisExecution.portfolio_scope == "bundle",
            CostBasisExecution.portfolio_id == portfolio_id,
        )
    elif portfolio_scope == "direct":
        q = q.filter(CostBasisExecution.portfolio_scope == "direct")
    elif portfolio_scope in (None, "global"):
        q = q.filter(
            (CostBasisExecution.portfolio_scope.is_(None))
            | (CostBasisExecution.portfolio_scope.in_(("global", "direct")))
        )
    return q.limit(1).first() is not None
