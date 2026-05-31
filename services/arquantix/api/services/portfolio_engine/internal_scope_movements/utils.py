"""Shared read-only helpers for internal scope dry-run."""
from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.orm import Session

from config.base_allowed_assets import BASE_ALLOWED_ASSETS
from config.supported_swap_assets import SUPPORTED_SWAP_ASSETS
from services.exchange.assets import ASSET_PRECISION
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


def _collateral_decimals_from_metadata(meta: dict[str, Any]) -> int | None:
    for key in ("collateral_decimals", "guarantee_decimals", "guarantee_asset_decimals"):
        value = meta.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
    collateral = meta.get("collateral")
    if isinstance(collateral, dict) and collateral.get("decimals") is not None:
        try:
            return int(collateral["decimals"])
        except (TypeError, ValueError):
            pass
    return None


def resolve_collateral_asset_decimals(
    asset: str | None,
    meta: dict[str, Any],
) -> tuple[int | None, str]:
    """
    Resolve token decimals for Lombard collateral raw amounts (dry-run only).

    Priority: OVT metadata → Base allowed assets / swap registry → exchange precision map.
    No silent default to 8 — unknown assets return (None, "unknown_asset").
    """
    from_meta = _collateral_decimals_from_metadata(meta)
    if from_meta is not None:
        return from_meta, "ovt_metadata"

    sym = normalize_asset(asset)
    if not sym:
        return None, "missing_asset_symbol"

    swap_meta = SUPPORTED_SWAP_ASSETS.get(sym)
    if swap_meta and swap_meta.get("decimals") is not None:
        return int(swap_meta["decimals"]), "supported_swap_assets"

    for row in BASE_ALLOWED_ASSETS:
        if row["symbol"] == sym:
            return int(row["decimals"]), "base_allowed_assets"

    if sym in ASSET_PRECISION:
        return int(ASSET_PRECISION[sym]), "exchange_asset_precision"

    # Aliases not present in BASE_ALLOWED_ASSETS (e.g. WETH on Lombard markets).
    alias_decimals: dict[str, int] = {
        "WETH": 18,
        "WBTC": 8,
    }
    if sym in alias_decimals:
        return alias_decimals[sym], "documented_alias"

    return None, "unknown_asset"


@dataclass(frozen=True)
class CollateralQuantityParse:
    quantity: Decimal | None
    warnings: tuple[str, ...] = ()
    missing_decimals: bool = False
    decimals: int | None = None
    decimals_source: str | None = None


def collateral_quantity_from_metadata(
    meta: dict[str, Any],
    *,
    asset: str | None = None,
) -> CollateralQuantityParse:
    """
    Parse Lombard collateral quantity from OVT metadata (read-only dry-run).

    ``guarantee_amount`` (human-readable) is used as-is when present.
    ``guarantee_amount_raw`` requires resolved decimals — never assumes 8 silently.
    """
    collateral_asset = asset or collateral_symbol_from_metadata(meta)

    if meta.get("guarantee_amount") is not None:
        try:
            qty = Decimal(str(meta["guarantee_amount"]))
            if qty > 0:
                return CollateralQuantityParse(quantity=qty, decimals_source="guarantee_amount")
        except Exception:
            pass

    if meta.get("guarantee_amount_raw") is None:
        return CollateralQuantityParse(quantity=None)

    decimals, source = resolve_collateral_asset_decimals(collateral_asset, meta)
    if decimals is None:
        warning = (
            f"missing_decimals_gap: cannot parse guarantee_amount_raw for collateral "
            f"{collateral_asset or '?'} — no decimals in metadata or asset registry"
        )
        return CollateralQuantityParse(
            quantity=None,
            warnings=(warning,),
            missing_decimals=True,
        )

    qty = parse_raw_amount(str(meta["guarantee_amount_raw"]), decimals)
    if qty <= 0:
        return CollateralQuantityParse(quantity=None, decimals=decimals, decimals_source=source)

    return CollateralQuantityParse(
        quantity=qty,
        decimals=decimals,
        decimals_source=source,
    )


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
