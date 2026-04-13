"""Tests for the POST /subscriptions/{id}/provision endpoint."""
import uuid
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.products.models import ProductDefinition
from services.portfolio_engine.strategies.models import StrategyDefinition
from services.portfolio_engine.subscriptions.models import ProductSubscription
from services.portfolio_engine.templates.models import PortfolioTemplate, TemplateAllocation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client_active(db: Session) -> Client:
    c = Client(
        id=uuid.uuid4(),
        email="ep_prov_client@example.com",
        status="active",
        kyc_status="approved",
    )
    db.add(c)
    db.flush()
    return c


@pytest.fixture
def product_active(db: Session) -> ProductDefinition:
    p = ProductDefinition(
        id=uuid.uuid4(),
        product_code="EP_PROV_PROD",
        name="Bundle Test",
        product_type="crypto_bundle",
        status="active",
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def template(db: Session, product_active: ProductDefinition) -> PortfolioTemplate:
    t = PortfolioTemplate(
        id=uuid.uuid4(),
        product_id=product_active.id,
        template_code="EP_PROV_TMPL",
        provisioned_portfolio_type="bundle_portfolio",
        name="Balanced",
        base_currency="USD",
        risk_profile="moderate",
        metadata_={},
    )
    db.add(t)
    db.flush()
    return t


@pytest.fixture
def asset_btc(db: Session) -> Asset:
    a = Asset(id=uuid.uuid4(), symbol="EP_BTC", name="Bitcoin", asset_type="crypto", metadata_={})
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def instrument_btc(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(), asset_id=asset_btc.id, code="EP_BTC-SPOT",
        name="BTC Spot", instrument_type="spot", metadata_={},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def template_with_alloc(
    db: Session, template: PortfolioTemplate, instrument_btc: Instrument,
) -> PortfolioTemplate:
    alloc = TemplateAllocation(
        id=uuid.uuid4(),
        template_id=template.id,
        instrument_id=instrument_btc.id,
        target_weight=Decimal("1.000000"),
        allocation_priority=50,
    )
    db.add(alloc)
    db.flush()
    return template


@pytest.fixture
def pending_sub(
    db: Session, client_active: Client, product_active: ProductDefinition,
) -> ProductSubscription:
    s = ProductSubscription(
        id=uuid.uuid4(),
        client_id=client_active.id,
        product_id=product_active.id,
        status="pending",
        metadata_={},
    )
    db.add(s)
    db.flush()
    return s


# ---------------------------------------------------------------------------
# Service-level tests (via direct call, reusing db fixture)
# ---------------------------------------------------------------------------

class TestProvisionEndpointService:

    def test_provision_creates_portfolio(
        self, db: Session,
        pending_sub: ProductSubscription,
        template_with_alloc: PortfolioTemplate,
        client_active: Client,
        product_active: ProductDefinition,
    ):
        from services.portfolio_engine.provisioning.service import ProvisioningService

        svc = ProvisioningService()
        portfolio = svc.provision_from_subscription(db, pending_sub.id, template_with_alloc.id)

        assert portfolio.client_id == client_active.id
        assert portfolio.origin_product_id == product_active.id
        assert portfolio.portfolio_type == "bundle_portfolio"
        assert portfolio.status == "active"

        refreshed = db.query(ProductSubscription).filter(
            ProductSubscription.id == pending_sub.id,
        ).first()
        assert refreshed.portfolio_id == portfolio.id
        assert refreshed.status == "active"

    def test_provision_404_subscription(self, db: Session, template: PortfolioTemplate):
        from services.portfolio_engine.provisioning.errors import ProvisioningSubscriptionNotFoundError
        from services.portfolio_engine.provisioning.service import ProvisioningService

        svc = ProvisioningService()
        with pytest.raises(ProvisioningSubscriptionNotFoundError):
            svc.provision_from_subscription(db, uuid.uuid4(), template.id)

    def test_provision_404_template(self, db: Session, pending_sub: ProductSubscription):
        from services.portfolio_engine.provisioning.errors import ProvisioningTemplateNotFoundError
        from services.portfolio_engine.provisioning.service import ProvisioningService

        svc = ProvisioningService()
        with pytest.raises(ProvisioningTemplateNotFoundError):
            svc.provision_from_subscription(db, pending_sub.id, uuid.uuid4())

    def test_provision_409_not_pending(
        self, db: Session, client_active: Client,
        product_active: ProductDefinition, template: PortfolioTemplate,
    ):
        from services.portfolio_engine.provisioning.errors import InvalidSubscriptionStateError
        from services.portfolio_engine.provisioning.service import ProvisioningService

        active_sub = ProductSubscription(
            id=uuid.uuid4(),
            client_id=client_active.id,
            product_id=product_active.id,
            status="active",
            metadata_={},
        )
        db.add(active_sub)
        db.flush()

        svc = ProvisioningService()
        with pytest.raises(InvalidSubscriptionStateError):
            svc.provision_from_subscription(db, active_sub.id, template.id)

    def test_provision_409_already_provisioned(
        self, db: Session, client_active: Client,
        product_active: ProductDefinition, template: PortfolioTemplate,
    ):
        from services.portfolio_engine.provisioning.errors import AlreadyProvisionedError
        from services.portfolio_engine.provisioning.service import ProvisioningService

        existing_pf = Portfolio(
            id=uuid.uuid4(), client_id=client_active.id,
            portfolio_type="bundle_portfolio", name="Existing", metadata_={},
        )
        db.add(existing_pf)
        db.flush()

        sub = ProductSubscription(
            id=uuid.uuid4(),
            client_id=client_active.id,
            product_id=product_active.id,
            portfolio_id=existing_pf.id,
            status="pending",
            metadata_={},
        )
        db.add(sub)
        db.flush()

        svc = ProvisioningService()
        with pytest.raises(AlreadyProvisionedError):
            svc.provision_from_subscription(db, sub.id, template.id)

    def test_provision_422_template_product_mismatch(
        self, db: Session, pending_sub: ProductSubscription,
    ):
        from services.portfolio_engine.provisioning.errors import TemplateProductMismatchError
        from services.portfolio_engine.provisioning.service import ProvisioningService

        other_product = ProductDefinition(
            id=uuid.uuid4(), product_code="EP_OTHER",
            name="Other", product_type="yield_vault", status="active",
        )
        db.add(other_product)
        db.flush()

        wrong_tmpl = PortfolioTemplate(
            id=uuid.uuid4(), product_id=other_product.id,
            template_code="EP_WRONG", provisioned_portfolio_type="yield_portfolio",
            name="Wrong", metadata_={},
        )
        db.add(wrong_tmpl)
        db.flush()

        svc = ProvisioningService()
        with pytest.raises(TemplateProductMismatchError):
            svc.provision_from_subscription(db, pending_sub.id, wrong_tmpl.id)

    def test_provision_422_client_not_eligible(
        self, db: Session, product_active: ProductDefinition, template: PortfolioTemplate,
    ):
        from services.portfolio_engine.provisioning.errors import ClientNotEligibleError
        from services.portfolio_engine.provisioning.service import ProvisioningService

        bad_client = Client(
            id=uuid.uuid4(), email="ep_bad@example.com",
            status="suspended", kyc_status="approved",
        )
        db.add(bad_client)
        db.flush()

        sub = ProductSubscription(
            id=uuid.uuid4(), client_id=bad_client.id,
            product_id=product_active.id, status="pending", metadata_={},
        )
        db.add(sub)
        db.flush()

        svc = ProvisioningService()
        with pytest.raises(ClientNotEligibleError):
            svc.provision_from_subscription(db, sub.id, template.id)

    def test_provision_422_inactive_product(
        self, db: Session, client_active: Client,
    ):
        from services.portfolio_engine.provisioning.errors import InactiveProductError
        from services.portfolio_engine.provisioning.service import ProvisioningService

        draft = ProductDefinition(
            id=uuid.uuid4(), product_code="EP_DRAFT",
            name="Draft", product_type="crypto_bundle", status="draft",
        )
        db.add(draft)
        db.flush()

        tmpl = PortfolioTemplate(
            id=uuid.uuid4(), product_id=draft.id,
            template_code="EP_DRAFT_TMPL", provisioned_portfolio_type="bundle_portfolio",
            name="Draft Template", metadata_={},
        )
        db.add(tmpl)
        db.flush()

        sub = ProductSubscription(
            id=uuid.uuid4(), client_id=client_active.id,
            product_id=draft.id, status="pending", metadata_={},
        )
        db.add(sub)
        db.flush()

        svc = ProvisioningService()
        with pytest.raises(InactiveProductError):
            svc.provision_from_subscription(db, sub.id, tmpl.id)
