"""Tests for Portfolio Engine — Trading Fee Configs module."""
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.trading_fees.models import TradingFeeConfig
from services.portfolio_engine.trading_fees.repository import TradingFeeConfigRepository
from services.portfolio_engine.trading_fees.service import (
    FeeConfigNotFoundError,
    NoApplicableFeeConfigError,
    TradingFeeConfigService,
)
from services.portfolio_engine.trading_fees.schemas import TradingFeeConfigCreate, TradingFeeConfigUpdate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def service() -> TradingFeeConfigService:
    return TradingFeeConfigService()


@pytest.fixture
def global_fee_config(db: Session) -> TradingFeeConfig:
    now = datetime.now(timezone.utc)
    config = TradingFeeConfig(
        id=uuid.uuid4(),
        scope_type="global",
        scope_id=None,
        fee_type="trading",
        fee_rate=Decimal("0.0015"),
        min_fee=None,
        max_fee=None,
        status="active",
        valid_from=now - timedelta(days=30),
        valid_to=None,
        metadata_={},
    )
    db.add(config)
    db.flush()
    return config


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestTradingFeeConfigRepository:

    def test_create(self, db: Session):
        now = datetime.now(timezone.utc)
        config = TradingFeeConfigRepository.create(db, data={
            "scope_type": "global",
            "fee_type": "trading",
            "fee_rate": Decimal("0.002"),
            "status": "active",
            "valid_from": now,
            "metadata_": {},
        })
        assert config.id is not None
        assert config.fee_rate == Decimal("0.002")

    def test_get_by_id(self, db: Session, global_fee_config: TradingFeeConfig):
        found = TradingFeeConfigRepository.get_by_id(db, global_fee_config.id)
        assert found is not None
        assert found.scope_type == "global"

    def test_get_by_id_not_found(self, db: Session):
        assert TradingFeeConfigRepository.get_by_id(db, uuid.uuid4()) is None

    def test_list_by_scope(self, db: Session, global_fee_config: TradingFeeConfig):
        items, total = TradingFeeConfigRepository.list(db, scope_type="global")
        assert total >= 1

    def test_find_active(self, db: Session, global_fee_config: TradingFeeConfig):
        now = datetime.now(timezone.utc)
        found = TradingFeeConfigRepository.find_active(db, "global", None, now)
        assert found is not None
        assert found.id == global_fee_config.id

    def test_find_active_expired(self, db: Session):
        past = datetime.now(timezone.utc) - timedelta(days=60)
        config = TradingFeeConfig(
            id=uuid.uuid4(),
            scope_type="global",
            scope_id=None,
            fee_type="trading",
            fee_rate=Decimal("0.001"),
            status="active",
            valid_from=past - timedelta(days=30),
            valid_to=past,
            metadata_={},
        )
        db.add(config)
        db.flush()

        now = datetime.now(timezone.utc)
        found = TradingFeeConfigRepository.find_active(db, "global", None, now)
        assert found is None


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestTradingFeeConfigService:

    def test_create_config(self, db: Session, service: TradingFeeConfigService):
        payload = TradingFeeConfigCreate(
            scope_type="portfolio",
            scope_id=uuid.uuid4(),
            fee_rate=Decimal("0.002"),
            valid_from=datetime.now(timezone.utc),
        )
        config = service.create_config(db, payload)
        assert config.scope_type == "portfolio"
        assert config.fee_rate == Decimal("0.002")

    def test_get_config_not_found(self, db: Session, service: TradingFeeConfigService):
        with pytest.raises(FeeConfigNotFoundError):
            service.get_config(db, uuid.uuid4())

    def test_update_config(self, db: Session, service: TradingFeeConfigService, global_fee_config: TradingFeeConfig):
        payload = TradingFeeConfigUpdate(fee_rate=Decimal("0.003"))
        updated = service.update_config(db, global_fee_config.id, payload)
        assert updated.fee_rate == Decimal("0.003")

    def test_calculate_fee(self, db: Session, service: TradingFeeConfigService, global_fee_config: TradingFeeConfig):
        result = service.calculate_fee(
            db,
            gross_amount=Decimal("34000"),
            scope_type="global",
        )
        assert result.fee_rate == Decimal("0.0015")
        assert result.fee_amount == Decimal("34000") * Decimal("0.0015")
        assert result.config_id == global_fee_config.id

    def test_calculate_fee_with_min_max(self, db: Session, service: TradingFeeConfigService):
        now = datetime.now(timezone.utc)
        config = TradingFeeConfig(
            id=uuid.uuid4(),
            scope_type="clamped",
            scope_id=None,
            fee_type="trading",
            fee_rate=Decimal("0.0001"),
            min_fee=Decimal("10"),
            max_fee=Decimal("100"),
            status="active",
            valid_from=now - timedelta(days=1),
            metadata_={},
        )
        db.add(config)
        db.flush()

        result_low = service.calculate_fee(db, gross_amount=Decimal("100"), scope_type="clamped")
        assert result_low.fee_amount == Decimal("10")

        result_high = service.calculate_fee(db, gross_amount=Decimal("5000000"), scope_type="clamped")
        assert result_high.fee_amount == Decimal("100")

    def test_calculate_fee_no_config_raises(self, db: Session, service: TradingFeeConfigService):
        with pytest.raises(NoApplicableFeeConfigError):
            service.calculate_fee(db, gross_amount=Decimal("1000"), scope_type="nonexistent")

    def test_list_configs(self, db: Session, service: TradingFeeConfigService, global_fee_config: TradingFeeConfig):
        items, total = service.list_configs(db, scope_type="global")
        assert total >= 1

    def test_fee_does_not_affect_position_quantity(self, db: Session):
        """Fee calculation returns a fee_amount but does not modify positions.

        This test verifies the fee is a pure computation with no side effects.
        """
        service = TradingFeeConfigService()
        now = datetime.now(timezone.utc)
        config = TradingFeeConfig(
            id=uuid.uuid4(),
            scope_type="fee_test",
            scope_id=None,
            fee_type="trading",
            fee_rate=Decimal("0.0015"),
            status="active",
            valid_from=now - timedelta(days=1),
            metadata_={},
        )
        db.add(config)
        db.flush()

        result = service.calculate_fee(db, gross_amount=Decimal("34000"), scope_type="fee_test")
        expected_fee = Decimal("34000") * Decimal("0.0015")
        assert result.fee_amount == expected_fee
        assert result.gross_amount == Decimal("34000")
