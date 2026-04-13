"""Tests for Portfolio Engine — Risk Policies + Rebalance Preview modules."""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.sleeves.models import Sleeve
from services.portfolio_engine.rebalancing.models import RebalancePolicy

from services.portfolio_engine.risk.models import RiskPolicy
from services.portfolio_engine.risk.repository import DuplicateRiskPolicyError, RiskPolicyRepository
from services.portfolio_engine.risk.service import (
    PortfolioReferenceError as RiskPortfolioRefError,
    RiskPolicyNotFoundError,
    RiskPolicyService,
    SleeveReferenceError as RiskSleeveRefError,
)
from services.portfolio_engine.risk.schemas import RiskPolicyCreate, RiskPolicyUpdate

from services.portfolio_engine.rebalance_preview.models import RebalancePreview, RebalancePreviewItem
from services.portfolio_engine.rebalance_preview.repository import RebalancePreviewRepository
from services.portfolio_engine.rebalance_preview.service import (
    InstrumentReferenceError,
    PolicyReferenceError,
    PortfolioReferenceError as PrevPortfolioRefError,
    PreviewNotFoundError,
    RebalancePreviewService,
)
from services.portfolio_engine.rebalance_preview.schemas import PreviewCreate, PreviewItemCreate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CLIENT_ID = uuid.uuid4()


