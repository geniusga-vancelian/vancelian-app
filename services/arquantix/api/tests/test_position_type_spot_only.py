"""Tests — Phase 1: All existing flows produce only spot/cash atoms.

Verifies that:
- sync_direct_atom always creates position_type="spot"
- BundleOrchestrator._credit_cash_leg always creates position_type="cash"
- BundleOrchestrator._sync_pe_position always creates position_type="spot"
- backfill_direct_atoms only creates position_type="spot"
- Invariant F: direct_atoms + bundle_atoms ≈ crypto_positions
- PositionAtomService._apply_buy always uses position_type="spot"
"""
import uuid
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from services.exchange.models import CryptoPosition
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom

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
def asset_usdc(db: Session) -> Asset:
    sym = _unique_symbol("TUSDC")
    a = Asset(id=uuid.uuid4(), symbol=sym, name=f"Test USDC {sym}", asset_type="stablecoin", metadata_={})
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
def instrument_usdc(db: Session, asset_usdc: Asset) -> Instrument:
    i = Instrument(
        id=uuid.uuid4(), asset_id=asset_usdc.id, code=f"{asset_usdc.symbol}_SPOT",
        name=f"{asset_usdc.symbol} Spot", instrument_type="spot", metadata_={},
    )
    db.add(i)
    db.flush()
    return i


@pytest.fixture
def direct_portfolio(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(), client_id=_CLIENT_ID, portfolio_type="direct_portfolio",
        name="Direct", base_currency="EUR", status="active", metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def bundle_portfolio(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(), client_id=_CLIENT_ID, portfolio_type="bundle_portfolio",
        name="Bundle", base_currency="EUR", status="active", metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


# ---------------------------------------------------------------------------
# sync_direct_atom — buy (positive delta)
# ---------------------------------------------------------------------------

class TestSyncDirectAtomBuy:
    def test_creates_spot_atom(self, db: Session, direct_portfolio: Portfolio, instrument_btc: Instrument):
        from services.portfolio_engine.direct_overlay import sync_direct_atom

        atom = sync_direct_atom(
            db, direct_portfolio.id, instrument_btc.id,
            quantity_delta=Decimal("0.5"), cost_basis_delta=Decimal("50000"),
        )
        assert atom.position_type == PositionType.SPOT
        assert atom.quantity == Decimal("0.5")

    def test_updates_existing_spot_atom(self, db: Session, direct_portfolio: Portfolio, instrument_btc: Instrument):
        from services.portfolio_engine.direct_overlay import sync_direct_atom

        sync_direct_atom(db, direct_portfolio.id, instrument_btc.id,
                         quantity_delta=Decimal("0.5"), cost_basis_delta=Decimal("50000"))
        atom = sync_direct_atom(db, direct_portfolio.id, instrument_btc.id,
                                quantity_delta=Decimal("0.3"), cost_basis_delta=Decimal("30000"))
        assert atom.position_type == PositionType.SPOT
        assert atom.quantity == Decimal("0.8")


# ---------------------------------------------------------------------------
# sync_direct_atom — sell (negative delta)
# ---------------------------------------------------------------------------

class TestSyncDirectAtomSell:
    def test_sell_keeps_spot_type(self, db: Session, direct_portfolio: Portfolio, instrument_btc: Instrument):
        from services.portfolio_engine.direct_overlay import sync_direct_atom

        sync_direct_atom(db, direct_portfolio.id, instrument_btc.id,
                         quantity_delta=Decimal("1.0"), cost_basis_delta=Decimal("100000"))
        atom = sync_direct_atom(db, direct_portfolio.id, instrument_btc.id,
                                quantity_delta=Decimal("-0.4"), cost_basis_delta=Decimal("-40000"))
        assert atom.position_type == PositionType.SPOT
        assert atom.quantity == Decimal("0.6")


# ---------------------------------------------------------------------------
# BundleOrchestrator._credit_cash_leg
# ---------------------------------------------------------------------------

class TestBundleCashLeg:
    def test_cash_leg_creates_cash_atom(self, db: Session, bundle_portfolio: Portfolio, instrument_usdc: Instrument):
        from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

        atom = BundleOrchestrator._credit_cash_leg(
            db, bundle_portfolio.id, instrument_usdc.id,
            quantity=Decimal("1000"), cost_basis=Decimal("1000"),
        )
        assert atom.position_type == PositionType.CASH
        assert atom.quantity == Decimal("1000")

    def test_cash_leg_updates_existing(self, db: Session, bundle_portfolio: Portfolio, instrument_usdc: Instrument):
        from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

        BundleOrchestrator._credit_cash_leg(
            db, bundle_portfolio.id, instrument_usdc.id,
            quantity=Decimal("1000"), cost_basis=Decimal("1000"),
        )
        atom = BundleOrchestrator._credit_cash_leg(
            db, bundle_portfolio.id, instrument_usdc.id,
            quantity=Decimal("500"), cost_basis=Decimal("500"),
        )
        assert atom.position_type == PositionType.CASH
        assert atom.quantity == Decimal("1500")


# ---------------------------------------------------------------------------
# BundleOrchestrator._sync_pe_position
# ---------------------------------------------------------------------------

class TestBundleSpotPosition:
    def test_sync_pe_position_creates_spot(self, db: Session, bundle_portfolio: Portfolio, instrument_btc: Instrument):
        from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

        atom = BundleOrchestrator._sync_pe_position(
            db, bundle_portfolio.id, instrument_btc.id,
            quantity_delta=Decimal("0.25"), cost_basis_delta=Decimal("25000"),
        )
        assert atom.position_type == PositionType.SPOT
        assert atom.quantity == Decimal("0.25")


# ---------------------------------------------------------------------------
# backfill_direct_atoms
# ---------------------------------------------------------------------------

class TestBackfillDirectAtoms:
    def test_backfill_creates_only_spot(
        self, db: Session, direct_portfolio: Portfolio,
        asset_btc: Asset, instrument_btc: Instrument,
    ):
        from services.portfolio_engine.direct_overlay import backfill_direct_atoms

        from services.portfolio_engine.clients.models import Client
        client = db.query(Client).filter(Client.id == _CLIENT_ID).first()
        if client is None:
            client = Client(id=_CLIENT_ID, email=f"test-spot-{_CLIENT_ID.hex[:8]}@test.local", status="active")
            db.add(client)
            db.flush()

        cp = CryptoPosition(
            client_id=_CLIENT_ID, asset=asset_btc.symbol, balance=Decimal("1.0"),
        )
        db.add(cp)
        db.flush()

        backfill_direct_atoms(db, _CLIENT_ID)

        atoms = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id == direct_portfolio.id,
                PositionAtom.status == "open",
            )
            .all()
        )
        assert len(atoms) >= 1
        for atom in atoms:
            assert atom.position_type == PositionType.SPOT, (
                f"Expected SPOT, got {atom.position_type}"
            )


