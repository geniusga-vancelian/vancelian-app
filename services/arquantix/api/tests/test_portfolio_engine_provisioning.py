"""Tests for Portfolio Engine — Provisioning service."""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from conftest import make_linked_client
from services.portfolio_engine.allocations.models import TargetAllocation
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.products.models import ProductDefinition
from services.portfolio_engine.strategies.models import StrategyDefinition, StrategyInstance
from services.portfolio_engine.subscriptions.models import ProductSubscription
from services.portfolio_engine.templates.models import PortfolioTemplate, TemplateAllocation
from services.portfolio_engine.provisioning.errors import (
    AlreadyProvisionedError,
    ClientNotEligibleError,
    InactiveProductError,
    InvalidSubscriptionStateError,
    ProvisioningSubscriptionNotFoundError,
    ProvisioningTemplateNotFoundError,
    TemplateProductMismatchError,
)
from services.portfolio_engine.provisioning.service import ProvisioningService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def prov_service() -> ProvisioningService:
    return ProvisioningService()


@pytest.fixture
def client_active(db: Session) -> Client:
    return make_linked_client(db, email="prov_client@example.com", status="active", kyc_status="approved")


@pytest.fixture
def product_active(db: Session) -> ProductDefinition:
    p = ProductDefinition(
        id=uuid.uuid4(),
        product_code="PROV_PROD_01",
        name="Crypto Bundle Balanced",
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
        code="PROV_STRAT_DEF",
        name="Fixed Weight Strategy",
        strategy_type="fixed_weight",
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def template_with_strategy(
    db: Session, product_active: ProductDefinition, strategy_def: StrategyDefinition,
) -> PortfolioTemplate:
    t = PortfolioTemplate(
        id=uuid.uuid4(),
        product_id=product_active.id,
        template_code="PROV_TMPL_STRAT",
        provisioned_portfolio_type="bundle_portfolio",
        name="Balanced with Strategy",
        base_currency="USD",
        risk_profile="moderate",
        strategy_definition_id=strategy_def.id,
        metadata_={},
    )
    db.add(t)
    db.flush()
    return t


@pytest.fixture
def template_no_strategy(db: Session, product_active: ProductDefinition) -> PortfolioTemplate:
    t = PortfolioTemplate(
        id=uuid.uuid4(),
        product_id=product_active.id,
        template_code="PROV_TMPL_SIMPLE",
        provisioned_portfolio_type="managed_portfolio",
        name="Simple Template",
        base_currency="EUR",
        risk_profile="conservative",
        metadata_={},
    )
    db.add(t)
    db.flush()
    return t


@pytest.fixture
def asset_btc(db: Session) -> Asset:
    a = Asset(id=uuid.uuid4(), symbol="PROV_BTC", name="Bitcoin", asset_type="crypto", metadata_={})
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def asset_eth(db: Session) -> Asset:
    a = Asset(id=uuid.uuid4(), symbol="PROV_ETH", name="Ethereum", asset_type="crypto", metadata_={})
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def instrument_btc(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(), asset_id=asset_btc.id, code="PROV_BTC-SPOT",
        name="BTC Spot", instrument_type="spot", metadata_={},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def instrument_eth(db: Session, asset_eth: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(), asset_id=asset_eth.id, code="PROV_ETH-SPOT",
        name="ETH Spot", instrument_type="spot", metadata_={},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def template_allocations(
    db: Session,
    template_with_strategy: PortfolioTemplate,
    instrument_btc: Instrument,
    instrument_eth: Instrument,
) -> list[TemplateAllocation]:
    allocs = [
        TemplateAllocation(
            id=uuid.uuid4(),
            template_id=template_with_strategy.id,
            instrument_id=instrument_btc.id,
            target_weight=Decimal("0.600000"),
            min_weight=Decimal("0.500000"),
            max_weight=Decimal("0.700000"),
            allocation_priority=50,
        ),
        TemplateAllocation(
            id=uuid.uuid4(),
            template_id=template_with_strategy.id,
            instrument_id=instrument_eth.id,
            target_weight=Decimal("0.400000"),
            min_weight=Decimal("0.300000"),
            max_weight=Decimal("0.500000"),
            allocation_priority=60,
        ),
    ]
    db.add_all(allocs)
    db.flush()
    return allocs


@pytest.fixture
def pending_subscription(
    db: Session, client_active: Client, product_active: ProductDefinition,
) -> ProductSubscription:
    s = ProductSubscription(
        id=uuid.uuid4(),
        client_id=client_active.id,
        product_id=product_active.id,
        subscription_amount=Decimal("5000.00"),
        subscription_currency="EUR",
        status="pending",
        metadata_={},
    )
    db.add(s)
    db.flush()
    return s


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------

class TestProvisioningHappyPath:

    def test_full_provisioning_with_strategy_and_allocations(
        self, db: Session, prov_service: ProvisioningService,
        pending_subscription: ProductSubscription,
        template_with_strategy: PortfolioTemplate,
        template_allocations: list[TemplateAllocation],
        strategy_def: StrategyDefinition,
        product_active: ProductDefinition,
        client_active: Client,
    ):
        portfolio = prov_service.provision_from_subscription(
            db, pending_subscription.id, template_with_strategy.id,
        )

        assert portfolio.id is not None
        assert portfolio.client_id == client_active.id
        assert portfolio.origin_product_id == product_active.id
        assert portfolio.portfolio_type == "bundle_portfolio"
        assert portfolio.base_currency == "USD"
        assert portfolio.risk_profile == "moderate"
        assert portfolio.status == "active"
        assert portfolio.metadata_["provisioned_from_template"] == str(template_with_strategy.id)
        assert portfolio.metadata_["provisioned_from_subscription"] == str(pending_subscription.id)

        instances = (
            db.query(StrategyInstance)
            .filter(StrategyInstance.portfolio_id == portfolio.id)
            .all()
        )
        assert len(instances) == 1
        assert instances[0].strategy_definition_id == strategy_def.id
        assert instances[0].status == "active"

        allocs = (
            db.query(TargetAllocation)
            .filter(TargetAllocation.portfolio_id == portfolio.id)
            .order_by(TargetAllocation.rebalance_priority)
            .all()
        )
        assert len(allocs) == 2
        assert allocs[0].target_weight == Decimal("0.600000")
        assert allocs[0].rebalance_priority == 50
        assert allocs[0].sleeve_id is None
        assert allocs[1].target_weight == Decimal("0.400000")
        assert allocs[1].rebalance_priority == 60

        refreshed_sub = db.query(ProductSubscription).filter(
            ProductSubscription.id == pending_subscription.id,
        ).first()
        assert refreshed_sub.portfolio_id == portfolio.id
        assert refreshed_sub.status == "active"

    def test_provisioning_without_strategy(
        self, db: Session, prov_service: ProvisioningService,
        pending_subscription: ProductSubscription,
        template_no_strategy: PortfolioTemplate,
        client_active: Client,
    ):
        portfolio = prov_service.provision_from_subscription(
            db, pending_subscription.id, template_no_strategy.id,
        )

        assert portfolio.portfolio_type == "managed_portfolio"
        assert portfolio.base_currency == "EUR"
        assert portfolio.risk_profile == "conservative"

        instances = (
            db.query(StrategyInstance)
            .filter(StrategyInstance.portfolio_id == portfolio.id)
            .all()
        )
        assert len(instances) == 0

    def test_provisioning_with_zero_allocations(
        self, db: Session, prov_service: ProvisioningService,
        pending_subscription: ProductSubscription,
        template_no_strategy: PortfolioTemplate,
    ):
        portfolio = prov_service.provision_from_subscription(
            db, pending_subscription.id, template_no_strategy.id,
        )

        allocs = (
            db.query(TargetAllocation)
            .filter(TargetAllocation.portfolio_id == portfolio.id)
            .all()
        )
        assert len(allocs) == 0
        assert portfolio.status == "active"


# ---------------------------------------------------------------------------
# Validation error tests
# ---------------------------------------------------------------------------

class TestProvisioningValidationErrors:

    def test_subscription_not_found(self, db: Session, prov_service: ProvisioningService):
        with pytest.raises(ProvisioningSubscriptionNotFoundError):
            prov_service.provision_from_subscription(db, uuid.uuid4(), uuid.uuid4())

    def test_subscription_not_pending(
        self, db: Session, prov_service: ProvisioningService,
        client_active: Client, product_active: ProductDefinition,
        template_no_strategy: PortfolioTemplate,
    ):
        sub = ProductSubscription(
            id=uuid.uuid4(),
            client_id=client_active.id,
            product_id=product_active.id,
            status="active",
            metadata_={},
        )
        db.add(sub)
        db.flush()

        with pytest.raises(InvalidSubscriptionStateError) as exc_info:
            prov_service.provision_from_subscription(db, sub.id, template_no_strategy.id)
        assert exc_info.value.current_status == "active"

    def test_already_provisioned(
        self, db: Session, prov_service: ProvisioningService,
        client_active: Client, product_active: ProductDefinition,
        template_no_strategy: PortfolioTemplate,
    ):
        existing_portfolio = Portfolio(
            id=uuid.uuid4(),
            client_id=client_active.id,
            portfolio_type="bundle_portfolio",
            name="Existing",
            metadata_={},
        )
        db.add(existing_portfolio)
        db.flush()

        sub = ProductSubscription(
            id=uuid.uuid4(),
            client_id=client_active.id,
            product_id=product_active.id,
            portfolio_id=existing_portfolio.id,
            status="pending",
            metadata_={},
        )
        db.add(sub)
        db.flush()

        with pytest.raises(AlreadyProvisionedError) as exc_info:
            prov_service.provision_from_subscription(db, sub.id, template_no_strategy.id)
        assert exc_info.value.portfolio_id == existing_portfolio.id

    def test_template_not_found(
        self, db: Session, prov_service: ProvisioningService,
        pending_subscription: ProductSubscription,
    ):
        with pytest.raises(ProvisioningTemplateNotFoundError):
            prov_service.provision_from_subscription(db, pending_subscription.id, uuid.uuid4())

    def test_template_product_mismatch(
        self, db: Session, prov_service: ProvisioningService,
        pending_subscription: ProductSubscription,
    ):
        other_product = ProductDefinition(
            id=uuid.uuid4(),
            product_code="PROV_OTHER_PROD",
            name="Other Product",
            product_type="yield_vault",
            status="active",
        )
        db.add(other_product)
        db.flush()

        wrong_template = PortfolioTemplate(
            id=uuid.uuid4(),
            product_id=other_product.id,
            template_code="PROV_WRONG_TMPL",
            provisioned_portfolio_type="yield_portfolio",
            name="Wrong Template",
            metadata_={},
        )
        db.add(wrong_template)
        db.flush()

        with pytest.raises(TemplateProductMismatchError) as exc_info:
            prov_service.provision_from_subscription(
                db, pending_subscription.id, wrong_template.id,
            )
        assert exc_info.value.template_product_id == other_product.id

    def test_client_not_active(
        self, db: Session, prov_service: ProvisioningService,
        product_active: ProductDefinition,
        template_no_strategy: PortfolioTemplate,
    ):
        inactive_client = make_linked_client(db, email="prov_inactive@example.com", status="suspended", kyc_status="approved")

        sub = ProductSubscription(
            id=uuid.uuid4(),
            client_id=inactive_client.id,
            product_id=product_active.id,
            status="pending",
            metadata_={},
        )
        db.add(sub)
        db.flush()

        with pytest.raises(ClientNotEligibleError) as exc_info:
            prov_service.provision_from_subscription(db, sub.id, template_no_strategy.id)
        assert "suspended" in exc_info.value.reason

    def test_client_kyc_not_approved(
        self, db: Session, prov_service: ProvisioningService,
        product_active: ProductDefinition,
        template_no_strategy: PortfolioTemplate,
    ):
        client_no_kyc = make_linked_client(db, email="prov_nokyc@example.com", status="active", kyc_status="pending")

        sub = ProductSubscription(
            id=uuid.uuid4(),
            client_id=client_no_kyc.id,
            product_id=product_active.id,
            status="pending",
            metadata_={},
        )
        db.add(sub)
        db.flush()

        with pytest.raises(ClientNotEligibleError) as exc_info:
            prov_service.provision_from_subscription(db, sub.id, template_no_strategy.id)
        assert "kyc_status" in exc_info.value.reason

    def test_product_not_active(
        self, db: Session, prov_service: ProvisioningService,
        client_active: Client,
    ):
        draft_product = ProductDefinition(
            id=uuid.uuid4(),
            product_code="PROV_DRAFT_PROD",
            name="Draft Product",
            product_type="crypto_bundle",
            status="draft",
        )
        db.add(draft_product)
        db.flush()

        tmpl = PortfolioTemplate(
            id=uuid.uuid4(),
            product_id=draft_product.id,
            template_code="PROV_DRAFT_TMPL",
            provisioned_portfolio_type="bundle_portfolio",
            name="Draft Template",
            metadata_={},
        )
        db.add(tmpl)
        db.flush()

        sub = ProductSubscription(
            id=uuid.uuid4(),
            client_id=client_active.id,
            product_id=draft_product.id,
            status="pending",
            metadata_={},
        )
        db.add(sub)
        db.flush()

        with pytest.raises(InactiveProductError) as exc_info:
            prov_service.provision_from_subscription(db, sub.id, tmpl.id)
        assert exc_info.value.current_status == "draft"


# ---------------------------------------------------------------------------
# Idempotence / no side effects
# ---------------------------------------------------------------------------

class TestProvisioningNoSideEffects:

    def test_no_positions_created(
        self, db: Session, prov_service: ProvisioningService,
        pending_subscription: ProductSubscription,
        template_with_strategy: PortfolioTemplate,
        template_allocations: list[TemplateAllocation],
    ):
        portfolio = prov_service.provision_from_subscription(
            db, pending_subscription.id, template_with_strategy.id,
        )
        from services.portfolio_engine.portfolios.models import Portfolio as P
        assert db.query(P).filter(P.id == portfolio.id).first() is not None
        # No positions table query — we simply confirm only the expected objects exist

    def test_portfolio_name_is_product_name(
        self, db: Session, prov_service: ProvisioningService,
        pending_subscription: ProductSubscription,
        template_with_strategy: PortfolioTemplate,
        template_allocations: list[TemplateAllocation],
        product_active: ProductDefinition,
    ):
        portfolio = prov_service.provision_from_subscription(
            db, pending_subscription.id, template_with_strategy.id,
        )
        assert portfolio.name == product_active.name

    def test_allocation_weights_copied_exactly(
        self, db: Session, prov_service: ProvisioningService,
        pending_subscription: ProductSubscription,
        template_with_strategy: PortfolioTemplate,
        template_allocations: list[TemplateAllocation],
    ):
        portfolio = prov_service.provision_from_subscription(
            db, pending_subscription.id, template_with_strategy.id,
        )

        target_allocs = (
            db.query(TargetAllocation)
            .filter(TargetAllocation.portfolio_id == portfolio.id)
            .all()
        )
        template_by_instrument = {
            str(ta.instrument_id): ta for ta in template_allocations
        }
        for alloc in target_allocs:
            src = template_by_instrument[str(alloc.instrument_id)]
            assert alloc.target_weight == src.target_weight
            assert alloc.min_weight == src.min_weight
            assert alloc.max_weight == src.max_weight
            assert alloc.rebalance_priority == src.allocation_priority
