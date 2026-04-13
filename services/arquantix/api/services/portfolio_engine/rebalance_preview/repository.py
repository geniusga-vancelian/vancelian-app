"""Repository layer for pe_rebalance_previews (Portfolio Engine)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import RebalancePreview, RebalancePreviewItem


class RebalancePreviewRepository:

    @staticmethod
    def create(db: Session, *, data: dict, items_data: list[dict]) -> RebalancePreview:
        preview = RebalancePreview(**data)
        db.add(preview)
        db.flush()
        for item_data in items_data:
            item = RebalancePreviewItem(preview_id=preview.id, **item_data)
            db.add(item)
        db.flush()
        return preview

    @staticmethod
    def get_by_id(db: Session, preview_id: UUID) -> Optional[RebalancePreview]:
        return db.query(RebalancePreview).filter(RebalancePreview.id == preview_id).first()

    @staticmethod
    def get_latest_by_portfolio(db: Session, portfolio_id: UUID) -> Optional[RebalancePreview]:
        return (
            db.query(RebalancePreview)
            .filter(RebalancePreview.portfolio_id == portfolio_id)
            .order_by(RebalancePreview.generated_at.desc())
            .first()
        )

    @staticmethod
    def list_by_portfolio(
        db: Session,
        portfolio_id: UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[RebalancePreview], int]:
        query = db.query(RebalancePreview).filter(RebalancePreview.portfolio_id == portfolio_id)
        total = query.count()
        items = query.order_by(RebalancePreview.generated_at.desc()).offset(skip).limit(limit).all()
        return items, total