@pytest.fixture
def asset_btc(db: Session) -> Asset:
    a = Asset(id=uuid.uuid4(), symbol="BTC_RP", name="Bitcoin", asset_type="cryptocurrency", metadata_={})
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def instrument_btc(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(id=uuid.uuid4(), asset_id=asset_btc.id, code="BTC_SPOT_RP", name="BTC Spot", instrument_type="spot", metadata_={})
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def instrument_eth(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(id=uuid.uuid4(), asset_id=asset_btc.id, code="ETH_SPOT_RP", name="ETH Spot", instrument_type="spot", metadata_={})
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def portfolio(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(), client_id=_CLIENT_ID, portfolio_type="bundle_portfolio",
        name="Test Portfolio RP", base_currency="EUR", status="active", metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def sleeve_core(db: Session, portfolio: Portfolio) -> Sleeve:
    s = Sleeve(
        id=uuid.uuid4(), portfolio_id=portfolio.id, name="Core",
        sleeve_type="core", allocation_target=Decimal("0.6"), metadata_={},
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def rebalance_policy(db: Session, portfolio: Portfolio) -> RebalancePolicy:
    rp = RebalancePolicy(
        id=uuid.uuid4(), portfolio_id=portfolio.id, method="periodic",
        frequency="monthly", parameters={},
    )
    db.add(rp)
    db.flush()
    return rp


@pytest.fixture
def risk_service() -> RiskPolicyService:
    return RiskPolicyService()


@pytest.fixture
def preview_service() -> RebalancePreviewService:
    return RebalancePreviewService()


# ===========================================================================
# RiskPolicy — Repository tests
# ===========================================================================

class TestRiskPolicyRepository:

    def test_create_portfolio_scope(self, db: Session, portfolio: Portfolio):
        policy = RiskPolicyRepository.create(
            db, data={"portfolio_id": portfolio.id, "max_asset_weight": Decimal("0.3"), "parameters": {}},
        )
        assert policy.id is not None
        assert policy.portfolio_id == portfolio.id
        assert policy.sleeve_id is None

    def test_create_sleeve_scope(self, db: Session, sleeve_core: Sleeve):
        policy = RiskPolicyRepository.create(
            db, data={"sleeve_id": sleeve_core.id, "max_leverage": Decimal("2.0"), "parameters": {}},
        )
        assert policy.sleeve_id == sleeve_core.id

    def test_get_by_id(self, db: Session, portfolio: Portfolio):
        policy = RiskPolicyRepository.create(db, data={"portfolio_id": portfolio.id, "parameters": {}})
        found = RiskPolicyRepository.get_by_id(db, policy.id)
        assert found is not None
        assert found.id == policy.id

    def test_get_by_id_not_found(self, db: Session):
        assert RiskPolicyRepository.get_by_id(db, uuid.uuid4()) is None

    def test_get_by_portfolio(self, db: Session, portfolio: Portfolio):
        RiskPolicyRepository.create(db, data={"portfolio_id": portfolio.id, "parameters": {}})
        found = RiskPolicyRepository.get_by_portfolio(db, portfolio.id)
        assert found is not None
        assert found.portfolio_id == portfolio.id

    def test_update(self, db: Session, portfolio: Portfolio):
        policy = RiskPolicyRepository.create(db, data={"portfolio_id": portfolio.id, "max_drawdown": Decimal("0.1"), "parameters": {}})
        RiskPolicyRepository.update(db, policy, data={"max_drawdown": Decimal("0.2"), "volatility_limit": Decimal("0.15")})
        db.flush()
        refreshed = RiskPolicyRepository.get_by_id(db, policy.id)
        assert refreshed.max_drawdown == Decimal("0.2")
        assert refreshed.volatility_limit == Decimal("0.15")

    def test_duplicate_portfolio_raises(self, db: Session, portfolio: Portfolio):
        RiskPolicyRepository.create(db, data={"portfolio_id": portfolio.id, "parameters": {}})
        with pytest.raises(DuplicateRiskPolicyError):
            RiskPolicyRepository.create(db, data={"portfolio_id": portfolio.id, "parameters": {}})

    def test_duplicate_sleeve_raises(self, db: Session, sleeve_core: Sleeve):
        RiskPolicyRepository.create(db, data={"sleeve_id": sleeve_core.id, "parameters": {}})
        with pytest.raises(DuplicateRiskPolicyError):
            RiskPolicyRepository.create(db, data={"sleeve_id": sleeve_core.id, "parameters": {}})


# ===========================================================================
# RiskPolicy — Service tests
# ===========================================================================

class TestRiskPolicyService:

    def test_create_policy(self, db: Session, risk_service: RiskPolicyService, portfolio: Portfolio):
        payload = RiskPolicyCreate(portfolio_id=portfolio.id, max_asset_weight=Decimal("0.25"))
        policy = risk_service.create_policy(db, payload)
        assert policy.portfolio_id == portfolio.id
        assert policy.max_asset_weight == Decimal("0.25")

    def test_create_policy_invalid_portfolio(self, db: Session, risk_service: RiskPolicyService):
        payload = RiskPolicyCreate(portfolio_id=uuid.uuid4())
        with pytest.raises(RiskPortfolioRefError):
            risk_service.create_policy(db, payload)

    def test_create_policy_invalid_sleeve(self, db: Session, risk_service: RiskPolicyService):
        payload = RiskPolicyCreate(sleeve_id=uuid.uuid4())
        with pytest.raises(RiskSleeveRefError):
            risk_service.create_policy(db, payload)

    def test_get_policy(self, db: Session, risk_service: RiskPolicyService, portfolio: Portfolio):
        created = risk_service.create_policy(db, RiskPolicyCreate(portfolio_id=portfolio.id))
        found = risk_service.get_policy(db, created.id)
        assert found.id == created.id

    def test_get_policy_not_found(self, db: Session, risk_service: RiskPolicyService):
        with pytest.raises(RiskPolicyNotFoundError):
            risk_service.get_policy(db, uuid.uuid4())

    def test_get_policy_by_portfolio(self, db: Session, risk_service: RiskPolicyService, portfolio: Portfolio):
        risk_service.create_policy(db, RiskPolicyCreate(portfolio_id=portfolio.id))
        found = risk_service.get_policy_by_portfolio(db, portfolio.id)
        assert found is not None

    def test_update_policy_partial(self, db: Session, risk_service: RiskPolicyService, portfolio: Portfolio):
        created = risk_service.create_policy(db, RiskPolicyCreate(portfolio_id=portfolio.id, max_drawdown=Decimal("0.1")))
        updated = risk_service.update_policy(db, created.id, RiskPolicyUpdate(max_drawdown=Decimal("0.2")))
        assert updated.max_drawdown == Decimal("0.2")
        assert updated.max_asset_weight is None

    def test_update_policy_not_found(self, db: Session, risk_service: RiskPolicyService):
        with pytest.raises(RiskPolicyNotFoundError):
            risk_service.update_policy(db, uuid.uuid4(), RiskPolicyUpdate(max_drawdown=Decimal("0.1")))


# ===========================================================================
# RiskPolicy — Schema validation tests
# ===========================================================================

class TestRiskPolicySchemaValidation:

    def test_xor_both_none_raises(self):
        with pytest.raises(ValueError, match="Exactly one"):
            RiskPolicyCreate()

    def test_xor_both_set_raises(self):
        with pytest.raises(ValueError, match="Exactly one"):
            RiskPolicyCreate(portfolio_id=uuid.uuid4(), sleeve_id=uuid.uuid4())

    def test_valid_portfolio_scope(self):
        payload = RiskPolicyCreate(portfolio_id=uuid.uuid4(), max_asset_weight=Decimal("0.3"))
        assert payload.max_asset_weight == Decimal("0.3")


# ===========================================================================
# RebalancePreview — Repository tests
# ===========================================================================

class TestRebalancePreviewRepository:

    def test_create_without_items(self, db: Session, portfolio: Portfolio):
        preview = RebalancePreviewRepository.create(
            db,
            data={"portfolio_id": portfolio.id, "status": "completed", "parameters": {}},
            items_data=[],
        )
        assert preview.id is not None
        assert preview.portfolio_id == portfolio.id

    def test_create_with_items(self, db: Session, portfolio: Portfolio, instrument_btc: Instrument, instrument_eth: Instrument):
        preview = RebalancePreviewRepository.create(
            db,
            data={
                "portfolio_id": portfolio.id,
                "drift_score": Decimal("0.05"),
                "total_turnover": Decimal("0.10"),
                "status": "completed",
                "parameters": {},
            },
            items_data=[
                {
                    "instrument_id": instrument_btc.id,
                    "current_weight": Decimal("0.65"),
                    "target_weight": Decimal("0.60"),
                    "drift": Decimal("0.05"),
                    "trade_direction": "sell",
                    "trade_required": Decimal("500"),
                    "estimated_trade_size": Decimal("500"),
                },
                {
                    "instrument_id": instrument_eth.id,
                    "current_weight": Decimal("0.35"),
                    "target_weight": Decimal("0.40"),
                    "drift": Decimal("-0.05"),
                    "trade_direction": "buy",
                    "trade_required": Decimal("500"),
                    "estimated_trade_size": Decimal("500"),
                },
            ],
        )
        assert len(preview.items) == 2

    def test_get_by_id(self, db: Session, portfolio: Portfolio):
        preview = RebalancePreviewRepository.create(
            db, data={"portfolio_id": portfolio.id, "status": "pending", "parameters": {}}, items_data=[],
        )
        found = RebalancePreviewRepository.get_by_id(db, preview.id)
        assert found is not None
        assert found.id == preview.id

    def test_get_by_id_not_found(self, db: Session):
        assert RebalancePreviewRepository.get_by_id(db, uuid.uuid4()) is None

    def test_get_latest_by_portfolio(self, db: Session, portfolio: Portfolio):
        RebalancePreviewRepository.create(
            db, data={"portfolio_id": portfolio.id, "status": "completed", "parameters": {}}, items_data=[],
        )
        p2 = RebalancePreviewRepository.create(
            db, data={"portfolio_id": portfolio.id, "status": "completed", "parameters": {}}, items_data=[],
        )
        latest = RebalancePreviewRepository.get_latest_by_portfolio(db, portfolio.id)
        assert latest is not None
        assert latest.id == p2.id

    def test_list_by_portfolio(self, db: Session, portfolio: Portfolio):
        RebalancePreviewRepository.create(
            db, data={"portfolio_id": portfolio.id, "status": "completed", "parameters": {}}, items_data=[],
        )
        RebalancePreviewRepository.create(
            db, data={"portfolio_id": portfolio.id, "status": "completed", "parameters": {}}, items_data=[],
        )
        items, total = RebalancePreviewRepository.list_by_portfolio(db, portfolio.id)
        assert total == 2


# ===========================================================================
# RebalancePreview — Service tests
# ===========================================================================

class TestRebalancePreviewService:

    def test_create_preview(self, db: Session, preview_service: RebalancePreviewService, portfolio: Portfolio, instrument_btc: Instrument):
        payload = PreviewCreate(
            portfolio_id=portfolio.id,
            status="completed",
            drift_score=Decimal("0.03"),
            items=[
                PreviewItemCreate(instrument_id=instrument_btc.id, current_weight=Decimal("0.6"), target_weight=Decimal("0.6"), drift=Decimal("0"), trade_direction="hold"),
            ],
        )
        preview = preview_service.create_preview(db, payload)
        assert preview.portfolio_id == portfolio.id
        assert len(preview.items) == 1

    def test_create_preview_with_policy(
        self, db: Session, preview_service: RebalancePreviewService,
        portfolio: Portfolio, rebalance_policy: RebalancePolicy,
    ):
        payload = PreviewCreate(
            portfolio_id=portfolio.id,
            rebalance_policy_id=rebalance_policy.id,
            status="completed",
        )
        preview = preview_service.create_preview(db, payload)
        assert preview.rebalance_policy_id == rebalance_policy.id

    def test_create_preview_invalid_portfolio(self, db: Session, preview_service: RebalancePreviewService):
        payload = PreviewCreate(portfolio_id=uuid.uuid4(), status="pending")
        with pytest.raises(PrevPortfolioRefError):
            preview_service.create_preview(db, payload)

    def test_create_preview_invalid_policy(self, db: Session, preview_service: RebalancePreviewService, portfolio: Portfolio):
        payload = PreviewCreate(portfolio_id=portfolio.id, rebalance_policy_id=uuid.uuid4(), status="pending")
        with pytest.raises(PolicyReferenceError):
            preview_service.create_preview(db, payload)

    def test_create_preview_invalid_instrument(self, db: Session, preview_service: RebalancePreviewService, portfolio: Portfolio):
        payload = PreviewCreate(
            portfolio_id=portfolio.id,
            status="pending",
            items=[PreviewItemCreate(instrument_id=uuid.uuid4())],
        )
        with pytest.raises(InstrumentReferenceError):
            preview_service.create_preview(db, payload)

    def test_get_preview(self, db: Session, preview_service: RebalancePreviewService, portfolio: Portfolio):
        created = preview_service.create_preview(db, PreviewCreate(portfolio_id=portfolio.id, status="completed"))
        found = preview_service.get_preview(db, created.id)
        assert found.id == created.id

    def test_get_preview_not_found(self, db: Session, preview_service: RebalancePreviewService):
        with pytest.raises(PreviewNotFoundError):
            preview_service.get_preview(db, uuid.uuid4())

    def test_get_latest_by_portfolio(self, db: Session, preview_service: RebalancePreviewService, portfolio: Portfolio):
        preview_service.create_preview(db, PreviewCreate(portfolio_id=portfolio.id, status="completed"))
        p2 = preview_service.create_preview(db, PreviewCreate(portfolio_id=portfolio.id, status="completed"))
        latest = preview_service.get_latest_by_portfolio(db, portfolio.id)
        assert latest is not None
        assert latest.id == p2.id

    def test_get_latest_returns_none(self, db: Session, preview_service: RebalancePreviewService, portfolio: Portfolio):
        latest = preview_service.get_latest_by_portfolio(db, portfolio.id)
        assert latest is None
