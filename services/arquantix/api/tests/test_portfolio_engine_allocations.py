"""Tests for Portfolio Engine — Target Allocations module."""
import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.sleeves.models import Sleeve
from services.portfolio_engine.allocations.models import TargetAllocation
from services.portfolio_engine.allocations.repository import TargetAllocationRepository
from services.portfolio_engine.allocations.service import (
    AllocationNotFoundError,
    InstrumentReferenceError,
    PortfolioReferenceError,
    SleeveReferenceError,
    TargetAllocationService,
)
from services.portfolio_engine.allocations.schemas import AllocationCreate, AllocationUpdate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CLIENT_ID = uuid.uuid4()


@pytest.fixture
def asset_btc(db: Session) -> Asset:
    a = Asset(id=uuid.uuid4(), symbol="BTC", name="Bitcoin", asset_type="crypto", metadata_={})
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def instrument_btc(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(id=uuid.uuid4(), asset_id=asset_btc.id, code="BTC-SPOT", name="BTC Spot", instrument_type="spot", metadata_={})
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def instrument_eth(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(id=uuid.uuid4(), asset_id=asset_btc.id, code="ETH-SPOT", name="ETH Spot", instrument_type="spot", metadata_={})
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def portfolio(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(), client_id=_CLIENT_ID, portfolio_type="bundle_portfolio",
        name="Test", base_currency="EUR", status="active", metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def sleeve(db: Session, portfolio: Portfolio) -> Sleeve:
    s = Sleeve(
        id=uuid.uuid4(), portfolio_id=portfolio.id, name="Core",
        sleeve_type="core", metadata_={},
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def alloc_btc(db: Session, portfolio: Portfolio, instrument_btc: Instrument) -> TargetAllocation:
    a = TargetAllocation(
        id=uuid.uuid4(), portfolio_id=portfolio.id, instrument_id=instrument_btc.id,
        target_weight=Decimal("0.600000"), min_weight=Decimal("0.500000"),
        max_weight=Decimal("0.700000"), rebalance_priority=50,
    )
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def alloc_service() -> TargetAllocationService:
    return TargetAllocationService()


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class TestAllocationSchemaValidation:

    def test_xor_both_none_rejected(self):
        with pytest.raises(ValidationError, match="Exactly one"):
            AllocationCreate(instrument_id=uuid.uuid4(), target_weight=Decimal("0.5"))

    def test_xor_both_set_rejected(self):
        with pytest.raises(ValidationError, match="Exactly one"):
            AllocationCreate(
                portfolio_id=uuid.uuid4(), sleeve_id=uuid.uuid4(),
                instrument_id=uuid.uuid4(), target_weight=Decimal("0.5"),
            )

    def test_min_greater_than_target_rejected(self):
        with pytest.raises(ValidationError, match="min_weight must be <= target_weight"):
            AllocationCreate(
                portfolio_id=uuid.uuid4(), instrument_id=uuid.uuid4(),
                target_weight=Decimal("0.3"), min_weight=Decimal("0.5"),
            )

    def test_max_less_than_target_rejected(self):
        with pytest.raises(ValidationError, match="max_weight must be >= target_weight"):
            AllocationCreate(
                portfolio_id=uuid.uuid4(), instrument_id=uuid.uuid4(),
                target_weight=Decimal("0.7"), max_weight=Decimal("0.5"),
            )

    def test_min_greater_than_max_rejected(self):
        with pytest.raises(ValidationError, match="min_weight must be <= max_weight"):
            AllocationCreate(
                portfolio_id=uuid.uuid4(), instrument_id=uuid.uuid4(),
                target_weight=Decimal("0.5"), min_weight=Decimal("0.6"), max_weight=Decimal("0.4"),
            )

    def test_valid_payload(self):
        payload = AllocationCreate(
            portfolio_id=uuid.uuid4(), instrument_id=uuid.uuid4(),
            target_weight=Decimal("0.5"), min_weight=Decimal("0.3"), max_weight=Decimal("0.7"),
        )
        assert payload.target_weight == Decimal("0.5")


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestTargetAllocationRepository:

    def test_create(self, db: Session, portfolio: Portfolio, instrument_btc: Instrument):
        a = TargetAllocationRepository.create(
            db, data={
                "portfolio_id": portfolio.id, "instrument_id": instrument_btc.id,
                "target_weight": Decimal("0.5"),
            },
        )
        assert a.id is not None
        assert a.target_weight == Decimal("0.5")

    def test_get_by_id(self, db: Session, alloc_btc: TargetAllocation):
        found = TargetAllocationRepository.get_by_id(db, alloc_btc.id)
        assert found is not None

    def test_list_by_portfolio(self, db: Session, alloc_btc: TargetAllocation, portfolio: Portfolio, instrument_eth: Instrument):
        TargetAllocationRepository.create(
            db, data={"portfolio_id": portfolio.id, "instrument_id": instrument_eth.id, "target_weight": Decimal("0.4")},
        )
        items, total = TargetAllocationRepository.list_by_portfolio(db, portfolio.id)
        assert total >= 2

    def test_update(self, db: Session, alloc_btc: TargetAllocation):
        TargetAllocationRepository.update(db, alloc_btc, data={"target_weight": Decimal("0.7")})
        db.flush()
        refreshed = TargetAllocationRepository.get_by_id(db, alloc_btc.id)
        assert refreshed.target_weight == Decimal("0.7")

    def test_delete(self, db: Session, alloc_btc: TargetAllocation):
        aid = alloc_btc.id
        TargetAllocationRepository.delete(db, alloc_btc)
        assert TargetAllocationRepository.get_by_id(db, aid) is None


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestTargetAllocationService:

    def test_create_portfolio_context(self, db: Session, alloc_service: TargetAllocationService, portfolio: Portfolio, instrument_btc: Instrument):
        payload = AllocationCreate(portfolio_id=portfolio.id, instrument_id=instrument_btc.id, target_weight=Decimal("0.6"))
        a = alloc_service.create_allocation(db, payload)
        assert a.portfolio_id == portfolio.id
        assert a.sleeve_id is None

    def test_create_sleeve_context(self, db: Session, alloc_service: TargetAllocationService, sleeve: Sleeve, instrument_btc: Instrument):
        payload = AllocationCreate(sleeve_id=sleeve.id, instrument_id=instrument_btc.id, target_weight=Decimal("0.5"))
        a = alloc_service.create_allocation(db, payload)
        assert a.sleeve_id == sleeve.id
        assert a.portfolio_id is None

    def test_create_invalid_portfolio(self, db: Session, alloc_service: TargetAllocationService, instrument_btc: Instrument):
        payload = AllocationCreate(portfolio_id=uuid.uuid4(), instrument_id=instrument_btc.id, target_weight=Decimal("0.5"))
        with pytest.raises(PortfolioReferenceError):
            alloc_service.create_allocation(db, payload)

    def test_create_invalid_sleeve(self, db: Session, alloc_service: TargetAllocationService, instrument_btc: Instrument):
        payload = AllocationCreate(sleeve_id=uuid.uuid4(), instrument_id=instrument_btc.id, target_weight=Decimal("0.5"))
        with pytest.raises(SleeveReferenceError):
            alloc_service.create_allocation(db, payload)

    def test_create_invalid_instrument(self, db: Session, alloc_service: TargetAllocationService, portfolio: Portfolio):
        payload = AllocationCreate(portfolio_id=portfolio.id, instrument_id=uuid.uuid4(), target_weight=Decimal("0.5"))
        with pytest.raises(InstrumentReferenceError):
            alloc_service.create_allocation(db, payload)

    def test_get_allocation(self, db: Session, alloc_service: TargetAllocationService, alloc_btc: TargetAllocation):
        found = alloc_service.get_allocation(db, alloc_btc.id)
        assert found.id == alloc_btc.id

    def test_get_allocation_not_found(self, db: Session, alloc_service: TargetAllocationService):
        with pytest.raises(AllocationNotFoundError):
            alloc_service.get_allocation(db, uuid.uuid4())

    def test_list_by_portfolio(self, db: Session, alloc_service: TargetAllocationService, alloc_btc: TargetAllocation, portfolio: Portfolio):
        items, total = alloc_service.list_allocations_by_portfolio(db, portfolio.id)
        assert total >= 1

    def test_update_allocation(self, db: Session, alloc_service: TargetAllocationService, alloc_btc: TargetAllocation):
        payload = AllocationUpdate(target_weight=Decimal("0.7"), max_weight=Decimal("0.8"))
        updated = alloc_service.update_allocation(db, alloc_btc.id, payload)
        assert updated.target_weight == Decimal("0.7")

    def test_update_allocation_weight_violation(self, db: Session, alloc_service: TargetAllocationService, alloc_btc: TargetAllocation):
        payload = AllocationUpdate(target_weight=Decimal("0.3"))
        with pytest.raises(ValueError, match="min_weight must be <= target_weight"):
            alloc_service.update_allocation(db, alloc_btc.id, payload)

    def test_delete_allocation(self, db: Session, alloc_service: TargetAllocationService, alloc_btc: TargetAllocation):
        aid = alloc_btc.id
        alloc_service.delete_allocation(db, aid)
        with pytest.raises(AllocationNotFoundError):
            alloc_service.get_allocation(db, aid)
