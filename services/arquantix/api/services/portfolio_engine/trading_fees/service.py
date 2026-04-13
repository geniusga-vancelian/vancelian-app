"""Service layer for TradingFeeConfig module."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import TradingFeeConfig
from .repository import TradingFeeConfigRepository
from .schemas import TradingFeeConfigCreate, TradingFeeConfigUpdate, FeeCalculationResult


class FeeConfigNotFoundError(Exception):
    def __init__(self, config_id: UUID):
        self.config_id = config_id
        super().__init__(f"TradingFeeConfig {config_id} not found")


class NoApplicableFeeConfigError(Exception):
    def __init__(self, scope_type: str, scope_id: Optional[UUID]):
        super().__init__(
            f"No active fee config found for scope_type={scope_type}, scope_id={scope_id}"
        )


class TradingFeeConfigService:

    def __init__(self) -> None:
        self._repo = TradingFeeConfigRepository()

    def create_config(self, db: Session, payload: TradingFeeConfigCreate) -> TradingFeeConfig:
        data = payload.model_dump()
        data["metadata_"] = data.pop("metadata")
        return self._repo.create(db, data=data)

    def get_config(self, db: Session, config_id: UUID) -> TradingFeeConfig:
        config = self._repo.get_by_id(db, config_id)
        if config is None:
            raise FeeConfigNotFoundError(config_id)
        return config

    def list_configs(
        self,
        db: Session,
        *,
        scope_type: Optional[str] = None,
        scope_id: Optional[UUID] = None,
        status: Optional[str] = None,
        fee_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[TradingFeeConfig], int]:
        return self._repo.list(
            db, scope_type=scope_type, scope_id=scope_id,
            status=status, fee_type=fee_type,
            skip=skip, limit=limit,
        )

    def update_config(
        self, db: Session, config_id: UUID, payload: TradingFeeConfigUpdate
    ) -> TradingFeeConfig:
        config = self.get_config(db, config_id)
        data = payload.model_dump(exclude_unset=True)
        return self._repo.update(db, config, data=data)

    def calculate_fee(
        self,
        db: Session,
        *,
        gross_amount: Decimal,
        scope_type: str,
        scope_id: Optional[UUID] = None,
        at_time: Optional[datetime] = None,
    ) -> FeeCalculationResult:
        """Calculate the fee for a gross amount using the applicable config.

        Fee clamping: if min_fee/max_fee are defined on the config, the
        computed fee is clamped to [min_fee, max_fee].
        """
        effective_time = at_time or datetime.utcnow()
        config = self._repo.find_active(db, scope_type, scope_id, effective_time)
        if config is None:
            raise NoApplicableFeeConfigError(scope_type, scope_id)

        fee_rate = Decimal(str(config.fee_rate))
        fee_amount = gross_amount * fee_rate

        if config.min_fee is not None:
            fee_amount = max(fee_amount, Decimal(str(config.min_fee)))
        if config.max_fee is not None:
            fee_amount = min(fee_amount, Decimal(str(config.max_fee)))

        return FeeCalculationResult(
            gross_amount=gross_amount,
            fee_rate=fee_rate,
            fee_amount=fee_amount,
            config_id=config.id,
        )
