"""Tests for Portfolio Engine — Position Atoms module."""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.sleeves.models import Sleeve
from services.portfolio_engine.wallets.models import WalletContainer
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.positions.repository import PositionAtomRepository
from services.portfolio_engine.positions.service import (
    InstrumentReferenceError,
    ParentPositionReferenceError,
    PortfolioReferenceError,
    PositionAtomService,
    PositionNotFoundError,
    SleevePortfolioMismatchError,
    SleeveReferenceError,
    WalletReferenceError,
)
from services.portfolio_engine.positions.schemas import PositionCreate, PositionUpdate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CLIENT_ID = uuid.uuid4()


@pytest.fixture
def asset_btc(db: Session) -> Asset:
    a = Asset(
        id=uuid.uuid4(),
        symbol="BTC",
        name="Bitcoin",
        asset_type="crypto",
        metadata_={},
    )
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def instrument_btc_spot(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(),
        asset_id=asset_btc.id,
        code="BTC-SPOT",
        name="BTC Spot",
        instrument_type="spot",
        metadata_={},
    )
    db.add(i)
    db.flush()
    return i


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
def wallet_spot(db: Session, portfolio_basic: Portfolio, instrument_btc_spot: Instrument) -> WalletContainer:
    w = WalletContainer(
        id=uuid.uuid4(),
        client_id=_CLIENT_ID,
        portfolio_id=portfolio_basic.id,
        wallet_type="spot_wallet",
        instrument_id=instrument_btc_spot.id,
        custody_provider="fireblocks",
        status="active",
        metadata_={},
    )
    db.add(w)
    db.flush()
    return w


