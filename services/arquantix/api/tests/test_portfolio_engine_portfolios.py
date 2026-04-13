"""Tests for Portfolio Engine — Portfolios + Sleeves modules."""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.products.models import ProductDefinition
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.portfolios.repository import PortfolioRepository
from services.portfolio_engine.portfolios.service import (
    OriginProductReferenceError,
    PortfolioNotFoundError,
    PortfolioService,
)
from services.portfolio_engine.portfolios.schemas import PortfolioCreate, PortfolioUpdate

from services.portfolio_engine.sleeves.models import Sleeve
from services.portfolio_engine.sleeves.repository import SleeveRepository
from services.portfolio_engine.sleeves.service import (
    PortfolioReferenceError,
    SleeveNotFoundError,
    SleeveService,
)
from services.portfolio_engine.sleeves.schemas import SleeveCreate, SleeveUpdate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CLIENT_ID = uuid.uuid4()


@pytest.fixture
def product(db: Session) -> ProductDefinition:
    p = ProductDefinition(
        id=uuid.uuid4(),
        product_code="PF_TEST_PROD",
        name="Test Product",
        product_type="crypto_bundle",
        status="active",
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def portfolio_basic(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=_CLIENT_ID,
        portfolio_type="bundle_portfolio",
        name="Balanced Crypto",
        base_currency="EUR",
        status="active",
        metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def sleeve_core(db: Session, portfolio_basic: Portfolio) -> Sleeve:
    s = Sleeve(
        id=uuid.uuid4(),
        portfolio_id=portfolio_basic.id,
        name="Core",
        sleeve_type="core",
        allocation_target=Decimal("0.600000"),
        metadata_={},
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def portfolio_service() -> PortfolioService:
    return PortfolioService()


@pytest.fixture
def sleeve_service() -> SleeveService:
    return SleeveService()


# ---------------------------------------------------------------------------
# Portfolio Repository tests
# ---------------------------------------------------------------------------

class TestPortfolioRepository:

    def test_create(self, db: Session):
        pf = PortfolioRepository.create(
            db,
            data={
                "client_id": _CLIENT_ID,
                "portfolio_type": "single_asset_wallet",
                "name": "BTC Wallet",
                "metadata_": {},
            },
        )
        assert pf.id is not None
        assert pf.name == "BTC Wallet"
        assert pf.status == "active"
        assert pf.base_currency == "EUR"

    def test_get_by_id(self, db: Session, portfolio_basic: Portfolio):
        found = PortfolioRepository.get_by_id(db, portfolio_basic.id)
        assert found is not None
        assert found.name == "Balanced Crypto"

    def test_get_by_id_not_found(self, db: Session):
        assert PortfolioRepository.get_by_id(db, uuid.uuid4()) is None

    def test_list(self, db: Session, portfolio_basic: Portfolio):
        PortfolioRepository.create(
            db,
            data={
                "client_id": _CLIENT_ID,
                "portfolio_type": "yield_portfolio",
                "name": "Yield Portfolio",
                "metadata_": {},
            },
        )
        items, total = PortfolioRepository.list(db)
        assert total >= 2

    def test_list_filter_by_client(self, db: Session, portfolio_basic: Portfolio):
        other_client = uuid.uuid4()
        PortfolioRepository.create(
            db,
            data={
                "client_id": other_client,
                "portfolio_type": "managed_portfolio",
                "name": "Other",
                "metadata_": {},
            },
        )
        items, total = PortfolioRepository.list(db, client_id=_CLIENT_ID)
        assert all(p.client_id == _CLIENT_ID for p in items)

    def test_list_filter_by_type(self, db: Session, portfolio_basic: Portfolio):
        items, total = PortfolioRepository.list(db, portfolio_type="bundle_portfolio")
        assert total >= 1
        assert all(p.portfolio_type == "bundle_portfolio" for p in items)

    def test_update(self, db: Session, portfolio_basic: Portfolio):
        PortfolioRepository.update(db, portfolio_basic, data={"name": "Updated Name", "status": "paused"})
        db.flush()
        refreshed = PortfolioRepository.get_by_id(db, portfolio_basic.id)
        assert refreshed.name == "Updated Name"
        assert refreshed.status == "paused"


# ---------------------------------------------------------------------------
# Portfolio Service tests
# ---------------------------------------------------------------------------

class TestPortfolioService:

    def test_create_portfolio(self, db: Session, portfolio_service: PortfolioService):
        payload = PortfolioCreate(
            client_id=_CLIENT_ID,
            portfolio_type="yield_portfolio",
            name="My Yield",
        )
        pf = portfolio_service.create_portfolio(db, payload)
        assert pf.name == "My Yield"
        assert pf.client_id == _CLIENT_ID

    def test_get_portfolio(self, db: Session, portfolio_service: PortfolioService, portfolio_basic: Portfolio):
        found = portfolio_service.get_portfolio(db, portfolio_basic.id)
        assert found.id == portfolio_basic.id

    def test_get_portfolio_not_found(self, db: Session, portfolio_service: PortfolioService):
        with pytest.raises(PortfolioNotFoundError):
            portfolio_service.get_portfolio(db, uuid.uuid4())

    def test_list_portfolios(self, db: Session, portfolio_service: PortfolioService, portfolio_basic: Portfolio):
        items, total = portfolio_service.list_portfolios(db)
        assert total >= 1

    def test_update_portfolio(self, db: Session, portfolio_service: PortfolioService, portfolio_basic: Portfolio):
        payload = PortfolioUpdate(name="Renamed")
        updated = portfolio_service.update_portfolio(db, portfolio_basic.id, payload)
        assert updated.name == "Renamed"
        assert updated.portfolio_type == "bundle_portfolio"

    def test_update_portfolio_partial(self, db: Session, portfolio_service: PortfolioService, portfolio_basic: Portfolio):
        payload = PortfolioUpdate(status="closed")
        updated = portfolio_service.update_portfolio(db, portfolio_basic.id, payload)
        assert updated.status == "closed"
        assert updated.name == "Balanced Crypto"

    def test_create_with_origin_product(
        self, db: Session, portfolio_service: PortfolioService, product: ProductDefinition,
    ):
        payload = PortfolioCreate(
            client_id=_CLIENT_ID,
            portfolio_type="bundle_portfolio",
            name="From Product",
            origin_product_id=product.id,
        )
        pf = portfolio_service.create_portfolio(db, payload)
        assert pf.origin_product_id == product.id

    def test_create_without_origin_product(self, db: Session, portfolio_service: PortfolioService):
        payload = PortfolioCreate(
            client_id=_CLIENT_ID,
            portfolio_type="yield_portfolio",
            name="No Origin",
        )
        pf = portfolio_service.create_portfolio(db, payload)
        assert pf.origin_product_id is None

    def test_create_invalid_origin_product(self, db: Session, portfolio_service: PortfolioService):
        payload = PortfolioCreate(
            client_id=_CLIENT_ID,
            portfolio_type="bundle_portfolio",
            name="Bad Origin",
            origin_product_id=uuid.uuid4(),
        )
        with pytest.raises(OriginProductReferenceError):
            portfolio_service.create_portfolio(db, payload)

    def test_update_attach_origin_product(
        self, db: Session, portfolio_service: PortfolioService,
        portfolio_basic: Portfolio, product: ProductDefinition,
    ):
        payload = PortfolioUpdate(origin_product_id=product.id)
        updated = portfolio_service.update_portfolio(db, portfolio_basic.id, payload)
        assert updated.origin_product_id == product.id
        assert updated.name == "Balanced Crypto"

    def test_update_invalid_origin_product(
        self, db: Session, portfolio_service: PortfolioService, portfolio_basic: Portfolio,
    ):
        payload = PortfolioUpdate(origin_product_id=uuid.uuid4())
        with pytest.raises(OriginProductReferenceError):
            portfolio_service.update_portfolio(db, portfolio_basic.id, payload)


# ---------------------------------------------------------------------------
# Sleeve Repository tests
# ---------------------------------------------------------------------------

class TestSleeveRepository:

    def test_create(self, db: Session, portfolio_basic: Portfolio):
        s = SleeveRepository.create(
            db,
            data={
                "portfolio_id": portfolio_basic.id,
                "name": "Satellite",
                "sleeve_type": "satellite",
                "allocation_target": Decimal("0.300000"),
                "metadata_": {},
            },
        )
        assert s.id is not None
        assert s.name == "Satellite"
        assert s.allocation_target == Decimal("0.300000")

    def test_get_by_id(self, db: Session, sleeve_core: Sleeve):
        found = SleeveRepository.get_by_id(db, sleeve_core.id)
        assert found is not None
        assert found.name == "Core"

    def test_list_by_portfolio(self, db: Session, portfolio_basic: Portfolio, sleeve_core: Sleeve):
        SleeveRepository.create(
            db,
            data={
                "portfolio_id": portfolio_basic.id,
                "name": "Alternative",
                "sleeve_type": "alternative",
                "metadata_": {},
            },
        )
        items, total = SleeveRepository.list_by_portfolio(db, portfolio_basic.id)
        assert total >= 2
        assert all(s.portfolio_id == portfolio_basic.id for s in items)

    def test_update(self, db: Session, sleeve_core: Sleeve):
        SleeveRepository.update(db, sleeve_core, data={"allocation_target": Decimal("0.500000")})
        db.flush()
        refreshed = SleeveRepository.get_by_id(db, sleeve_core.id)
        assert refreshed.allocation_target == Decimal("0.500000")


# ---------------------------------------------------------------------------
# Sleeve Service tests
# ---------------------------------------------------------------------------

class TestSleeveService:

    def test_create_sleeve(self, db: Session, sleeve_service: SleeveService, portfolio_basic: Portfolio):
        payload = SleeveCreate(name="Yield", sleeve_type="yield", allocation_target=Decimal("0.100000"))
        sleeve = sleeve_service.create_sleeve(db, portfolio_basic.id, payload)
        assert sleeve.name == "Yield"
        assert sleeve.portfolio_id == portfolio_basic.id

    def test_create_sleeve_invalid_portfolio(self, db: Session, sleeve_service: SleeveService):
        payload = SleeveCreate(name="Ghost", sleeve_type="core")
        with pytest.raises(PortfolioReferenceError):
            sleeve_service.create_sleeve(db, uuid.uuid4(), payload)

    def test_get_sleeve(self, db: Session, sleeve_service: SleeveService, sleeve_core: Sleeve):
        found = sleeve_service.get_sleeve(db, sleeve_core.id)
        assert found.id == sleeve_core.id

    def test_get_sleeve_not_found(self, db: Session, sleeve_service: SleeveService):
        with pytest.raises(SleeveNotFoundError):
            sleeve_service.get_sleeve(db, uuid.uuid4())

    def test_list_sleeves(self, db: Session, sleeve_service: SleeveService, portfolio_basic: Portfolio, sleeve_core: Sleeve):
        items, total = sleeve_service.list_sleeves(db, portfolio_basic.id)
        assert total >= 1

    def test_update_sleeve(self, db: Session, sleeve_service: SleeveService, sleeve_core: Sleeve):
        payload = SleeveUpdate(name="Core (v2)")
        updated = sleeve_service.update_sleeve(db, sleeve_core.id, payload)
        assert updated.name == "Core (v2)"
        assert updated.sleeve_type == "core"
