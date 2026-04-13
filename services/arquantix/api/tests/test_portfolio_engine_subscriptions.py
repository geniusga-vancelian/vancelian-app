"""Tests for Portfolio Engine — Subscriptions module."""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from conftest import make_linked_client
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.products.models import ProductDefinition
from services.portfolio_engine.subscriptions.models import ProductSubscription
from services.portfolio_engine.subscriptions.repository import SubscriptionRepository
from services.portfolio_engine.subscriptions.service import (
    ClientReferenceError,
    PortfolioReferenceError,
    ProductReferenceError,
    SubscriptionNotFoundError,
    SubscriptionService,
)
from services.portfolio_engine.subscriptions.schemas import SubscriptionCreate, SubscriptionUpdate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def client(db: Session) -> Client:
    return make_linked_client(db, email="sub_client@example.com", status="active", kyc_status="approved")


@pytest.fixture
def product(db: Session) -> ProductDefinition:
    p = ProductDefinition(
        id=uuid.uuid4(),
        product_code="SUB_TEST_PROD",
        name="Test Product",
        product_type="crypto_bundle",
        status="active",
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def portfolio(db: Session, client: Client) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=client.id,
        portfolio_type="bundle_portfolio",
        name="Test Portfolio",
        base_currency="EUR",
        status="active",
        metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def subscription(db: Session, client: Client, product: ProductDefinition) -> ProductSubscription:
    s = ProductSubscription(
        id=uuid.uuid4(),
        client_id=client.id,
        product_id=product.id,
        subscription_amount=Decimal("1000.00"),
        subscription_currency="EUR",
        status="active",
        metadata_={},
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def sub_service() -> SubscriptionService:
    return SubscriptionService()


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestSubscriptionRepository:

    def test_create(self, db: Session, client: Client, product: ProductDefinition):
        s = SubscriptionRepository.create(
            db,
            data={
                "client_id": client.id,
                "product_id": product.id,
                "subscription_amount": Decimal("500.00"),
            },
        )
        assert s.id is not None
        assert s.client_id == client.id
        assert s.product_id == product.id
        assert s.status == "pending"
        assert s.subscription_currency == "EUR"
        assert s.portfolio_id is None

    def test_create_with_metadata(self, db: Session, client: Client, product: ProductDefinition):
        s = SubscriptionRepository.create(
            db,
            data={
                "client_id": client.id,
                "product_id": product.id,
                "metadata": {"channel": "mobile"},
            },
        )
        assert s.metadata_ == {"channel": "mobile"}

    def test_get_by_id(self, db: Session, subscription: ProductSubscription):
        found = SubscriptionRepository.get_by_id(db, subscription.id)
        assert found is not None
        assert found.id == subscription.id

    def test_get_by_id_not_found(self, db: Session):
        assert SubscriptionRepository.get_by_id(db, uuid.uuid4()) is None

    def test_list_all(self, db: Session, subscription: ProductSubscription, client: Client, product: ProductDefinition):
        SubscriptionRepository.create(
            db,
            data={"client_id": client.id, "product_id": product.id},
        )
        items, total = SubscriptionRepository.list(db)
        assert total >= 2

    def test_list_filter_by_client(self, db: Session, subscription: ProductSubscription, client: Client):
        items, total = SubscriptionRepository.list(db, client_id=client.id)
        assert total >= 1
        assert all(s.client_id == client.id for s in items)

    def test_list_filter_by_product(self, db: Session, subscription: ProductSubscription, product: ProductDefinition):
        items, total = SubscriptionRepository.list(db, product_id=product.id)
        assert total >= 1
        assert all(s.product_id == product.id for s in items)

    def test_list_filter_by_status(self, db: Session, subscription: ProductSubscription):
        items, total = SubscriptionRepository.list(db, status="active")
        assert total >= 1
        assert all(s.status == "active" for s in items)

    def test_update(self, db: Session, subscription: ProductSubscription):
        SubscriptionRepository.update(db, subscription, data={"status": "cancelled"})
        db.flush()
        refreshed = SubscriptionRepository.get_by_id(db, subscription.id)
        assert refreshed.status == "cancelled"

    def test_update_metadata(self, db: Session, subscription: ProductSubscription):
        SubscriptionRepository.update(db, subscription, data={"metadata": {"reason": "test"}})
        db.flush()
        refreshed = SubscriptionRepository.get_by_id(db, subscription.id)
        assert refreshed.metadata_ == {"reason": "test"}

    def test_update_portfolio_id(self, db: Session, subscription: ProductSubscription, portfolio: Portfolio):
        SubscriptionRepository.update(db, subscription, data={"portfolio_id": portfolio.id})
        db.flush()
        refreshed = SubscriptionRepository.get_by_id(db, subscription.id)
        assert refreshed.portfolio_id == portfolio.id


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestSubscriptionService:

    def test_create_subscription(
        self, db: Session, sub_service: SubscriptionService,
        client: Client, product: ProductDefinition,
    ):
        payload = SubscriptionCreate(
            client_id=client.id,
            product_id=product.id,
            subscription_amount=Decimal("1000.00"),
        )
        s = sub_service.create_subscription(db, payload)
        assert s.client_id == client.id
        assert s.product_id == product.id
        assert s.status == "pending"
        assert s.portfolio_id is None

    def test_create_with_portfolio(
        self, db: Session, sub_service: SubscriptionService,
        client: Client, product: ProductDefinition, portfolio: Portfolio,
    ):
        payload = SubscriptionCreate(
            client_id=client.id,
            product_id=product.id,
            portfolio_id=portfolio.id,
        )
        s = sub_service.create_subscription(db, payload)
        assert s.portfolio_id == portfolio.id

    def test_create_invalid_client(self, db: Session, sub_service: SubscriptionService, product: ProductDefinition):
        payload = SubscriptionCreate(
            client_id=uuid.uuid4(),
            product_id=product.id,
        )
        with pytest.raises(ClientReferenceError):
            sub_service.create_subscription(db, payload)

    def test_create_invalid_product(self, db: Session, sub_service: SubscriptionService, client: Client):
        payload = SubscriptionCreate(
            client_id=client.id,
            product_id=uuid.uuid4(),
        )
        with pytest.raises(ProductReferenceError):
            sub_service.create_subscription(db, payload)

    def test_create_invalid_portfolio(
        self, db: Session, sub_service: SubscriptionService,
        client: Client, product: ProductDefinition,
    ):
        payload = SubscriptionCreate(
            client_id=client.id,
            product_id=product.id,
            portfolio_id=uuid.uuid4(),
        )
        with pytest.raises(PortfolioReferenceError):
            sub_service.create_subscription(db, payload)

    def test_get_subscription(
        self, db: Session, sub_service: SubscriptionService,
        subscription: ProductSubscription,
    ):
        found = sub_service.get_subscription(db, subscription.id)
        assert found.id == subscription.id

    def test_get_subscription_not_found(self, db: Session, sub_service: SubscriptionService):
        with pytest.raises(SubscriptionNotFoundError):
            sub_service.get_subscription(db, uuid.uuid4())

    def test_list_subscriptions(
        self, db: Session, sub_service: SubscriptionService,
        subscription: ProductSubscription,
    ):
        items, total = sub_service.list_subscriptions(db)
        assert total >= 1

    def test_list_filter_by_client(
        self, db: Session, sub_service: SubscriptionService,
        subscription: ProductSubscription, client: Client,
    ):
        items, total = sub_service.list_subscriptions(db, client_id=client.id)
        assert total >= 1

    def test_update_subscription_status(
        self, db: Session, sub_service: SubscriptionService,
        subscription: ProductSubscription,
    ):
        payload = SubscriptionUpdate(status="redeemed")
        updated = sub_service.update_subscription(db, subscription.id, payload)
        assert updated.status == "redeemed"
        assert updated.client_id == subscription.client_id

    def test_update_subscription_partial(
        self, db: Session, sub_service: SubscriptionService,
        subscription: ProductSubscription,
    ):
        payload = SubscriptionUpdate(subscription_amount=Decimal("2000.00"))
        updated = sub_service.update_subscription(db, subscription.id, payload)
        assert updated.subscription_amount == Decimal("2000.00")
        assert updated.status == "active"

    def test_update_attach_portfolio(
        self, db: Session, sub_service: SubscriptionService,
        subscription: ProductSubscription, portfolio: Portfolio,
    ):
        payload = SubscriptionUpdate(portfolio_id=portfolio.id)
        updated = sub_service.update_subscription(db, subscription.id, payload)
        assert updated.portfolio_id == portfolio.id

    def test_update_invalid_portfolio(
        self, db: Session, sub_service: SubscriptionService,
        subscription: ProductSubscription,
    ):
        payload = SubscriptionUpdate(portfolio_id=uuid.uuid4())
        with pytest.raises(PortfolioReferenceError):
            sub_service.update_subscription(db, subscription.id, payload)


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class TestSubscriptionSchemas:

    def test_create_defaults(self):
        payload = SubscriptionCreate(
            client_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
        )
        assert payload.status == "pending"
        assert payload.subscription_currency == "EUR"
        assert payload.portfolio_id is None
        assert payload.subscription_amount is None
        assert payload.metadata == {}

    def test_create_with_overrides(self):
        payload = SubscriptionCreate(
            client_id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            subscription_amount=Decimal("5000"),
            subscription_currency="USD",
            status="active",
        )
        assert payload.status == "active"
        assert payload.subscription_currency == "USD"
        assert payload.subscription_amount == Decimal("5000")

    def test_update_partial(self):
        payload = SubscriptionUpdate(status="cancelled")
        dumped = payload.model_dump(exclude_unset=True)
        assert "status" in dumped
        assert "portfolio_id" not in dumped
        assert "subscription_amount" not in dumped
        assert "metadata" not in dumped
