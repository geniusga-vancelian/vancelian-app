"""Tests for Portfolio Engine — Wallet Containers module."""
import uuid

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.wallets.models import WalletContainer
from services.portfolio_engine.wallets.repository import WalletContainerRepository
from services.portfolio_engine.wallets.service import (
    InstrumentReferenceError,
    PortfolioReferenceError,
    WalletContainerService,
    WalletNotFoundError,
)
from services.portfolio_engine.wallets.schemas import WalletCreate, WalletUpdate


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
def wallet_service() -> WalletContainerService:
    return WalletContainerService()


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestWalletContainerRepository:

    def test_create(self, db: Session, portfolio_basic: Portfolio):
        w = WalletContainerRepository.create(
            db,
            data={
                "client_id": _CLIENT_ID,
                "portfolio_id": portfolio_basic.id,
                "wallet_type": "staking_wallet",
                "status": "active",
                "metadata_": {},
            },
        )
        assert w.id is not None
        assert w.wallet_type == "staking_wallet"
        assert w.status == "active"

    def test_get_by_id(self, db: Session, wallet_spot: WalletContainer):
        found = WalletContainerRepository.get_by_id(db, wallet_spot.id)
        assert found is not None
        assert found.wallet_type == "spot_wallet"

    def test_get_by_id_not_found(self, db: Session):
        assert WalletContainerRepository.get_by_id(db, uuid.uuid4()) is None

    def test_list_all(self, db: Session, wallet_spot: WalletContainer):
        WalletContainerRepository.create(
            db,
            data={
                "wallet_type": "fee_wallet",
                "status": "active",
                "metadata_": {},
            },
        )
        items, total = WalletContainerRepository.list(db)
        assert total >= 2

    def test_list_filter_by_client(self, db: Session, wallet_spot: WalletContainer):
        items, total = WalletContainerRepository.list(db, client_id=_CLIENT_ID)
        assert total >= 1
        assert all(w.client_id == _CLIENT_ID for w in items)

    def test_list_filter_by_wallet_type(self, db: Session, wallet_spot: WalletContainer):
        items, total = WalletContainerRepository.list(db, wallet_type="spot_wallet")
        assert total >= 1
        assert all(w.wallet_type == "spot_wallet" for w in items)

    def test_list_filter_by_portfolio(self, db: Session, wallet_spot: WalletContainer, portfolio_basic: Portfolio):
        items, total = WalletContainerRepository.list(db, portfolio_id=portfolio_basic.id)
        assert total >= 1
        assert all(w.portfolio_id == portfolio_basic.id for w in items)

    def test_update(self, db: Session, wallet_spot: WalletContainer):
        WalletContainerRepository.update(db, wallet_spot, data={"status": "frozen", "custody_provider": "anchorage"})
        db.flush()
        refreshed = WalletContainerRepository.get_by_id(db, wallet_spot.id)
        assert refreshed.status == "frozen"
        assert refreshed.custody_provider == "anchorage"


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestWalletContainerService:

    def test_create_wallet(self, db: Session, wallet_service: WalletContainerService, portfolio_basic: Portfolio, instrument_btc_spot: Instrument):
        payload = WalletCreate(
            client_id=_CLIENT_ID,
            portfolio_id=portfolio_basic.id,
            wallet_type="spot_wallet",
            instrument_id=instrument_btc_spot.id,
            custody_provider="fireblocks",
        )
        wallet = wallet_service.create_wallet(db, payload)
        assert wallet.wallet_type == "spot_wallet"
        assert wallet.portfolio_id == portfolio_basic.id
        assert wallet.instrument_id == instrument_btc_spot.id

    def test_create_wallet_minimal(self, db: Session, wallet_service: WalletContainerService):
        payload = WalletCreate(wallet_type="fee_wallet")
        wallet = wallet_service.create_wallet(db, payload)
        assert wallet.wallet_type == "fee_wallet"
        assert wallet.portfolio_id is None
        assert wallet.instrument_id is None

    def test_create_wallet_invalid_portfolio(self, db: Session, wallet_service: WalletContainerService):
        payload = WalletCreate(wallet_type="spot_wallet", portfolio_id=uuid.uuid4())
        with pytest.raises(PortfolioReferenceError):
            wallet_service.create_wallet(db, payload)

    def test_create_wallet_invalid_instrument(self, db: Session, wallet_service: WalletContainerService, portfolio_basic: Portfolio):
        payload = WalletCreate(
            wallet_type="spot_wallet",
            portfolio_id=portfolio_basic.id,
            instrument_id=uuid.uuid4(),
        )
        with pytest.raises(InstrumentReferenceError):
            wallet_service.create_wallet(db, payload)

    def test_get_wallet(self, db: Session, wallet_service: WalletContainerService, wallet_spot: WalletContainer):
        found = wallet_service.get_wallet(db, wallet_spot.id)
        assert found.id == wallet_spot.id

    def test_get_wallet_not_found(self, db: Session, wallet_service: WalletContainerService):
        with pytest.raises(WalletNotFoundError):
            wallet_service.get_wallet(db, uuid.uuid4())

    def test_list_wallets(self, db: Session, wallet_service: WalletContainerService, wallet_spot: WalletContainer):
        items, total = wallet_service.list_wallets(db)
        assert total >= 1

    def test_list_wallets_filter_by_client(self, db: Session, wallet_service: WalletContainerService, wallet_spot: WalletContainer):
        items, total = wallet_service.list_wallets(db, client_id=_CLIENT_ID)
        assert total >= 1
        assert all(w.client_id == _CLIENT_ID for w in items)

    def test_update_wallet(self, db: Session, wallet_service: WalletContainerService, wallet_spot: WalletContainer):
        payload = WalletUpdate(status="frozen")
        updated = wallet_service.update_wallet(db, wallet_spot.id, payload)
        assert updated.status == "frozen"
        assert updated.wallet_type == "spot_wallet"

    def test_update_wallet_partial(self, db: Session, wallet_service: WalletContainerService, wallet_spot: WalletContainer):
        payload = WalletUpdate(custody_provider="anchorage")
        updated = wallet_service.update_wallet(db, wallet_spot.id, payload)
        assert updated.custody_provider == "anchorage"
        assert updated.status == "active"

    def test_update_wallet_invalid_portfolio_ref(self, db: Session, wallet_service: WalletContainerService, wallet_spot: WalletContainer):
        payload = WalletUpdate(portfolio_id=uuid.uuid4())
        with pytest.raises(PortfolioReferenceError):
            wallet_service.update_wallet(db, wallet_spot.id, payload)

    def test_update_wallet_invalid_instrument_ref(self, db: Session, wallet_service: WalletContainerService, wallet_spot: WalletContainer):
        payload = WalletUpdate(instrument_id=uuid.uuid4())
        with pytest.raises(InstrumentReferenceError):
            wallet_service.update_wallet(db, wallet_spot.id, payload)
