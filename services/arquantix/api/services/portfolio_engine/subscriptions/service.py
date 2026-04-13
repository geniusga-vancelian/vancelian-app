"""Service layer for Subscriptions module
(Portfolio Engine — product subscription layer)."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..clients.models import Client
from ..portfolios.models import Portfolio
from ..products.models import ProductDefinition
from .models import ProductSubscription
from .repository import SubscriptionRepository
from .schemas import SubscriptionCreate, SubscriptionUpdate


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class SubscriptionNotFoundError(Exception):
    def __init__(self, subscription_id: UUID):
        self.subscription_id = subscription_id
        super().__init__(f"ProductSubscription {subscription_id} not found")


class ClientReferenceError(Exception):
    def __init__(self, client_id: UUID):
        self.client_id = client_id
        super().__init__(f"Referenced client {client_id} does not exist")


class ProductReferenceError(Exception):
    def __init__(self, product_id: UUID):
        self.product_id = product_id
        super().__init__(f"Referenced product {product_id} does not exist")


class PortfolioReferenceError(Exception):
    def __init__(self, portfolio_id: UUID):
        self.portfolio_id = portfolio_id
        super().__init__(f"Referenced portfolio {portfolio_id} does not exist")


class ProductNotAvailableError(Exception):
    """Product exists but is not publicly available for subscription."""
    def __init__(self, product_id: UUID, reason: str):
        self.product_id = product_id
        super().__init__(
            f"Product {product_id} is not available for subscription: {reason}"
        )


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

def _validate_client_exists(db: Session, client_id: UUID) -> None:
    if db.query(Client).filter(Client.id == client_id).first() is None:
        raise ClientReferenceError(client_id)


def _validate_product_available(db: Session, product_id: UUID) -> None:
    product = db.query(ProductDefinition).filter(ProductDefinition.id == product_id).first()
    if product is None:
        raise ProductReferenceError(product_id)
    if product.status != "active":
        raise ProductNotAvailableError(product_id, f"status is '{product.status}', expected 'active'")
    if not product.is_public:
        raise ProductNotAvailableError(product_id, "product is not published")


def _validate_portfolio_exists(db: Session, portfolio_id: UUID) -> None:
    if db.query(Portfolio).filter(Portfolio.id == portfolio_id).first() is None:
        raise PortfolioReferenceError(portfolio_id)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

class SubscriptionService:

    def __init__(self) -> None:
        self._repo = SubscriptionRepository()

    def create_subscription(self, db: Session, payload: SubscriptionCreate) -> ProductSubscription:
        _validate_client_exists(db, payload.client_id)
        _validate_product_available(db, payload.product_id)
        if payload.portfolio_id is not None:
            _validate_portfolio_exists(db, payload.portfolio_id)
        data = payload.model_dump()
        return self._repo.create(db, data=data)

    def get_subscription(self, db: Session, subscription_id: UUID) -> ProductSubscription:
        subscription = self._repo.get_by_id(db, subscription_id)
        if subscription is None:
            raise SubscriptionNotFoundError(subscription_id)
        return subscription

    def list_subscriptions(
        self,
        db: Session,
        *,
        client_id: Optional[UUID] = None,
        product_id: Optional[UUID] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple:
        return self._repo.list(
            db,
            client_id=client_id,
            product_id=product_id,
            status=status,
            skip=skip,
            limit=limit,
        )

    def update_subscription(
        self, db: Session, subscription_id: UUID, payload: SubscriptionUpdate,
    ) -> ProductSubscription:
        subscription = self.get_subscription(db, subscription_id)
        data = payload.model_dump(exclude_unset=True)
        if "portfolio_id" in data and data["portfolio_id"] is not None:
            _validate_portfolio_exists(db, data["portfolio_id"])
        return self._repo.update(db, subscription, data=data)
