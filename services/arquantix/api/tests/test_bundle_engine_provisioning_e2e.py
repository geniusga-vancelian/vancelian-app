"""E2E provisioning test for Bundle Engine v1.

Proves the full business loop:
  BUNDLE → SUBSCRIPTION → PROVISIONING → PORTFOLIO → TARGET ALLOCATIONS → REBALANCE POLICY

Two scenarios:
  1. With rebalance_frequency in subscription metadata → RebalancePolicy created
  2. Without rebalance_frequency → no RebalancePolicy created
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.allocations.models import TargetAllocation
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundles.schemas import BundleAllocationCreate, BundleCreate
from services.portfolio_engine.bundles.service import BundleEngineService
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.products.models import ProductDefinition
from services.portfolio_engine.provisioning.service import ProvisioningService
from services.portfolio_engine.rebalancing.models import RebalancePolicy
from services.portfolio_engine.subscriptions.models import ProductSubscription
from services.portfolio_engine.templates.models import PortfolioTemplate, TemplateAllocation


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def bundle_svc() -> BundleEngineService:
    return BundleEngineService()


@pytest.fixture
def provisioning_svc() -> ProvisioningService:
    return ProvisioningService()


@pytest.fixture
def e2e_assets(db: Session) -> dict[str, Asset]:
    """Create BTC and ETH assets with unique symbols."""
    suffix = uuid.uuid4().hex[:6].upper()
    btc = Asset(id=uuid.uuid4(), symbol=f"BTC_{suffix}", name="Bitcoin", asset_type="cryptocurrency")
    eth = Asset(id=uuid.uuid4(), symbol=f"ETH_{suffix}", name="Ethereum", asset_type="cryptocurrency")
    db.add_all([btc, eth])
    db.flush()
    return {"BTC": btc, "ETH": eth}


@pytest.fixture
def e2e_instruments(db: Session, e2e_assets: dict[str, Asset]) -> dict[str, Instrument]:
    """Create BTC-SPOT and ETH-SPOT instruments."""
    suffix = uuid.uuid4().hex[:6].upper()
    btc_instr = Instrument(
        id=uuid.uuid4(),
        asset_id=e2e_assets["BTC"].id,
        code=f"BTC_SPOT_{suffix}",
        name="Bitcoin Spot",
        instrument_type="spot",
    )
    eth_instr = Instrument(
        id=uuid.uuid4(),
        asset_id=e2e_assets["ETH"].id,
        code=f"ETH_SPOT_{suffix}",
        name="Ethereum Spot",
        instrument_type="spot",
    )
    db.add_all([btc_instr, eth_instr])
    db.flush()
    return {"BTC": btc_instr, "ETH": eth_instr}


@pytest.fixture
def e2e_bundle(
    db: Session,
    bundle_svc: BundleEngineService,
    e2e_instruments: dict[str, Instrument],
):
    """Create a bundle with BTC 70% / ETH 30%."""
    code = f"E2E_BUNDLE_{uuid.uuid4().hex[:6].upper()}"
    payload = BundleCreate(
        name="Crypto Bundle Top 2 E2E",
        product_code=code,
        description="E2E test bundle",
        risk_label="high",
        base_currency="USD",
        is_public=True,
        allocations=[
            BundleAllocationCreate(
                instrument_id=e2e_instruments["BTC"].id,
                target_weight=Decimal("0.7"),
            ),
            BundleAllocationCreate(
                instrument_id=e2e_instruments["ETH"].id,
                target_weight=Decimal("0.3"),
            ),
        ],
        available_rebalance_frequencies=["weekly", "monthly", "quarterly"],
    )
    result = bundle_svc.create_bundle(db, payload, actor_type="admin", actor_id="e2e-test")
    db.flush()
    return result


@pytest.fixture
def eligible_client(db: Session) -> Client:
    """Create an active client with approved KYC."""
    client = Client(
        id=uuid.uuid4(),
        email=f"e2e-{uuid.uuid4().hex[:8]}@test.com",
        status="active",
        kyc_status="approved",
    )
    db.add(client)
    db.flush()
    return client


# ---------------------------------------------------------------------------
# E2E Test: Full provisioning with rebalance frequency
# ---------------------------------------------------------------------------

class TestBundleProvisioningE2E:

    def test_full_provisioning_with_rebalance_frequency(
        self,
        db: Session,
        e2e_bundle,
        e2e_instruments: dict[str, Instrument],
        eligible_client: Client,
        provisioning_svc: ProvisioningService,
    ):
        """
        BUNDLE → SUBSCRIPTION → PROVISIONING → PORTFOLIO + ALLOCATIONS + REBALANCE POLICY

        This is the most important test of the Bundle Engine:
        it proves that a dynamically created bundle is fully provisionable.
        """
        product_id = e2e_bundle.id
        template_id = e2e_bundle.template_id

        # ── A. Verify bundle creation ──
        product = db.query(ProductDefinition).filter_by(id=product_id).first()
        assert product is not None, "ProductDefinition must exist"
        assert product.status == "active"
        assert product.product_type == "crypto_bundle"
        meta = product.metadata_ or {}
        assert "available_rebalance_frequencies" in meta
        assert meta["available_rebalance_frequencies"] == ["weekly", "monthly", "quarterly"]

        # ── B. Verify template + allocations ──
        template = db.query(PortfolioTemplate).filter_by(product_id=product_id).first()
        assert template is not None, "Exactly one PortfolioTemplate must be linked"
        assert template.id == template_id

        template_allocs = (
            db.query(TemplateAllocation)
            .filter_by(template_id=template.id)
            .order_by(TemplateAllocation.target_weight.desc())
            .all()
        )
        assert len(template_allocs) == 2, "2 TemplateAllocations must exist"
        assert template_allocs[0].instrument_id == e2e_instruments["BTC"].id
        assert template_allocs[0].target_weight == Decimal("0.7")
        assert template_allocs[1].instrument_id == e2e_instruments["ETH"].id
        assert template_allocs[1].target_weight == Decimal("0.3")

        # ── C. Create subscription ──
        subscription = ProductSubscription(
            id=uuid.uuid4(),
            client_id=eligible_client.id,
            product_id=product_id,
            subscription_currency="USD",
            status="pending",
            metadata_={"rebalance_frequency": "monthly"},
        )
        db.add(subscription)
        db.flush()

        assert subscription.metadata_["rebalance_frequency"] == "monthly"
        assert subscription.portfolio_id is None
        assert subscription.status == "pending"

        # ── D. Provision ──
        portfolio = provisioning_svc.provision_from_subscription(
            db, subscription.id, template.id,
        )

        # ── E. Verify portfolio ──
        assert portfolio is not None, "Portfolio must be created"
        assert portfolio.client_id == eligible_client.id
        assert portfolio.origin_product_id == product_id
        assert portfolio.portfolio_type == "bundle_portfolio"
        assert portfolio.status == "active"
        assert portfolio.base_currency == "USD"

        # ── F. Verify subscription finalized ──
        db.refresh(subscription)
        assert subscription.portfolio_id == portfolio.id
        assert subscription.status == "active"

        # ── G. Verify target allocations copied ──
        target_allocs = (
            db.query(TargetAllocation)
            .filter_by(portfolio_id=portfolio.id)
            .order_by(TargetAllocation.target_weight.desc())
            .all()
        )
        assert len(target_allocs) == 2, "2 TargetAllocations must exist in live portfolio"

        btc_alloc = [a for a in target_allocs if a.instrument_id == e2e_instruments["BTC"].id]
        eth_alloc = [a for a in target_allocs if a.instrument_id == e2e_instruments["ETH"].id]
        assert len(btc_alloc) == 1, "BTC allocation must be present"
        assert len(eth_alloc) == 1, "ETH allocation must be present"
        assert btc_alloc[0].target_weight == Decimal("0.7")
        assert eth_alloc[0].target_weight == Decimal("0.3")

        # ── H. Verify rebalance policy ──
        policy = (
            db.query(RebalancePolicy)
            .filter_by(portfolio_id=portfolio.id)
            .first()
        )
        assert policy is not None, "RebalancePolicy must be created from subscription metadata"
        assert policy.method == "periodic"
        assert policy.frequency == "monthly"
        assert policy.parameters.get("provisioned_from_subscription") == str(subscription.id)

    def test_provisioning_without_rebalance_frequency(
        self,
        db: Session,
        e2e_bundle,
        e2e_instruments: dict[str, Instrument],
        eligible_client: Client,
        provisioning_svc: ProvisioningService,
    ):
        """
        Same flow but WITHOUT rebalance_frequency in subscription metadata.
        Verifies: portfolio + allocations created, NO RebalancePolicy.
        """
        product_id = e2e_bundle.id
        template_id = e2e_bundle.template_id

        template = db.query(PortfolioTemplate).filter_by(id=template_id).first()
        assert template is not None

        # Subscription without rebalance_frequency
        subscription = ProductSubscription(
            id=uuid.uuid4(),
            client_id=eligible_client.id,
            product_id=product_id,
            subscription_currency="USD",
            status="pending",
            metadata_={},
        )
        db.add(subscription)
        db.flush()

        # Provision
        portfolio = provisioning_svc.provision_from_subscription(
            db, subscription.id, template.id,
        )

        # Portfolio created
        assert portfolio is not None
        assert portfolio.client_id == eligible_client.id
        assert portfolio.origin_product_id == product_id
        assert portfolio.status == "active"

        # Subscription finalized
        db.refresh(subscription)
        assert subscription.portfolio_id == portfolio.id
        assert subscription.status == "active"

        # Target allocations copied
        target_allocs = (
            db.query(TargetAllocation)
            .filter_by(portfolio_id=portfolio.id)
            .all()
        )
        assert len(target_allocs) == 2

        btc_alloc = [a for a in target_allocs if a.instrument_id == e2e_instruments["BTC"].id]
        eth_alloc = [a for a in target_allocs if a.instrument_id == e2e_instruments["ETH"].id]
        assert len(btc_alloc) == 1
        assert len(eth_alloc) == 1
        assert btc_alloc[0].target_weight == Decimal("0.7")
        assert eth_alloc[0].target_weight == Decimal("0.3")

        # NO rebalance policy
        policy = (
            db.query(RebalancePolicy)
            .filter_by(portfolio_id=portfolio.id)
            .first()
        )
        assert policy is None, "No RebalancePolicy should be created without rebalance_frequency"
