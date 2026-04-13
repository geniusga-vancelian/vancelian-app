"""Provisioning service — creates a client-owned portfolio from a product subscription
and a portfolio template within a single atomic transaction.

No trade execution, no positions, no wallets, no side effects.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from ..allocations.models import TargetAllocation
from ..clients.models import Client
from ..portfolios.models import Portfolio
from ..products.models import ProductDefinition
from ..rebalancing.models import RebalancePolicy
from ..strategies.models import StrategyDefinition, StrategyInstance
from ..subscriptions.models import ProductSubscription
from ..templates.models import PortfolioTemplate, TemplateAllocation

_VALID_REBALANCE_FREQUENCIES = {"daily", "weekly", "biweekly", "monthly", "quarterly", "annually"}
from .errors import (
    AlreadyProvisionedError,
    ClientNotEligibleError,
    InactiveProductError,
    InvalidSubscriptionStateError,
    ProvisioningSubscriptionNotFoundError,
    ProvisioningTemplateNotFoundError,
    TemplateProductMismatchError,
)


class ProvisioningService:

    def provision_from_subscription(
        self,
        db: Session,
        subscription_id: UUID,
        template_id: UUID,
    ) -> Portfolio:
        """Provision a client-owned portfolio from a pending subscription and a template.

        Returns the newly created Portfolio on success.
        Raises a dedicated exception on any validation failure.
        Commits once on success; rolls back on any exception.
        """
        try:
            subscription = self._load_and_validate_subscription(db, subscription_id)
            client = self._validate_client_eligible(db, subscription.client_id)
            product = self._validate_product_active(db, subscription.product_id)
            template = self._load_and_validate_template(db, template_id, subscription.product_id)

            portfolio = self._create_portfolio(db, subscription, product, template)

            if template.strategy_definition_id is not None:
                self._create_strategy_instance(db, portfolio, template)

            self._copy_allocations(db, portfolio, template)

            self._create_rebalance_policy_from_subscription(db, portfolio, subscription)

            self._finalize_subscription(db, subscription, portfolio)

            db.commit()
            return portfolio
        except Exception:
            db.rollback()
            raise

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_and_validate_subscription(
        db: Session, subscription_id: UUID,
    ) -> ProductSubscription:
        subscription = (
            db.query(ProductSubscription)
            .filter(ProductSubscription.id == subscription_id)
            .first()
        )
        if subscription is None:
            raise ProvisioningSubscriptionNotFoundError(subscription_id)
        if subscription.status != "pending":
            raise InvalidSubscriptionStateError(subscription_id, subscription.status)
        if subscription.portfolio_id is not None:
            raise AlreadyProvisionedError(subscription_id, subscription.portfolio_id)
        return subscription

    @staticmethod
    def _validate_client_eligible(db: Session, client_id: UUID) -> Client:
        client = db.query(Client).filter(Client.id == client_id).first()
        if client is None:
            raise ClientNotEligibleError(client_id, "client not found")
        if client.status != "active":
            raise ClientNotEligibleError(client_id, f"status is '{client.status}', expected 'active'")

        # Use centralized EligibilityService when person is linked
        if client.person_id is not None:
            from database import Person
            person = db.query(Person).filter(Person.id == client.person_id).first()
            if person is not None:
                from services.compliance.eligibility_service import EligibilityService
                result = EligibilityService.evaluate_client_eligibility(db, person, client)
                if not result.eligible:
                    raise ClientNotEligibleError(client_id, "; ".join(result.reasons))
                return client

        # Fallback: use client-level KYC (backward-compatible for unlinked clients)
        if client.kyc_status != "approved":
            raise ClientNotEligibleError(client_id, f"kyc_status is '{client.kyc_status}', expected 'approved'")
        return client

    @staticmethod
    def _validate_product_active(db: Session, product_id: UUID) -> ProductDefinition:
        product = (
            db.query(ProductDefinition)
            .filter(ProductDefinition.id == product_id)
            .first()
        )
        if product is None:
            raise InactiveProductError(product_id, "not found")
        if product.status != "active":
            raise InactiveProductError(product_id, product.status)
        return product

    @staticmethod
    def _load_and_validate_template(
        db: Session, template_id: UUID, expected_product_id: UUID,
    ) -> PortfolioTemplate:
        template = (
            db.query(PortfolioTemplate)
            .filter(PortfolioTemplate.id == template_id)
            .first()
        )
        if template is None:
            raise ProvisioningTemplateNotFoundError(template_id)
        if template.product_id != expected_product_id:
            raise TemplateProductMismatchError(template_id, template.product_id, expected_product_id)
        return template

    # ------------------------------------------------------------------
    # Creation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _create_portfolio(
        db: Session,
        subscription: ProductSubscription,
        product: ProductDefinition,
        template: PortfolioTemplate,
    ) -> Portfolio:
        portfolio = Portfolio(
            client_id=subscription.client_id,
            origin_product_id=subscription.product_id,
            portfolio_type=template.provisioned_portfolio_type,
            name=product.name,
            base_currency=template.base_currency,
            risk_profile=template.risk_profile,
            status="active",
            metadata_={
                "provisioned_from_template": str(template.id),
                "provisioned_from_subscription": str(subscription.id),
            },
        )
        db.add(portfolio)
        db.flush()
        return portfolio

    @staticmethod
    def _create_strategy_instance(
        db: Session,
        portfolio: Portfolio,
        template: PortfolioTemplate,
    ) -> StrategyInstance:
        instance = StrategyInstance(
            portfolio_id=portfolio.id,
            sleeve_id=None,
            strategy_definition_id=template.strategy_definition_id,
            name=f"Strategy for {portfolio.name}",
            status="active",
            parameters={},
            metadata_={},
        )
        db.add(instance)
        db.flush()
        return instance

    @staticmethod
    def _copy_allocations(
        db: Session,
        portfolio: Portfolio,
        template: PortfolioTemplate,
    ) -> list[TargetAllocation]:
        template_allocations = (
            db.query(TemplateAllocation)
            .filter(TemplateAllocation.template_id == template.id)
            .all()
        )
        created: list[TargetAllocation] = []
        for ta in template_allocations:
            alloc = TargetAllocation(
                portfolio_id=portfolio.id,
                sleeve_id=None,
                instrument_id=ta.instrument_id,
                target_weight=ta.target_weight,
                min_weight=ta.min_weight,
                max_weight=ta.max_weight,
                rebalance_priority=ta.allocation_priority,
            )
            db.add(alloc)
            created.append(alloc)
        if created:
            db.flush()
        return created

    @staticmethod
    def _create_rebalance_policy_from_subscription(
        db: Session,
        portfolio: Portfolio,
        subscription: ProductSubscription,
    ) -> RebalancePolicy | None:
        meta = subscription.metadata_ or {}
        frequency = meta.get("rebalance_frequency")
        if frequency is None:
            return None
        if frequency not in _VALID_REBALANCE_FREQUENCIES:
            return None
        policy = RebalancePolicy(
            portfolio_id=portfolio.id,
            method="periodic",
            frequency=frequency,
            drift_threshold=None,
            parameters={
                "provisioned_from_subscription": str(subscription.id),
            },
        )
        db.add(policy)
        db.flush()
        return policy

    @staticmethod
    def _finalize_subscription(
        db: Session,
        subscription: ProductSubscription,
        portfolio: Portfolio,
    ) -> None:
        subscription.portfolio_id = portfolio.id
        subscription.status = "active"
        db.flush()
