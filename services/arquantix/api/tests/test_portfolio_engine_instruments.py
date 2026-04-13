"""Tests for Portfolio Engine — Instruments module (create / get / list / update / FK validation)."""
import uuid

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.instruments.repository import InstrumentRepository, DuplicateCodeError
from services.portfolio_engine.instruments.service import (
    AssetReferenceError,
    InstrumentNotFoundError,
    InstrumentService,
)
from services.portfolio_engine.instruments.schemas import InstrumentCreate, InstrumentUpdate


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def asset_btc(db: Session) -> Asset:
    asset = Asset(
        id=uuid.uuid4(),
        symbol="BTC",
        name="Bitcoin",
        asset_type="crypto",
        supports_staking=False,
        supports_collateral=True,
        supports_borrowing=False,
        supports_yield=False,
        metadata_={},
    )
    db.add(asset)
    db.flush()
    return asset


@pytest.fixture
def instrument_btc_spot(db: Session, asset_btc: Asset) -> Instrument:
    instrument = Instrument(
        id=uuid.uuid4(),
        asset_id=asset_btc.id,
        code="BTC-SPOT",
        name="Bitcoin Spot",
        instrument_type="spot",
        metadata_={},
    )
    db.add(instrument)
    db.flush()
    return instrument


@pytest.fixture
def service() -> InstrumentService:
    return InstrumentService()


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestInstrumentRepository:

    def test_create(self, db: Session, asset_btc: Asset):
        instrument = InstrumentRepository.create(
            db,
            data={
                "asset_id": asset_btc.id,
                "code": "BTC-STAKING",
                "name": "Bitcoin Staking",
                "instrument_type": "staking_position",
                "lockup_period_days": 30,
                "metadata_": {"protocol": "babylon"},
            },
        )
        assert instrument.id is not None
        assert instrument.code == "BTC-STAKING"
        assert instrument.asset_id == asset_btc.id
        assert instrument.lockup_period_days == 30
        assert instrument.metadata_ == {"protocol": "babylon"}

    def test_create_duplicate_code(self, db: Session, instrument_btc_spot: Instrument, asset_btc: Asset):
        with pytest.raises(DuplicateCodeError):
            InstrumentRepository.create(
                db,
                data={
                    "asset_id": asset_btc.id,
                    "code": "BTC-SPOT",
                    "name": "Bitcoin Spot duplicate",
                    "instrument_type": "spot",
                    "metadata_": {},
                },
            )

    def test_get_by_id(self, db: Session, instrument_btc_spot: Instrument):
        found = InstrumentRepository.get_by_id(db, instrument_btc_spot.id)
        assert found is not None
        assert found.code == "BTC-SPOT"

    def test_get_by_id_not_found(self, db: Session):
        found = InstrumentRepository.get_by_id(db, uuid.uuid4())
        assert found is None

    def test_list(self, db: Session, instrument_btc_spot: Instrument, asset_btc: Asset):
        InstrumentRepository.create(
            db,
            data={
                "asset_id": asset_btc.id,
                "code": "BTC-COLLATERAL",
                "name": "Bitcoin Collateral",
                "instrument_type": "collateral_position",
                "metadata_": {},
            },
        )
        items, total = InstrumentRepository.list(db)
        assert total >= 2
        assert any(i.code == "BTC-SPOT" for i in items)

    def test_list_filter_by_type(self, db: Session, instrument_btc_spot: Instrument, asset_btc: Asset):
        InstrumentRepository.create(
            db,
            data={
                "asset_id": asset_btc.id,
                "code": "BTC-VAULT",
                "name": "Bitcoin Vault Share",
                "instrument_type": "vault_share",
                "metadata_": {},
            },
        )
        items, total = InstrumentRepository.list(db, instrument_type="vault_share")
        assert total >= 1
        assert all(i.instrument_type == "vault_share" for i in items)

    def test_list_filter_by_asset_id(self, db: Session, instrument_btc_spot: Instrument, asset_btc: Asset):
        items, total = InstrumentRepository.list(db, asset_id=asset_btc.id)
        assert total >= 1
        assert all(i.asset_id == asset_btc.id for i in items)

    def test_update(self, db: Session, instrument_btc_spot: Instrument):
        InstrumentRepository.update(
            db, instrument_btc_spot, data={"name": "BTC Spot (updated)", "provider": "vancelian"},
        )
        db.flush()
        refreshed = InstrumentRepository.get_by_id(db, instrument_btc_spot.id)
        assert refreshed.name == "BTC Spot (updated)"
        assert refreshed.provider == "vancelian"


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestInstrumentService:

    def test_create_instrument(self, db: Session, service: InstrumentService, asset_btc: Asset):
        payload = InstrumentCreate(
            asset_id=asset_btc.id,
            code="ETH-SPOT",
            name="Ethereum Spot",
            instrument_type="spot",
        )
        instrument = service.create_instrument(db, payload)
        assert instrument.code == "ETH-SPOT"
        assert instrument.asset_id == asset_btc.id

    def test_create_instrument_invalid_asset(self, db: Session, service: InstrumentService):
        payload = InstrumentCreate(
            asset_id=uuid.uuid4(),
            code="FAKE-SPOT",
            name="Fake Spot",
            instrument_type="spot",
        )
        with pytest.raises(AssetReferenceError):
            service.create_instrument(db, payload)

    def test_get_instrument(self, db: Session, service: InstrumentService, instrument_btc_spot: Instrument):
        found = service.get_instrument(db, instrument_btc_spot.id)
        assert found.id == instrument_btc_spot.id

    def test_get_instrument_not_found(self, db: Session, service: InstrumentService):
        with pytest.raises(InstrumentNotFoundError):
            service.get_instrument(db, uuid.uuid4())

    def test_list_instruments(self, db: Session, service: InstrumentService, instrument_btc_spot: Instrument):
        items, total = service.list_instruments(db)
        assert total >= 1

    def test_update_instrument(self, db: Session, service: InstrumentService, instrument_btc_spot: Instrument):
        payload = InstrumentUpdate(name="BTC Spot v2")
        updated = service.update_instrument(db, instrument_btc_spot.id, payload)
        assert updated.name == "BTC Spot v2"
        assert updated.code == "BTC-SPOT"

    def test_update_instrument_partial(self, db: Session, service: InstrumentService, instrument_btc_spot: Instrument):
        payload = InstrumentUpdate(provider="binance")
        updated = service.update_instrument(db, instrument_btc_spot.id, payload)
        assert updated.provider == "binance"
        assert updated.name == "Bitcoin Spot"
