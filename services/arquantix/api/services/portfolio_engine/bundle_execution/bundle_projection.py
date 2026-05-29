"""Projection UX historique bundle — dépôts positifs, allocations agrégées."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import NAMESPACE_URL, uuid5

from services.portfolio_engine.bundle_execution.projection_config import (
    bundle_transaction_projection_v2_enabled,
)
from services.privy_wallet.service import _format_decimal

_ALLOCATION_KIND = "bundle_allocation_aggregate"
_DEALLOCATION_KIND = "bundle_deallocation_aggregate"

_SELL_ACTIONS = frozenset(
    {
        "withdraw_sell",
        "rebalance_sell",
        "sell",
        "deallocation",
    }
)

_SUCCESS_STATUSES = frozenset({"confirmed", "completed", "success", "partial"})
_FAILED_STATUSES = frozenset({"failed", "cancelled", "canceled", "reverted", "error"})
_PENDING_STATUSES = frozenset({"pending", "submitted", "processing", "in_progress"})


def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.min.replace(tzinfo=None)


def _decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _batch_id(tx: dict[str, Any]) -> str:
    return str(
        tx.get("bundle_batch_id")
        or tx.get("external_reference")
        or _tx_meta(tx).get("batch_id")
        or "",
    ).strip()


def _tx_meta(tx: dict[str, Any]) -> dict[str, Any]:
    meta = tx.get("metadata_json")
    return meta if isinstance(meta, dict) else {}


def _is_fund_transfer(tx: dict[str, Any]) -> bool:
    kind = str(tx.get("transaction_kind") or "").strip().lower()
    if kind == "bundle_deposit":
        return True
    if kind != "bundle_pe_transfer":
        return False
    direction = str(tx.get("direction") or "").strip().lower()
    title = str(tx.get("title") or "").lower()
    return direction == "debit" or title.startswith("transfert vers")


def _is_release_transfer(tx: dict[str, Any]) -> bool:
    kind = str(tx.get("transaction_kind") or "").strip().lower()
    if kind == "bundle_withdrawal":
        return True
    if kind != "bundle_pe_transfer":
        return False
    direction = str(tx.get("direction") or "").strip().lower()
    title = str(tx.get("title") or "").lower()
    return direction == "credit" or title.startswith("retrait")


def _leg_action(tx: dict[str, Any]) -> str:
    action = str(
        tx.get("bundle_action")
        or _tx_meta(tx).get("bundle_action")
        or _tx_meta(tx).get("leg_action")
        or "",
    ).strip().lower()
    if action:
        return action
    ledger = str(tx.get("ledger_event_type") or _tx_meta(tx).get("ledger_event_type") or "")
    if "SELL" in ledger.upper():
        return "withdraw_sell"
    if "ALLOCATION" in ledger.upper() or "REBALANCE" in ledger.upper():
        return "allocation"
    title = str(tx.get("title") or "").lower()
    if "vente interne" in title:
        return "withdraw_sell"
    if "rééquilibrage" in title and "vente" in title:
        return "rebalance_sell"
    return "allocation"


def _is_internal_leg(tx: dict[str, Any]) -> bool:
    kind = str(tx.get("transaction_kind") or "").strip().lower()
    if kind in {_ALLOCATION_KIND, _DEALLOCATION_KIND}:
        return False
    if kind == "bundle_internal_swap":
        return True
    if str(tx.get("side") or "").strip().lower() == "swap" and str(
        tx.get("portfolio_scope") or "",
    ).lower() == "bundle":
        return True
    return False


def _leg_status(tx: dict[str, Any]) -> str:
    status = str(tx.get("status") or "confirmed").strip().lower()
    return status or "confirmed"


def _aggregate_status(legs: list[dict[str, Any]]) -> str:
    if not legs:
        return "completed"
    statuses = {_leg_status(leg) for leg in legs}
    if statuses & _PENDING_STATUSES:
        return "in_progress"
    success = sum(1 for leg in legs if _leg_status(leg) in _SUCCESS_STATUSES)
    failed = sum(1 for leg in legs if _leg_status(leg) in _FAILED_STATUSES)
    if success > 0 and failed > 0:
        return "partial"
    if failed == len(legs):
        return "failed"
    if success > 0:
        return "completed"
    return "in_progress"


def _expandable_leg(tx: dict[str, Any]) -> dict[str, Any]:
    from_asset = str(tx.get("from_asset") or _tx_meta(tx).get("from_asset") or "").upper()
    to_asset = str(tx.get("to_asset") or tx.get("asset") or "").upper()
    amount_in = str(
        tx.get("swap_amount_from")
        or (_tx_meta(tx).get("entry_asset") and tx.get("amount_crypto"))
        or tx.get("amount_crypto")
        or "",
    )
    amount_out = str(tx.get("swap_amount_to") or tx.get("amount_crypto") or "")
    if from_asset and not amount_in and str(tx.get("asset") or "").upper() == from_asset:
        amount_in = str(tx.get("amount_crypto") or "")
    return {
        "from_asset": from_asset,
        "to_asset": to_asset,
        "amount_in": amount_in,
        "amount_out": amount_out,
        "status": _leg_status(tx),
        "leg_id": tx.get("leg_id"),
        "tx_hash": tx.get("tx_hash"),
    }


def project_bundle_deposit(tx: dict[str, Any], *, portfolio_name: str) -> dict[str, Any]:
    amount = str(tx.get("amount_crypto") or tx.get("amount") or "0")
    asset = str(tx.get("asset") or "USDC").upper()
    return {
        **tx,
        "transaction_kind": "bundle_deposit",
        "side": "deposit",
        "direction": "credit",
        "asset": asset,
        "amount_crypto": amount,
        "title": f"Dépôt · {portfolio_name}",
        "subtitle": f"+{amount} {asset}",
        "from_asset": None,
        "to_asset": asset,
        "portfolio_scope": "bundle",
    }


def project_bundle_withdrawal(tx: dict[str, Any], *, portfolio_name: str) -> dict[str, Any]:
    amount = str(tx.get("amount_crypto") or tx.get("amount") or "0")
    asset = str(tx.get("asset") or "USDC").upper()
    return {
        **tx,
        "transaction_kind": "bundle_withdrawal",
        "side": "transfer",
        "direction": "debit",
        "asset": asset,
        "amount_crypto": amount,
        "title": f"Retrait · {portfolio_name}",
        "subtitle": f"−{amount} {asset}",
        "from_asset": asset,
        "to_asset": None,
        "portfolio_scope": "bundle",
    }


def aggregate_bundle_allocations_by_batch(
    legs: list[dict[str, Any]],
    *,
    portfolio_name: str,
    deallocation: bool = False,
) -> list[dict[str, Any]]:
    """Regroupe les legs internes par ``batch_id`` en une ligne métier."""
    by_batch: dict[str, list[dict[str, Any]]] = {}
    for leg in legs:
        batch = _batch_id(leg)
        if not batch:
            continue
        by_batch.setdefault(batch, []).append(leg)

    aggregates: list[dict[str, Any]] = []
    kind = _DEALLOCATION_KIND if deallocation else _ALLOCATION_KIND
    label = "Désallocation" if deallocation else "Allocation"

    for batch_id, batch_legs in by_batch.items():
        batch_legs.sort(key=lambda tx: _parse_dt(tx.get("created_at")), reverse=True)
        anchor = batch_legs[0]
        expandable = [_expandable_leg(leg) for leg in batch_legs]

        entry_asset = "USDC"
        for leg in batch_legs:
            candidate = str(leg.get("from_asset") or _tx_meta(leg).get("entry_asset") or "").upper()
            if candidate:
                entry_asset = candidate
                break

        total = Decimal("0")
        for leg in batch_legs:
            leg_from = str(leg.get("from_asset") or "").upper()
            if leg_from == entry_asset:
                total += _decimal(leg.get("swap_amount_from") or leg.get("amount_crypto"))
            elif str(leg.get("asset") or "").upper() == entry_asset and not deallocation:
                total += _decimal(leg.get("amount_crypto"))

        successful = sum(1 for leg in batch_legs if _leg_status(leg) in _SUCCESS_STATUSES)
        failed = sum(1 for leg in batch_legs if _leg_status(leg) in _FAILED_STATUSES)
        status = _aggregate_status(batch_legs)
        total_str = _format_decimal(total)

        aggregates.append(
            {
                "id": uuid5(NAMESPACE_URL, f"bundle-aggregate:{kind}:{batch_id}"),
                "side": "allocation",
                "asset": entry_asset,
                "amount_crypto": total_str,
                "amount": total_str,
                "amount_fiat": "0",
                "price": "0",
                "currency": anchor.get("currency") or "EUR",
                "status": status,
                "fee_amount": None,
                "fee_asset": None,
                "external_reference": batch_id,
                "bundle_batch_id": batch_id,
                "created_at": anchor.get("created_at"),
                "title": f"{label} · {portfolio_name}",
                "subtitle": f"{successful}/{len(batch_legs)} legs · {status}",
                "direction": "info",
                "transaction_kind": kind,
                "source_system": anchor.get("source_system") or "bundle_projection",
                "tx_hash": None,
                "custody_provider": "privy",
                "portfolio_scope": "bundle",
                "portfolio_id": anchor.get("portfolio_id"),
                "legs_count": len(batch_legs),
                "successful_legs_count": successful,
                "failed_legs_count": failed,
                "expandable_legs": expandable,
            },
        )

    aggregates.sort(key=lambda tx: _parse_dt(tx.get("created_at")), reverse=True)
    return aggregates


def project_bundle_transactions(
    raw_txs: list[dict[str, Any]],
    *,
    portfolio_name: str = "Bundle",
) -> list[dict[str, Any]]:
    """Projection bundle : dépôts +, retraits −, allocations agrégées."""
    if not bundle_transaction_projection_v2_enabled():
        return raw_txs

    projected: list[dict[str, Any]] = []
    allocation_legs: list[dict[str, Any]] = []
    deallocation_legs: list[dict[str, Any]] = []

    for tx in raw_txs:
        kind = str(tx.get("transaction_kind") or "").strip().lower()
        if kind in {_ALLOCATION_KIND, _DEALLOCATION_KIND}:
            projected.append(tx)
            continue
        if _is_fund_transfer(tx):
            projected.append(project_bundle_deposit(tx, portfolio_name=portfolio_name))
            continue
        if _is_release_transfer(tx):
            projected.append(project_bundle_withdrawal(tx, portfolio_name=portfolio_name))
            continue
        if _is_internal_leg(tx):
            action = _leg_action(tx)
            if action in _SELL_ACTIONS or kind == "bundle_internal_swap" and "vente" in str(
                tx.get("title") or "",
            ).lower():
                deallocation_legs.append(tx)
            else:
                allocation_legs.append(tx)
            continue
        projected.append(tx)

    projected.extend(
        aggregate_bundle_allocations_by_batch(
            allocation_legs,
            portfolio_name=portfolio_name,
            deallocation=False,
        ),
    )
    projected.extend(
        aggregate_bundle_allocations_by_batch(
            deallocation_legs,
            portfolio_name=portfolio_name,
            deallocation=True,
        ),
    )

    projected.sort(key=lambda tx: _parse_dt(tx.get("created_at")), reverse=True)
    return projected
