"""Tests for Portfolio Engine — Assets module (create / get / list / update)."""
import uuid

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.assets.repository import AssetRepository, DuplicateSymbolError
from services.portfolio_engine.assets.service import AssetNotFoundError, AssetService
from services.portfolio_engine.assets.schemas import AssetCreate, AssetUpdate


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
def service() -> AssetService:
    return AssetService()


# ---------------------------------------------------------------------------
# Repository tests
# ---------------------------------------------------------------------------

class TestAssetRepository:

    def test_create(self, db: Session):
        asset = AssetRepository.create(
            db,
            data={
                "symbol": "ETH",
                "name": "Ethereum",
                "asset_type": "crypto",
                "supports_staking": True,
                "metadata_": {"chain": "ethereum"},
            },
        )
        assert asset.id is not None
        assert asset.symbol == "ETH"
        assert asset.asset_type == "crypto"
        assert asset.supports_staking is True
        assert asset.metadata_ == {"chain": "ethereum"}

    def test_create_duplicate_symbol(self, db: Session, asset_btc: Asset):
        with pytest.raises(DuplicateSymbolError):
            AssetRepository.create(
                db,
                data={
                    "symbol": "BTC",
                    "name": "Bitcoin duplicate",
                    "asset_type": "crypto",
                    "metadata_": {},
                },
            )

    def test_get_by_id(self, db: Session, asset_btc: Asset):
        found = AssetRepository.get_by_id(db, asset_btc.id)
        assert found is not None
        assert found.symbol == "BTC"

    def test_get_by_id_not_found(self, db: Session):
        found = AssetRepository.get_by_id(db, uuid.uuid4())
        assert found is None

    def test_list(self, db: Session, asset_btc: Asset):
        AssetRepository.create(db, data={"symbol": "USDC", "name": "USD Coin", "asset_type": "stablecoin", "metadata_": {}})
        items, total = AssetRepository.list(db)
        assert total >= 2
        assert any(a.symbol == "BTC" for a in items)

    def test_list_filter_by_type(self, db: Session, asset_btc: Asset):
        AssetRepository.create(db, data={"symbol": "USDC", "name": "USD Coin", "asset_type": "stablecoin", "metadata_": {}})
        items, total = AssetRepository.list(db, asset_type="stablecoin")
        assert total >= 1
        assert all(a.asset_type == "stablecoin" for a in items)

    def test_update(self, db: Session, asset_btc: Asset):
        AssetRepository.update(db, asset_btc, data={"name": "Bitcoin (updated)", "supports_staking": True})
        db.flush()
        refreshed = AssetRepository.get_by_id(db, asset_btc.id)
        assert refreshed.name == "Bitcoin (updated)"
        assert refreshed.supports_staking is True


# ---------------------------------------------------------------------------
# Service tests
# ---------------------------------------------------------------------------

class TestAssetService:

    def test_create_asset(self, db: Session, service: AssetService):
        payload = AssetCreate(
            symbol="SOL",
            name="Solana",
            asset_type="crypto",
            supports_staking=True,
        )
        asset = service.create_asset(db, payload)
        assert asset.symbol == "SOL"
        assert asset.supports_staking is True

    def test_get_asset(self, db: Session, service: AssetService, asset_btc: Asset):
        found = service.get_asset(db, asset_btc.id)
        assert found.id == asset_btc.id

    def test_get_asset_not_found(self, db: Session, service: AssetService):
        with pytest.raises(AssetNotFoundError):
            service.get_asset(db, uuid.uuid4())

    def test_list_assets(self, db: Session, service: AssetService, asset_btc: Asset):
        items, total = service.list_assets(db)
        assert total >= 1

    def test_update_asset(self, db: Session, service: AssetService, asset_btc: Asset):
        payload = AssetUpdate(name="Bitcoin Core")
        updated = service.update_asset(db, asset_btc.id, payload)
        assert updated.name == "Bitcoin Core"
        assert updated.symbol == "BTC"