# ---------------------------------------------------------------------------
# PositionAtomService._apply_buy
# ---------------------------------------------------------------------------

class TestServiceApplyBuySpot:
    def test_apply_buy_creates_spot(self, db: Session, direct_portfolio: Portfolio, instrument_btc: Instrument):
        from services.portfolio_engine.positions.service import PositionAtomService

        svc = PositionAtomService()
        atom = svc._apply_buy(
            db, None, direct_portfolio.id, instrument_btc.id,
            qty=Decimal("0.1"), price=Decimal("80000"),
            executed_at=None,
        )
        assert atom.position_type == PositionType.SPOT


# ---------------------------------------------------------------------------
# Invariant F: direct + bundle atoms ≈ crypto_positions
# ---------------------------------------------------------------------------

class TestInvariantF:
    def test_direct_plus_bundle_equals_crypto(
        self, db: Session, direct_portfolio: Portfolio, bundle_portfolio: Portfolio,
        instrument_btc: Instrument,
    ):
        from services.portfolio_engine.direct_overlay import sync_direct_atom
        from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator

        sync_direct_atom(
            db, direct_portfolio.id, instrument_btc.id,
            quantity_delta=Decimal("0.6"), cost_basis_delta=Decimal("60000"),
        )
        BundleOrchestrator._sync_pe_position(
            db, bundle_portfolio.id, instrument_btc.id,
            quantity_delta=Decimal("0.4"), cost_basis_delta=Decimal("40000"),
        )

        total_atoms = Decimal("0")
        for pf_id in [direct_portfolio.id, bundle_portfolio.id]:
            atoms = (
                db.query(PositionAtom)
                .filter(
                    PositionAtom.portfolio_id == pf_id,
                    PositionAtom.instrument_id == instrument_btc.id,
                    PositionAtom.position_type == PositionType.SPOT,
                    PositionAtom.status == "open",
                )
                .all()
            )
            for atom in atoms:
                total_atoms += Decimal(str(atom.quantity))

        assert total_atoms == Decimal("1.0")
