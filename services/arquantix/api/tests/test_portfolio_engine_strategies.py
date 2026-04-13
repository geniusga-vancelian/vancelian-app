"""Tests for Portfolio Engine — Strategies module (definitions + instances)."""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.sleeves.models import Sleeve
from services.portfolio_engine.strategies.models import StrategyDefinition, StrategyInstance
from services.portfolio_engine.strategies.repository import (
    DuplicateDefinitionCodeError,
    StrategyDefinitionRepository,
    StrategyInstanceRepository,
)
from services.portfolio_engine.strategies.service import (
    DefinitionNotFoundError,
    DefinitionReferenceError,
    InstanceNotFoundError,
    PortfolioReferenceError,
    SleevePortfolioMismatchError,
    SleeveReferenceError,
    StrategyDefinitionService,
    StrategyInstanceService,
)
from services.portfolio_engine.strategies.schemas import (
    DefinitionCreate,
    DefinitionUpdate,
    InstanceCreate,
    InstanceUpdate,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CLIENT_ID = uuid.uuid4()


@pytest.fixture
def definition_target_alloc(db: Session) -> StrategyDefinition:
    d = StrategyDefinition(
        id=uuid.uuid4(),
        code="target_allocation_v1",
        name="Target Allocation",
        strategy_type="target_allocation",
        description="Rebalance towards target weights",
        parameters_schema={"weights": "object"},
    )
    db.add(d)
    db.flush()
    return d


@pytest.fixture
def definition_staking(db: Session) -> StrategyDefinition:
    d = StrategyDefinition(
        id=uuid.uuid4(),
        code="staking_eth_v1",
        name="ETH Staking",
        strategy_type="staking",
        parameters_schema={},
    )
    db.add(d)
    db.flush()
    return d


@pytest.fixture
def portfolio_basic(db: Session) -> Portfolio:
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
def portfolio_other(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=_CLIENT_ID,
        portfolio_type="yield_portfolio",
        name="Other Portfolio",
        base_currency="EUR",
        status="active",
        metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def sleeve_core(db: Session, portfolio_basic: Portfolio) -> Sleeve:
    s = Sleeve(
        id=uuid.uuid4(),
        portfolio_id=portfolio_basic.id,
        name="Core",
        sleeve_type="core",
        allocation_target=Decimal("0.600000"),
        metadata_={},
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def sleeve_other_portfolio(db: Session, portfolio_other: Portfolio) -> Sleeve:
    """Sleeve belonging to a different portfolio — used for mismatch tests."""
    s = Sleeve(
        id=uuid.uuid4(),
        portfolio_id=portfolio_other.id,
        name="Other Sleeve",
        sleeve_type="satellite",
        metadata_={},
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def instance_basic(
    db: Session,
    portfolio_basic: Portfolio,
    definition_target_alloc: StrategyDefinition,
) -> StrategyInstance:
    inst = StrategyInstance(
        id=uuid.uuid4(),
        portfolio_id=portfolio_basic.id,
        strategy_definition_id=definition_target_alloc.id,
        name="My Target Allocation",
        status="active",
        priority=50,
        parameters={"target_weights": {"BTC": 0.6, "ETH": 0.4}},
        metadata_={},
    )
    db.add(inst)
    db.flush()
    return inst


@pytest.fixture
def def_service() -> StrategyDefinitionService:
    return StrategyDefinitionService()


@pytest.fixture
def inst_service() -> StrategyInstanceService:
    return StrategyInstanceService()


# ---------------------------------------------------------------------------
# StrategyDefinition Repository tests
# ---------------------------------------------------------------------------

class TestStrategyDefinitionRepository:

    def test_create(self, db: Session):
        d = StrategyDefinitionRepository.create(
            db,
            data={
                "code": "buy_hold_v1",
                "name": "Buy and Hold",
                "strategy_type": "buy_and_hold",
                "parameters_schema": {},
            },
        )
        assert d.id is not None
        assert d.code == "buy_hold_v1"

    def test_get_by_id(self, db: Session, definition_target_alloc: StrategyDefinition):
        found = StrategyDefinitionRepository.get_by_id(db, definition_target_alloc.id)
        assert found is not None
        assert found.code == "target_allocation_v1"

    def test_get_by_id_not_found(self, db: Session):
        assert StrategyDefinitionRepository.get_by_id(db, uuid.uuid4()) is None

    def test_list(self, db: Session, definition_target_alloc: StrategyDefinition, definition_staking: StrategyDefinition):
        items, total = StrategyDefinitionRepository.list(db)
        assert total >= 2

    def test_list_filter_by_type(self, db: Session, definition_target_alloc: StrategyDefinition, definition_staking: StrategyDefinition):
        items, total = StrategyDefinitionRepository.list(db, strategy_type="staking")
        assert total >= 1
        assert all(d.strategy_type == "staking" for d in items)

    def test_duplicate_code_raises(self, db: Session, definition_target_alloc: StrategyDefinition):
        with pytest.raises(DuplicateDefinitionCodeError):
            StrategyDefinitionRepository.create(
                db,
                data={
                    "code": "target_allocation_v1",
                    "name": "Duplicate",
                    "strategy_type": "target_allocation",
                    "parameters_schema": {},
                },
            )

    def test_update(self, db: Session, definition_target_alloc: StrategyDefinition):
        StrategyDefinitionRepository.update(
            db, definition_target_alloc, data={"name": "Updated Name"},
        )
        db.flush()
        refreshed = StrategyDefinitionRepository.get_by_id(db, definition_target_alloc.id)
        assert refreshed.name == "Updated Name"


# ---------------------------------------------------------------------------
# StrategyDefinition Service tests
# ---------------------------------------------------------------------------

class TestStrategyDefinitionService:

    def test_create_definition(self, db: Session, def_service: StrategyDefinitionService):
        payload = DefinitionCreate(
            code="cppi_v1",
            name="CPPI Strategy",
            strategy_type="cppi",
        )
        d = def_service.create_definition(db, payload)
        assert d.code == "cppi_v1"

    def test_get_definition(self, db: Session, def_service: StrategyDefinitionService, definition_target_alloc: StrategyDefinition):
        found = def_service.get_definition(db, definition_target_alloc.id)
        assert found.id == definition_target_alloc.id

    def test_get_definition_not_found(self, db: Session, def_service: StrategyDefinitionService):
        with pytest.raises(DefinitionNotFoundError):
            def_service.get_definition(db, uuid.uuid4())

    def test_list_definitions(self, db: Session, def_service: StrategyDefinitionService, definition_target_alloc: StrategyDefinition):
        items, total = def_service.list_definitions(db)
        assert total >= 1

    def test_update_definition(self, db: Session, def_service: StrategyDefinitionService, definition_target_alloc: StrategyDefinition):
        payload = DefinitionUpdate(description="Updated description")
        updated = def_service.update_definition(db, definition_target_alloc.id, payload)
        assert updated.description == "Updated description"
        assert updated.code == "target_allocation_v1"

    def test_update_definition_partial(self, db: Session, def_service: StrategyDefinitionService, definition_target_alloc: StrategyDefinition):
        payload = DefinitionUpdate(name="Renamed")
        updated = def_service.update_definition(db, definition_target_alloc.id, payload)
        assert updated.name == "Renamed"
        assert updated.strategy_type == "target_allocation"


# ---------------------------------------------------------------------------
# StrategyInstance Repository tests
# ---------------------------------------------------------------------------

class TestStrategyInstanceRepository:

    def test_create(self, db: Session, portfolio_basic: Portfolio, definition_target_alloc: StrategyDefinition):
        inst = StrategyInstanceRepository.create(
            db,
            data={
                "portfolio_id": portfolio_basic.id,
                "strategy_definition_id": definition_target_alloc.id,
                "name": "Test Instance",
                "parameters": {"target_weights": {"BTC": 1.0}},
                "metadata_": {},
            },
        )
        assert inst.id is not None
        assert inst.status == "active"
        assert inst.priority == 100

    def test_get_by_id(self, db: Session, instance_basic: StrategyInstance):
        found = StrategyInstanceRepository.get_by_id(db, instance_basic.id)
        assert found is not None
        assert found.name == "My Target Allocation"

    def test_get_by_id_not_found(self, db: Session):
        assert StrategyInstanceRepository.get_by_id(db, uuid.uuid4()) is None

    def test_list_by_portfolio(self, db: Session, instance_basic: StrategyInstance, portfolio_basic: Portfolio):
        items, total = StrategyInstanceRepository.list_by_portfolio(db, portfolio_basic.id)
        assert total >= 1
        assert all(i.portfolio_id == portfolio_basic.id for i in items)

    def test_list_by_portfolio_filter_status(self, db: Session, instance_basic: StrategyInstance, portfolio_basic: Portfolio):
        items, total = StrategyInstanceRepository.list_by_portfolio(db, portfolio_basic.id, status="active")
        assert total >= 1

        items_none, total_none = StrategyInstanceRepository.list_by_portfolio(db, portfolio_basic.id, status="archived")
        assert total_none == 0

    def test_update(self, db: Session, instance_basic: StrategyInstance):
        StrategyInstanceRepository.update(db, instance_basic, data={"status": "paused", "priority": 10})
        db.flush()
        refreshed = StrategyInstanceRepository.get_by_id(db, instance_basic.id)
        assert refreshed.status == "paused"
        assert refreshed.priority == 10


# ---------------------------------------------------------------------------
# StrategyInstance Service tests
# ---------------------------------------------------------------------------

class TestStrategyInstanceService:

    def test_create_instance(
        self, db: Session, inst_service: StrategyInstanceService,
        portfolio_basic: Portfolio, definition_target_alloc: StrategyDefinition,
    ):
        payload = InstanceCreate(
            portfolio_id=portfolio_basic.id,
            strategy_definition_id=definition_target_alloc.id,
            name="Instance 1",
        )
        inst = inst_service.create_instance(db, payload)
        assert inst.portfolio_id == portfolio_basic.id
        assert inst.strategy_definition_id == definition_target_alloc.id

    def test_create_instance_with_sleeve(
        self, db: Session, inst_service: StrategyInstanceService,
        portfolio_basic: Portfolio, definition_target_alloc: StrategyDefinition,
        sleeve_core: Sleeve,
    ):
        payload = InstanceCreate(
            portfolio_id=portfolio_basic.id,
            sleeve_id=sleeve_core.id,
            strategy_definition_id=definition_target_alloc.id,
            name="Core Strategy",
        )
        inst = inst_service.create_instance(db, payload)
        assert inst.sleeve_id == sleeve_core.id

    def test_create_instance_invalid_portfolio(
        self, db: Session, inst_service: StrategyInstanceService,
        definition_target_alloc: StrategyDefinition,
    ):
        payload = InstanceCreate(
            portfolio_id=uuid.uuid4(),
            strategy_definition_id=definition_target_alloc.id,
        )
        with pytest.raises(PortfolioReferenceError):
            inst_service.create_instance(db, payload)

    def test_create_instance_invalid_definition(
        self, db: Session, inst_service: StrategyInstanceService,
        portfolio_basic: Portfolio,
    ):
        payload = InstanceCreate(
            portfolio_id=portfolio_basic.id,
            strategy_definition_id=uuid.uuid4(),
        )
        with pytest.raises(DefinitionReferenceError):
            inst_service.create_instance(db, payload)

    def test_create_instance_invalid_sleeve(
        self, db: Session, inst_service: StrategyInstanceService,
        portfolio_basic: Portfolio, definition_target_alloc: StrategyDefinition,
    ):
        payload = InstanceCreate(
            portfolio_id=portfolio_basic.id,
            sleeve_id=uuid.uuid4(),
            strategy_definition_id=definition_target_alloc.id,
        )
        with pytest.raises(SleeveReferenceError):
            inst_service.create_instance(db, payload)

    def test_create_instance_sleeve_portfolio_mismatch(
        self, db: Session, inst_service: StrategyInstanceService,
        portfolio_basic: Portfolio, definition_target_alloc: StrategyDefinition,
        sleeve_other_portfolio: Sleeve,
    ):
        payload = InstanceCreate(
            portfolio_id=portfolio_basic.id,
            sleeve_id=sleeve_other_portfolio.id,
            strategy_definition_id=definition_target_alloc.id,
        )
        with pytest.raises(SleevePortfolioMismatchError):
            inst_service.create_instance(db, payload)

    def test_get_instance(
        self, db: Session, inst_service: StrategyInstanceService,
        instance_basic: StrategyInstance,
    ):
        found = inst_service.get_instance(db, instance_basic.id)
        assert found.id == instance_basic.id

    def test_get_instance_not_found(self, db: Session, inst_service: StrategyInstanceService):
        with pytest.raises(InstanceNotFoundError):
            inst_service.get_instance(db, uuid.uuid4())

    def test_list_instances_by_portfolio(
        self, db: Session, inst_service: StrategyInstanceService,
        instance_basic: StrategyInstance, portfolio_basic: Portfolio,
    ):
        items, total = inst_service.list_instances_by_portfolio(db, portfolio_basic.id)
        assert total >= 1

    def test_update_instance(
        self, db: Session, inst_service: StrategyInstanceService,
        instance_basic: StrategyInstance,
    ):
        payload = InstanceUpdate(status="paused", priority=10)
        updated = inst_service.update_instance(db, instance_basic.id, payload)
        assert updated.status == "paused"
        assert updated.priority == 10

    def test_update_instance_partial(
        self, db: Session, inst_service: StrategyInstanceService,
        instance_basic: StrategyInstance,
    ):
        payload = InstanceUpdate(name="Renamed Strategy")
        updated = inst_service.update_instance(db, instance_basic.id, payload)
        assert updated.name == "Renamed Strategy"
        assert updated.status == "active"

    def test_update_instance_sleeve_mismatch(
        self, db: Session, inst_service: StrategyInstanceService,
        instance_basic: StrategyInstance, sleeve_other_portfolio: Sleeve,
    ):
        payload = InstanceUpdate(sleeve_id=sleeve_other_portfolio.id)
        with pytest.raises(SleevePortfolioMismatchError):
            inst_service.update_instance(db, instance_basic.id, payload)

    def test_update_instance_invalid_sleeve(
        self, db: Session, inst_service: StrategyInstanceService,
        instance_basic: StrategyInstance,
    ):
        payload = InstanceUpdate(sleeve_id=uuid.uuid4())
        with pytest.raises(SleeveReferenceError):
            inst_service.update_instance(db, instance_basic.id, payload)
