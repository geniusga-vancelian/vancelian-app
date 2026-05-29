"""Projection UX Mon Trading — exclut les opérations internes bundle."""
from __future__ import annotations

import logging
from typing import Any

from services.portfolio_engine.bundle_execution.projection_config import (
    bundle_transaction_projection_v2_enabled,
)

logger = logging.getLogger(__name__)

_BUNDLE_INTERNAL_KINDS = frozenset(
    {
        "bundle_internal_swap",
        "bundle_allocation_aggregate",
        "bundle_deallocation_aggregate",
        "bundle_deposit",
        "bundle_withdrawal",
    }
)

_BUNDLE_INTERNAL_SOURCES = frozenset({"bundle_lifi", "bundle_ledger"})

_ALLOCATION_TITLE_PREFIXES = (
    "allocation ·",
    "allocation ",
    "rééquilibrage ·",
    "vente interne ·",
)


def _tx_meta(tx: dict[str, Any]) -> dict[str, Any]:
    meta = tx.get("metadata_json")
    return meta if isinstance(meta, dict) else {}


def detect_suspected_bundle_internal_swap_without_context(tx: dict[str, Any]) -> bool:
    """Swap ressemblant à une allocation bundle sans ``bundle_execution`` explicite."""
    kind = str(tx.get("transaction_kind") or "").strip().lower()
    if kind in _BUNDLE_INTERNAL_KINDS:
        return False

    meta = _tx_meta(tx)
    if meta.get("bundle_execution") is True:
        return False

    source = str(tx.get("source_system") or "").strip().lower()
    if source in _BUNDLE_INTERNAL_SOURCES:
        return True

    if tx.get("bundle_batch_id") and str(tx.get("portfolio_scope") or "").lower() == "bundle":
        return True

    if meta.get("bundle_batch_id") and meta.get("bundle_portfolio_id"):
        return True

    ledger_event = str(tx.get("ledger_event_type") or meta.get("ledger_event_type") or "")
    if ledger_event.startswith("BUNDLE_ALLOCATION") or ledger_event.startswith("BUNDLE_REBALANCE"):
        return True

    title = str(tx.get("title") or "").strip().lower()
    if any(title.startswith(prefix) for prefix in _ALLOCATION_TITLE_PREFIXES):
        return True

    bundle_action = str(tx.get("bundle_action") or meta.get("bundle_action") or "").strip().lower()
    if bundle_action in {
        "allocation",
        "rebalance",
        "rebalance_buy",
        "rebalance_sell",
        "withdraw_sell",
        "funding",
        "withdraw",
    }:
        return True

    return False


def exclude_bundle_internal_transaction(tx: dict[str, Any]) -> bool:
    """True si la transaction ne doit pas apparaître en Mon Trading."""
    kind = str(tx.get("transaction_kind") or "").strip().lower()
    if kind in _BUNDLE_INTERNAL_KINDS:
        return True

    if str(tx.get("portfolio_scope") or "").strip().lower() == "bundle":
        side = str(tx.get("side") or "").strip().lower()
        if side == "swap" or kind == "crypto_swap":
            return True

    meta = _tx_meta(tx)
    if meta.get("bundle_execution") is True:
        return True
    if meta.get("bundle_portfolio_id") and meta.get("bundle_batch_id"):
        return True

    if tx.get("bundle_batch_id") and kind == "crypto_swap":
        return True

    source = str(tx.get("source_system") or "").strip().lower()
    if source in _BUNDLE_INTERNAL_SOURCES and kind != "bundle_pe_transfer":
        return True

    if detect_suspected_bundle_internal_swap_without_context(tx):
        return True

    return False


def is_self_trading_visible_transaction(tx: dict[str, Any]) -> bool:
    """True si la transaction peut être affichée en self-trading."""
    if exclude_bundle_internal_transaction(tx):
        return False

    if detect_suspected_bundle_internal_swap_without_context(tx):
        logger.warning(
            "bundle_projection.suspected_internal_swap_leak",
            extra={
                "tx_id": str(tx.get("id") or ""),
                "title": tx.get("title"),
                "source_system": tx.get("source_system"),
                "transaction_kind": tx.get("transaction_kind"),
            },
        )
        return False

    return True


def project_self_trading_transactions(raw_txs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filtre défensif — conserve transferts PE bundle (debit fund / credit release)."""
    if not bundle_transaction_projection_v2_enabled():
        return raw_txs
    return [tx for tx in raw_txs if is_self_trading_visible_transaction(tx)]
