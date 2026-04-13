"""Repository layer for pe_execution_instructions (Portfolio Engine — execution layer)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import ExecutionInstruction


class ExecutionRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> ExecutionInstruction:
        instruction = ExecutionInstruction(**data)
        db.add(instruction)
        db.flush()
        return instruction

    @staticmethod
    def get_by_id(db: Session, execution_id: UUID) -> Optional[ExecutionInstruction]:
        return db.query(ExecutionInstruction).filter(ExecutionInstruction.id == execution_id).first()

    @staticmethod
    def list(
        db: Session,
        *,
        order_id: Optional[UUID] = None,
        venue: Optional[str] = None,
        execution_type: Optional[str] = None,
        status: Optional[str] = None,
        instrument_id: Optional[UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ExecutionInstruction], int]:
        query = db.query(ExecutionInstruction)
        if order_id:
            query = query.filter(ExecutionInstruction.order_id == order_id)
        if venue:
            query = query.filter(ExecutionInstruction.venue == venue)
        if execution_type:
            query = query.filter(ExecutionInstruction.execution_type == execution_type)
        if status:
            query = query.filter(ExecutionInstruction.status == status)
        if instrument_id:
            query = query.filter(ExecutionInstruction.instrument_id == instrument_id)
        total = query.count()
        items = query.order_by(ExecutionInstruction.requested_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update_fields(db: Session, instruction: ExecutionInstruction, **kwargs) -> ExecutionInstruction:
        for key, value in kwargs.items():
            setattr(instruction, key, value)
        db.flush()
        return instruction
