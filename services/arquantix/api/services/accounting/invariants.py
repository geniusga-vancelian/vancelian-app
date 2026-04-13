"""PnL accounting invariants check.

Computes portfolio-level invariants for diagnostic and test purposes.
Method: Weighted Average Cost (WAC).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from services.custody.enums import TransactionDirection, TransactionKind, TransactionType
from services.custody.models import CustodyAccount, CustodyAccountBalance, CustodyTransaction
from services.exchange.assets import ASSET_PROVIDER_SYMBOL_MAP
from services.exchange.models import CryptoPosition, ExchangeOrder
from services.market_data.fx import get_eurusdt_rate, usdt_to_eur
from database import MarketDataInstrument, MarketDataLatestQuote


def _dec(v: Any) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


def _get_client_eur_balance(db: Session, client_id: UUID) -> Decimal:
    """Return client's EUR available balance from custody."""
    acc = (
        db.query(CustodyAccount)
        .filter(
            CustodyAccount.client_id == client_id,
            CustodyAccount.currency == "EUR",
            CustodyAccount.account_type == "client_deposit_account",
        )
        .first()
    )
    if acc is None:
        return Decimal("0")
    bal = (
        db.query(CustodyAccountBalance)
        .filter(CustodyAccountBalance.account_id == acc.id)
        .first()
    )
    return _dec(bal.available_balance) if bal else Decimal("0")


def _get_crypto_value_eur(db: Session, client_id: UUID) -> Decimal:
    """Return mark-to-market value of all crypto positions in EUR."""
    positions = (
        db.query(CryptoPosition)
        .filter(CryptoPosition.client_id == client_id, CryptoPosition.balance > 0)
        .all()
    )
    eurusdt_rate = get_eurusdt_rate(db, strict=False)
    total = Decimal("0")
    for pos in positions:
        ps = ASSET_PROVIDER_SYMBOL_MAP.get(pos.asset, f"{pos.asset}USDT")
        inst = (
            db.query(MarketDataInstrument)
            .filter(MarketDataInstrument.provider_symbol == ps)
            .first()
        )
        if inst:
            quote = (
                db.query(MarketDataLatestQuote)
                .filter(MarketDataLatestQuote.instrument_id == inst.id)
                .first()
            )
            if quote and quote.last_price:
                price_eur = usdt_to_eur(Decimal(str(quote.last_price)), eurusdt_rate)
                total += _dec(pos.balance) * price_eur
    return total


def _get_net_external_cash_flows(db: Session, client_id: UUID) -> Decimal:
    """Return deposits - withdrawals (external flows only: BANK_TRANSFER_IN/OUT or simulated, EUR)."""
    from sqlalchemy import or_

    acc = (
        db.query(CustodyAccount)
        .filter(
            CustodyAccount.client_id == client_id,
            CustodyAccount.currency == "EUR",
        )
        .first()
    )
    if acc is None:
        return Decimal("0")

    # External deposits: BANK_TRANSFER_IN or (simulated: deposit + credit, no transaction_kind)
    deposits = (
        db.query(func.coalesce(func.sum(CustodyTransaction.amount), 0))
        .filter(
            CustodyTransaction.account_id == acc.id,
            CustodyTransaction.direction == TransactionDirection.CREDIT.value,
            CustodyTransaction.status == "completed",
            or_(
                CustodyTransaction.transaction_kind == TransactionKind.BANK_TRANSFER_IN.value,
                (
                    (CustodyTransaction.transaction_kind.is_(None))
                    & (CustodyTransaction.transaction_type == TransactionType.DEPOSIT.value)
                ),
            ),
        )
        .scalar()
    )
    # External withdrawals: BANK_TRANSFER_OUT or (simulated: withdrawal + debit, no transaction_kind)
    withdrawals = (
        db.query(func.coalesce(func.sum(CustodyTransaction.amount), 0))
        .filter(
            CustodyTransaction.account_id == acc.id,
            CustodyTransaction.direction == TransactionDirection.DEBIT.value,
            CustodyTransaction.status == "completed",
            or_(
                CustodyTransaction.transaction_kind == TransactionKind.BANK_TRANSFER_OUT.value,
                (
                    (CustodyTransaction.transaction_kind.is_(None))
                    & (CustodyTransaction.transaction_type == TransactionType.WITHDRAWAL.value)
                ),
            ),
        )
        .scalar()
    )
    return _dec(deposits) - _dec(withdrawals)


def _get_realized_unrealized(db: Session, client_id: UUID) -> tuple[Decimal, Decimal]:
    """Return (realized_pnl, unrealized_pnl) in EUR using WAC."""
    from services.wallet_statistics.service import build_wallet_statistics

    positions = (
        db.query(CryptoPosition)
        .filter(CryptoPosition.client_id == client_id, CryptoPosition.balance > 0)
        .all()
    )
    orders = (
        db.query(ExchangeOrder)
        .filter(
            ExchangeOrder.client_id == client_id,
            ExchangeOrder.status == "completed",
        )
        .all()
    )
    traded_assets = {o.asset for o in orders}
    realized = Decimal("0")
    unrealized = Decimal("0")
    for asset in traded_assets:
        stats = build_wallet_statistics(db, client_id, asset, reference_currency="EUR")
        realized += _dec(stats.get("realized_pnl", 0))
        unrealized += _dec(stats.get("unrealized_pnl", 0))
    return (realized, unrealized)


def compute_pnl_invariants(db: Session, client_id: UUID) -> dict:
    """Compute portfolio invariants A, B, C for a client.

    Returns:
        - nav: cash_eur + crypto_value
        - cash_eur
        - crypto_value
        - realized_pnl
        - unrealized_pnl
        - total_pnl
        - net_external_cash_flows
        - invariant_a_ok: NAV == cash_eur + crypto_value
        - invariant_b_ok: total_pnl == realized + unrealized
        - invariant_c_ok: NAV == net_external_cash_flows + realized + unrealized
    """
    cash_eur = _get_client_eur_balance(db, client_id)
    crypto_value = _get_crypto_value_eur(db, client_id)
    nav = cash_eur + crypto_value
    realized, unrealized = _get_realized_unrealized(db, client_id)
    total_pnl = realized + unrealized
    net_flows = _get_net_external_cash_flows(db, client_id)

    # Invariant A: NAV = cash + crypto
    invariant_a_ok = abs(nav - (cash_eur + crypto_value)) < Decimal("0.01")

    # Invariant B: total_pnl = realized + unrealized
    invariant_b_ok = abs(total_pnl - (realized + unrealized)) < Decimal("0.01")

    # Invariant C: NAV = net_flows + realized + unrealized
    rhs_c = net_flows + realized + unrealized
    invariant_c_ok = abs(nav - rhs_c) < Decimal("0.01")

    return {
        "client_id": str(client_id),
        "nav": float(nav.quantize(Decimal("0.01"))),
        "cash_eur": float(cash_eur.quantize(Decimal("0.01"))),
        "crypto_value": float(crypto_value.quantize(Decimal("0.01"))),
        "realized_pnl": float(realized.quantize(Decimal("0.01"))),
        "unrealized_pnl": float(unrealized.quantize(Decimal("0.01"))),
        "total_pnl": float(total_pnl.quantize(Decimal("0.01"))),
        "net_external_cash_flows": float(net_flows.quantize(Decimal("0.01"))),
        "invariant_a_ok": invariant_a_ok,
        "invariant_b_ok": invariant_b_ok,
        "invariant_c_ok": invariant_c_ok,
        "all_ok": invariant_a_ok and invariant_b_ok and invariant_c_ok,
    }
