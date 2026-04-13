"""Admin endpoints for Exchange Test UI + Crypto Custody overview."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import MarketDataInstrument, MarketDataLatestQuote, get_db
from services.custody.repository import (
    CustodyAccountRepository,
    CustodyBalanceRepository,
)
from services.market_data.fx import get_eurusdt_rate, usdt_to_eur
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.hardening.security.dependencies import require_admin_or_ops

from .assets import ASSET_PRECISION, ASSET_PROVIDER_SYMBOL_MAP, SUPPORTED_ASSETS, get_settlement_wallet_balance
from .service import MAX_QUOTE_AGE_SECONDS
from .custody_repository import (
    ACCOUNT_TYPE_CLIENTS_POOL,
    ACCOUNT_TYPE_SETTLEMENT_WALLET,
    CryptoCustodyAccountRepository,
    CryptoCustodyBalanceRepository,
)
from .models import CryptoPosition, CryptoSettlementDelta, ExchangeOrder
from .repository import CryptoPositionRepository, ExchangeFeeConfigRepository
from .service import ExchangeService

exchange_admin_router = APIRouter(prefix="/api/admin/exchange", tags=["exchange-admin"])
_guard = require_admin_or_ops()


def _fmt(d: Decimal | float | None, decimals: int = 2) -> str:
    if d is None:
        return "0.00"
    return f"{Decimal(str(d)):.{decimals}f}"


# ------------------------------------------------------------------
# GET /api/admin/exchange/context — data for Exchange Test UI
# ------------------------------------------------------------------

@exchange_admin_router.get("/context")
def exchange_test_context(
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    clients = db.query(Client).filter(Client.status == "active").order_by(Client.email).all()

    client_data = []
    for c in clients:
        acct = CustodyAccountRepository.find_client_account(db, c.id, "EUR")
        balance = None
        iban = None
        if acct:
            bal = CustodyBalanceRepository.get_by_account_id(db, acct.id)
            balance = _fmt(bal.available_balance) if bal else "0.00"
            raw = acct.iban or ""
            iban = f"{raw[:4]}{'*' * max(0, len(raw) - 8)}{raw[-4:]}" if len(raw) > 8 else raw

        positions = CryptoPositionRepository.list_by_client(db, c.id)
        pos_map = {p.asset: _fmt(p.balance, ASSET_PRECISION.get(p.asset, 8)) for p in positions}

        client_data.append({
            "id": str(c.id),
            "email": c.email,
            "eur_balance": balance,
            "iban_masked": iban,
            "crypto_positions": pos_map,
        })

    now_utc = datetime.now(timezone.utc)
    try:
        eurusdt_rate = get_eurusdt_rate(db, strict=False)
    except Exception:
        eurusdt_rate = None

    assets = []
    for a in sorted(SUPPORTED_ASSETS):
        fee_bps = ExchangeFeeConfigRepository.get_active_fee_bps(db, a)
        spread_bps = ExchangeFeeConfigRepository.get_active_spread_bps(db, a)

        provider_symbol = ASSET_PROVIDER_SYMBOL_MAP.get(a)
        quote_data: dict[str, Any] = {
            "bid_price": None,
            "ask_price": None,
            "mid_price": None,
            "bid_price_eur": None,
            "ask_price_eur": None,
            "mid_price_eur": None,
            "quote_time": None,
            "is_fresh": False,
        }

        if provider_symbol:
            quote = (
                db.query(MarketDataLatestQuote)
                .join(MarketDataInstrument, MarketDataLatestQuote.instrument_id == MarketDataInstrument.id)
                .filter(MarketDataInstrument.provider_symbol == provider_symbol)
                .first()
            )
            if quote and quote.last_price:
                mid = float(quote.last_price)
                bid = float(quote.bid_price) if quote.bid_price else None
                ask = float(quote.ask_price) if quote.ask_price else None
                quote_data["mid_price"] = mid
                quote_data["bid_price"] = bid
                quote_data["ask_price"] = ask
                if quote.quote_time:
                    qt = quote.quote_time
                    if qt.tzinfo is None:
                        qt = qt.replace(tzinfo=timezone.utc)
                    quote_data["quote_time"] = qt.isoformat()
                    age = (now_utc - qt).total_seconds()
                    quote_data["is_fresh"] = age <= MAX_QUOTE_AGE_SECONDS
                if eurusdt_rate:
                    quote_data["mid_price_eur"] = float(usdt_to_eur(Decimal(str(mid)), eurusdt_rate))
                    if bid:
                        quote_data["bid_price_eur"] = float(usdt_to_eur(Decimal(str(bid)), eurusdt_rate))
                    if ask:
                        quote_data["ask_price_eur"] = float(usdt_to_eur(Decimal(str(ask)), eurusdt_rate))

        assets.append({
            "symbol": a,
            "precision": ASSET_PRECISION.get(a, 8),
            "fee_bps": fee_bps,
            "spread_bps": spread_bps,
            **quote_data,
        })

    return {"clients": client_data, "supported_assets": assets}


# ------------------------------------------------------------------
# GET /api/admin/exchange/crypto-custody — crypto accounts overview (DB-first, legacy fallback)
# ------------------------------------------------------------------

def _build_custody_account_payload(
    account: Any,
    balance: Any,
    pool_balance_override: Optional[Decimal] = None,
) -> dict:
    """Build one account payload with actual_balance, expected_balance, mismatch."""
    actual = Decimal(str(balance.actual_balance)) if balance else Decimal("0")
    expected = Decimal(str(balance.expected_balance)) if balance else Decimal("0")
    if pool_balance_override is not None and account.account_type == ACCOUNT_TYPE_CLIENTS_POOL:
        expected = pool_balance_override
    mismatch = actual - expected
    precision = ASSET_PRECISION.get(account.asset, 8)
    updated_at = None
    if balance and getattr(balance, "updated_from_provider_at", None):
        updated_at = balance.updated_from_provider_at.isoformat()
    return {
        "id": str(account.id),
        "asset": account.asset,
        "account_type": account.account_type,
        "provider": account.provider,
        "label": account.label,
        "status": account.status,
        "actual_balance": _fmt(actual, precision),
        "expected_balance": _fmt(expected, precision),
        "mismatch": _fmt(mismatch, precision),
        "updated_from_provider_at": updated_at,
        "balance": _fmt(actual, precision),
    }


@exchange_admin_router.get("/crypto-custody")
def crypto_custody_summary(
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    db_accounts = CryptoCustodyAccountRepository.list_accounts(db)
    accounts: list[dict] = []

    if db_accounts:
        for acc in db_accounts:
            bal = CryptoCustodyBalanceRepository.get_balance(db, acc.id)
            pool_override = None
            if acc.account_type == ACCOUNT_TYPE_CLIENTS_POOL:
                pool_override = CryptoPositionRepository.get_aggregate_balance(db, acc.asset)
            payload = _build_custody_account_payload(acc, bal, pool_balance_override=pool_override)
            accounts.append(payload)
    else:
        for asset in sorted(SUPPORTED_ASSETS):
            precision = ASSET_PRECISION.get(asset, 8)
            pool_balance = CryptoPositionRepository.get_aggregate_balance(db, asset)
            accounts.append({
                "id": f"pool-{asset.lower()}",
                "asset": asset,
                "account_type": "crypto_clients_pool",
                "type": "crypto_clients_pool",
                "label": f"Clients Pool — {asset}",
                "provider": "Fireblocks",
                "balance": _fmt(pool_balance, precision),
                "actual_balance": None,
                "expected_balance": None,
                "mismatch": None,
                "updated_from_provider_at": None,
                "status": "active",
            })
            wallet_balance = get_settlement_wallet_balance(asset)
            accounts.append({
                "id": f"wallet-{asset.lower()}",
                "asset": asset,
                "account_type": "crypto_settlement_wallet",
                "type": "crypto_settlement_wallet",
                "label": f"Settlement Wallet — {asset}",
                "provider": "Fireblocks",
                "balance": _fmt(wallet_balance, precision),
                "actual_balance": None,
                "expected_balance": None,
                "mismatch": None,
                "updated_from_provider_at": None,
                "status": "active",
            })

    return {"accounts": accounts}


# ------------------------------------------------------------------
# POST /api/admin/exchange/crypto-custody/bootstrap — create technical accounts for all supported assets
# ------------------------------------------------------------------

@exchange_admin_router.post("/crypto-custody/bootstrap")
def crypto_custody_bootstrap(
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    created: list[dict] = []
    for asset in sorted(SUPPORTED_ASSETS):
        for account_type in (ACCOUNT_TYPE_CLIENTS_POOL, ACCOUNT_TYPE_SETTLEMENT_WALLET):
            acc = CryptoCustodyAccountRepository.get_or_create_account(db, asset, account_type)
            CryptoCustodyBalanceRepository.get_or_create_balance(db, acc.id, asset)
            created.append({
                "id": str(acc.id),
                "asset": asset,
                "account_type": account_type,
                "label": acc.label,
            })
    db.commit()
    return {"status": "ok", "created": created, "count": len(created)}


# ------------------------------------------------------------------
# GET /api/admin/exchange/crypto-custody/{account_id} — detail one technical account
# ------------------------------------------------------------------

@exchange_admin_router.get("/crypto-custody/{account_id}")
def crypto_custody_account_detail(
    account_id: str,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    from .custody_models import CryptoCustodyAccount
    try:
        uid = UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid account id")
    acc = db.query(CryptoCustodyAccount).filter(CryptoCustodyAccount.id == uid).first()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    bal = CryptoCustodyBalanceRepository.get_balance(db, acc.id)
    pool_override = CryptoPositionRepository.get_aggregate_balance(db, acc.asset) if acc.account_type == ACCOUNT_TYPE_CLIENTS_POOL else None
    return _build_custody_account_payload(acc, bal, pool_balance_override=pool_override)


# ------------------------------------------------------------------
# POST /api/admin/exchange/crypto-custody/{id}/set-actual-balance — seed actual balance (admin, pre-Fireblocks)
# ------------------------------------------------------------------

class SetActualBalanceBody(BaseModel):
    actual_balance: str  # decimal string


@exchange_admin_router.post("/crypto-custody/{account_id}/set-actual-balance")
def set_actual_balance(
    account_id: str,
    body: SetActualBalanceBody,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        uid = UUID(account_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid account id")
    from .custody_models import CryptoCustodyAccount
    acc = db.query(CryptoCustodyAccount).filter(CryptoCustodyAccount.id == uid).first()
    if not acc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    bal = CryptoCustodyBalanceRepository.get_or_create_balance(db, acc.id, acc.asset)
    new_balance = Decimal(body.actual_balance)
    CryptoCustodyBalanceRepository.update_actual_balance(db, acc.id, new_balance, provider_timestamp=None)
    db.commit()
    return {
        "status": "ok",
        "account_id": str(acc.id),
        "asset": acc.asset,
        "account_type": acc.account_type,
        "actual_balance": str(new_balance),
    }


# ------------------------------------------------------------------
# GET /api/admin/exchange/crypto-custody/{account_id}/history
# ------------------------------------------------------------------

@exchange_admin_router.get("/crypto-custody/{account_id}/history")
def crypto_account_history(
    account_id: str,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
    limit: int = Query(50, ge=1, le=200),
):
    from .custody_models import CryptoCustodyAccount
    account_type: Optional[str] = None
    asset: Optional[str] = None
    try:
        uid = UUID(account_id)
        acc = db.query(CryptoCustodyAccount).filter(CryptoCustodyAccount.id == uid).first()
        if acc:
            account_type = acc.account_type
            asset = acc.asset
    except ValueError:
        pass
    if account_type is None or asset is None:
        parts = account_id.split("-", 1)
        if len(parts) != 2:
            return {"movements": []}
        account_type, asset_lower = parts
        asset = asset_lower.upper()
        account_type = "crypto_clients_pool" if account_type == "pool" else "crypto_settlement_wallet"

    if account_type == ACCOUNT_TYPE_CLIENTS_POOL or account_type == "pool":
        orders = (
            db.query(ExchangeOrder)
            .filter(ExchangeOrder.asset == asset, ExchangeOrder.status == "completed")
            .order_by(ExchangeOrder.created_at.desc())
            .limit(limit)
            .all()
        )
        movements = []
        for o in orders:
            precision = ASSET_PRECISION.get(asset, 8)
            direction = "credit" if o.side == "buy" else "debit"
            reason = f"Achat client — {asset}" if o.side == "buy" else f"Vente client — {asset}"
            movements.append({
                "date": o.created_at.isoformat() if o.created_at else None,
                "kind": f"exchange_{o.side}",
                "direction": direction,
                "amount": _fmt(o.amount_crypto, precision),
                "asset": asset,
                "status": o.status,
                "reason": reason,
                "external_reference": o.external_reference,
                "client_id": str(o.client_id),
            })
        return {"movements": movements}

    elif account_type == ACCOUNT_TYPE_SETTLEMENT_WALLET or account_type == "wallet":
        deltas = (
            db.query(CryptoSettlementDelta)
            .filter(CryptoSettlementDelta.asset == asset)
            .order_by(CryptoSettlementDelta.settlement_date.desc())
            .limit(limit)
            .all()
        )
        movements = []
        for d in deltas:
            precision = ASSET_PRECISION.get(asset, 8)
            amount = Decimal(str(d.delta_amount))
            direction = "debit" if amount > 0 else "credit"
            status = "settled" if d.settled else "pending"
            reason = f"Settlement fin de journée — {asset}"
            movements.append({
                "date": d.settlement_date.isoformat() if d.settlement_date else None,
                "kind": "settlement",
                "direction": direction,
                "amount": _fmt(abs(amount), precision),
                "asset": asset,
                "status": status,
                "reason": reason,
                "external_reference": None,
            })
        return {"movements": movements}

    return {"movements": []}


# ------------------------------------------------------------------
# POST /api/admin/exchange/run-settlement — trigger settlement from UI
# ------------------------------------------------------------------

@exchange_admin_router.post("/run-settlement")
def admin_run_settlement(
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    svc = ExchangeService()
    result = svc.run_settlement(db, actor)

    assets_processed = set()
    for d in result.get("details", []):
        if d.get("asset"):
            assets_processed.add(d["asset"])

    return {
        "status": "completed",
        "assets_processed": len(assets_processed),
        "deltas_settled": result.get("settled_count", 0),
        "blocked_count": result.get("blocked_count", 0),
        "details": result.get("details", []),
    }
