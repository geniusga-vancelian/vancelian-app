"""Historique transactions internes à un bundle (allocations, rebalance, retrait interne)."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.bundle_execution.bundle_pe_transactions import (
    list_bundle_pe_asset_transactions,
)
from services.transaction_intents.bundle_intent_sync import bundle_context_from_swap_audit
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    bundle_context_for_swap,
    is_bundle_portfolio_swap,
)
from services.privy_wallet.transaction_merge import person_wallet_swap_to_crypto_tx


def _bundle_action_label(action: str) -> str:
    labels = {
        "allocation": "Allocation",
        "rebalance": "Rééquilibrage",
        "rebalance_buy": "Rééquilibrage · achat",
        "rebalance_sell": "Rééquilibrage · vente",
        "withdraw_sell": "Vente interne",
        "withdraw": "Retrait interne",
        "funding": "Financement interne",
    }
    return labels.get(action, "Opération bundle")


def _swap_to_bundle_tx(swap: PersonWalletSwap, *, asset: str | None = None) -> dict[str, Any] | None:
    ctx = bundle_context_for_swap(swap) or bundle_context_from_swap_audit(swap)
    if ctx is None:
        return None

    asset_u = (asset or swap.to_asset or swap.from_asset or "").strip().upper()
    mapped = person_wallet_swap_to_crypto_tx(swap, asset=asset_u)
    if mapped is None and asset is None:
        mapped = person_wallet_swap_to_crypto_tx(swap, asset=str(swap.to_asset).upper())
    if mapped is None:
        return None

    action = str(ctx.get("bundle_action") or ctx.get("leg_action") or "allocation").strip().lower()
    from_asset = str(swap.from_asset).upper()
    to_asset = str(swap.to_asset).upper()
    mapped["title"] = f"{_bundle_action_label(action)} · {from_asset} → {to_asset}"
    mapped["transaction_kind"] = "bundle_internal_swap"
    mapped["source_system"] = "bundle_lifi"
    mapped["portfolio_scope"] = "bundle"
    mapped["portfolio_id"] = str(ctx.get("portfolio_id") or "")
    mapped["bundle_action"] = action
    mapped["bundle_batch_id"] = str(ctx.get("batch_id") or "")
    return mapped


def _tx_sort_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.min.replace(tzinfo=None)


def list_bundle_portfolio_transactions(
    db: Session,
    *,
    client_id: UUID,
    person_id: UUID | None,
    portfolio_id: UUID,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Transactions visibles dans l'espace bundle : swaps internes + entrées/sorties jambe USDC."""
    from services.portfolio_engine.bundle_ledger.history import (
        maybe_list_bundle_transactions_from_ledger,
    )
    from services.portfolio_engine.bundle_execution.bundle_projection import (
        project_bundle_transactions,
    )
    from services.portfolio_engine.portfolios.models import Portfolio

    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.client_id == client_id)
        .first()
    )
    portfolio_name = portfolio.name if portfolio is not None else "Bundle"

    ledger_txs, _meta = maybe_list_bundle_transactions_from_ledger(
        db,
        client_id=client_id,
        person_id=person_id,
        portfolio_id=portfolio_id,
        limit=limit,
    )
    if ledger_txs is not None:
        raw = ledger_txs
    else:
        raw = _list_bundle_portfolio_transactions_legacy(
            db,
            client_id=client_id,
            person_id=person_id,
            portfolio_id=portfolio_id,
            limit=limit,
        )

    projected = project_bundle_transactions(raw, portfolio_name=portfolio_name)
    return projected[:limit]


def _list_bundle_portfolio_transactions_legacy(
    db: Session,
    *,
    client_id: UUID,
    person_id: UUID | None,
    portfolio_id: UUID,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """Projection legacy audit + swaps Li.FI (pre-Phase 4B)."""
    portfolio_id_str = str(portfolio_id)
    by_id: dict[str, dict[str, Any]] = {}

    if person_id is not None:
        swaps = (
            db.query(PersonWalletSwap)
            .filter(
                PersonWalletSwap.person_id == person_id,
                PersonWalletSwap.status == SwapSessionStatus.CONFIRMED.value,
            )
            .order_by(PersonWalletSwap.confirmed_at.desc(), PersonWalletSwap.created_at.desc())
            .limit(max(limit * 6, 120))
            .all()
        )
        for swap in swaps:
            if not is_bundle_portfolio_swap(swap, portfolio_id=portfolio_id_str):
                continue
            ctx = bundle_context_for_swap(swap) or bundle_context_from_swap_audit(swap) or {}
            if str(ctx.get("portfolio_id") or "") != portfolio_id_str:
                continue
            mapped = _swap_to_bundle_tx(swap)
            if mapped is None:
                continue
            by_id[str(mapped["id"])] = mapped

    for asset in ("USDC", "EURC"):
        for pe_tx in list_bundle_pe_asset_transactions(
            db,
            client_id=client_id,
            person_id=person_id,
            asset=asset,
            limit=limit,
            portfolio_id=portfolio_id_str,
        ):
            tx_id = str(pe_tx.get("id") or "")
            if not tx_id:
                continue
            enriched = dict(pe_tx)
            enriched["portfolio_scope"] = "bundle"
            enriched["portfolio_id"] = portfolio_id_str
            by_id[tx_id] = enriched

    txs = list(by_id.values())
    txs.sort(key=lambda tx: _tx_sort_dt(tx.get("created_at")), reverse=True)
    return txs[:limit]
