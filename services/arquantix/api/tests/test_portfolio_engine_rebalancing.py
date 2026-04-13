"""Tests for Portfolio Engine — Rebalance Policies module."""
import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.sleeves.models import Sleeve
from services.portfolio_engine.rebalancing.models import RebalancePolicy
from services.portfolio_engine.rebalancing.repository import RebalancePolicyRepository
from services.portfolio_engine.rebalancing.service import (
    PolicyNotFoundError,
    PortfolioReferenceError,
    RebalancePolicyService,
    SleeveReferenceError,
)
from services.portfolio_engine.rebalancing.schemas import RebalancePolicyCreate, RebalancePolicyUpdate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CLIENT_ID = uuid.uuid4()


@pytest.fixture
def portfolio(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(), client_id=_CLIENT_ID, portfolio_type="bundle_portfolio",
        name="Test", base_currency="EUR", status="active", metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def sleeve(db: Session, portfolio: Portfolio) -> Sleeve:
    s = Sleeve(
        id=uuid.uuid4(), portfolio_id=portfolio.id, name="Core",
        sleeve_type="core", metadata_={},
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def policy_basic(db: Session, portfolio: Portfolio) -> RebalancePolicy:
    p = RebalancePolicy(
        id=uuid.uuid4(), portfolio_id=portfolio.id, method="drift_threshold",
        frequency="monthly", drift_threshold=Decimal("0.050000"),
        min_trade_size=Decimal("10.0"), lockup_aware=True,
        cash_flow_priority=True, parameters={},
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def policy_service() -> RebalancePolicyService:
    return RebalancePolicyService()


# ---------------------------------------------------------------------------
# Schema validation tests
# ---------------------------------------------------------------------------

class TestRebalancePolicySchemaValidation:

    def test_xor_both_none_rejected(self):
        with pytest.raises(ValidationError, match="Exactly one"):
            RebalancePolicyCreate(method="drift_threshold")

    def test_xor_both_set_rejected(self):
        with pytest.raises(ValidationError, match="Exactly one"):
            RebalancePolicyCreate(
                portfolio_id=uuid.uuid4(), sleeve_id=uuid.uuid4(), method="drift_threshold",
            )

    def test_valid_portfolio_context(self):
        payload = RebalancePolicyCreate(portfolio_id=uuid.uuid4(), method="calendar", frequency="monthly")
        assert payload.portfolio_id is not None
        assert payload.sleeve_id is None

    def test_valid_sleeve_context(self):
        payload = RebalancePolicyCreate(sleeve_id=uuid.uuid4(), method="manual")
        assert payload.sleeve_id is not None


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestRebalancePolicyRepository:

    def test_create(self, db: Session, portfolio: Portfolio):
        p = RebalancePolicyRepository.create(
            db, data={
                "portfolio_id": portfolio.id, "method": "calendar",
                "frequency": "quarterly", "parameters": {},
            },
        )
        assert p.id is not None
        assert p.method == "calendar"
        assert p.lockup_aware is True

    def test_get_by_id(self, db: Session, policy_basic: RebalancePolicy):
        found = RebalancePolicyRepository.get_by_id(db, policy_basic.id)
        assert found is not None

    def test_get_by_portfolio(self, db: Session, policy_basic: RebalancePolicy, portfolio: Portfolio):
        found = RebalancePolicyRepository.get_by_portfolio(db, portfolio.id)
        assert found is not None
        assert found.id == policy_basic.id

    def test_get_by_portfolio_none(self, db: Session):
        found = RebalancePolicyRepository.get_by_portfolio(db, uuid.uuid4())
        assert found is None

    def test_list(self, db: Session, policy_basic: RebalancePolicy):
        items, total = RebalancePolicyRepository.list(db)
        assert total >= 1

    def test_update(self, db: Session, policy_basic: RebalancePolicy):
        RebalancePolicyRepository.update(db, policy_basic, data={"method": "hybrid", "frequency": "weekly"})
        db.flush()
        refreshed = RebalancePolicyRepository.get_by_id(db, policy_basic.id)
        assert refreshed.method == "hybrid"
        assert refreshed.frequency == "weekly"


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestRebalancePolicyService:

    def test_create_portfolio_context(self, db: Session, policy_service: RebalancePolicyService, portfolio: Portfolio):
        payload = RebalancePolicyCreate(portfolio_id=portfolio.id, method="drift_threshold", drift_threshold=Decimal("0.05"))
        p = policy_service.create_policy(db, payload)
        assert p.portfolio_id == portfolio.id

    def test_create_sleeve_context(self, db: Session, policy_service: RebalancePolicyService, sleeve: Sleeve):
        payload = RebalancePolicyCreate(sleeve_id=sleeve.id, method="calendar", frequency="monthly")
        p = policy_service.create_policy(db, payload)
        assert p.sleeve_id == sleeve.id

    def test_create_invalid_portfolio(self, db: Session, policy_service: RebalancePolicyService):
        payload = RebalancePolicyCreate(portfolio_id=uuid.uuid4(), method="manual")
        with pytest.raises(PortfolioReferenceError):
            policy_service.create_policy(db, payload)

    def test_create_invalid_sleeve(self, db: Session, policy_service: RebalancePolicyService):
        payload = RebalancePolicyCreate(sleeve_id=uuid.uuid4(), method="manual")
        with pytest.raises(SleeveReferenceError):
            policy_service.create_policy(db, payload)

    def test_get_policy(self, db: Session, policy_service: RebalancePolicyService, policy_basic: RebalancePolicy):
        found = policy_service.get_policy(db, policy_basic.id)
        assert found.id == policy_basic.id

    def test_get_policy_not_found(self, db: Session, policy_service: RebalancePolicyService):
        with pytest.raises(PolicyNotFoundError):
            policy_service.get_policy(db, uuid.uuid4())

    def test_get_policy_for_portfolio(self, db: Session, policy_service: RebalancePolicyService, policy_basic: RebalancePolicy, portfolio: Portfolio):
        found = policy_service.get_policy_for_portfolio(db, portfolio.id)
        assert found is not None
        assert found.id == policy_basic.id

    def test_get_policy_for_portfolio_none(self, db: Session, policy_service: RebalancePolicyService):
        found = policy_service.get_policy_for_portfolio(db, uuid.uuid4())
        assert found is None

    def test_update_policy(self, db: Session, policy_service: RebalancePolicyService, policy_basic: RebalancePolicy):
        payload = RebalancePolicyUpdate(method="hybrid", lockup_aware=False)
        updated = policy_service.update_policy(db, policy_basic.id, payload)
        assert updated.method == "hybrid"
        assert updated.lockup_aware is False

    def test_update_policy_partial(self, db: Session, policy_service: RebalancePolicyService, policy_basic: RebalancePolicy):
        payload = RebalancePolicyUpdate(drift_threshold=Decimal("0.10"))
        updated = policy_service.update_policy(db, policy_basic.id, payload)
        assert updated.drift_threshold == Decimal("0.10")
        assert updated.method == "drift_threshold"