@pytest.fixture
def position_btc(
    db: Session,
    portfolio_basic: Portfolio,
    instrument_btc_spot: Instrument,
    sleeve_core: Sleeve,
    wallet_spot: WalletContainer,
) -> PositionAtom:
    p = PositionAtom(
        id=uuid.uuid4(),
        portfolio_id=portfolio_basic.id,
        sleeve_id=sleeve_core.id,
        wallet_id=wallet_spot.id,
        instrument_id=instrument_btc_spot.id,
        position_type="spot",
        status="open",
        quantity=Decimal("1.5000000000"),
        available_quantity=Decimal("1.0000000000"),
        locked_quantity=Decimal("0.5000000000"),
        market_value=Decimal("45000.0000000000"),
        cost_basis=Decimal("40000.0000000000"),
        average_entry_price=Decimal("30000.0000000000"),
        metadata_={},
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def portfolio_other(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=_CLIENT_ID,
        portfolio_type="bundle_portfolio",
        name="Other Portfolio",
        base_currency="EUR",
        status="active",
        metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def sleeve_other(db: Session, portfolio_other: Portfolio) -> Sleeve:
    s = Sleeve(
        id=uuid.uuid4(),
        portfolio_id=portfolio_other.id,
        name="Alt",
        sleeve_type="alternative",
        allocation_target=Decimal("0.200000"),
        metadata_={},
    )
    db.add(s)
    db.flush()
    return s


@pytest.fixture
def position_service() -> PositionAtomService:
    return PositionAtomService()


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestPositionAtomRepository:

    def test_create(self, db: Session, portfolio_basic: Portfolio, instrument_btc_spot: Instrument):
        p = PositionAtomRepository.create(
            db,
            data={
                "portfolio_id": portfolio_basic.id,
                "instrument_id": instrument_btc_spot.id,
                "position_type": "spot",
                "quantity": Decimal("2.0"),
                "metadata_": {},
            },
        )
        assert p.id is not None
        assert p.position_type == "spot"
        assert p.status == "open"
        assert p.quantity == Decimal("2.0")

    def test_get_by_id(self, db: Session, position_btc: PositionAtom):
        found = PositionAtomRepository.get_by_id(db, position_btc.id)
        assert found is not None
        assert found.position_type == "spot"

    def test_get_by_id_not_found(self, db: Session):
        assert PositionAtomRepository.get_by_id(db, uuid.uuid4()) is None

    def test_list_all(self, db: Session, position_btc: PositionAtom, portfolio_basic: Portfolio, instrument_btc_spot: Instrument):
        PositionAtomRepository.create(
            db,
            data={
                "portfolio_id": portfolio_basic.id,
                "instrument_id": instrument_btc_spot.id,
                "position_type": "staked",
                "metadata_": {},
            },
        )
        items, total = PositionAtomRepository.list(db)
        assert total >= 2

    def test_list_filter_by_portfolio(self, db: Session, position_btc: PositionAtom, portfolio_basic: Portfolio):
        items, total = PositionAtomRepository.list(db, portfolio_id=portfolio_basic.id)
        assert total >= 1
        assert all(p.portfolio_id == portfolio_basic.id for p in items)

    def test_list_filter_by_position_type(self, db: Session, position_btc: PositionAtom):
        items, total = PositionAtomRepository.list(db, position_type="spot")
        assert total >= 1
        assert all(p.position_type == "spot" for p in items)

    def test_list_filter_by_status(self, db: Session, position_btc: PositionAtom):
        items, total = PositionAtomRepository.list(db, status="open")
        assert total >= 1
        assert all(p.status == "open" for p in items)

    def test_list_filter_by_instrument(self, db: Session, position_btc: PositionAtom, instrument_btc_spot: Instrument):
        items, total = PositionAtomRepository.list(db, instrument_id=instrument_btc_spot.id)
        assert total >= 1
        assert all(p.instrument_id == instrument_btc_spot.id for p in items)

    def test_update(self, db: Session, position_btc: PositionAtom):
        PositionAtomRepository.update(
            db, position_btc,
            data={"quantity": Decimal("3.0"), "status": "closed"},
        )
        db.flush()
        refreshed = PositionAtomRepository.get_by_id(db, position_btc.id)
        assert refreshed.quantity == Decimal("3.0")
        assert refreshed.status == "closed"


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestPositionAtomService:

    def test_create_position(
        self, db: Session, position_service: PositionAtomService,
        portfolio_basic: Portfolio, instrument_btc_spot: Instrument,
    ):
        payload = PositionCreate(
            portfolio_id=portfolio_basic.id,
            instrument_id=instrument_btc_spot.id,
            position_type="spot",
            quantity=Decimal("1.0"),
        )
        pos = position_service.create_position(db, payload)
        assert pos.portfolio_id == portfolio_basic.id
        assert pos.instrument_id == instrument_btc_spot.id
        assert pos.position_type == "spot"

    def test_create_position_with_all_refs(
        self, db: Session, position_service: PositionAtomService,
        portfolio_basic: Portfolio, instrument_btc_spot: Instrument,
        sleeve_core: Sleeve, wallet_spot: WalletContainer,
    ):
        payload = PositionCreate(
            portfolio_id=portfolio_basic.id,
            instrument_id=instrument_btc_spot.id,
            sleeve_id=sleeve_core.id,
            wallet_id=wallet_spot.id,
            position_type="spot",
            quantity=Decimal("0.5"),
        )
        pos = position_service.create_position(db, payload)
        assert pos.sleeve_id == sleeve_core.id
        assert pos.wallet_id == wallet_spot.id

    def test_create_position_invalid_portfolio(self, db: Session, position_service: PositionAtomService, instrument_btc_spot: Instrument):
        payload = PositionCreate(
            portfolio_id=uuid.uuid4(),
            instrument_id=instrument_btc_spot.id,
            position_type="spot",
        )
        with pytest.raises(PortfolioReferenceError):
            position_service.create_position(db, payload)

    def test_create_position_invalid_instrument(self, db: Session, position_service: PositionAtomService, portfolio_basic: Portfolio):
        payload = PositionCreate(
            portfolio_id=portfolio_basic.id,
            instrument_id=uuid.uuid4(),
            position_type="spot",
        )
        with pytest.raises(InstrumentReferenceError):
            position_service.create_position(db, payload)

    def test_create_position_invalid_sleeve(
        self, db: Session, position_service: PositionAtomService,
        portfolio_basic: Portfolio, instrument_btc_spot: Instrument,
    ):
        payload = PositionCreate(
            portfolio_id=portfolio_basic.id,
            instrument_id=instrument_btc_spot.id,
            sleeve_id=uuid.uuid4(),
            position_type="spot",
        )
        with pytest.raises(SleeveReferenceError):
            position_service.create_position(db, payload)

    def test_create_position_invalid_wallet(
        self, db: Session, position_service: PositionAtomService,
        portfolio_basic: Portfolio, instrument_btc_spot: Instrument,
    ):
        payload = PositionCreate(
            portfolio_id=portfolio_basic.id,
            instrument_id=instrument_btc_spot.id,
            wallet_id=uuid.uuid4(),
            position_type="spot",
        )
        with pytest.raises(WalletReferenceError):
            position_service.create_position(db, payload)

    def test_create_position_invalid_parent(
        self, db: Session, position_service: PositionAtomService,
        portfolio_basic: Portfolio, instrument_btc_spot: Instrument,
    ):
        payload = PositionCreate(
            portfolio_id=portfolio_basic.id,
            instrument_id=instrument_btc_spot.id,
            parent_position_id=uuid.uuid4(),
            position_type="spot",
        )
        with pytest.raises(ParentPositionReferenceError):
            position_service.create_position(db, payload)

    def test_create_position_with_parent(
        self, db: Session, position_service: PositionAtomService,
        portfolio_basic: Portfolio, instrument_btc_spot: Instrument,
        position_btc: PositionAtom,
    ):
        payload = PositionCreate(
            portfolio_id=portfolio_basic.id,
            instrument_id=instrument_btc_spot.id,
            parent_position_id=position_btc.id,
            position_type="spot",
            quantity=Decimal("0.5"),
        )
        pos = position_service.create_position(db, payload)
        assert pos.parent_position_id == position_btc.id

    def test_get_position(self, db: Session, position_service: PositionAtomService, position_btc: PositionAtom):
        found = position_service.get_position(db, position_btc.id)
        assert found.id == position_btc.id

    def test_get_position_not_found(self, db: Session, position_service: PositionAtomService):
        with pytest.raises(PositionNotFoundError):
            position_service.get_position(db, uuid.uuid4())

    def test_list_positions(self, db: Session, position_service: PositionAtomService, position_btc: PositionAtom):
        items, total = position_service.list_positions(db)
        assert total >= 1

    def test_list_positions_by_portfolio(
        self, db: Session, position_service: PositionAtomService,
        position_btc: PositionAtom, portfolio_basic: Portfolio,
    ):
        items, total = position_service.list_positions(db, portfolio_id=portfolio_basic.id)
        assert total >= 1
        assert all(p.portfolio_id == portfolio_basic.id for p in items)

    def test_update_position(self, db: Session, position_service: PositionAtomService, position_btc: PositionAtom):
        payload = PositionUpdate(quantity=Decimal("2.5"), status="closed")
        updated = position_service.update_position(db, position_btc.id, payload)
        assert updated.quantity == Decimal("2.5")
        assert updated.status == "closed"

    def test_update_position_partial(self, db: Session, position_service: PositionAtomService, position_btc: PositionAtom):
        payload = PositionUpdate(market_value=Decimal("50000.0"))
        updated = position_service.update_position(db, position_btc.id, payload)
        assert updated.market_value == Decimal("50000.0")
        assert updated.quantity == Decimal("1.5000000000")
        assert updated.position_type == "spot"

    def test_update_position_invalid_sleeve_ref(self, db: Session, position_service: PositionAtomService, position_btc: PositionAtom):
        payload = PositionUpdate(sleeve_id=uuid.uuid4())
        with pytest.raises(SleeveReferenceError):
            position_service.update_position(db, position_btc.id, payload)

    def test_update_position_invalid_wallet_ref(self, db: Session, position_service: PositionAtomService, position_btc: PositionAtom):
        payload = PositionUpdate(wallet_id=uuid.uuid4())
        with pytest.raises(WalletReferenceError):
            position_service.update_position(db, position_btc.id, payload)

    def test_update_position_invalid_parent_ref(self, db: Session, position_service: PositionAtomService, position_btc: PositionAtom):
        payload = PositionUpdate(parent_position_id=uuid.uuid4())
        with pytest.raises(ParentPositionReferenceError):
            position_service.update_position(db, position_btc.id, payload)

    def test_create_position_sleeve_portfolio_mismatch(
        self, db: Session, position_service: PositionAtomService,
        portfolio_basic: Portfolio, instrument_btc_spot: Instrument,
        sleeve_other: Sleeve,
    ):
        payload = PositionCreate(
            portfolio_id=portfolio_basic.id,
            instrument_id=instrument_btc_spot.id,
            sleeve_id=sleeve_other.id,
            position_type="spot",
            quantity=Decimal("1.0"),
        )
        with pytest.raises(SleevePortfolioMismatchError):
            position_service.create_position(db, payload)

    def test_update_position_sleeve_portfolio_mismatch(
        self, db: Session, position_service: PositionAtomService,
        position_btc: PositionAtom, sleeve_other: Sleeve,
    ):
        payload = PositionUpdate(sleeve_id=sleeve_other.id)
        with pytest.raises(SleevePortfolioMismatchError):
            position_service.update_position(db, position_btc.id, payload)
