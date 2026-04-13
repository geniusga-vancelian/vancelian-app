"""Tests — Phase 1: Guards reject non-allowed position types.

Verifies that:
- Repository.create() rejects lending/staking/borrowing/arbitrary strings
- Repository.update() rejects non-allowed position_type changes
- Service.create_position() rejects non-allowed position types
- Service.update_position() rejects non-allowed position types
- spot and cash pass through successfully
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.positions.repository import PositionAtomRepository
from services.portfolio_engine.positions.schemas import PositionCreate, PositionUpdate
from services.portfolio_engine.positions.service import PositionAtomService

_CLIENT_ID = uuid.uuid4()


def _unique_symbol(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:6].upper()}"


@pytest.fixture
def asset_btc(db: Session) -> Asset:
    sym = _unique_symbol("TBTC")
    a = Asset(id=uuid.uuid4(), symbol=sym, name=f"Test Bitcoin {sym}", asset_type="crypto", metadata_={})
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def instrument_btc(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(), asset_id=asset_btc.id, code=f"{asset_btc.symbol}_SPOT",
        name=f"{asset_btc.symbol} Spot", instrument_type="spot", metadata_={},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def portfolio(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(), client_id=_CLIENT_ID, portfolio_type="direct_portfolio",
        name="Direct", base_currency="EUR", status="active", metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def repo() -> PositionAtomRepository:
    return PositionAtomRepository()


@pytest.fixture
def svc() -> PositionAtomService:
    return PositionAtomService()


@pytest.fixture
def existing_spot_atom(db: Session, portfolio: Portfolio, instrument_btc: Instrument, repo: PositionAtomRepository) -> PositionAtom:
    return repo.create(db, data={
        "portfolio_id": portfolio.id,
        "instrument_id": instrument_btc.id,
        "position_type": PositionType.SPOT,
        "status": "open",
        "quantity": Decimal("1.0"),
        "available_quantity": Decimal("1.0"),
        "metadata_": {},
    })


# ---------------------------------------------------------------------------
# Repository.create() — rejections
# ---------------------------------------------------------------------------

class TestRepositoryCreateReject:
    @pytest.mark.parametrize("bad_type", [
        "lending", "staking", "borrowing", "collateral",
        "foo_bar", "SPOT", "Spot", "",
    ])
    def test_create_rejects_non_allowed_types(
        self, db: Session, portfolio: Portfolio, instrument_btc: Instrument,
        repo: PositionAtomRepository, bad_type: str,
    ):
        with pytest.raises(ValueError, match="not allowed"):
            repo.create(db, data={
                "portfolio_id": portfolio.id,
                "instrument_id": instrument_btc.id,
                "position_type": bad_type,
                "status": "open",
                "quantity": Decimal("1.0"),
                "available_quantity": Decimal("1.0"),
                "metadata_": {},
            })


# ---------------------------------------------------------------------------
# Repository.create() — allowed types pass
# ---------------------------------------------------------------------------

class TestRepositoryCreateAllowed:
    @pytest.mark.parametrize("good_type", [PositionType.SPOT, PositionType.CASH])
    def test_create_allows_spot_and_cash(
        self, db: Session, portfolio: Portfolio, instrument_btc: Instrument,
        repo: PositionAtomRepository, good_type: PositionType,
    ):
        atom = repo.create(db, data={
            "portfolio_id": portfolio.id,
            "instrument_id": instrument_btc.id,
            "position_type": good_type,
            "status": "open",
            "quantity": Decimal("1.0"),
            "available_quantity": Decimal("1.0"),
            "metadata_": {},
        })
        assert atom.position_type == good_type


# ---------------------------------------------------------------------------
# Repository.update() — rejections
# ---------------------------------------------------------------------------

class TestRepositoryUpdateReject:
    def test_update_rejects_non_allowed_type(
        self, db: Session, existing_spot_atom: PositionAtom,
        repo: PositionAtomRepository,
    ):
        with pytest.raises(ValueError, match="not allowed"):
            repo.update(db, existing_spot_atom, data={"position_type": "lending"})

    def test_update_without_position_type_passes(
        self, db: Session, existing_spot_atom: PositionAtom,
        repo: PositionAtomRepository,
    ):
        updated = repo.update(db, existing_spot_atom, data={"quantity": Decimal("2.0")})
        assert updated.quantity == Decimal("2.0")
        assert updated.position_type == PositionType.SPOT


# ---------------------------------------------------------------------------
# Service.create_position() — rejections
# ---------------------------------------------------------------------------

class TestServiceCreateReject:
    @pytest.mark.parametrize("bad_type", [
        PositionType.LENDING, PositionType.STAKING,
        PositionType.BORROWING, PositionType.COLLATERAL,
    ])
    def test_service_create_rejects_non_allowed(
        self, db: Session, portfolio: Portfolio, instrument_btc: Instrument,
        svc: PositionAtomService, bad_type: PositionType,
    ):
        payload = PositionCreate(
            portfolio_id=portfolio.id,
            instrument_id=instrument_btc.id,
            position_type=bad_type,
        )
        with pytest.raises(ValueError, match="not allowed"):
            svc.create_position(db, payload)


class TestServiceCreateAllowed:
    @pytest.mark.parametrize("good_type", [PositionType.SPOT, PositionType.CASH])
    def test_service_create_allows_spot_and_cash(
        self, db: Session, portfolio: Portfolio, instrument_btc: Instrument,
        svc: PositionAtomService, good_type: PositionType,
    ):
        payload = PositionCreate(
            portfolio_id=portfolio.id,
            instrument_id=instrument_btc.id,
            position_type=good_type,
        )
        atom = svc.create_position(db, payload)
        assert atom.position_type == good_type


# ---------------------------------------------------------------------------
# Service.update_position() — rejections
# ---------------------------------------------------------------------------

class TestServiceUpdateReject:
    def test_service_update_rejects_lending(
        self, db: Session, existing_spot_atom: PositionAtom,
        svc: PositionAtomService,
    ):
        payload = PositionUpdate(position_type=PositionType.LENDING)
        with pytest.raises(ValueError, match="not allowed"):
            svc.update_position(db, existing_spot_atom.id, payload)

    def test_service_update_allows_cash(
        self, db: Session, existing_spot_atom: PositionAtom,
        svc: PositionAtomService,
    ):
        payload = PositionUpdate(position_type=PositionType.CASH)
        updated = svc.update_position(db, existing_spot_atom.id, payload)
        assert updated.position_type == PositionType.CASH
