"""Tests for Portfolio Engine — Target Allocations + Rebalance Policies modules."""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.sleeves.models import Sleeve
from services.portfolio_engine.allocations.models import TargetAllocation
from services.portfolio_engine.allocations.repository import DuplicateAllocationError, TargetAllocationRepository
from services.portfolio_engine.allocations.service import (
    AllocationNotFoundError,
    InstrumentReferenceError,
    PortfolioReferenceError as AllocPortfolioRefError,
    SleeveReferenceError as AllocSleeveRefError,
    TargetAllocationService,
)
from services.portfolio_engine.allocations.schemas import AllocationCreate, AllocationUpdate
from services.portfolio_engine.rebalancing.models import RebalancePolicy
from services.portfolio_engine.rebalancing.repository import DuplicatePolicyError, RebalancePolicyRepository
from services.portfolio_engine.rebalancing.service import (
    PolicyNotFoundError,
    PortfolioReferenceError as RebalPortfolioRefError,
    SleeveReferenceError as RebalSleeveRefError,
    RebalancePolicyService,
)
from services.portfolio_engine.rebalancing.schemas import RebalancePolicyCreate, RebalancePolicyUpdate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CLIENT_ID = uuid.uuid4()


@pytest.fixture
def asset_btc(db: Session) -> Asset:
    a = Asset(
        id=uuid.uuid4(),
        symbol="BTC",
        name="Bitcoin",
        asset_type="cryptocurrency",
        metadata_={},
    )
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def instrument_btc_spot(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(),
        asset_id=asset_btc.id,
        code="BTC_SPOT",
        name="BTC Spot",
        instrument_type="spot",
        metadata_={},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def instrument_eth_spot(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(),
        asset_id=asset_btc.id,
        code="ETH_SPOT",
        name="ETH Spot",
        instrument_type="spot",
        metadata_={},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def portfolio(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=_CLIENT_ID,
        portfolio_type="bundle_portfolio",
        name="Balanced Crypto",
        base_currency="EUR",
        status="active",
        metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def sleeve_core(db: Session, portfolio: Portfolio) -> Sleeve:
    s = Sleeve(
        id=uuid.uuid4(),
        portfolio_id=portfolio.id,
        name="Core",
        sleeve_type="core",
        allocation_target=Decimal("0.600000"),
        metadata_={},
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def alloc_service() -> TargetAllocationService:
    return TargetAllocationService()


@pytest.fixture
def rebal_service() -> RebalancePolicyService:
    return RebalancePolicyService()


# ---------------------------------------------------------------------------
# TargetAllocation — Repository tests
# ---------------------------------------------------------------------------

class TestTargetAllocationRepository:

    def test_create_portfolio_scope(self, db: Session, portfolio: Portfolio, instrument_btc_spot: Instrument):
        alloc = TargetAllocationRepository.create(
            db,
            data={
                "portfolio_id": portfolio.id,
                "instrument_id": instrument_btc_spot.id,
                "target_weight": Decimal("0.600000"),
                "rebalance_priority": 50,
            },
        )
        assert alloc.id is not None
        assert alloc.portfolio_id == portfolio.id
        assert alloc.sleeve_id is None

    def test_create_sleeve_scope(self, db: Session, sleeve_core: Sleeve, instrument_btc_spot: Instrument):
        alloc = TargetAllocationRepository.create(
            db,
            data={
                "sleeve_id": sleeve_core.id,
                "instrument_id": instrument_btc_spot.id,
                "target_weight": Decimal("0.500000"),
            },
        )
        assert alloc.sleeve_id == sleeve_core.id
        assert alloc.portfolio_id is None

    def test_get_by_id(self, db: Session, portfolio: Portfolio, instrument_btc_spot: Instrument):
        alloc = TargetAllocationRepository.create(
            db, data={"portfolio_id": portfolio.id, "instrument_id": instrument_btc_spot.id, "target_weight": Decimal("0.4")},
        )
        found = TargetAllocationRepository.get_by_id(db, alloc.id)
        assert found is not None
        assert found.id == alloc.id

    def test_get_by_id_not_found(self, db: Session):
        assert TargetAllocationRepository.get_by_id(db, uuid.uuid4()) is None

    def test_list_by_portfolio(self, db: Session, portfolio: Portfolio, instrument_btc_spot: Instrument, instrument_eth_spot: Instrument):
        TargetAllocationRepository.create(db, data={"portfolio_id": portfolio.id, "instrument_id": instrument_btc_spot.id, "target_weight": Decimal("0.6"), "rebalance_priority": 10})
        TargetAllocationRepository.create(db, data={"portfolio_id": portfolio.id, "instrument_id": instrument_eth_spot.id, "target_weight": Decimal("0.4"), "rebalance_priority": 20})
        items, total = TargetAllocationRepository.list_by_portfolio(db, portfolio.id)
        assert total == 2
        assert items[0].rebalance_priority <= items[1].rebalance_priority

    def test_update(self, db: Session, portfolio: Portfolio, instrument_btc_spot: Instrument):
        alloc = TargetAllocationRepository.create(db, data={"portfolio_id": portfolio.id, "instrument_id": instrument_btc_spot.id, "target_weight": Decimal("0.5")})
        TargetAllocationRepository.update(db, alloc, data={"target_weight": Decimal("0.7")})
        db.flush()
        refreshed = TargetAllocationRepository.get_by_id(db, alloc.id)
        assert refreshed.target_weight == Decimal("0.7")

    def test_delete(self, db: Session, portfolio: Portfolio, instrument_btc_spot: Instrument):
        alloc = TargetAllocationRepository.create(db, data={"portfolio_id": portfolio.id, "instrument_id": instrument_btc_spot.id, "target_weight": Decimal("0.5")})
        alloc_id = alloc.id
        TargetAllocationRepository.delete(db, alloc)
        db.flush()
        assert TargetAllocationRepository.get_by_id(db, alloc_id) is None

    def test_duplicate_portfolio_instrument_raises(self, db: Session, portfolio: Portfolio, instrument_btc_spot: Instrument):
        TargetAllocationRepository.create(
            db, data={"portfolio_id": portfolio.id, "instrument_id": instrument_btc_spot.id, "target_weight": Decimal("0.5")},
        )
        with pytest.raises(DuplicateAllocationError):
            TargetAllocationRepository.create(
                db, data={"portfolio_id": portfolio.id, "instrument_id": instrument_btc_spot.id, "target_weight": Decimal("0.3")},
            )

    def test_duplicate_sleeve_instrument_raises(self, db: Session, sleeve_core: Sleeve, instrument_btc_spot: Instrument):
        TargetAllocationRepository.create(
            db, data={"sleeve_id": sleeve_core.id, "instrument_id": instrument_btc_spot.id, "target_weight": Decimal("0.5")},
        )
        with pytest.raises(DuplicateAllocationError):
            TargetAllocationRepository.create(
                db, data={"sleeve_id": sleeve_core.id, "instrument_id": instrument_btc_spot.id, "target_weight": Decimal("0.3")},
            )

    def test_same_instrument_different_context_ok(self, db: Session, portfolio: Portfolio, sleeve_core: Sleeve, instrument_btc_spot: Instrument):
        TargetAllocationRepository.create(
            db, data={"portfolio_id": portfolio.id, "instrument_id": instrument_btc_spot.id, "target_weight": Decimal("0.5")},
        )
        alloc2 = TargetAllocationRepository.create(
            db, data={"sleeve_id": sleeve_core.id, "instrument_id": instrument_btc_spot.id, "target_weight": Decimal("0.4")},
        )
        assert alloc2.id is not None


# ---------------------------------------------------------------------------
# TargetAllocation — Service tests
# ---------------------------------------------------------------------------

class TestTargetAllocationService:

    def test_create_allocation(self, db: Session, alloc_service: TargetAllocationService, portfolio: Portfolio, instrument_btc_spot: Instrument):
        payload = AllocationCreate(
            portfolio_id=portfolio.id,
            instrument_id=instrument_btc_spot.id,
            target_weight=Decimal("0.6"),
        )
        alloc = alloc_service.create_allocation(db, payload)
        assert alloc.portfolio_id == portfolio.id
        assert alloc.target_weight == Decimal("0.6")

    def test_create_allocation_invalid_portfolio(self, db: Session, alloc_service: TargetAllocationService, instrument_btc_spot: Instrument):
        payload = AllocationCreate(
            portfolio_id=uuid.uuid4(),
            instrument_id=instrument_btc_spot.id,
            target_weight=Decimal("0.5"),
        )
        with pytest.raises(AllocPortfolioRefError):
            alloc_service.create_allocation(db, payload)

    def test_create_allocation_invalid_sleeve(self, db: Session, alloc_service: TargetAllocationService, instrument_btc_spot: Instrument):
        payload = AllocationCreate(
            sleeve_id=uuid.uuid4(),
            instrument_id=instrument_btc_spot.id,
            target_weight=Decimal("0.5"),
        )
        with pytest.raises(AllocSleeveRefError):
            alloc_service.create_allocation(db, payload)

    def test_create_allocation_invalid_instrument(self, db: Session, alloc_service: TargetAllocationService, portfolio: Portfolio):
        payload = AllocationCreate(
            portfolio_id=portfolio.id,
            instrument_id=uuid.uuid4(),
            target_weight=Decimal("0.5"),
        )
        with pytest.raises(InstrumentReferenceError):
            alloc_service.create_allocation(db, payload)

    def test_get_allocation(self, db: Session, alloc_service: TargetAllocationService, portfolio: Portfolio, instrument_btc_spot: Instrument):
        payload = AllocationCreate(portfolio_id=portfolio.id, instrument_id=instrument_btc_spot.id, target_weight=Decimal("0.3"))
        created = alloc_service.create_allocation(db, payload)
        found = alloc_service.get_allocation(db, created.id)
        assert found.id == created.id

    def test_get_allocation_not_found(self, db: Session, alloc_service: TargetAllocationService):
        with pytest.raises(AllocationNotFoundError):
            alloc_service.get_allocation(db, uuid.uuid4())

    def test_update_allocation_partial(self, db: Session, alloc_service: TargetAllocationService, portfolio: Portfolio, instrument_btc_spot: Instrument):
        payload = AllocationCreate(portfolio_id=portfolio.id, instrument_id=instrument_btc_spot.id, target_weight=Decimal("0.5"))
        created = alloc_service.create_allocation(db, payload)
        update_payload = AllocationUpdate(target_weight=Decimal("0.8"))
        updated = alloc_service.update_allocation(db, created.id, update_payload)
        assert updated.target_weight == Decimal("0.8")
        assert updated.rebalance_priority == 100

    def test_delete_allocation(self, db: Session, alloc_service: TargetAllocationService, portfolio: Portfolio, instrument_btc_spot: Instrument):
        payload = AllocationCreate(portfolio_id=portfolio.id, instrument_id=instrument_btc_spot.id, target_weight=Decimal("0.5"))
        created = alloc_service.create_allocation(db, payload)
        alloc_service.delete_allocation(db, created.id)
        with pytest.raises(AllocationNotFoundError):
            alloc_service.get_allocation(db, created.id)

    def test_list_allocations_by_portfolio(self, db: Session, alloc_service: TargetAllocationService, portfolio: Portfolio, instrument_btc_spot: Instrument):
        alloc_service.create_allocation(db, AllocationCreate(portfolio_id=portfolio.id, instrument_id=instrument_btc_spot.id, target_weight=Decimal("0.6")))
        items, total = alloc_service.list_allocations_by_portfolio(db, portfolio.id)
        assert total >= 1


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class TestAllocationSchemaValidation:

    def test_xor_both_none_raises(self):
        with pytest.raises(ValueError, match="Exactly one"):
            AllocationCreate(instrument_id=uuid.uuid4(), target_weight=Decimal("0.5"))

    def test_xor_both_set_raises(self):
        with pytest.raises(ValueError, match="Exactly one"):
            AllocationCreate(
                portfolio_id=uuid.uuid4(),
                sleeve_id=uuid.uuid4(),
                instrument_id=uuid.uuid4(),
                target_weight=Decimal("0.5"),
            )

    def test_min_greater_than_target_raises(self):
        with pytest.raises(ValueError, match="min_weight"):
            AllocationCreate(
                portfolio_id=uuid.uuid4(),
                instrument_id=uuid.uuid4(),
                target_weight=Decimal("0.3"),
                min_weight=Decimal("0.5"),
            )

    def test_max_less_than_target_raises(self):
        with pytest.raises(ValueError, match="max_weight"):
            AllocationCreate(
                portfolio_id=uuid.uuid4(),
                instrument_id=uuid.uuid4(),
                target_weight=Decimal("0.8"),
                max_weight=Decimal("0.5"),
            )

    def test_min_greater_than_max_raises(self):
        with pytest.raises(ValueError, match="min_weight must be <= max_weight"):
            AllocationCreate(
                portfolio_id=uuid.uuid4(),
                instrument_id=uuid.uuid4(),
                target_weight=Decimal("0.5"),
                min_weight=Decimal("0.6"),
                max_weight=Decimal("0.4"),
            )

    def test_valid_weights_pass(self):
        alloc = AllocationCreate(
            portfolio_id=uuid.uuid4(),
            instrument_id=uuid.uuid4(),
            target_weight=Decimal("0.5"),
            min_weight=Decimal("0.3"),
            max_weight=Decimal("0.7"),
        )
        assert alloc.target_weight == Decimal("0.5")


# ---------------------------------------------------------------------------
# RebalancePolicy — Repository tests
# ---------------------------------------------------------------------------

class TestRebalancePolicyRepository:

    def test_create_portfolio_scope(self, db: Session, portfolio: Portfolio):
        policy = RebalancePolicyRepository.create(
            db,
            data={
                "portfolio_id": portfolio.id,
                "method": "periodic",
                "frequency": "monthly",
                "drift_threshold": Decimal("0.050000"),
                "parameters": {},
            },
        )
        assert policy.id is not None
        assert policy.portfolio_id == portfolio.id

    def test_create_sleeve_scope(self, db: Session, sleeve_core: Sleeve):
        policy = RebalancePolicyRepository.create(
            db,
            data={
                "sleeve_id": sleeve_core.id,
                "method": "threshold",
                "drift_threshold": Decimal("0.100000"),
                "parameters": {},
            },
        )
        assert policy.sleeve_id == sleeve_core.id
        assert policy.portfolio_id is None

    def test_get_by_id(self, db: Session, portfolio: Portfolio):
        policy = RebalancePolicyRepository.create(
            db, data={"portfolio_id": portfolio.id, "method": "periodic", "parameters": {}},
        )
        found = RebalancePolicyRepository.get_by_id(db, policy.id)
        assert found is not None
        assert found.id == policy.id

    def test_get_by_id_not_found(self, db: Session):
        assert RebalancePolicyRepository.get_by_id(db, uuid.uuid4()) is None

    def test_get_by_portfolio(self, db: Session, portfolio: Portfolio):
        RebalancePolicyRepository.create(
            db, data={"portfolio_id": portfolio.id, "method": "hybrid", "parameters": {}},
        )
        found = RebalancePolicyRepository.get_by_portfolio(db, portfolio.id)
        assert found is not None
        assert found.portfolio_id == portfolio.id

    def test_update(self, db: Session, portfolio: Portfolio):
        policy = RebalancePolicyRepository.create(
            db, data={"portfolio_id": portfolio.id, "method": "periodic", "frequency": "monthly", "parameters": {}},
        )
        RebalancePolicyRepository.update(db, policy, data={"frequency": "weekly", "drift_threshold": Decimal("0.03")})
        db.flush()
        refreshed = RebalancePolicyRepository.get_by_id(db, policy.id)
        assert refreshed.frequency == "weekly"
        assert refreshed.drift_threshold == Decimal("0.03")

    def test_duplicate_portfolio_policy_raises(self, db: Session, portfolio: Portfolio):
        RebalancePolicyRepository.create(
            db, data={"portfolio_id": portfolio.id, "method": "periodic", "parameters": {}},
        )
        with pytest.raises(DuplicatePolicyError):
            RebalancePolicyRepository.create(
                db, data={"portfolio_id": portfolio.id, "method": "threshold", "parameters": {}},
            )

    def test_duplicate_sleeve_policy_raises(self, db: Session, sleeve_core: Sleeve):
        RebalancePolicyRepository.create(
            db, data={"sleeve_id": sleeve_core.id, "method": "periodic", "parameters": {}},
        )
        with pytest.raises(DuplicatePolicyError):
            RebalancePolicyRepository.create(
                db, data={"sleeve_id": sleeve_core.id, "method": "threshold", "parameters": {}},
            )


# ---------------------------------------------------------------------------
# RebalancePolicy — Service tests
# ---------------------------------------------------------------------------

class TestRebalancePolicyService:

    def test_create_policy(self, db: Session, rebal_service: RebalancePolicyService, portfolio: Portfolio):
        payload = RebalancePolicyCreate(
            portfolio_id=portfolio.id,
            method="periodic",
            frequency="monthly",
        )
        policy = rebal_service.create_policy(db, payload)
        assert policy.portfolio_id == portfolio.id
        assert policy.method == "periodic"

    def test_create_policy_invalid_portfolio(self, db: Session, rebal_service: RebalancePolicyService):
        payload = RebalancePolicyCreate(
            portfolio_id=uuid.uuid4(),
            method="periodic",
        )
        with pytest.raises(RebalPortfolioRefError):
            rebal_service.create_policy(db, payload)

    def test_create_policy_invalid_sleeve(self, db: Session, rebal_service: RebalancePolicyService):
        payload = RebalancePolicyCreate(
            sleeve_id=uuid.uuid4(),
            method="threshold",
        )
        with pytest.raises(RebalSleeveRefError):
            rebal_service.create_policy(db, payload)

    def test_get_policy(self, db: Session, rebal_service: RebalancePolicyService, portfolio: Portfolio):
        payload = RebalancePolicyCreate(portfolio_id=portfolio.id, method="manual")
        created = rebal_service.create_policy(db, payload)
        found = rebal_service.get_policy(db, created.id)
        assert found.id == created.id

    def test_get_policy_not_found(self, db: Session, rebal_service: RebalancePolicyService):
        with pytest.raises(PolicyNotFoundError):
            rebal_service.get_policy(db, uuid.uuid4())

    def test_get_policy_by_portfolio(self, db: Session, rebal_service: RebalancePolicyService, portfolio: Portfolio):
        rebal_service.create_policy(db, RebalancePolicyCreate(portfolio_id=portfolio.id, method="periodic"))
        found = rebal_service.get_policy_by_portfolio(db, portfolio.id)
        assert found is not None
        assert found.portfolio_id == portfolio.id

    def test_update_policy_partial(self, db: Session, rebal_service: RebalancePolicyService, portfolio: Portfolio):
        created = rebal_service.create_policy(db, RebalancePolicyCreate(portfolio_id=portfolio.id, method="periodic", frequency="monthly"))
        updated = rebal_service.update_policy(db, created.id, RebalancePolicyUpdate(frequency="weekly"))
        assert updated.frequency == "weekly"
        assert updated.method == "periodic"

    def test_update_policy_not_found(self, db: Session, rebal_service: RebalancePolicyService):
        with pytest.raises(PolicyNotFoundError):
            rebal_service.update_policy(db, uuid.uuid4(), RebalancePolicyUpdate(method="manual"))


# ---------------------------------------------------------------------------
# RebalancePolicy schema validation tests
# ---------------------------------------------------------------------------

class TestRebalancePolicySchemaValidation:

    def test_xor_both_none_raises(self):
        with pytest.raises(ValueError, match="Exactly one"):
            RebalancePolicyCreate(method="periodic")

    def test_xor_both_set_raises(self):
        with pytest.raises(ValueError, match="Exactly one"):
            RebalancePolicyCreate(
                portfolio_id=uuid.uuid4(),
                sleeve_id=uuid.uuid4(),
                method="periodic",
            )

    def test_valid_portfolio_scope(self):
        payload = RebalancePolicyCreate(portfolio_id=uuid.uuid4(), method="threshold", drift_threshold=Decimal("0.05"))
        assert payload.drift_threshold == Decimal("0.05")

    def test_valid_sleeve_scope(self):
        payload = RebalancePolicyCreate(sleeve_id=uuid.uuid4(), method="periodic", frequency="quarterly")
        assert payload.frequency == "quarterly"
