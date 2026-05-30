"""Shared read-only helpers for internal scope dry-run."""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from services.portfolio_engine.clients.models import Client

TOLERANCE = Decimal("0.000001")

VAULT_INTEGRATION_MODES = frozenset({"direct_morpho", "ledgity_vault"})
LOMBARD_INTEGRATION_MODE = "lombard_v1"


def resolve_client_id(db: Session, person_id: UUID) -> UUID | None:
    row = db.query(Client.id).filter(Client.person_id == person_id).first()
    return row[0] if row else None


def parse_raw_amount(amount_raw: str | None, decimals: int) -> Decimal:
    raw = Decimal(str(amount_raw or "0"))
    if decimals <= 0:
        return raw
    return raw / (Decimal(10) ** decimals)


def parse_metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def normalize_asset(symbol: str | None) -> str:
    return (symbol or "").strip().upper()


def collateral_symbol_from_metadata(meta: dict[str, Any]) -> str | None:
    collateral = meta.get("collateral")
    if isinstance(collateral, str) and collateral.strip():
        return normalize_asset(collateral)
    if isinstance(collateral, dict):
        sym = collateral.get("symbol") or collateral.get("asset")
        if sym:
            return normalize_asset(str(sym))
    sym = meta.get("collateral_symbol") or meta.get("guarantee_asset")
    return normalize_asset(str(sym)) if sym else None


def collateral_quantity_from_metadata(meta: dict[str, Any], *, decimals: int = 8) -> Decimal | None:
    if meta.get("guarantee_amount_raw") is not None:
        qty = parse_raw_amount(str(meta["guarantee_amount_raw"]), decimals)
        if qty > 0:
            return qty
    if meta.get("guarantee_amount") is not None:
        try:
            qty = Decimal(str(meta["guarantee_amount"]))
            if qty > 0:
                return qty
        except Exception:
            pass
    return None


def borrow_usdc_from_metadata(meta: dict[str, Any], *, fallback_decimals: int = 6) -> Decimal | None:
    if meta.get("borrow_amount_raw") is not None:
        qty = parse_raw_amount(str(meta["borrow_amount_raw"]), fallback_decimals)
        if qty > 0:
            return qty
    if meta.get("borrow_amount") is not None:
        try:
            qty = Decimal(str(meta["borrow_amount"]))
            if qty > 0:
                return qty
        except Exception:
            pass
    return None


def apply_net_delta(
    net: dict[tuple[str, str], Decimal],
    *,
    scope: str,
    asset: str,
    delta: Decimal,
) -> None:
    key = (scope, normalize_asset(asset))
    net[key] = net.get(key, Decimal("0")) + delta


def accumulate_movement_net(
    net: dict[tuple[str, str], Decimal],
    movement: Any,
) -> None:
    asset = normalize_asset(movement.asset)
    apply_net_delta(net, scope=movement.source_scope, asset=asset, delta=-movement.quantity)
    apply_net_delta(net, scope=movement.destination_scope, asset=asset, delta=movement.quantity)


def ovt_table_exists(db: Session) -> bool:
    try:
        r = db.execute(
            sa.text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'onchain_vault_transactions'"
            )
        )
        return r.fetchone() is not None
    except Exception:
        return False


def user_vault_positions_table_exists(db: Session) -> bool:
    try:
        r = db.execute(
            sa.text(
                "SELECT 1 FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = 'user_vault_positions'"
            )
        )
        return r.fetchone() is not None
    except Exception:
        return False
