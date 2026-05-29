#!/usr/bin/env python3
"""Inspection read-only de l'état bundle (cash leg, locks, swaps Li.FI, intents).

Strictement read-only — aucune mutation DB, pas de release/retry automatique.

Usage (depuis ``services/arquantix/api``)::

    python3 -m scripts.inspect_bundle_state \\
        --person-id <UUID> \\
        --portfolio-id <UUID> \\
        [--batch-id <UUID>]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

api_dir = Path(__file__).resolve().parent.parent
if str(api_dir) not in sys.path:
    sys.path.insert(0, str(api_dir))

from dotenv import load_dotenv

load_dotenv(api_dir / ".env.local")
load_dotenv(api_dir / ".env")

from sqlalchemy.orm import Session

from database import SessionLocal
from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundle_execution.bundle_funding import (
    resolve_bundle_cash_leg_available,
)
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import (
    is_bundle_internal_swap,
)
from services.portfolio_engine.bundles.bundle_invest_lock import (
    ACTIVE_INVEST_LOCK_STATUSES,
    get_invest_lock,
    invest_lock_ttl_minutes,
)
from services.portfolio_engine.bundles.bundle_withdraw_lock import (
    BLOCKING_WITHDRAW_LOCK_STATUSES,
    RECOVERABLE_WITHDRAW_LOCK_STATUSES,
    get_withdraw_lock,
    withdraw_lock_ttl_minutes,
)
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom
from services.transaction_intents.bundle_intent_sync import bundle_context_from_swap_audit
from services.transaction_intents.enums import IntentProductType


LIVE_SWAP_STATUSES = frozenset({
    SwapSessionStatus.SUBMITTED.value,
    SwapSessionStatus.AWAITING_SIGNATURE.value,
    SwapSessionStatus.PENDING.value,
    SwapSessionStatus.QUOTE_RECEIVED.value,
})


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _lock_age_minutes(lock: dict[str, Any]) -> float | None:
    ref = lock.get("updated_at") or lock.get("created_at")
    dt = _parse_iso(str(ref) if ref else None)
    if dt is None:
        return None
    return round((datetime.now(timezone.utc) - dt).total_seconds() / 60.0, 2)


def _raw_metadata_lock(metadata: dict | None, key: str) -> dict[str, Any] | None:
    if not isinstance(metadata, dict):
        return None
    raw = metadata.get(key)
    return dict(raw) if isinstance(raw, dict) else None


def _resolve_entry_instrument(db: Session, portfolio: Portfolio) -> Instrument | None:
    from services.portfolio_engine.products.models import ProductDefinition

    product = None
    if portfolio.origin_product_id:
        product = (
            db.query(ProductDefinition)
            .filter(ProductDefinition.id == portfolio.origin_product_id)
            .first()
        )
    meta = product.metadata_ if product and isinstance(product.metadata_, dict) else {}
    entry_asset = str(meta.get("entry_asset_default") or "USDC").upper()
    asset = db.query(Asset).filter(Asset.symbol == entry_asset).first()
    if asset is None:
        return None
    return (
        db.query(Instrument)
        .filter(Instrument.asset_id == asset.id, Instrument.instrument_type == "spot")
        .first()
    )


def _list_spot_legs(db: Session, portfolio_id: UUID) -> list[dict[str, Any]]:
    rows = (
        db.query(PositionAtom, Instrument, Asset)
        .join(Instrument, Instrument.id == PositionAtom.instrument_id)
        .join(Asset, Asset.id == Instrument.asset_id)
        .filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.position_type == PositionType.SPOT,
            PositionAtom.status == "open",
        )
        .all()
    )
    out = []
    for atom, _instr, asset in rows:
        qty = Decimal(str(atom.quantity or 0))
        if qty <= 0:
            continue
        out.append({
            "asset": asset.symbol,
            "quantity": float(qty),
            "cost_basis_eur": float(atom.cost_basis or 0),
            "atom_id": str(atom.id),
        })
    return out


def _bundle_swaps(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    batch_id: str | None,
) -> list[dict[str, Any]]:
    portfolio_id_str = str(portfolio_id)
    swaps = (
        db.query(PersonWalletSwap)
        .filter(PersonWalletSwap.person_id == person_id)
        .order_by(PersonWalletSwap.created_at.desc())
        .limit(300)
        .all()
    )
    out: list[dict[str, Any]] = []
    for swap in swaps:
        if not is_bundle_internal_swap(swap):
            continue
        ctx = bundle_context_from_swap_audit(swap) or {}
        if str(ctx.get("portfolio_id") or "") != portfolio_id_str:
            continue
        if batch_id and str(ctx.get("batch_id") or "") != batch_id:
            continue
        out.append({
            "swap_id": str(swap.id),
            "status": swap.status,
            "from_asset": swap.from_asset,
            "to_asset": swap.to_asset,
            "amount_in": float(swap.amount_in or 0),
            "estimated_receive": float(swap.estimated_receive or 0),
            "tx_hash": swap.tx_hash,
            "bundle_action": ctx.get("bundle_action"),
            "batch_id": ctx.get("batch_id"),
            "is_live": swap.status in LIVE_SWAP_STATUSES,
            "confirmed_at": swap.confirmed_at.isoformat() if swap.confirmed_at else None,
        })
    return out


def _bundle_intents(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    batch_id: str | None,
) -> list[dict[str, Any]]:
    q = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.person_id == person_id,
            TransactionIntent.product_type.in_([
                IntentProductType.BUNDLE_INVEST.value,
                IntentProductType.BUNDLE_WITHDRAW.value,
            ]),
        )
        .order_by(TransactionIntent.created_at.desc())
        .limit(50)
    )
    out: list[dict[str, Any]] = []
    for row in q:
        meta = row.metadata_json if isinstance(row.metadata_json, dict) else {}
        row_batch = str(meta.get("batch_id") or row.linked_reference_id or "")
        row_bundle = str(meta.get("bundle_id") or "")
        if row_bundle and row_bundle != str(portfolio_id):
            continue
        if batch_id and row_batch != batch_id:
            continue
        out.append({
            "intent_id": str(row.id),
            "product_type": row.product_type,
            "status": row.status,
            "batch_id": row_batch,
            "bundle_id": row_bundle or str(portfolio_id),
            "legs_count": len(meta.get("legs") or []) if isinstance(meta.get("legs"), list) else 0,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        })
    return out


def _invest_lock_assessment(
    metadata: dict | None,
    *,
    live_swap_count: int,
) -> dict[str, Any]:
    active = get_invest_lock(metadata)
    raw = _raw_metadata_lock(metadata, "bundle_invest_lock")
    if active is None and raw is None:
        return {"present": False, "blocking": False, "recoverable": True, "status": "none"}

    status = str((active or raw or {}).get("status") or "")
    age = _lock_age_minutes(active or raw or {})
    ttl = invest_lock_ttl_minutes()
    blocking = status in ACTIVE_INVEST_LOCK_STATUSES
    live_blocks_expire = live_swap_count > 0 and status in {
        "submitted", "pending_confirmation", "partial_pending", "pending_signature",
    }
    recoverable = not blocking or (
        age is not None and age >= ttl and not live_blocks_expire
    )

    return {
        "present": True,
        "active": active is not None,
        "status": status,
        "batch_id": (active or raw or {}).get("batch_id"),
        "age_minutes": age,
        "ttl_minutes": ttl,
        "blocking": blocking and not (age is not None and age >= ttl and not live_blocks_expire),
        "recoverable": recoverable or not blocking,
        "live_swaps_prevent_expire": live_blocks_expire,
        "raw_terminal_in_metadata": status in {"failed", "expired", "completed"} and active is None,
    }


def _withdraw_lock_assessment(
    metadata: dict | None,
    *,
    live_sell_count: int,
) -> dict[str, Any]:
    active = get_withdraw_lock(metadata)
    raw = _raw_metadata_lock(metadata, "bundle_withdraw_lock")
    if active is None and raw is None:
        return {"present": False, "blocking": False, "recoverable": True, "status": "none"}

    status = str((active or raw or {}).get("status") or "")
    phase = str((active or raw or {}).get("withdraw_phase") or "")
    age = _lock_age_minutes(active or raw or {})
    ttl = withdraw_lock_ttl_minutes()
    blocking = status in BLOCKING_WITHDRAW_LOCK_STATUSES
    recoverable_status = status in RECOVERABLE_WITHDRAW_LOCK_STATUSES
    live_blocks_expire = live_sell_count > 0 and blocking

    return {
        "present": True,
        "active": active is not None,
        "status": status,
        "withdraw_phase": phase,
        "batch_id": (active or raw or {}).get("batch_id"),
        "requested_release_amount": (active or raw or {}).get("requested_release_amount"),
        "released_amount": (active or raw or {}).get("released_amount"),
        "sell_legs_total": (active or raw or {}).get("sell_legs_total"),
        "sell_legs_confirmed": (active or raw or {}).get("sell_legs_confirmed"),
        "sell_legs_failed": (active or raw or {}).get("sell_legs_failed"),
        "age_minutes": age,
        "ttl_minutes": ttl,
        "blocking": blocking and not (age is not None and age >= ttl and not live_blocks_expire),
        "recoverable": recoverable_status or not blocking,
        "live_sells_prevent_expire": live_blocks_expire,
    }


def _recommendations(payload: dict[str, Any]) -> list[str]:
    recs: list[str] = []
    cash = payload.get("cash_leg", {}).get("available_usdc", 0) or 0
    invest = payload.get("invest_lock", {})
    withdraw = payload.get("withdraw_lock", {})
    live_swaps = [s for s in payload.get("lifi_swaps", []) if s.get("is_live")]
    live_sells = [
        s for s in payload.get("lifi_swaps", [])
        if s.get("is_live") and str(s.get("bundle_action") or "") in ("withdraw_sell", "withdraw")
    ]

    if cash > 0 and not invest.get("blocking"):
        recs.append(
            f"Cash leg USDC disponible ({cash}) — réallocation possible via rebalance ou nouvel invest."
        )
    if invest.get("blocking"):
        if live_swaps:
            recs.append(
                "Invest lock actif avec swap(s) Li.FI vivant(s) — attendre confirmation ou reprendre signature (resume/finalize)."
            )
        elif invest.get("age_minutes") and invest["age_minutes"] >= invest.get("ttl_minutes", 120):
            recs.append(
                "Invest lock stale (> TTL) sans swap vivant — appeler GET active-lock pour reconcile/expire, puis resume ou rebalance."
            )
        else:
            recs.append(
                "Invest lock actif — utiliser POST /bundle/invest/resume ou finaliser les legs pending."
            )
    if withdraw.get("blocking"):
        if live_sells:
            recs.append("Retrait en cours — swaps sell vivants, ne pas release manuellement vers self-trading.")
        else:
            recs.append("Retrait lock actif sans sell vivant — POST /bundle/withdraw/finalize si cash leg prêt.")
    elif withdraw.get("recoverable") and withdraw.get("status") not in ("none", "released"):
        recs.append(
            "Retrait partiel / failed_partial récupérable — finalize pour release du cash confirmé uniquement."
        )
    if not recs:
        recs.append("État nominal — aucune action ops requise (read-only).")
    return recs


def inspect_bundle_state(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    batch_id: str | None = None,
) -> dict[str, Any]:
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.portfolio_type == "bundle_portfolio",
        )
        .first()
    )
    if portfolio is None:
        raise ValueError(f"bundle_portfolio_not_found: {portfolio_id}")

    client = (
        db.query(Client)
        .filter(Client.id == portfolio.client_id, Client.person_id == person_id)
        .first()
    )
    if client is None:
        client = db.query(Client).filter(Client.id == portfolio.client_id).first()
        if client is None or client.person_id != person_id:
            raise ValueError(
                f"person_id {person_id} ne correspond pas au client du portfolio {portfolio_id}"
            )

    entry_instrument = _resolve_entry_instrument(db, portfolio)
    cash_available = Decimal("0")
    if entry_instrument is not None:
        cash_available = resolve_bundle_cash_leg_available(
            db,
            portfolio_id=portfolio_id,
            entry_instrument_id=entry_instrument.id,
        )

    swaps = _bundle_swaps(
        db, person_id=person_id, portfolio_id=portfolio_id, batch_id=batch_id,
    )
    live_swaps = [s for s in swaps if s.get("is_live")]
    live_sells = [
        s for s in live_swaps
        if str(s.get("bundle_action") or "") in ("withdraw_sell", "withdraw", "")
    ]

    invest_lock = _invest_lock_assessment(
        portfolio.metadata_, live_swap_count=len(live_swaps),
    )
    withdraw_lock = _withdraw_lock_assessment(
        portfolio.metadata_, live_sell_count=len(live_sells),
    )

    overall_blocking = invest_lock.get("blocking") or withdraw_lock.get("blocking")
    overall_recoverable = (
        float(cash_available) > 0
        or invest_lock.get("recoverable")
        or withdraw_lock.get("recoverable")
    ) and not overall_blocking

    return {
        "inspected_at": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "person_id": str(person_id),
        "client_id": str(client.id),
        "portfolio_id": str(portfolio_id),
        "portfolio_name": portfolio.name,
        "batch_id_filter": batch_id,
        "cash_leg": {
            "entry_asset": entry_instrument and "USDC",
            "available_usdc": float(cash_available),
            "recoverable_funds_in_bundle": float(cash_available) > 0,
        },
        "spot_legs": _list_spot_legs(db, portfolio_id),
        "invest_lock": invest_lock,
        "withdraw_lock": withdraw_lock,
        "lifi_swaps": swaps,
        "transaction_intents": _bundle_intents(
            db, person_id=person_id, portfolio_id=portfolio_id, batch_id=batch_id,
        ),
        "overall": {
            "blocking": overall_blocking,
            "recoverable": overall_recoverable,
            "live_lifi_swap_count": len(live_swaps),
            "live_withdraw_sell_count": len(live_sells),
        },
        "recommendations": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspection read-only état bundle (ops / debug)",
    )
    parser.add_argument("--person-id", required=True, help="UUID person")
    parser.add_argument("--portfolio-id", required=True, help="UUID bundle portfolio")
    parser.add_argument("--batch-id", default=None, help="Filtrer swaps/intents par batch")
    parser.add_argument("--pretty", action="store_true", default=True)
    args = parser.parse_args()

    person_id = UUID(args.person_id)
    portfolio_id = UUID(args.portfolio_id)
    batch_id = args.batch_id.strip() if args.batch_id else None

    db = SessionLocal()
    try:
        payload = inspect_bundle_state(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
        )
        payload["recommendations"] = _recommendations(payload)
        print(json.dumps(payload, indent=2 if args.pretty else None, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc), "read_only": True}, indent=2), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
