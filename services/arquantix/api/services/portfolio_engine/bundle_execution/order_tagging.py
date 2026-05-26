"""Tag ``exchange_orders`` metadata for bundle execution legs."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.exchange.models import ExchangeOrder

from .types import ExecutionLeg


def tag_order_by_external_reference(
    db: Session,
    *,
    external_reference: str,
    leg: ExecutionLeg,
    execution_provider: str,
    bundle_action: str | None = None,
) -> None:
    order = (
        db.query(ExchangeOrder)
        .filter(ExchangeOrder.external_reference == external_reference)
        .first()
    )
    if order is None:
        return
    meta = dict(order.metadata_ or {})
    meta["bundle_id"] = str(leg.portfolio_id)
    meta["bundle_batch_id"] = leg.batch_id
    meta["bundle_action"] = bundle_action or leg.bundle_action
    meta["portfolio_scope"] = "bundle"
    meta["portfolio_id"] = str(leg.portfolio_id)
    meta["execution_provider"] = execution_provider
    meta["batch_id"] = leg.batch_id
    meta["leg_id"] = leg.leg_id
    order.metadata_ = meta
    db.flush()


def tag_swap_leg_orders(
    db: Session,
    *,
    external_reference: str,
    leg: ExecutionLeg,
    execution_provider: str,
    bundle_action: str | None = None,
) -> None:
    """Tag both sell and buy legs of an exchange swap."""
    tag_order_by_external_reference(
        db,
        external_reference=f"{external_reference}-sell",
        leg=leg,
        execution_provider=execution_provider,
        bundle_action=bundle_action,
    )
    tag_order_by_external_reference(
        db,
        external_reference=f"{external_reference}-buy",
        leg=leg,
        execution_provider=execution_provider,
        bundle_action=bundle_action,
    )
