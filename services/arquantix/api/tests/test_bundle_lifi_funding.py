"""Tests — funding comptable bundle (fund PE first, Privy inchangé)."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundle_execution.bundle_funding import (
    BundleFundingError,
    fund_bundle_cash_leg_from_self_trading,
    resolve_self_trading_available,
    sum_bundle_cash_leg_quantity,
)
from services.portfolio_engine.bundles.orchestrator import (
    POSITION_TYPE_CASH,
    POSITION_TYPE_SPOT,
    BundleOrchestrator,
)
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.products.models import ProductDefinition
from services.privy_wallet.repository import PersonWalletBalanceRepository

from conftest import make_linked_client


def _instrument_usdc(db: Session) -> Instrument:
    asset = db.query(Asset).filter(Asset.symbol == "USDC").first()
    if asset is None:
        asset = Asset(symbol="USDC", name="USD Coin", asset_type="stablecoin")
        db.add(asset)
        db.flush()
    instr = (
        db.query(Instrument)
        .filter(Instrument.asset_id == asset.id, Instrument.instrument_type == "spot")
        .first()
    )
    if instr is None:
        instr = Instrument(
            asset_id=asset.id,
            code="USDC_SPOT",
            name="USDC Spot",
            instrument_type="spot",
        )
        db.add(instr)
        db.flush()
    return instr


def _bundle_portfolio(db: Session, client_id) -> Portfolio:
    suffix = uuid.uuid4().hex[:6].upper()
    product = ProductDefinition(
        product_code=f"BUNDLE-FUND-{suffix}",
        name=f"Test Bundle {suffix}",
        product_type="crypto_bundle",
        base_currency="EUR",
        is_public=True,
        status="active",
        metadata_={"entry_asset_default": "USDC", "entry_assets_allowed": ["USDC"]},
    )
    db.add(product)
    db.flush()
    portfolio = Portfolio(
        client_id=client_id,
        origin_product_id=product.id,
        portfolio_type="bundle_portfolio",
        name="Test Bundle PF",
        base_currency="USD",
        status="active",
    )
    db.add(portfolio)
    db.flush()
    return portfolio


def _seed_privy_usdc(db: Session, person_id, wallet_id, amount: str = "1000") -> None:
    row = PersonWalletBalanceRepository().get_or_create_for_update(
        db, wallet_id=wallet_id, person_id=person_id, asset="USDC",
    )
    PersonWalletBalanceRepository.increment_balance(
        db, row, delta=Decimal(amount), sync_source="test",
    )


def test_fund_moves_self_trading_to_cash_leg_without_privy_change(db: Session):
    pe = make_linked_client(db)
    usdc_instr = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)

    from services.auth.person_identity_bridge import upsert_person_crypto_wallet, PROVIDER_PRIVY

    wallet = upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        chain_id=8453,
        address=f"0x{uuid.uuid4().hex[:40]}",
    )
    _seed_privy_usdc(db, pe.person_id, wallet.id, "500")
    db.commit()

    privy_before = PersonWalletBalanceRepository().get_or_create_for_update(
        db, wallet_id=wallet.id, person_id=pe.person_id, asset="USDC",
    )
    privy_bal_before = Decimal(str(privy_before.balance))

    fund = fund_bundle_cash_leg_from_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc_instr.id,
        amount=Decimal("200"),
        batch_id="batch-test-1",
    )
    db.commit()

    assert fund["privy_ledger_touched"] is False
    assert fund["amount"] == 200.0

    direct_pf = ensure_direct_portfolio(db, pe.id)
    direct_atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == direct_pf.id,
            PositionAtom.instrument_id == usdc_instr.id,
            PositionAtom.position_type == POSITION_TYPE_SPOT,
        )
        .first()
    )
    cash_atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.instrument_id == usdc_instr.id,
            PositionAtom.position_type == POSITION_TYPE_CASH,
        )
        .first()
    )

    assert direct_atom is not None
    assert Decimal(str(direct_atom.quantity)) == Decimal("300")
    assert cash_atom is not None
    assert Decimal(str(cash_atom.quantity)) == Decimal("200")

    privy_after = PersonWalletBalanceRepository().get_or_create_for_update(
        db, wallet_id=wallet.id, person_id=pe.person_id, asset="USDC",
    )
    assert Decimal(str(privy_after.balance)) == privy_bal_before


def test_fund_rejects_insufficient_self_trading(db: Session):
    pe = make_linked_client(db)
    usdc_instr = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc_instr.id, Decimal("50"), Decimal("43"))
    db.commit()

    with pytest.raises(BundleFundingError) as exc:
        fund_bundle_cash_leg_from_self_trading(
            db,
            client_id=pe.id,
            person_id=None,
            portfolio_id=portfolio.id,
            entry_asset="USDC",
            entry_instrument_id=usdc_instr.id,
            amount=Decimal("100"),
            batch_id="batch-test-2",
        )
    assert "insufficient" in exc.value.code


def test_sum_bundle_cash_leg_quantity(db: Session):
    pe = make_linked_client(db)
    usdc_instr = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    BundleOrchestrator._credit_cash_leg(
        db, portfolio.id, usdc_instr.id, Decimal("75"), Decimal("64.5"),
    )
    db.commit()

    total = sum_bundle_cash_leg_quantity(
        db, client_id=pe.id, instrument_id=usdc_instr.id,
    )
    assert total == Decimal("75")


@patch.dict("os.environ", {"BUNDLE_EXECUTION_PROVIDER": "lifi_base", "BUNDLE_LIFI_SYNC_MOCK": "1", "LIFI_SWAPS_MOCK": "1"})
def test_lifi_invest_funds_cash_leg_before_allocation(db: Session, monkeypatch):
    """Invest LI.FI : le cash leg est alimenté au fund, avant tout leg d'allocation."""
    monkeypatch.setenv("BUNDLE_EXECUTION_PROVIDER", "lifi_base")
    monkeypatch.setenv("BUNDLE_LIFI_SYNC_MOCK", "1")
    monkeypatch.setenv("LIFI_SWAPS_MOCK", "1")

    from tests.test_bundle_orchestrator import _create_pe_bundle_portfolio, _seed_market_data

    _seed_market_data(db)
    pe = make_linked_client(db)
    usdc_instr = _instrument_usdc(db)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc_instr.id, Decimal("500"), Decimal("430"))
    db.commit()

    portfolio_id, _ = _create_pe_bundle_portfolio(
        db, pe.id,
        allocations={"BTC": Decimal("1.0")},
    )

    orchestrator = BundleOrchestrator()
    result = orchestrator.invest_into_bundle(
        db,
        client_id=pe.id,
        portfolio_id=portfolio_id,
        funding_asset="USDC",
        funding_amount=Decimal("200"),
    )
    db.commit()

    assert result["funding"]["action"] == "fund_cash_leg_from_self_trading"
    assert result["funding"]["privy_ledger_touched"] is False

    cash_atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio_id,
            PositionAtom.instrument_id == usdc_instr.id,
            PositionAtom.position_type == POSITION_TYPE_CASH,
        )
        .first()
    )
    assert cash_atom is not None
    assert Decimal(str(cash_atom.quantity)) == Decimal("200")

    direct_atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == direct_pf.id,
            PositionAtom.instrument_id == usdc_instr.id,
            PositionAtom.position_type == POSITION_TYPE_SPOT,
        )
        .first()
    )
    assert direct_atom is not None
    assert Decimal(str(direct_atom.quantity)) == Decimal("300")
