"""Repository layer for pe_orders (Portfolio Engine — transaction layer)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import Order


class OrderRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> Order:
        order = Order(**data)
        db.add(order)
        db.flush()
        return order

    @staticmethod
    def get_by_id(db: Session, order_id: UUID) -> Optional[Order]:
        return db.query(Order).filter(Order.id == order_id).first()

    @staticmethod
    def list(
        db: Session,
        *,
        client_id: Optional[UUID] = None,
        portfolio_id: Optional[UUID] = None,
        order_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[Order], int]:
        query = db.query(Order)
        if client_id:
            query = query.filter(Order.client_id == client_id)
        if portfolio_id:
            query = query.filter(Order.portfolio_id == portfolio_id)
        if order_type:
            query = query.filter(Order.order_type == order_type)
        if status:
            query = query.filter(Order.status == status)
        total = query.count()
        items = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update_status(db: Session, order: Order, *, status: str, rejection_reason: Optional[str] = None) -> Order:
        order.status = status
        if rejection_reason is not None:
            order.rejection_reason = rejection_reason
        db.flush()
        return order
