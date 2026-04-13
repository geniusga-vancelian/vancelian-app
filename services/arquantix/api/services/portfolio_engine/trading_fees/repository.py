"""Repository layer for pe_trading_fee_configs."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import TradingFeeConfig


class TradingFeeConfigRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> TradingFeeConfig:
        config = TradingFeeConfig(**data)
        db.add(config)
        db.flush()
        return config

    @staticmethod
    def get_by_id(db: Session, config_id: UUID) -> Optional[TradingFeeConfig]:
        return db.query(TradingFeeConfig).filter(TradingFeeConfig.id == config_id).first()

    @staticmethod
    def list(
        db: Session,
        *,
        scope_type: Optional[str] = None,
        scope_id: Optional[UUID] = None,
        status: Optional[str] = None,
        fee_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[TradingFeeConfig], int]:
        query = db.query(TradingFeeConfig)
        if scope_type:
            query = query.filter(TradingFeeConfig.scope_type == scope_type)
        if scope_id:
            query = query.filter(TradingFeeConfig.scope_id == scope_id)
        if status:
            query = query.filter(TradingFeeConfig.status == status)
        if fee_type:
            query = query.filter(TradingFeeConfig.fee_type == fee_type)
        total = query.count()
        items = query.order_by(TradingFeeConfig.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def update(db: Session, config: TradingFeeConfig, *, data: dict) -> TradingFeeConfig:
        for key, value in data.items():
            col_name = "metadata_" if key == "metadata" else key
            setattr(config, col_name, value)
        db.flush()
        return config

    @staticmethod
    def find_active(
        db: Session,
        scope_type: str,
        scope_id: Optional[UUID],
        at_time,
    ) -> Optional[TradingFeeConfig]:
        """Find the active fee config applicable at a given time."""
        from sqlalchemy import and_, or_

        query = db.query(TradingFeeConfig).filter(
            TradingFeeConfig.scope_type == scope_type,
            TradingFeeConfig.status == "active",
            TradingFeeConfig.valid_from <= at_time,
            or_(
                TradingFeeConfig.valid_to.is_(None),
                TradingFeeConfig.valid_to >= at_time,
            ),
        )
        if scope_id is not None:
            query = query.filter(TradingFeeConfig.scope_id == scope_id)
        else:
            query = query.filter(TradingFeeConfig.scope_id.is_(None))

        return query.order_by(TradingFeeConfig.valid_from.desc()).first()
