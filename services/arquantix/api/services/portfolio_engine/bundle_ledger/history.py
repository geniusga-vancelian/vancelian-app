"""Lecture historique bundle depuis ``bundle_ledger_entries`` (Phase 4B)."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.bundle_ledger.config import bundle_ledger_history_enabled
from services.portfolio_engine.bundle_ledger.enums import BundleLedgerEventType
from services.portfolio_engine.bundle_ledger.models import BundleLedgerEntry
from services.portfolio_engine.bundle_ledger.reconciliation import reconcile_bundle_ledger_shadow
from services.portfolio_engine.portfolios.models import Portfolio
from services.privy_wallet.service import _format_decimal

logger = logging.getLogger(__name__)


def resolve_history_source(
    reconciliation: dict[str, Any],
) -> tuple[str, str | None]:
    """Retourne ``(ledger|legacy, fallback_reason)`` selon flag + réconciliation."""
    from services.portfolio_engine.bundle_ledger.config import bundle_ledger_history_enabled

    if not bundle_ledger_history_enabled():
        return "legacy", "flag_disabled"

    verdict = str(reconciliation.get("verdict") or "")
    entry_count = int(reconciliation.get("ledger_entry_count") or 0)

    if verdict == "DIFF":
        return "legacy", "ledger_diff"
    if verdict == "INCOMPLETE" or entry_count == 0:
        return "legacy", "ledger_incomplete_or_empty"
    if verdict == "MATCH" and entry_count > 0:
        return "ledger", None
    return "legacy", verdict or "unknown"

_UI_EVENT_TYPES = frozenset({
    BundleLedgerEventType.BUNDLE_DEPOSIT.value,
    BundleLedgerEventType.BUNDLE_WITHDRAWAL.value,
    BundleLedgerEventType.BUNDLE_ALLOCATION_BUY.value,
    BundleLedgerEventType.BUNDLE_ALLOCATION_SELL.value,
    BundleLedgerEventType.BUNDLE_REBALANCE_BUY.value,
    BundleLedgerEventType.BUNDLE_REBALANCE_SELL.value,
})


def _tx_sort_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.min.replace(tzinfo=None)


def _action_label(event_type: str) -> str:
    labels = {
        BundleLedgerEventType.BUNDLE_ALLOCATION_BUY.value: "Allocation",
        BundleLedgerEventType.BUNDLE_ALLOCATION_SELL.value: "Vente interne",
        BundleLedgerEventType.BUNDLE_REBALANCE_BUY.value: "Rééquilibrage · achat",
        BundleLedgerEventType.BUNDLE_REBALANCE_SELL.value: "Rééquilibrage · vente",
    }
    return labels.get(event_type, "Opération bundle")


def _is_internal_cash_entry(entry: BundleLedgerEntry) -> bool:
    meta = entry.metadata_ if isinstance(entry.metadata_, dict) else {}
    if meta.get("internal_cash_leg"):
        return True
    if entry.event_type == BundleLedgerEventType.BUNDLE_CASH_RELEASED.value:
        return True
    if (
        entry.event_type == BundleLedgerEventType.BUNDLE_DEPOSIT.value
        and entry.source_system == "lifi"
    ):
        return True
    return False


def ledger_entry_to_bundle_tx(
    entry: BundleLedgerEntry,
    *,
    portfolio_name: str,
) -> dict[str, Any] | None:
    if entry.event_type not in _UI_EVENT_TYPES:
        return None
    if _is_internal_cash_entry(entry):
        return None

    amount = _format_decimal(entry.quantity)
    if not amount or amount == "0":
        return None

    created = entry.created_at or datetime.utcnow()
    meta = entry.metadata_ if isinstance(entry.metadata_, dict) else {}

    if entry.event_type == BundleLedgerEventType.BUNDLE_DEPOSIT.value:
        asset = entry.asset_symbol.upper()
        return {
            "id": entry.id,
            "side": "deposit",
            "asset": asset,
            "amount_crypto": amount,
            "amount_fiat": "0",
            "price": "0",
            "currency": "EUR",
            "status": "confirmed",
            "fee_amount": None,
            "fee_asset": None,
            "external_reference": entry.batch_id,
            "created_at": created,
            "title": f"Dépôt · {portfolio_name}",
            "subtitle": f"+{amount} {asset}",
            "direction": "credit",
            "from_asset": None,
            "to_asset": asset,
            "transaction_kind": "bundle_deposit",
            "source_system": "bundle_ledger",
            "tx_hash": None,
            "custody_provider": "privy",
            "portfolio_scope": "bundle",
            "portfolio_id": str(entry.bundle_portfolio_id),
            "bundle_batch_id": entry.batch_id,
            "ledger_event_type": entry.event_type,
        }

    if entry.event_type == BundleLedgerEventType.BUNDLE_WITHDRAWAL.value:
        asset = entry.asset_symbol.upper()
        return {
            "id": entry.id,
            "side": "transfer",
            "asset": asset,
            "amount_crypto": amount,
            "amount_fiat": "0",
            "price": "0",
            "currency": "EUR",
            "status": "confirmed",
            "fee_amount": None,
            "fee_asset": None,
            "external_reference": entry.batch_id,
            "created_at": created,
            "title": f"Retrait · {portfolio_name}",
            "subtitle": f"−{amount} {asset}",
            "direction": "debit",
            "from_asset": asset,
            "to_asset": None,
            "transaction_kind": "bundle_withdrawal",
            "source_system": "bundle_ledger",
            "tx_hash": None,
            "custody_provider": "privy",
            "portfolio_scope": "bundle",
            "portfolio_id": str(entry.bundle_portfolio_id),
            "bundle_batch_id": entry.batch_id,
            "ledger_event_type": entry.event_type,
        }

    from_asset = str(meta.get("entry_asset") or meta.get("from_asset") or "").upper()
    to_asset = entry.asset_symbol.upper()
    if entry.event_type in {
        BundleLedgerEventType.BUNDLE_ALLOCATION_SELL.value,
        BundleLedgerEventType.BUNDLE_REBALANCE_SELL.value,
    }:
        from_asset = entry.asset_symbol.upper()
        to_asset = str(meta.get("entry_asset") or meta.get("to_asset") or "").upper()

    if entry.event_type == BundleLedgerEventType.BUNDLE_ALLOCATION_BUY.value:
        from_asset = str(meta.get("entry_asset") or from_asset).upper()
        to_asset = entry.asset_symbol.upper()

    action = _action_label(entry.event_type)
    if meta.get("withdraw_sell"):
        action = "Vente interne"

    return {
        "id": entry.id,
        "side": "swap",
        "asset": to_asset or from_asset,
        "amount_crypto": amount,
        "amount_fiat": "0",
        "price": "0",
        "currency": "EUR",
        "status": "confirmed",
        "fee_amount": None,
        "fee_asset": None,
        "external_reference": entry.batch_id,
        "created_at": created,
        "title": f"{action} · {from_asset} → {to_asset}",
        "subtitle": f"{amount} {from_asset} → {to_asset}",
        "direction": "internal",
        "from_asset": from_asset,
        "to_asset": to_asset,
        "transaction_kind": "bundle_internal_swap",
        "source_system": "bundle_ledger",
        "tx_hash": meta.get("tx_hash"),
        "custody_provider": "privy",
        "portfolio_scope": "bundle",
        "portfolio_id": str(entry.bundle_portfolio_id),
        "bundle_batch_id": entry.batch_id,
        "bundle_action": meta.get("withdraw_sell") and "withdraw_sell" or action.lower().split()[0],
        "ledger_event_type": entry.event_type,
        "leg_id": entry.leg_id,
    }


def list_bundle_transactions_from_ledger(
    db: Session,
    *,
    client_id: UUID,
    person_id: UUID | None,
    portfolio_id: UUID,
    limit: int = 100,
) -> list[dict[str, Any]]:
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.client_id == client_id)
        .first()
    )
    portfolio_name = portfolio.name if portfolio is not None else "Bundle"

    q = db.query(BundleLedgerEntry).filter(
        BundleLedgerEntry.bundle_portfolio_id == portfolio_id,
    )
    if person_id is not None:
        q = q.filter(BundleLedgerEntry.person_id == person_id)

    rows = q.order_by(BundleLedgerEntry.created_at.desc()).limit(max(limit * 4, 200)).all()
    by_id: dict[str, dict[str, Any]] = {}
    for entry in rows:
        mapped = ledger_entry_to_bundle_tx(entry, portfolio_name=portfolio_name)
        if mapped is None:
            continue
        by_id[str(mapped["id"])] = mapped

    txs = list(by_id.values())
    txs.sort(key=lambda tx: _tx_sort_dt(tx.get("created_at")), reverse=True)
    return txs[:limit]


def maybe_list_bundle_transactions_from_ledger(
    db: Session,
    *,
    client_id: UUID,
    person_id: UUID | None,
    portfolio_id: UUID,
    limit: int = 100,
) -> tuple[list[dict[str, Any]] | None, dict[str, Any] | None]:
    """Retourne ``(transactions, meta)`` ou ``(None, None)`` pour fallback legacy."""
    from services.portfolio_engine.bundle_ledger.observability import log_bundle_ledger_event

    if not bundle_ledger_history_enabled():
        return None, None

    if person_id is None:
        log_bundle_ledger_event(
            "ledger_history_fallback",
            person_id=None,
            portfolio_id=str(portfolio_id),
            verdict="fallback",
            fallback_reason="no_person_id",
            entries_count=0,
        )
        return None, {"fallback": "no_person_id", "source": "legacy"}

    try:
        recon = reconcile_bundle_ledger_shadow(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
        )
    except Exception as exc:
        log_bundle_ledger_event(
            "ledger_history_fallback",
            person_id=str(person_id),
            portfolio_id=str(portfolio_id),
            verdict="fallback",
            fallback_reason="reconciliation_error",
            entries_count=0,
            error=str(exc),
        )
        return None, {"fallback": "reconciliation_error", "source": "legacy", "error": str(exc)}

    verdict = recon.get("verdict")
    entry_count = int(recon.get("ledger_entry_count") or 0)

    if verdict == "DIFF":
        from services.portfolio_engine.bundle_ledger.observability import log_bundle_ledger_event as _log

        _log(
            "ledger_reconciliation_diff",
            person_id=str(person_id),
            portfolio_id=str(portfolio_id),
            verdict=verdict,
            fallback_reason="ledger_diff",
            entries_count=entry_count,
            differences=recon.get("differences"),
        )
        log_bundle_ledger_event(
            "ledger_history_fallback",
            person_id=str(person_id),
            portfolio_id=str(portfolio_id),
            verdict=verdict,
            fallback_reason="ledger_diff",
            entries_count=entry_count,
        )
        return None, {
            "fallback": "ledger_diff",
            "source": "legacy",
            "verdict": verdict,
            "differences": recon.get("differences"),
        }

    if verdict == "INCOMPLETE" or entry_count == 0:
        log_bundle_ledger_event(
            "ledger_history_fallback",
            person_id=str(person_id),
            portfolio_id=str(portfolio_id),
            verdict=str(verdict),
            fallback_reason="ledger_incomplete_or_empty",
            entries_count=entry_count,
        )
        return None, {
            "fallback": "ledger_incomplete_or_empty",
            "source": "legacy",
            "verdict": verdict,
            "missing_ledger_entries": recon.get("missing_ledger_entries"),
        }

    txs = list_bundle_transactions_from_ledger(
        db,
        client_id=client_id,
        person_id=person_id,
        portfolio_id=portfolio_id,
        limit=limit,
    )
    log_bundle_ledger_event(
        "ledger_history_read",
        person_id=str(person_id),
        portfolio_id=str(portfolio_id),
        verdict=verdict,
        fallback_reason=None,
        entries_count=entry_count,
        transactions_returned=len(txs),
    )
    return txs, {
        "source": "bundle_ledger",
        "verdict": verdict,
        "shadow_mode": False,
    }
