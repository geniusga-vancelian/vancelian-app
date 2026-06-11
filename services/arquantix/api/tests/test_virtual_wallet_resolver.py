"""Tests VirtualWalletResolver (ADR 008 Phase 1)."""
import uuid

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.wallets.enums import WalletType
from services.portfolio_engine.wallets.resolver import (
    backfill_position_atom_wallet_ids,
    ensure_portfolio_wallets,
    find_wallet,
    resolve_trade_wallets_for_leg,
    resolve_wallet,
)


_CLIENT_ID = uuid.uuid4()


@pytest.fixture
def bundle_portfolio(db: Session) -> Portfolio:
    pf = Portfolio(
        id=uuid.uuid4(),
        client_id=_CLIENT_ID,
        portfolio_type="bundle_portfolio",
        name="Two Crypto Kings",
        base_currency="USD",
        status="active",
        metadata_={},
    )
    db.add(pf)
    db.flush()
    return pf


@pytest.fixture
def usdc_instrument(db: Session) -> Instrument:
    asset = Asset(id=uuid.uuid4(), symbol="USDC", name="USDC", asset_type="stablecoin")
    db.add(asset)
    db.flush()
    instr = Instrument(
        id=uuid.uuid4(),
        asset_id=asset.id,
        code="USDC-SPOT",
        name="USDC",
        instrument_type="spot",
        metadata_={},
    )
    db.add(instr)
    db.flush()
    return instr


@pytest.fixture
def btc_instrument(db: Session) -> Instrument:
    asset = Asset(id=uuid.uuid4(), symbol="BTC", name="Bitcoin", asset_type="cryptocurrency")
    db.add(asset)
    db.flush()
    instr = Instrument(
        id=uuid.uuid4(),
        asset_id=asset.id,
        code="BTC-SPOT",
        name="BTC",
        instrument_type="spot",
        metadata_={},
    )
    db.add(instr)
    db.flush()
    return instr


def test_ensure_portfolio_wallets_idempotent(
    db: Session,
    bundle_portfolio: Portfolio,
    usdc_instrument: Instrument,
    btc_instrument: Instrument,
):
    first = ensure_portfolio_wallets(
        db,
        portfolio_id=bundle_portfolio.id,
        client_id=_CLIENT_ID,
        spot_instrument_ids=[btc_instrument.id],
        entry_instrument_id=usdc_instrument.id,
    )
    second = ensure_portfolio_wallets(
        db,
        portfolio_id=bundle_portfolio.id,
        client_id=_CLIENT_ID,
        spot_instrument_ids=[btc_instrument.id],
        entry_instrument_id=usdc_instrument.id,
    )
    assert first["spot_wallet_ids"] == second["spot_wallet_ids"]
    assert first["cash_wallet_ids"] == second["cash_wallet_ids"]

    cash = find_wallet(
        db,
        portfolio_id=bundle_portfolio.id,
        instrument_id=usdc_instrument.id,
        wallet_type=WalletType.CASH_WALLET.value,
    )
    spot = find_wallet(
        db,
        portfolio_id=bundle_portfolio.id,
        instrument_id=btc_instrument.id,
        wallet_type=WalletType.SPOT_WALLET.value,
    )
    assert cash is not None
    assert spot is not None
    assert cash.id != spot.id


def test_resolve_trade_wallets_rebalance_buy(
    db: Session,
    bundle_portfolio: Portfolio,
    usdc_instrument: Instrument,
    btc_instrument: Instrument,
):
    ensure_portfolio_wallets(
        db,
        portfolio_id=bundle_portfolio.id,
        client_id=_CLIENT_ID,
        spot_instrument_ids=[btc_instrument.id],
        entry_instrument_id=usdc_instrument.id,
    )
    wallet_from, wallet_to = resolve_trade_wallets_for_leg(
        db,
        portfolio_id=bundle_portfolio.id,
        client_id=_CLIENT_ID,
        leg_action="rebalance_buy",
        from_instrument_id=usdc_instrument.id,
        to_instrument_id=btc_instrument.id,
        entry_instrument_id=usdc_instrument.id,
    )
    cash = find_wallet(
        db,
        portfolio_id=bundle_portfolio.id,
        instrument_id=usdc_instrument.id,
        wallet_type=WalletType.CASH_WALLET.value,
    )
    spot = find_wallet(
        db,
        portfolio_id=bundle_portfolio.id,
        instrument_id=btc_instrument.id,
        wallet_type=WalletType.SPOT_WALLET.value,
    )
    assert wallet_from == cash.id
    assert wallet_to == spot.id


def test_backfill_position_atom_wallet_id(
    db: Session,
    bundle_portfolio: Portfolio,
    usdc_instrument: Instrument,
):
    ensure_portfolio_wallets(
        db,
        portfolio_id=bundle_portfolio.id,
        client_id=_CLIENT_ID,
        spot_instrument_ids=[],
        entry_instrument_id=usdc_instrument.id,
    )
    atom = PositionAtom(
        portfolio_id=bundle_portfolio.id,
        instrument_id=usdc_instrument.id,
        position_type=PositionType.CASH,
        status="open",
        quantity="100",
        available_quantity="100",
        metadata_={},
    )
    db.add(atom)
    db.flush()
    assert atom.wallet_id is None

    linked = backfill_position_atom_wallet_ids(
        db,
        portfolio_id=bundle_portfolio.id,
        client_id=_CLIENT_ID,
    )
    assert linked == 1
    wallet = resolve_wallet(
        db,
        portfolio_id=bundle_portfolio.id,
        instrument_id=usdc_instrument.id,
        wallet_type=WalletType.CASH_WALLET.value,
    )
    assert atom.wallet_id == wallet.id
