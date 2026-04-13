"""Tests for Portfolio Engine — Position Relations module."""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.relations.models import PositionRelation
from services.portfolio_engine.relations.repository import (
    DuplicateRelationError,
    PositionRelationRepository,
)
from services.portfolio_engine.relations.service import (
    PositionReferenceError,
    PositionRelationService,
    RelationNotFoundError,
    SelfRelationError,
)
from services.portfolio_engine.relations.schemas import RelationCreate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

_CLIENT_ID = uuid.uuid4()


@pytest.fixture
def asset_btc(db: Session) -> Asset:
    a = Asset(
        id=uuid.uuid4(), symbol="BTC", name="Bitcoin",
        asset_type="crypto", metadata_={},
    )
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def asset_usdc(db: Session) -> Asset:
    a = Asset(
        id=uuid.uuid4(), symbol="USDC", name="USD Coin",
        asset_type="stablecoin", metadata_={},
    )
    db.add(a)
    db.flush()
    return a


@pytest.fixture
def instrument_btc(db: Session, asset_btc: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(), asset_id=asset_btc.id, code="BTC-SPOT",
        name="BTC Spot", instrument_type="spot", metadata_={},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def instrument_usdc(db: Session, asset_usdc: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(), asset_id=asset_usdc.id, code="USDC-SPOT",
        name="USDC Spot", instrument_type="spot", metadata_={},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def portfolio(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(), client_id=_CLIENT_ID, portfolio_type="bundle_portfolio",
        name="Test Portfolio", base_currency="EUR", status="active", metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def position_btc_spot(db: Session, portfolio: Portfolio, instrument_btc: Instrument) -> PositionAtom:
    p = PositionAtom(
        id=uuid.uuid4(), portfolio_id=portfolio.id, instrument_id=instrument_btc.id,
        position_type="spot", status="open", quantity=Decimal("1.0"), metadata_={},
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def position_btc_collateral(db: Session, portfolio: Portfolio, instrument_btc: Instrument) -> PositionAtom:
    p = PositionAtom(
        id=uuid.uuid4(), portfolio_id=portfolio.id, instrument_id=instrument_btc.id,
        position_type="collateral", status="open", quantity=Decimal("0.5"), metadata_={},
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def position_usdc_debt(db: Session, portfolio: Portfolio, instrument_usdc: Instrument) -> PositionAtom:
    p = PositionAtom(
        id=uuid.uuid4(), portfolio_id=portfolio.id, instrument_id=instrument_usdc.id,
        position_type="debt", status="open", quantity=Decimal("10000.0"), metadata_={},
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def relation_collateralizes(
    db: Session, position_btc_collateral: PositionAtom, position_usdc_debt: PositionAtom,
) -> PositionRelation:
    r = PositionRelation(
        id=uuid.uuid4(),
        source_position_id=position_btc_collateral.id,
        target_position_id=position_usdc_debt.id,
        relation_type="collateralizes",
        parameters={"ltv": 0.65},
    )
    db.add(r)
    db.flush()
    return r


@pytest.fixture
def relation_service() -> PositionRelationService:
    return PositionRelationService()


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestPositionRelationRepository:

    def test_create(self, db: Session, position_btc_spot: PositionAtom, position_btc_collateral: PositionAtom):
        r = PositionRelationRepository.create(
            db,
            data={
                "source_position_id": position_btc_spot.id,
                "target_position_id": position_btc_collateral.id,
                "relation_type": "derived_from",
                "parameters": {},
            },
        )
        assert r.id is not None
        assert r.relation_type == "derived_from"

    def test_get_by_id(self, db: Session, relation_collateralizes: PositionRelation):
        found = PositionRelationRepository.get_by_id(db, relation_collateralizes.id)
        assert found is not None
        assert found.relation_type == "collateralizes"

    def test_get_by_id_not_found(self, db: Session):
        assert PositionRelationRepository.get_by_id(db, uuid.uuid4()) is None

    def test_list_by_position_source(
        self, db: Session, relation_collateralizes: PositionRelation,
        position_btc_collateral: PositionAtom,
    ):
        items, total = PositionRelationRepository.list_by_position(db, position_btc_collateral.id)
        assert total >= 1
        assert any(r.id == relation_collateralizes.id for r in items)

    def test_list_by_position_target(
        self, db: Session, relation_collateralizes: PositionRelation,
        position_usdc_debt: PositionAtom,
    ):
        items, total = PositionRelationRepository.list_by_position(db, position_usdc_debt.id)
        assert total >= 1
        assert any(r.id == relation_collateralizes.id for r in items)

    def test_list_by_position_filter_type(
        self, db: Session, relation_collateralizes: PositionRelation,
        position_btc_collateral: PositionAtom,
    ):
        items, total = PositionRelationRepository.list_by_position(
            db, position_btc_collateral.id, relation_type="collateralizes",
        )
        assert total >= 1

        items_none, total_none = PositionRelationRepository.list_by_position(
            db, position_btc_collateral.id, relation_type="settles_into",
        )
        assert total_none == 0

    def test_duplicate_raises(
        self, db: Session, relation_collateralizes: PositionRelation,
        position_btc_collateral: PositionAtom, position_usdc_debt: PositionAtom,
    ):
        with pytest.raises(DuplicateRelationError):
            PositionRelationRepository.create(
                db,
                data={
                    "source_position_id": position_btc_collateral.id,
                    "target_position_id": position_usdc_debt.id,
                    "relation_type": "collateralizes",
                    "parameters": {},
                },
            )

    def test_same_pair_different_type_ok(
        self, db: Session, relation_collateralizes: PositionRelation,
        position_btc_collateral: PositionAtom, position_usdc_debt: PositionAtom,
    ):
        r = PositionRelationRepository.create(
            db,
            data={
                "source_position_id": position_btc_collateral.id,
                "target_position_id": position_usdc_debt.id,
                "relation_type": "depends_on",
                "parameters": {},
            },
        )
        assert r.id is not None
        assert r.relation_type == "depends_on"

    def test_delete(self, db: Session, relation_collateralizes: PositionRelation):
        rid = relation_collateralizes.id
        PositionRelationRepository.delete(db, relation_collateralizes)
        assert PositionRelationRepository.get_by_id(db, rid) is None


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestPositionRelationService:

    def test_create_relation(
        self, db: Session, relation_service: PositionRelationService,
        position_btc_spot: PositionAtom, position_btc_collateral: PositionAtom,
    ):
        payload = RelationCreate(
            source_position_id=position_btc_spot.id,
            target_position_id=position_btc_collateral.id,
            relation_type="derived_from",
        )
        rel = relation_service.create_relation(db, payload)
        assert rel.source_position_id == position_btc_spot.id
        assert rel.target_position_id == position_btc_collateral.id

    def test_create_relation_with_parameters(
        self, db: Session, relation_service: PositionRelationService,
        position_btc_collateral: PositionAtom, position_usdc_debt: PositionAtom,
    ):
        payload = RelationCreate(
            source_position_id=position_btc_collateral.id,
            target_position_id=position_usdc_debt.id,
            relation_type="collateralizes",
            parameters={"ltv": 0.7, "margin_call_threshold": 0.85},
        )
        rel = relation_service.create_relation(db, payload)
        assert rel.parameters["ltv"] == 0.7

    def test_create_self_relation_rejected(
        self, db: Session, relation_service: PositionRelationService,
        position_btc_spot: PositionAtom,
    ):
        payload = RelationCreate(
            source_position_id=position_btc_spot.id,
            target_position_id=position_btc_spot.id,
            relation_type="depends_on",
        )
        with pytest.raises(SelfRelationError):
            relation_service.create_relation(db, payload)

    def test_create_relation_invalid_source(
        self, db: Session, relation_service: PositionRelationService,
        position_btc_spot: PositionAtom,
    ):
        payload = RelationCreate(
            source_position_id=uuid.uuid4(),
            target_position_id=position_btc_spot.id,
            relation_type="funds",
        )
        with pytest.raises(PositionReferenceError):
            relation_service.create_relation(db, payload)

    def test_create_relation_invalid_target(
        self, db: Session, relation_service: PositionRelationService,
        position_btc_spot: PositionAtom,
    ):
        payload = RelationCreate(
            source_position_id=position_btc_spot.id,
            target_position_id=uuid.uuid4(),
            relation_type="funds",
        )
        with pytest.raises(PositionReferenceError):
            relation_service.create_relation(db, payload)

    def test_create_duplicate_rejected(
        self, db: Session, relation_service: PositionRelationService,
        relation_collateralizes: PositionRelation,
        position_btc_collateral: PositionAtom, position_usdc_debt: PositionAtom,
    ):
        payload = RelationCreate(
            source_position_id=position_btc_collateral.id,
            target_position_id=position_usdc_debt.id,
            relation_type="collateralizes",
        )
        with pytest.raises(DuplicateRelationError):
            relation_service.create_relation(db, payload)

    def test_get_relation(
        self, db: Session, relation_service: PositionRelationService,
        relation_collateralizes: PositionRelation,
    ):
        found = relation_service.get_relation(db, relation_collateralizes.id)
        assert found.id == relation_collateralizes.id

    def test_get_relation_not_found(self, db: Session, relation_service: PositionRelationService):
        with pytest.raises(RelationNotFoundError):
            relation_service.get_relation(db, uuid.uuid4())

    def test_list_relations_for_position(
        self, db: Session, relation_service: PositionRelationService,
        relation_collateralizes: PositionRelation,
        position_btc_collateral: PositionAtom,
    ):
        items, total = relation_service.list_relations_for_position(db, position_btc_collateral.id)
        assert total >= 1

    def test_delete_relation(
        self, db: Session, relation_service: PositionRelationService,
        relation_collateralizes: PositionRelation,
    ):
        rid = relation_collateralizes.id
        relation_service.delete_relation(db, rid)
        with pytest.raises(RelationNotFoundError):
            relation_service.get_relation(db, rid)

    def test_delete_relation_not_found(self, db: Session, relation_service: PositionRelationService):
        with pytest.raises(RelationNotFoundError):
            relation_service.delete_relation(db, uuid.uuid4())
