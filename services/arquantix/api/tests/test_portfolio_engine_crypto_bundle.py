"""Tests for Crypto Bundle Top 2 — E2E product, subscription, provisioning, catalog."""
import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.products.models import ProductDefinition
from services.portfolio_engine.products.catalog import CatalogService
from services.portfolio_engine.templates.models import PortfolioTemplate, TemplateAllocation
from services.portfolio_engine.subscriptions.models import ProductSubscription
from services.portfolio_engine.provisioning.service import ProvisioningService
from services.portfolio_engine.rebalancing.models import RebalancePolicy
from services.portfolio_engine.allocations.models import TargetAllocation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def btc_asset(db: Session) -> Asset:
    a = Asset(
        id=uuid.uuid4(),
        symbol="BTC_CB",
        name="Bitcoin",
        asset_type="crypto",
    )
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def eth_asset(db: Session) -> Asset:
    a = Asset(
        id=uuid.uuid4(),
        symbol="ETH_CB",
        name="Ethereum",
        asset_type="crypto",
    )
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def btc_instrument(db: Session, btc_asset: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(),
        asset_id=btc_asset.id,
        code="BTC-SPOT-CB",
        name="Bitcoin Spot",
        instrument_type="spot",
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def eth_instrument(db: Session, eth_asset: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(),
        asset_id=eth_asset.id,
        code="ETH-SPOT-CB",
        name="Ethereum Spot",
        instrument_type="spot",
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def bundle_product(db: Session) -> ProductDefinition:
    p = ProductDefinition(
        id=uuid.uuid4(),
        product_code=f"CRYPTO_BUNDLE_TOP2_{uuid.uuid4().hex[:6]}",
        name="Crypto Bundle Top 2",
        description="A simple crypto allocation strategy composed of 70% BTC and 30% ETH.",
        product_type="crypto_bundle",
        risk_label="high",
        base_currency="USD",
        is_public=True,
        status="active",
        metadata_={
            "short_description": "70% BTC / 30% ETH",
            "available_rebalance_frequencies": ["weekly", "monthly", "quarterly"],
        },
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def bundle_template(
    db: Session,
    bundle_product: ProductDefinition,
) -> PortfolioTemplate:
    t = PortfolioTemplate(
        id=uuid.uuid4(),
        product_id=bundle_product.id,
        template_code=f"CB_TOP2_TPL_{uuid.uuid4().hex[:6]}",
        provisioned_portfolio_type="bundle_portfolio",
        name="Crypto Bundle Top 2 Template",
        base_currency="USD",
        risk_profile="high",
        metadata_={},
    )
    db.add(t)
    db.flush()
    return t


@pytest.fixture
def template_allocations(
    db: Session,
    bundle_template: PortfolioTemplate,
    btc_instrument: Instrument,
    eth_instrument: Instrument,
) -> list[TemplateAllocation]:
    allocs = []
    for inst, weight in [(btc_instrument, Decimal("0.700000")), (eth_instrument, Decimal("0.300000"))]:
        ta = TemplateAllocation(
            id=uuid.uuid4(),
            template_id=bundle_template.id,
            instrument_id=inst.id,
            target_weight=weight,
            allocation_priority=100,
        )
        db.add(ta)
        allocs.append(ta)
    db.flush()
    return allocs


@pytest.fixture
def pe_client(db: Session) -> Client:
    c = Client(
        id=uuid.uuid4(),
        email=f"cb_client_{uuid.uuid4().hex[:6]}@test.com",
        status="active",
        kyc_status="approved",
    )
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def provisioning_service() -> ProvisioningService:
    return ProvisioningService()


@pytest.fixture
def catalog_service() -> CatalogService:
    return CatalogService()


# ---------------------------------------------------------------------------
# 1. Product + Template + Allocations bootstrap tests
# ---------------------------------------------------------------------------

class TestBootstrapData:

    def test_product_creation(self, db: Session, bundle_product: ProductDefinition):
        assert bundle_product.product_code.startswith("CRYPTO_BUNDLE_TOP2_")
        assert bundle_product.product_type == "crypto_bundle"
        assert bundle_product.status == "active"
        assert bundle_product.is_public is True
        assert bundle_product.description is not None

    def test_template_allocations_btc_eth(
        self, db: Session, template_allocations: list[TemplateAllocation],
        btc_instrument: Instrument, eth_instrument: Instrument,
    ):
        assert len(template_allocations) == 2
        weights = {ta.instrument_id: ta.target_weight for ta in template_allocations}
        assert weights[btc_instrument.id] == Decimal("0.700000")
        assert weights[eth_instrument.id] == Decimal("0.300000")


# ---------------------------------------------------------------------------
# 2. Subscription with frequency tests
# ---------------------------------------------------------------------------

class TestSubscriptionWithFrequency:

    def _create_subscription(
        self, db: Session, pe_client: Client, bundle_product: ProductDefinition, frequency: str,
    ) -> ProductSubscription:
        sub = ProductSubscription(
            id=uuid.uuid4(),
            client_id=pe_client.id,
            product_id=bundle_product.id,
            subscription_amount=Decimal("1000.00"),
            subscription_currency="USD",
            status="pending",
            metadata_={"rebalance_frequency": frequency},
        )
        db.add(sub)
        db.flush()
        return sub

    def test_subscription_weekly(self, db: Session, pe_client, bundle_product):
        sub = self._create_subscription(db, pe_client, bundle_product, "weekly")
        assert sub.metadata_["rebalance_frequency"] == "weekly"

    def test_subscription_monthly(self, db: Session, pe_client, bundle_product):
        sub = self._create_subscription(db, pe_client, bundle_product, "monthly")
        assert sub.metadata_["rebalance_frequency"] == "monthly"

    def test_subscription_quarterly(self, db: Session, pe_client, bundle_product):
        sub = self._create_subscription(db, pe_client, bundle_product, "quarterly")
        assert sub.metadata_["rebalance_frequency"] == "quarterly"


# ---------------------------------------------------------------------------
# 3. Provisioning with frequency propagation
# ---------------------------------------------------------------------------

class TestProvisioningWithFrequency:

    def _provision(
        self,
        db: Session,
        pe_client: Client,
        bundle_product: ProductDefinition,
        bundle_template: PortfolioTemplate,
        template_allocations: list,
        frequency: str,
    ):
        sub = ProductSubscription(
            id=uuid.uuid4(),
            client_id=pe_client.id,
            product_id=bundle_product.id,
            subscription_amount=Decimal("1000.00"),
            subscription_currency="USD",
            status="pending",
            metadata_={"rebalance_frequency": frequency},
        )
        db.add(sub)
        db.flush()

        svc = ProvisioningService()
        portfolio = svc.provision_from_subscription(db, sub.id, bundle_template.id)
        return portfolio, sub

    def test_provisioning_creates_portfolio(
        self, db, pe_client, bundle_product, bundle_template, template_allocations,
    ):
        portfolio, sub = self._provision(
            db, pe_client, bundle_product, bundle_template, template_allocations, "monthly",
        )
        assert portfolio is not None
        assert portfolio.client_id == pe_client.id
        assert portfolio.origin_product_id == bundle_product.id
        assert portfolio.portfolio_type == "bundle_portfolio"

    def test_provisioning_copies_allocations(
        self, db, pe_client, bundle_product, bundle_template, template_allocations,
        btc_instrument, eth_instrument,
    ):
        portfolio, _ = self._provision(
            db, pe_client, bundle_product, bundle_template, template_allocations, "weekly",
        )
        allocs = (
            db.query(TargetAllocation)
            .filter(TargetAllocation.portfolio_id == portfolio.id)
            .all()
        )
        assert len(allocs) == 2
        weights = {a.instrument_id: a.target_weight for a in allocs}
        assert weights[btc_instrument.id] == Decimal("0.700000")
        assert weights[eth_instrument.id] == Decimal("0.300000")

    def test_provisioning_creates_rebalance_policy_weekly(
        self, db, pe_client, bundle_product, bundle_template, template_allocations,
    ):
        portfolio, _ = self._provision(
            db, pe_client, bundle_product, bundle_template, template_allocations, "weekly",
        )
        policy = (
            db.query(RebalancePolicy)
            .filter(RebalancePolicy.portfolio_id == portfolio.id)
            .first()
        )
        assert policy is not None
        assert policy.method == "periodic"
        assert policy.frequency == "weekly"

    def test_provisioning_creates_rebalance_policy_monthly(
        self, db, pe_client, bundle_product, bundle_template, template_allocations,
    ):
        portfolio, _ = self._provision(
            db, pe_client, bundle_product, bundle_template, template_allocations, "monthly",
        )
        policy = (
            db.query(RebalancePolicy)
            .filter(RebalancePolicy.portfolio_id == portfolio.id)
            .first()
        )
        assert policy is not None
        assert policy.frequency == "monthly"

    def test_provisioning_creates_rebalance_policy_quarterly(
        self, db, pe_client, bundle_product, bundle_template, template_allocations,
    ):
        portfolio, _ = self._provision(
            db, pe_client, bundle_product, bundle_template, template_allocations, "quarterly",
        )
        policy = (
            db.query(RebalancePolicy)
            .filter(RebalancePolicy.portfolio_id == portfolio.id)
            .first()
        )
        assert policy is not None
        assert policy.frequency == "quarterly"

    def test_provisioning_no_frequency_no_policy(
        self, db, pe_client, bundle_product, bundle_template, template_allocations,
    ):
        sub = ProductSubscription(
            id=uuid.uuid4(),
            client_id=pe_client.id,
            product_id=bundle_product.id,
            status="pending",
            metadata_={},
        )
        db.add(sub)
        db.flush()

        svc = ProvisioningService()
        portfolio = svc.provision_from_subscription(db, sub.id, bundle_template.id)

        policy = (
            db.query(RebalancePolicy)
            .filter(RebalancePolicy.portfolio_id == portfolio.id)
            .first()
        )
        assert policy is None

    def test_provisioning_invalid_frequency_no_policy(
        self, db, pe_client, bundle_product, bundle_template, template_allocations,
    ):
        sub = ProductSubscription(
            id=uuid.uuid4(),
            client_id=pe_client.id,
            product_id=bundle_product.id,
            status="pending",
            metadata_={"rebalance_frequency": "every_5_minutes"},
        )
        db.add(sub)
        db.flush()

        svc = ProvisioningService()
        portfolio = svc.provision_from_subscription(db, sub.id, bundle_template.id)

        policy = (
            db.query(RebalancePolicy)
            .filter(RebalancePolicy.portfolio_id == portfolio.id)
            .first()
        )
        assert policy is None

    def test_provisioning_finalizes_subscription(
        self, db, pe_client, bundle_product, bundle_template, template_allocations,
    ):
        portfolio, sub = self._provision(
            db, pe_client, bundle_product, bundle_template, template_allocations, "monthly",
        )
        db.refresh(sub)
        assert sub.status == "active"
        assert sub.portfolio_id == portfolio.id


# ---------------------------------------------------------------------------
# 4. Catalog service tests
# ---------------------------------------------------------------------------

class TestCatalogService:

    def test_public_catalog_returns_active_public(
        self, db, bundle_product, bundle_template, template_allocations,
        btc_asset, eth_asset, catalog_service,
    ):
        items = catalog_service.get_public_catalog(db)
        matching = [i for i in items if i.product_code == bundle_product.product_code]
        assert len(matching) == 1
        item = matching[0]
        assert item.name == "Crypto Bundle Top 2"
        assert len(item.allocations) == 2
        assert "weekly" in item.available_rebalance_frequencies
        assert "monthly" in item.available_rebalance_frequencies
        assert "quarterly" in item.available_rebalance_frequencies

    def test_public_catalog_allocation_summary(
        self, db, bundle_product, bundle_template, template_allocations,
        btc_asset, eth_asset, catalog_service,
    ):
        items = catalog_service.get_public_catalog(db)
        matching = [i for i in items if i.product_code == bundle_product.product_code]
        item = matching[0]
        symbols = {a.asset_symbol: a.target_weight for a in item.allocations}
        assert symbols["BTC_CB"] == Decimal("0.700000")
        assert symbols["ETH_CB"] == Decimal("0.300000")

    def test_public_catalog_excludes_draft(self, db, catalog_service):
        draft = ProductDefinition(
            id=uuid.uuid4(),
            product_code=f"DRAFT_{uuid.uuid4().hex[:6]}",
            name="Draft Product",
            product_type="crypto_bundle",
            is_public=True,
            status="draft",
        )
        db.add(draft)
        db.flush()
        items = catalog_service.get_public_catalog(db)
        codes = [i.product_code for i in items]
        assert draft.product_code not in codes

    def test_public_catalog_excludes_private(self, db, catalog_service):
        private = ProductDefinition(
            id=uuid.uuid4(),
            product_code=f"PRIVATE_{uuid.uuid4().hex[:6]}",
            name="Private Product",
            product_type="crypto_bundle",
            is_public=False,
            status="active",
        )
        db.add(private)
        db.flush()
        items = catalog_service.get_public_catalog(db)
        codes = [i.product_code for i in items]
        assert private.product_code not in codes

    def test_product_detail(
        self, db, bundle_product, bundle_template, template_allocations,
        btc_asset, eth_asset, catalog_service,
    ):
        detail = catalog_service.get_product_detail(db, bundle_product.id)
        assert detail is not None
        assert detail.product_code == bundle_product.product_code
        assert detail.template_id == bundle_template.id
        assert detail.template_code == bundle_template.template_code
        assert len(detail.allocations) == 2
        assert detail.is_public is True
        assert detail.status == "active"

    def test_product_detail_not_found(self, db, catalog_service):
        detail = catalog_service.get_product_detail(db, uuid.uuid4())
        assert detail is None
