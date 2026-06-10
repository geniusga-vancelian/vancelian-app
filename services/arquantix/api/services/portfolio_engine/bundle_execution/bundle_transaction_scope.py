"""Périmètre des transactions bundle vs Mon Trading (self-trading)."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.transaction_intents.bundle_intent_sync import bundle_context_from_swap_audit

# Mouvements internes au bundle — visibles dans l'historique du bundle, pas Mon Trading.
_BUNDLE_INTERNAL_ACTIONS = frozenset(
    {
        "allocation",
        "rebalance",
        "rebalance_v3",
        "rebalance_buy",
        "rebalance_sell",
        "withdraw_sell",
        "funding",
        "withdraw",
    }
)


def bundle_context_for_swap(swap: Any) -> dict[str, Any] | None:
    ctx = bundle_context_from_swap_audit(swap)
    if not isinstance(ctx, dict):
        return None
    if not ctx.get("bundle_execution"):
        return None
    return ctx


def is_bundle_internal_swap(swap: Any) -> bool:
    """Swap LI.FI exécuté dans le cadre d'un batch bundle (allocation, rebalance, retrait interne).

    Signal principal : ``bundle_execution=true`` dans ``bundle_leg_context`` (via
    ``bundle_context_for_swap``). Un ``batch_id`` seul, sans ce flag, n'est jamais
    considéré comme opération interne bundle.
    """
    ctx = bundle_context_for_swap(swap)
    if ctx is None:
        return False
    action = str(ctx.get("bundle_action") or ctx.get("leg_action") or "").strip().lower()
    if action in _BUNDLE_INTERNAL_ACTIONS:
        return True
    # Leg bundle taggé mais action non reconnue — reste interne si batch + execution flag.
    return bool(str(ctx.get("batch_id") or "").strip())


def swap_has_strong_bundle_batch_context(swap: Any) -> bool:
    """Signal fort batch+portfolio dans l'audit — exclusion self-trading (Phase 6A)."""
    ctx = bundle_context_from_swap_audit(swap)
    if not isinstance(ctx, dict):
        return False
    if ctx.get("bundle_execution") is True:
        return True
    batch = str(ctx.get("batch_id") or "").strip()
    portfolio = str(ctx.get("portfolio_id") or "").strip()
    return bool(batch and portfolio)


def is_bundle_portfolio_swap(swap: Any, *, portfolio_id: str | None = None) -> bool:
    """Swap visible dans l'historique bundle (tag complet ou contexte batch fort)."""
    if is_bundle_internal_swap(swap):
        ctx = bundle_context_for_swap(swap) or bundle_context_from_swap_audit(swap) or {}
        if portfolio_id and str(ctx.get("portfolio_id") or "") != portfolio_id:
            return False
        return True
    if not swap_has_strong_bundle_batch_context(swap):
        return False
    ctx = bundle_context_from_swap_audit(swap) or {}
    if portfolio_id and str(ctx.get("portfolio_id") or "") != portfolio_id:
        return False
    return True


def bundle_portfolio_id_from_swap(swap: Any) -> str | None:
    ctx = bundle_context_for_swap(swap)
    if ctx is None:
        return None
    pid = str(ctx.get("portfolio_id") or "").strip()
    return pid or None


def is_bundle_scoped_exchange_order(order: Any) -> bool:
    meta = getattr(order, "metadata_", None) or {}
    if not isinstance(meta, dict):
        return False
    return str(meta.get("portfolio_scope") or "").strip().lower() == "bundle"


def privy_deposit_is_bundle_internal(db: Session, deposit: Any) -> bool:
    meta = deposit.metadata_json if isinstance(getattr(deposit, "metadata_json", None), dict) else {}
    swap_id_raw = meta.get("swap_id")
    if not swap_id_raw:
        return False
    try:
        swap_id = UUID(str(swap_id_raw))
    except (ValueError, TypeError):
        return False
    from services.lifi.models import PersonWalletSwap

    swap = db.query(PersonWalletSwap).filter(PersonWalletSwap.id == swap_id).first()
    if swap is None:
        return False
    return is_bundle_internal_swap(swap)
