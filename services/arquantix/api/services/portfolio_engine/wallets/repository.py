"""Repository layer for pe_wallet_containers (Portfolio Engine — ledger layer)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import WalletContainer


class WalletContainerRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> WalletContainer:
        wallet = WalletContainer(**data)
        db.add(wallet)
        db.flush()
        return wallet

    @staticmethod
    def get_by_id(db: Session, wallet_id: UUID) -> Optional[WalletContainer]:
        return db.query(WalletContainer).filter(WalletContainer.id == wallet_id).first()

    @staticmethod
    def list(
        db: Session,
        *,
        client_id: Optional[UUID] = None,
        portfolio_id: Optional[UUID] = None,
        wallet_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[WalletContainer], int]:
        query = db.query(WalletContainer)
        if client_id:
            query = query.filter(WalletContainer.client_id == client_id)
        if portfolio_id:
            query = query.filter(WalletContainer.portfolio_id == portfolio_id)
        if wallet_type:
            query = query.filter(WalletContainer.wallet_type == wallet_type)
        if status:
            query = query.filter(WalletContainer.status == status)
        total = query.count()
        items = query.order_by(WalletContainer.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, wallet: WalletContainer, *, data: dict) -> WalletContainer:
        for key, value in data.items():
            col_name = "metadata_" if key == "metadata" else key
            setattr(wallet, col_name, value)
        db.flush()
        return wallet
