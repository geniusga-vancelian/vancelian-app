"""Résolution canonique d'une opération client : identité (custody vs exchange)."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from services.exchange.models import ExchangeOrder
from services.portfolio_engine.clients.models import Client
from services.custody.repository import (
    CustodyAccountRepository,
    CustodyTransactionRepository,
)


@dataclass(frozen=True)
class OperationRef:
    """Identité documentaire : même couple que pour un futur OperationStatementPayload."""

    source_system: str  # "custody" | "exchange"
    source_id: UUID


class OperationResolver:
    """Reproduit la logique de résolution de ``get_transaction_detail`` (custody puis exchange)."""

    @staticmethod
    def resolve(db: Session, client: Client, transaction_id: UUID) -> OperationRef | None:
        tx = CustodyTransactionRepository.get_by_id(db, transaction_id)
        if tx is not None:
            account = CustodyAccountRepository.get_by_id(db, tx.account_id)
            if account is None or account.client_id != client.id:
                return None
            return OperationRef(source_system="custody", source_id=transaction_id)

        order = (
            db.query(ExchangeOrder)
            .filter(
                ExchangeOrder.id == transaction_id,
                ExchangeOrder.client_id == client.id,
            )
            .first()
        )
        if order is not None:
            return OperationRef(source_system="exchange", source_id=transaction_id)

        return None
