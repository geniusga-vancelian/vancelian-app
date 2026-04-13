"""Signaux métier : premier dépôt, premier investissement (hors dépôt cash)."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from services.custody.enums import TransactionStatus, TransactionType
from services.custody.models import CustodyAccount, CustodyAccountBalance, CustodyTransaction
from services.exchange.models import CryptoPosition, ExchangeOrder
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.orders.models import Order as PeOrder


def has_first_deposit(db: Session, client: Client) -> bool:
    """True si solde custody > 0 ou au moins un dépôt complété."""
    cid = client.id
    bal = (
        db.query(CustodyAccountBalance.id)
        .join(CustodyAccount, CustodyAccountBalance.account_id == CustodyAccount.id)
        .filter(
            CustodyAccount.client_id == cid,
            CustodyAccountBalance.available_balance > 0,
        )
        .first()
    )
    if bal is not None:
        return True
    tx = (
        db.query(CustodyTransaction.id)
        .join(CustodyAccount, CustodyTransaction.account_id == CustodyAccount.id)
        .filter(
            CustodyAccount.client_id == cid,
            CustodyTransaction.transaction_type == TransactionType.DEPOSIT.value,
            CustodyTransaction.status == TransactionStatus.COMPLETED.value,
        )
        .first()
    )
    return tx is not None


def has_first_investment(db: Session, client: Client) -> bool:
    """True si ordre exchange complété, ordre PE abouti, ou position crypto non nulle."""
    cid = client.id
    ex = (
        db.query(ExchangeOrder.id)
        .filter(
            ExchangeOrder.client_id == cid,
            ExchangeOrder.status == "completed",
        )
        .first()
    )
    if ex is not None:
        return True
    pe = (
        db.query(PeOrder.id)
        .filter(
            PeOrder.client_id == cid,
            PeOrder.status.in_(("filled", "completed", "settled", "executed")),
        )
        .first()
    )
    if pe is not None:
        return True
    pos = (
        db.query(CryptoPosition.id)
        .filter(
            CryptoPosition.client_id == cid,
            CryptoPosition.available_balance > Decimal("0"),
        )
        .first()
    )
    return pos is not None
