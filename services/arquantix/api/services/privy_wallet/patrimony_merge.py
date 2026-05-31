"""Fusion des soldes Privy on-chain dans le patrimoine crypto client (PE + Privy)."""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.market_data.fx import get_eurusdt_rate, usdt_to_eur
from services.privy_wallet.chain_balance import (
    aggregate_confirmed_deposit_balances,
    reconcile_chain_buckets_with_ledger,
)
from services.privy_wallet.dedicated_wallet_assets import dedicated_wallet_placeholders_for_person
from services.privy_wallet.repository import PersonCryptoWalletRepository, PersonWalletBalanceRepository
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

    privy_wallets = PersonCryptoWalletRepository().list_active_for_person(db, person_id)
    wallet_by_id = {wallet.id: wallet for wallet in privy_wallets}
    chain_buckets = reconcile_chain_buckets_with_ledger(
        db,
        person_id=person_id,
        wallets=privy_wallets,
        buckets=aggregate_confirmed_deposit_balances(
            db,
            person_id=person_id,
            wallets=privy_wallets,
        ),
    )
    assets_with_positive = {bucket.asset for bucket in chain_buckets}
    dedicated_placeholders = dedicated_wallet_placeholders_for_person(
        db,
        person_id=person_id,
        exclude_assets=assets_with_positive,
    )
    if not chain_buckets and not platform_positions and not dedicated_placeholders:
        return []

    eurusdt_rate = get_eurusdt_rate(db, strict=False)
    merged: dict[str, dict[str, Any]] = {}

    def _merge_key(asset: str, chain_id: int | None) -> str:
        return f"{asset}:{chain_id if chain_id is not None else 'none'}"

    for pos in platform_positions:
        asset = str(pos.get("asset") or "").upper()
        if not asset:
            continue
        key = _merge_key(asset, pos.get("chain_id"))
        merged[key] = {
            **pos,
            "asset": asset,
            "name": pos.get("name") or ASSET_NAMES.get(asset, asset),
            "platform_balance": str(pos.get("balance") or "0"),
            "platform_available": str(pos.get("available_balance") or "0"),
            "trading_available": str(pos.get("trading_available") or "0"),
            "privy_balance": "0",
            "privy_available": "0",
            "chain_id": pos.get("chain_id"),
            "chain_type": pos.get("chain_type"),
        }

    for bucket in chain_buckets:
        asset = bucket.asset
        wallet = wallet_by_id.get(bucket.wallet_id)
        privy_bal = _format_decimal(bucket.balance)
        privy_avail = privy_bal
        chain_id = bucket.chain_id if bucket.chain_id > 0 else None
        chain_type = wallet.chain_type if wallet else "ethereum"
        if chain_id == 0:
            chain_type = "solana"
        key = _merge_key(asset, chain_id)
        if key not in merged:
            price_eur, est_eur, price_usd, est_usd = _price_asset(
                db, asset, privy_bal, eurusdt_rate
            )
            merged[key] = {
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
                "chain_id": chain_id,
                "chain_type": chain_type,
                "wallet_address": wallet.address if wallet else None,
            }
        else:
            entry = merged[key]
            entry["privy_balance"] = privy_bal
            entry["privy_available"] = privy_avail
            if chain_id is not None:
                entry["chain_id"] = chain_id
            if chain_type:
                entry["chain_type"] = chain_type
            if wallet and wallet.address:
                entry["wallet_address"] = wallet.address
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

    for placeholder in dedicated_placeholders:
        asset = str(placeholder.get("asset") or "").upper()
        if not asset:
            continue
        chain_id = placeholder.get("chain_id")
        key = _merge_key(asset, chain_id if isinstance(chain_id, int) else None)
        if key in merged:
            continue
        merged[key] = placeholder

    out: list[dict[str, Any]] = []
    for _, entry in merged.items():
        balance = Decimal(str(entry.get("balance") or "0"))
        if balance <= 0 and not entry.get("dedicated_wallet"):
            continue
        if "platform_balance" not in entry:
            entry["platform_balance"] = str(entry.get("balance") or "0")
            entry["platform_available"] = str(entry.get("available_balance") or "0")
            entry["trading_available"] = str(entry.get("trading_available") or "0")
            entry["privy_balance"] = "0"
            entry["privy_available"] = "0"
        elif "trading_available" not in entry:
            entry["trading_available"] = "0"
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
    chain_id: int | None = None,
) -> dict[str, Any] | None:
    """Retourne la position fusionnée pour un actif, optionnellement filtrée par ``chain_id`` (ex. 8453 = Base)."""
    asset_u = asset.strip().upper()
    merged = merge_app_crypto_positions(platform_positions or [], db, person_id=person_id)
    candidates = [p for p in merged if str(p.get("asset") or "").upper() == asset_u]
    if not candidates:
        return None
    if chain_id is not None:
        scoped = [
            p
            for p in candidates
            if p.get("chain_id") is not None and int(p.get("chain_id")) == int(chain_id)
        ]
        if scoped:
            return scoped[0]
        return None
    return candidates[0]


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

    asset_u = asset.upper()
    if asset_u == "EURC":
        p_eur = Decimal("1")
        val_eur = (bal * p_eur).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        p_usdt = (p_eur * eurusdt_rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        val_usd = (bal * p_usdt).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{p_eur:.2f}", f"{val_eur:.2f}", f"{p_usdt:.2f}", f"{val_usd:.2f}"
    if asset_u == "USDT":
        p_usdt = Decimal("1")
        p_eur = usdt_to_eur(p_usdt, eurusdt_rate)
        val_eur = (bal * p_eur).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        val_usd = (bal * p_usdt).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return f"{p_eur:.2f}", f"{val_eur:.2f}", f"{p_usdt:.2f}", f"{val_usd:.2f}"

    provider_symbol = ASSET_PROVIDER_SYMBOL_MAP.get(asset_u)
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
