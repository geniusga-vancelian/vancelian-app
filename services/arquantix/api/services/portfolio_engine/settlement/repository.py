"""Repository layer for pe_settlement_instructions (Portfolio Engine — settlement layer).

No DELETE method provided. Settlement instructions are never deleted.
Status transitions are handled through the service layer.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import SettlementInstruction


class SettlementRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> SettlementInstruction:
        instruction = SettlementInstruction(**data)
        db.add(instruction)
        db.flush()
        return instruction

    @staticmethod
    def get_by_id(db: Session, settlement_id: UUID) -> Optional[SettlementInstruction]:
        return (
            db.query(SettlementInstruction)
            .filter(SettlementInstruction.id == settlement_id)
            .first()
        )

    @staticmethod
    def list(
        db: Session,
        *,
        order_id: Optional[UUID] = None,
        trade_id: Optional[UUID] = None,
        settlement_group_id: Optional[UUID] = None,
        settlement_type: Optional[str] = None,
        status: Optional[str] = None,
        from_account_id: Optional[UUID] = None,
        to_account_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[SettlementInstruction], int]:
        query = db.query(SettlementInstruction)
        if order_id:
            query = query.filter(SettlementInstruction.order_id == order_id)
        if trade_id:
            query = query.filter(SettlementInstruction.trade_id == trade_id)
        if settlement_group_id:
            query = query.filter(SettlementInstruction.settlement_group_id == settlement_group_id)
        if settlement_type:
            query = query.filter(SettlementInstruction.settlement_type == settlement_type)
        if status:
            query = query.filter(SettlementInstruction.status == status)
        if from_account_id:
            query = query.filter(SettlementInstruction.from_account_id == from_account_id)
        if to_account_id:
            query = query.filter(SettlementInstruction.to_account_id == to_account_id)
        total = query.count()
        items = query.order_by(SettlementInstruction.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update_status(
        db: Session,
        instruction: SettlementInstruction,
        *,
        status: str,
        **kwargs,
    ) -> SettlementInstruction:
        instruction.status = status
        for key, value in kwargs.items():
            setattr(instruction, key, value)
        db.flush()
        return instruction
