"""Fusion des soldes Privy on-chain dans le patrimoine crypto client (PE + Privy)."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.market_data.fx import get_eurusdt_rate, usdt_to_eur
from services.privy_wallet.repository import PersonWalletBalanceRepository
from services.privy_wallet.service import _format_decimal
from services.test_clients.schemas import ASSET_NAMES


def merge_app_crypto_positions(
    platform_positions: list[dict[str, Any]],
    db: Session,
    *,
    person_id: UUID | None,
) -> list[dict[str, Any]]:
    """Fusionne ``crypto_positions`` PE et ``person_wallet_balances`` Privy.

    Retourne des dicts compatibles ``CryptoPositionPayload`` (champ ``balance`` = total).
    """
    if person_id is None:
        return list(platform_positions)

    privy_rows = [
        row
        for row in PersonWalletBalanceRepository().list_for_person(db, person_id)
        if Decimal(str(row.balance)) > 0
    ]
    if not privy_rows and not platform_positions:
        return []

    eurusdt_rate = get_eurusdt_rate(db, strict=False)
    merged: dict[str, dict[str, Any]] = {}

    for pos in platform_positions:
        asset = str(pos.get("asset") or "").upper()
        if not asset:
            continue
        merged[asset] = {
            **pos,
            "asset": asset,
            "name": pos.get("name") or ASSET_NAMES.get(asset, asset),
            "platform_balance": str(pos.get("balance") or "0"),
            "platform_available": str(pos.get("available_balance") or "0"),
            "privy_balance": "0",
            "privy_available": "0",
        }

    for row in privy_rows:
        asset = str(row.asset or "").upper()
        if not asset:
            continue
        privy_bal = _format_decimal(row.balance)
        privy_avail = _format_decimal(row.available_balance)
        if asset not in merged:
            price_eur, est_eur, price_usd, est_usd = _price_asset(
                db, asset, privy_bal, eurusdt_rate
            )
            merged[asset] = {
                "asset": asset,
                "name": ASSET_NAMES.get(asset, asset),
                "balance": privy_bal,
                "available_balance": privy_avail,
                "platform_balance": "0",
                "platform_available": "0",
                "privy_balance": privy_bal,
                "privy_available": privy_avail,
                "price_eur": price_eur,
                "estimated_value_eur": est_eur,
                "price_usd": price_usd,
                "estimated_value_usd": est_usd,
                "performance_1d_pct": None,
                "icon_key": asset.lower(),
                "portfolio_scope": "privy",
            }
        else:
            entry = merged[asset]
            entry["privy_balance"] = privy_bal
            entry["privy_available"] = privy_avail
            total_bal = Decimal(str(entry["platform_balance"])) + Decimal(privy_bal)
            total_avail = Decimal(str(entry["platform_available"])) + Decimal(privy_avail)
            price_eur, est_eur, price_usd, est_usd = _price_asset(
                db, asset, str(total_bal), eurusdt_rate
            )
            entry["balance"] = _format_decimal(total_bal)
            entry["available_balance"] = _format_decimal(total_avail)
            if est_eur:
                entry["estimated_value_eur"] = est_eur
            if price_eur:
                entry["price_eur"] = price_eur
            if est_usd:
                entry["estimated_value_usd"] = est_usd
            if price_usd:
                entry["price_usd"] = price_usd
            if privy_bal != "0" and entry["platform_balance"] != "0":
                entry["portfolio_scope"] = "merged"

    out: list[dict[str, Any]] = []
    for asset, entry in merged.items():
        if Decimal(str(entry.get("balance") or "0")) <= 0:
            continue
        if "platform_balance" not in entry:
            entry["platform_balance"] = str(entry.get("balance") or "0")
            entry["platform_available"] = str(entry.get("available_balance") or "0")
            entry["privy_balance"] = "0"
            entry["privy_available"] = "0"
        out.append(entry)

    out.sort(
        key=lambda x: Decimal(str(x.get("estimated_value_eur") or "0")),
        reverse=True,
    )
    return out


def privy_nav_eur(db: Session, person_id: UUID | None) -> Decimal:
    """Valeur EUR des seuls soldes Privy (hors double-comptage plateforme)."""
    if person_id is None:
        return Decimal("0")
    eurusdt_rate = get_eurusdt_rate(db, strict=False)
    total = Decimal("0")
    for row in PersonWalletBalanceRepository().list_for_person(db, person_id):
        bal = Decimal(str(row.balance))
        if bal <= 0:
            continue
        _, est_eur, _, _ = _price_asset(db, str(row.asset), _format_decimal(bal), eurusdt_rate)
        if est_eur:
            total += Decimal(est_eur)
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def find_merged_position(
    db: Session,
    *,
    person_id: UUID | None,
    asset: str,
    platform_positions: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    asset_u = asset.strip().upper()
    merged = merge_app_crypto_positions(platform_positions or [], db, person_id=person_id)
    return next((p for p in merged if str(p.get("asset") or "").upper() == asset_u), None)


def _price_asset(
    db: Session,
    asset: str,
    balance: str,
    eurusdt_rate: Decimal,
) -> tuple[str | None, str | None, str | None, str | None]:
    from database import MarketDataInstrument, MarketDataLatestQuote
    from services.exchange.assets import ASSET_PROVIDER_SYMBOL_MAP

    bal = Decimal(str(balance))
    if bal <= 0:
        return None, None, None, None
    provider_symbol = ASSET_PROVIDER_SYMBOL_MAP.get(asset.upper())
    if not provider_symbol:
        return None, None, None, None
    inst = (
        db.query(MarketDataInstrument)
        .filter(MarketDataInstrument.provider_symbol == provider_symbol)
        .first()
    )
    if not inst:
        return None, None, None, None
    quote = (
        db.query(MarketDataLatestQuote)
        .filter(MarketDataLatestQuote.instrument_id == inst.id)
        .first()
    )
    if not quote or quote.last_price is None:
        return None, None, None, None
    p_usdt = Decimal(str(quote.last_price))
    p_eur = usdt_to_eur(p_usdt, eurusdt_rate)
    val_eur = (bal * p_eur).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    val_usd = (bal * p_usdt).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{p_eur:.2f}", f"{val_eur:.2f}", f"{p_usdt:.2f}", f"{val_usd:.2f}"
