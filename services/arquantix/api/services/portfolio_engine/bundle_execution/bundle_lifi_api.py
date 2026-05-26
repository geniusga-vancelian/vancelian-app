"""API helpers — reconstituer un ``ExecutionLeg`` depuis un swap bundle."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from services.portfolio_engine.bundle_execution.types import ExecutionLeg


def leg_from_swap_audit(swap) -> ExecutionLeg | None:
    audit = swap.audit_log
    if not isinstance(audit, list):
        return None
    ctx: dict = {}
    for entry in audit:
        if isinstance(entry, dict) and entry.get("event") == "bundle_leg_context":
            ctx = entry
            break
    if not ctx.get("portfolio_id"):
        return None
    action = str(ctx.get("leg_action") or "allocation")
    bundle_action = str(ctx.get("bundle_action") or "allocation")
    return ExecutionLeg(
        leg_id=str(ctx.get("leg_id") or swap.id),
        portfolio_id=UUID(str(ctx["portfolio_id"])),
        client_id=UUID(str(ctx["client_id"])),
        action=action,
        from_asset=str(swap.from_asset),
        to_asset=str(swap.to_asset),
        amount_from=Decimal(str(swap.amount_in)),
        batch_id=str(ctx.get("batch_id") or ""),
        bundle_action=str(bundle_action),
        chain="base",
        metadata={
            k: ctx[k]
            for k in ("entry_instrument_id", "target_instrument_id")
            if k in ctx
        },
    )
