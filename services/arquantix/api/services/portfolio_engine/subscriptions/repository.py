"""Repository layer for pe_product_subscriptions
(Portfolio Engine — Subscriptions module)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import ProductSubscription


class SubscriptionRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> ProductSubscription:
        if "metadata" in data:
            data["metadata_"] = data.pop("metadata")
        subscription = ProductSubscription(**data)
        db.add(subscription)
        db.flush()
        return subscription

    @staticmethod
    def get_by_id(db: Session, subscription_id: UUID) -> Optional[ProductSubscription]:
        return db.query(ProductSubscription).filter(ProductSubscription.id == subscription_id).first()

    @staticmethod
    def list(
        db: Session,
        *,
        client_id: Optional[UUID] = None,
        product_id: Optional[UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ProductSubscription], int]:
        query = db.query(ProductSubscription)
        if client_id is not None:
            query = query.filter(ProductSubscription.client_id == client_id)
        if product_id is not None:
            query = query.filter(ProductSubscription.product_id == product_id)
        if status:
            query = query.filter(ProductSubscription.status == status)
        total = query.count()
        items = query.order_by(ProductSubscription.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, subscription: ProductSubscription, *, data: dict) -> ProductSubscription:
        for key, value in data.items():
            col_name = "metadata_" if key == "metadata" else key
            setattr(subscription, col_name, value)
        db.flush()
        return subscription
