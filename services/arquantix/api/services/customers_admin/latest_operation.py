"""Dernière transaction « opération » (custody ou exchange) pour un client PE — PDF relevé unitaire."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import desc as sql_desc
from sqlalchemy.orm import Session

from services.custody.models import CustodyAccount, CustodyTransaction
from services.exchange.models import ExchangeOrder
from services.portfolio_engine.clients.models import Client as PeClient


def find_latest_completed_operation_transaction_id(
    db: Session,
    client: PeClient,
) -> Optional[UUID]:
    """
    Retourne l'UUID de la transaction custody ou de l'ordre exchange le plus récent
    (``status == completed``), pour résolution identique à ``OperationResolver``.
    """
    best_id: Optional[UUID] = None
    best_ts: Optional[datetime] = None

    accounts = db.query(CustodyAccount).filter(CustodyAccount.client_id == client.id).all()
    for acc in accounts:
        tx = (
            db.query(CustodyTransaction)
            .filter(
                CustodyTransaction.account_id == acc.id,
                CustodyTransaction.status == "completed",
            )
            .order_by(sql_desc(CustodyTransaction.created_at), sql_desc(CustodyTransaction.id))
            .first()
        )
        if tx is not None and (best_ts is None or tx.created_at > best_ts):
            best_ts = tx.created_at
            best_id = tx.id

    order = (
        db.query(ExchangeOrder)
        .filter(
            ExchangeOrder.client_id == client.id,
            ExchangeOrder.status == "completed",
        )
        .order_by(sql_desc(ExchangeOrder.created_at))
        .first()
    )
    if order is not None and (best_ts is None or order.created_at > best_ts):
        best_id = order.id

    return best_id
