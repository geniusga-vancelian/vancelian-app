"""Tests for Portfolio Engine — Templates module (PortfolioTemplate + TemplateAllocation)."""
import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.products.models import ProductDefinition
from services.portfolio_engine.strategies.models import StrategyDefinition
from services.portfolio_engine.templates.models import PortfolioTemplate, TemplateAllocation
from services.portfolio_engine.templates.repository import (
    DuplicateTemplateAllocationError,
    DuplicateTemplateCodeError,
    PortfolioTemplateRepository,
    TemplateAllocationRepository,
)
from services.portfolio_engine.templates.service import (
    InstrumentReferenceError,
    PortfolioTemplateService,
    ProductReferenceError,
    StrategyDefinitionReferenceError,
    TemplateAllocationNotFoundError,
    TemplateAllocationService,
    TemplateNotFoundError,
)
from services.portfolio_engine.templates.schemas import (
    TemplateAllocationCreate,
    TemplateAllocationUpdate,
    TemplateCreate,
    TemplateUpdate,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def product(db: Session) -> ProductDefinition:
    p = ProductDefinition(
        id=uuid.uuid4(),
        product_code="TMPL_TEST_PROD",
        name="Test Product",
        product_type="crypto_bundle",
        status="active",
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def strategy_def(db: Session) -> StrategyDefinition:
    s = StrategyDefinition(
        id=uuid.uuid4(),
        code="TMPL_TEST_STRAT",
        name="Test Strategy",
        strategy_type="fixed_weight",
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def asset_btc(db: Session) -> Asset:
    a = Asset(id=uuid.uuid4(), symbol="TMPL_BTC", name="Bitcoin", asset_type="crypto", metadata_={})
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def instrument_btc(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(), asset_id=asset_btc.id, code="TMPL_BTC-SPOT",
        name="BTC Spot", instrument_type="spot", metadata_={},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def instrument_eth(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(), asset_id=asset_btc.id, code="TMPL_ETH-SPOT",
        name="ETH Spot", instrument_type="spot", metadata_={},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def template(db: Session, product: ProductDefinition) -> PortfolioTemplate:
    t = PortfolioTemplate(
        id=uuid.uuid4(),
        product_id=product.id,
        template_code="BALANCED_V1",
        provisioned_portfolio_type="bundle_portfolio",
        name="Balanced Template v1",
        base_currency="EUR",
        metadata_={},
    )
    db.add(t)
    db.flush()
    return t


@pytest.fixture
def alloc_btc(db: Session, template: PortfolioTemplate, instrument_btc: Instrument) -> TemplateAllocation:
    a = TemplateAllocation(
        id=uuid.uuid4(),
        template_id=template.id,
        instrument_id=instrument_btc.id,
        target_weight=Decimal("0.600000"),
        min_weight=Decimal("0.500000"),
        max_weight=Decimal("0.700000"),
        allocation_priority=50,
    )
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def template_svc() -> PortfolioTemplateService:
    return PortfolioTemplateService()


@pytest.fixture
def alloc_svc() -> TemplateAllocationService:
    return TemplateAllocationService()


# ---------------------------------------------------------------------------
# TemplateAllocation schema validation tests
# ---------------------------------------------------------------------------

class TestTemplateAllocationSchemaValidation:

    def test_min_greater_than_target_rejected(self):
        with pytest.raises(ValidationError, match="min_weight must be <= target_weight"):
            TemplateAllocationCreate(
                template_id=uuid.uuid4(), instrument_id=uuid.uuid4(),
                target_weight=Decimal("0.3"), min_weight=Decimal("0.5"),
            )

    def test_max_less_than_target_rejected(self):
        with pytest.raises(ValidationError, match="max_weight must be >= target_weight"):
            TemplateAllocationCreate(
                template_id=uuid.uuid4(), instrument_id=uuid.uuid4(),
                target_weight=Decimal("0.7"), max_weight=Decimal("0.5"),
            )

    def test_min_greater_than_max_rejected(self):
        with pytest.raises(ValidationError, match="min_weight must be <= max_weight"):
            TemplateAllocationCreate(
                template_id=uuid.uuid4(), instrument_id=uuid.uuid4(),
                target_weight=Decimal("0.5"), min_weight=Decimal("0.6"), max_weight=Decimal("0.4"),
            )

    def test_valid_payload(self):
        payload = TemplateAllocationCreate(
            template_id=uuid.uuid4(), instrument_id=uuid.uuid4(),
            target_weight=Decimal("0.5"), min_weight=Decimal("0.3"), max_weight=Decimal("0.7"),
        )
        assert payload.target_weight == Decimal("0.5")
        assert payload.allocation_priority == 100


# ---------------------------------------------------------------------------
# PortfolioTemplate repository tests
# ---------------------------------------------------------------------------

class TestPortfolioTemplateRepository:

    def test_create(self, db: Session, product: ProductDefinition):
        t = PortfolioTemplateRepository.create(
            db,
            data={
                "product_id": product.id,
                "template_code": "NEW_TMPL_01",
                "provisioned_portfolio_type": "managed_portfolio",
                "name": "New Template",
            },
        )
        assert t.id is not None
        assert t.template_code == "NEW_TMPL_01"
        assert t.provisioned_portfolio_type == "managed_portfolio"
        assert t.base_currency == "EUR"

    def test_create_with_metadata(self, db: Session, product: ProductDefinition):
        t = PortfolioTemplateRepository.create(
            db,
            data={
                "product_id": product.id,
                "template_code": "META_TMPL",
                "provisioned_portfolio_type": "bundle_portfolio",
                "name": "Metadata Template",
                "metadata": {"version": "2.0"},
            },
        )
        assert t.metadata_ == {"version": "2.0"}

    def test_create_duplicate_code(self, db: Session, template: PortfolioTemplate, product: ProductDefinition):
        with pytest.raises(DuplicateTemplateCodeError):
            PortfolioTemplateRepository.create(
                db,
                data={
                    "product_id": product.id,
                    "template_code": "BALANCED_V1",
                    "provisioned_portfolio_type": "bundle_portfolio",
                    "name": "Duplicate",
                },
            )

    def test_get_by_id(self, db: Session, template: PortfolioTemplate):
        found = PortfolioTemplateRepository.get_by_id(db, template.id)
        assert found is not None
        assert found.template_code == "BALANCED_V1"

    def test_get_by_id_not_found(self, db: Session):
        assert PortfolioTemplateRepository.get_by_id(db, uuid.uuid4()) is None

    def test_list_all(self, db: Session, template: PortfolioTemplate, product: ProductDefinition):
        PortfolioTemplateRepository.create(
            db,
            data={"product_id": product.id, "template_code": "SECOND_TMPL", "provisioned_portfolio_type": "yield_portfolio", "name": "Second"},
        )
        items, total = PortfolioTemplateRepository.list(db)
        assert total >= 2

    def test_list_filter_by_product(self, db: Session, template: PortfolioTemplate, product: ProductDefinition):
        items, total = PortfolioTemplateRepository.list(db, product_id=product.id)
        assert total >= 1
        assert all(t.product_id == product.id for t in items)

    def test_update(self, db: Session, template: PortfolioTemplate):
        PortfolioTemplateRepository.update(db, template, data={"name": "Updated Name"})
        db.flush()
        refreshed = PortfolioTemplateRepository.get_by_id(db, template.id)
        assert refreshed.name == "Updated Name"

    def test_update_metadata(self, db: Session, template: PortfolioTemplate):
        PortfolioTemplateRepository.update(db, template, data={"metadata": {"fee": "1%"}})
        db.flush()
        refreshed = PortfolioTemplateRepository.get_by_id(db, template.id)
        assert refreshed.metadata_ == {"fee": "1%"}


# ---------------------------------------------------------------------------
# TemplateAllocation repository tests
# ---------------------------------------------------------------------------

class TestTemplateAllocationRepository:

    def test_create(self, db: Session, template: PortfolioTemplate, instrument_btc: Instrument):
        a = TemplateAllocationRepository.create(
            db,
            data={
                "template_id": template.id,
                "instrument_id": instrument_btc.id,
                "target_weight": Decimal("0.5"),
            },
        )
        assert a.id is not None
        assert a.target_weight == Decimal("0.5")

    def test_create_duplicate_instrument(self, db: Session, alloc_btc: TemplateAllocation, template: PortfolioTemplate, instrument_btc: Instrument):
        with pytest.raises(DuplicateTemplateAllocationError):
            TemplateAllocationRepository.create(
                db,
                data={
                    "template_id": template.id,
                    "instrument_id": instrument_btc.id,
                    "target_weight": Decimal("0.3"),
                },
            )

    def test_get_by_id(self, db: Session, alloc_btc: TemplateAllocation):
        found = TemplateAllocationRepository.get_by_id(db, alloc_btc.id)
        assert found is not None

    def test_list_by_template(self, db: Session, alloc_btc: TemplateAllocation, template: PortfolioTemplate, instrument_eth: Instrument):
        TemplateAllocationRepository.create(
            db,
            data={"template_id": template.id, "instrument_id": instrument_eth.id, "target_weight": Decimal("0.4")},
        )
        items, total = TemplateAllocationRepository.list_by_template(db, template.id)
        assert total >= 2

    def test_update(self, db: Session, alloc_btc: TemplateAllocation):
        TemplateAllocationRepository.update(db, alloc_btc, data={"target_weight": Decimal("0.7")})
        db.flush()
        refreshed = TemplateAllocationRepository.get_by_id(db, alloc_btc.id)
        assert refreshed.target_weight == Decimal("0.7")

    def test_delete(self, db: Session, alloc_btc: TemplateAllocation):
        aid = alloc_btc.id
        TemplateAllocationRepository.delete(db, alloc_btc)
        assert TemplateAllocationRepository.get_by_id(db, aid) is None


# ---------------------------------------------------------------------------
# PortfolioTemplate service tests
# ---------------------------------------------------------------------------

class TestPortfolioTemplateService:

    def test_create_template(self, db: Session, template_svc: PortfolioTemplateService, product: ProductDefinition):
        payload = TemplateCreate(
            product_id=product.id,
            template_code="SVC_TMPL_01",
            provisioned_portfolio_type="managed_portfolio",
            name="Service Template",
        )
        t = template_svc.create_template(db, payload)
        assert t.product_id == product.id
        assert t.provisioned_portfolio_type == "managed_portfolio"
        assert t.base_currency == "EUR"

    def test_create_template_with_strategy(
        self, db: Session, template_svc: PortfolioTemplateService,
        product: ProductDefinition, strategy_def: StrategyDefinition,
    ):
        payload = TemplateCreate(
            product_id=product.id,
            template_code="SVC_TMPL_STRAT",
            provisioned_portfolio_type="structured_portfolio",
            name="Strategy Template",
            strategy_definition_id=strategy_def.id,
        )
        t = template_svc.create_template(db, payload)
        assert t.strategy_definition_id == strategy_def.id

    def test_create_invalid_product(self, db: Session, template_svc: PortfolioTemplateService):
        payload = TemplateCreate(
            product_id=uuid.uuid4(),
            template_code="BAD_PROD",
            provisioned_portfolio_type="bundle_portfolio",
            name="Bad Product",
        )
        with pytest.raises(ProductReferenceError):
            template_svc.create_template(db, payload)

    def test_create_invalid_strategy(self, db: Session, template_svc: PortfolioTemplateService, product: ProductDefinition):
        payload = TemplateCreate(
            product_id=product.id,
            template_code="BAD_STRAT",
            provisioned_portfolio_type="bundle_portfolio",
            name="Bad Strategy",
            strategy_definition_id=uuid.uuid4(),
        )
        with pytest.raises(StrategyDefinitionReferenceError):
            template_svc.create_template(db, payload)

    def test_get_template(self, db: Session, template_svc: PortfolioTemplateService, template: PortfolioTemplate):
        found = template_svc.get_template(db, template.id)
        assert found.id == template.id

    def test_get_template_not_found(self, db: Session, template_svc: PortfolioTemplateService):
        with pytest.raises(TemplateNotFoundError):
            template_svc.get_template(db, uuid.uuid4())

    def test_list_templates(self, db: Session, template_svc: PortfolioTemplateService, template: PortfolioTemplate):
        items, total = template_svc.list_templates(db)
        assert total >= 1

    def test_update_template(self, db: Session, template_svc: PortfolioTemplateService, template: PortfolioTemplate):
        payload = TemplateUpdate(name="Updated Name")
        updated = template_svc.update_template(db, template.id, payload)
        assert updated.name == "Updated Name"
        assert updated.template_code == "BALANCED_V1"

    def test_update_provisioned_portfolio_type(
        self, db: Session, template_svc: PortfolioTemplateService, template: PortfolioTemplate,
    ):
        payload = TemplateUpdate(provisioned_portfolio_type="yield_portfolio")
        updated = template_svc.update_template(db, template.id, payload)
        assert updated.provisioned_portfolio_type == "yield_portfolio"
        assert updated.template_code == "BALANCED_V1"

    def test_update_template_invalid_strategy(
        self, db: Session, template_svc: PortfolioTemplateService, template: PortfolioTemplate,
    ):
        payload = TemplateUpdate(strategy_definition_id=uuid.uuid4())
        with pytest.raises(StrategyDefinitionReferenceError):
            template_svc.update_template(db, template.id, payload)


# ---------------------------------------------------------------------------
# TemplateAllocation service tests
# ---------------------------------------------------------------------------

class TestTemplateAllocationService:

    def test_create_allocation(
        self, db: Session, alloc_svc: TemplateAllocationService,
        template: PortfolioTemplate, instrument_btc: Instrument,
    ):
        payload = TemplateAllocationCreate(
            template_id=template.id,
            instrument_id=instrument_btc.id,
            target_weight=Decimal("0.6"),
        )
        a = alloc_svc.create_allocation(db, payload)
        assert a.template_id == template.id
        assert a.instrument_id == instrument_btc.id

    def test_create_invalid_template(self, db: Session, alloc_svc: TemplateAllocationService, instrument_btc: Instrument):
        payload = TemplateAllocationCreate(
            template_id=uuid.uuid4(),
            instrument_id=instrument_btc.id,
            target_weight=Decimal("0.5"),
        )
        with pytest.raises(TemplateNotFoundError):
            alloc_svc.create_allocation(db, payload)

    def test_create_invalid_instrument(self, db: Session, alloc_svc: TemplateAllocationService, template: PortfolioTemplate):
        payload = TemplateAllocationCreate(
            template_id=template.id,
            instrument_id=uuid.uuid4(),
            target_weight=Decimal("0.5"),
        )
        with pytest.raises(InstrumentReferenceError):
            alloc_svc.create_allocation(db, payload)

    def test_get_allocation(self, db: Session, alloc_svc: TemplateAllocationService, alloc_btc: TemplateAllocation):
        found = alloc_svc.get_allocation(db, alloc_btc.id)
        assert found.id == alloc_btc.id

    def test_get_allocation_not_found(self, db: Session, alloc_svc: TemplateAllocationService):
        with pytest.raises(TemplateAllocationNotFoundError):
            alloc_svc.get_allocation(db, uuid.uuid4())

    def test_list_by_template(
        self, db: Session, alloc_svc: TemplateAllocationService,
        alloc_btc: TemplateAllocation, template: PortfolioTemplate,
    ):
        items, total = alloc_svc.list_allocations_by_template(db, template.id)
        assert total >= 1

    def test_update_allocation(self, db: Session, alloc_svc: TemplateAllocationService, alloc_btc: TemplateAllocation):
        payload = TemplateAllocationUpdate(target_weight=Decimal("0.7"), max_weight=Decimal("0.8"))
        updated = alloc_svc.update_allocation(db, alloc_btc.id, payload)
        assert updated.target_weight == Decimal("0.7")

    def test_delete_allocation(self, db: Session, alloc_svc: TemplateAllocationService, alloc_btc: TemplateAllocation):
        aid = alloc_btc.id
        alloc_svc.delete_allocation(db, aid)
        with pytest.raises(TemplateAllocationNotFoundError):
            alloc_svc.get_allocation(db, aid)


# ---------------------------------------------------------------------------
# Template schema tests
# ---------------------------------------------------------------------------

class TestTemplateSchemas:

    def test_create_defaults(self):
        payload = TemplateCreate(
            product_id=uuid.uuid4(),
            template_code="SCHEMA_TEST",
            provisioned_portfolio_type="bundle_portfolio",
            name="Schema Test",
        )
        assert payload.base_currency == "EUR"
        assert payload.metadata == {}
        assert payload.strategy_definition_id is None
        assert payload.provisioned_portfolio_type == "bundle_portfolio"

    def test_create_requires_provisioned_portfolio_type(self):
        with pytest.raises(ValidationError):
            TemplateCreate(
                product_id=uuid.uuid4(),
                template_code="MISSING_TYPE",
                name="Missing Type",
            )

    def test_create_invalid_provisioned_portfolio_type(self):
        with pytest.raises(ValidationError, match="provisioned_portfolio_type"):
            TemplateCreate(
                product_id=uuid.uuid4(),
                template_code="BAD_TYPE",
                provisioned_portfolio_type="not_a_real_type",
                name="Bad Type",
            )

    def test_update_partial(self):
        payload = TemplateUpdate(name="Only Name")
        dumped = payload.model_dump(exclude_unset=True)
        assert "name" in dumped
        assert "base_currency" not in dumped
        assert "metadata" not in dumped
        assert "provisioned_portfolio_type" not in dumped

    def test_update_provisioned_portfolio_type(self):
        payload = TemplateUpdate(provisioned_portfolio_type="yield_portfolio")
        dumped = payload.model_dump(exclude_unset=True)
        assert dumped["provisioned_portfolio_type"] == "yield_portfolio"

    def test_update_invalid_provisioned_portfolio_type(self):
        with pytest.raises(ValidationError, match="provisioned_portfolio_type"):
            TemplateUpdate(provisioned_portfolio_type="invalid_type")
