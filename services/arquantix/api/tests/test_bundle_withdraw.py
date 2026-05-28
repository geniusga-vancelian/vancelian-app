"""Tests — retrait bundle miroir fund-first (unwind → release)."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import Session

from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundle_execution.bundle_funding import (
    BundleFundingError,
    fund_bundle_cash_leg_from_self_trading,
    release_bundle_cash_leg_to_self_trading,
    resolve_bundle_cash_leg_available,
)
from services.portfolio_engine.bundle_execution.pe_settlement import apply_withdraw_sell_atoms
from services.portfolio_engine.bundle_execution.types import ExecutionLeg, ExecutionResult
from services.portfolio_engine.bundles.orchestrator import (
    POSITION_TYPE_CASH,
    POSITION_TYPE_SPOT,
    BundleOrchestrator,
)
from services.portfolio_engine.bundles.bundle_invest_lock import (
    acquire_invest_lock,
    get_invest_lock,
    load_portfolio_for_invest_lock,
)
from services.portfolio_engine.bundles.withdraw import (
    BundleWithdrawOrchestrator,
    BundleWithdrawOrchestratorError,
)
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.products.models import ProductDefinition
from services.privy_wallet.repository import PersonWalletBalanceRepository

from conftest import make_linked_client
from tests.test_bundle_lifi_funding import _bundle_portfolio, _instrument_usdc, _seed_privy_usdc


def _instrument_for_asset(db: Session, symbol: str) -> Instrument:
    asset = db.query(Asset).filter(Asset.symbol == symbol).first()
    if asset is None:
        asset = Asset(symbol=symbol, name=symbol, asset_type="cryptocurrency")
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
            code=f"{symbol}_SPOT",
            name=f"{symbol} Spot",
            instrument_type="spot",
        )
        db.add(instr)
        db.flush()
    return instr


class _MockSyncSellProvider:
    name = "exchange"

    def execute_leg(self, db, leg: ExecutionLeg, actor) -> ExecutionResult:
        return ExecutionResult(
            leg_id=leg.leg_id,
            status="completed",
            from_asset=leg.from_asset,
            to_asset=leg.to_asset,
            amount_from=leg.amount_from,
            amount_to=leg.amount_from,
            provider_order_id=f"mock-{leg.leg_id}",
            raw={"reference_value_net": leg.amount_from},
        )


def test_release_cash_leg_credits_self_trading_without_privy(db: Session):
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
    _seed_privy_usdc(db, pe.person_id, wallet.id, "200")
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc_instr.id, Decimal("100"), Decimal("86"))
    BundleOrchestrator._credit_cash_leg(
        db, portfolio.id, usdc_instr.id, Decimal("50"), Decimal("43"),
    )
    db.commit()

    privy_before = PersonWalletBalanceRepository().get_or_create_for_update(
        db, wallet_id=wallet.id, person_id=pe.person_id, asset="USDC",
    )
    privy_bal = Decimal(str(privy_before.balance))

    release = release_bundle_cash_leg_to_self_trading(
        db,
        client_id=pe.id,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc_instr.id,
        amount=Decimal("30"),
        batch_id="withdraw-release-1",
    )
    db.commit()

    assert release["privy_ledger_touched"] is False
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
    assert Decimal(str(direct_atom.quantity)) == Decimal("130")
    assert Decimal(str(cash_atom.quantity)) == Decimal("20")

    privy_after = PersonWalletBalanceRepository().get_or_create_for_update(
        db, wallet_id=wallet.id, person_id=pe.person_id, asset="USDC",
    )
    assert Decimal(str(privy_after.balance)) == privy_bal


def test_release_rejects_insufficient_cash_leg(db: Session):
    pe = make_linked_client(db)
    usdc_instr = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    BundleOrchestrator._credit_cash_leg(
        db, portfolio.id, usdc_instr.id, Decimal("10"), Decimal("8.6"),
    )
    db.commit()

    with pytest.raises(BundleFundingError) as exc:
        release_bundle_cash_leg_to_self_trading(
            db,
            client_id=pe.id,
            person_id=None,
            portfolio_id=portfolio.id,
            entry_asset="USDC",
            entry_instrument_id=usdc_instr.id,
            amount=Decimal("20"),
            batch_id="withdraw-release-2",
        )
    assert "insufficient_cash_leg" in exc.value.code


def test_withdraw_sell_atoms_debits_spot_and_credits_cash_leg(db: Session):
    pe = make_linked_client(db)
    usdc_instr = _instrument_usdc(db)
    link_instr = _instrument_for_asset(db, "LINK")
    portfolio = _bundle_portfolio(db, pe.id)

    BundleOrchestrator._sync_pe_position(
        db, portfolio.id, link_instr.id, Decimal("5"), Decimal("50"),
    )
    db.commit()

    apply_withdraw_sell_atoms(
        db,
        portfolio_id=portfolio.id,
        instrument_id=link_instr.id,
        entry_instrument_id=usdc_instr.id,
        sell_qty=Decimal("2"),
        entry_received=Decimal("20"),
        cost_basis_eur=Decimal("20"),
    )
    db.commit()

    spot = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.instrument_id == link_instr.id,
            PositionAtom.position_type == POSITION_TYPE_SPOT,
        )
        .first()
    )
    cash = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.instrument_id == usdc_instr.id,
            PositionAtom.position_type == POSITION_TYPE_CASH,
        )
        .first()
    )
    assert Decimal(str(spot.quantity)) == Decimal("3")
    assert cash is not None
    assert Decimal(str(cash.quantity)) == Decimal("20")


def test_cash_only_withdraw_clears_stale_invest_lock(db: Session):
    pe = make_linked_client(db)
    usdc_instr = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc_instr.id, Decimal("13"), Decimal("11"))
    BundleOrchestrator._credit_cash_leg(
        db, portfolio.id, usdc_instr.id, Decimal("20"), Decimal("17.2"),
    )
    portfolio_locked = load_portfolio_for_invest_lock(
        db, client_id=pe.id, portfolio_id=portfolio.id,
    )
    acquire_invest_lock(
        db,
        portfolio_locked,
        client_id=pe.id,
        batch_id=str(uuid.uuid4()),
        status="partial_pending",
    )
    db.commit()

    mock_adapter = MagicMock()
    mock_adapter.provider_name = "exchange"
    mock_adapter.execute_leg = _MockSyncSellProvider().execute_leg

    orch = BundleWithdrawOrchestrator(execution_adapter=mock_adapter)
    result = orch.withdraw_from_bundle(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        full_withdraw=True,
    )
    db.commit()

    db.refresh(portfolio_locked)
    assert result["release"]["released"] is True
    assert get_invest_lock(portfolio_locked.metadata_) is None


def test_cash_only_withdraw_blocked_when_invest_swap_still_pending(db: Session):
    pe = make_linked_client(db)
    usdc_instr = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    BundleOrchestrator._credit_cash_leg(
        db, portfolio.id, usdc_instr.id, Decimal("20"), Decimal("17.2"),
    )
    batch_id = str(uuid.uuid4())
    portfolio_locked = load_portfolio_for_invest_lock(
        db, client_id=pe.id, portfolio_id=portfolio.id,
    )
    acquire_invest_lock(
        db,
        portfolio_locked,
        client_id=pe.id,
        batch_id=batch_id,
        status="pending_signature",
    )
    db.commit()

    from datetime import datetime, timezone

    from services.lifi.enums import SwapSessionStatus
    from services.lifi.models import PersonWalletSwap

    db.add(
        PersonWalletSwap(
            person_id=pe.person_id,
            from_asset="USDC",
            to_asset="LINK",
            from_chain="base",
            to_chain="base",
            amount_in=Decimal("10"),
            status=SwapSessionStatus.AWAITING_SIGNATURE.value,
            expires_at=datetime.now(timezone.utc),
            audit_log=[
                {
                    "event": "bundle_leg_context",
                    "batch_id": batch_id,
                    "portfolio_id": str(portfolio.id),
                    "bundle_action": "allocation",
                }
            ],
        )
    )
    db.commit()

    mock_adapter = MagicMock()
    mock_adapter.provider_name = "exchange"
    orch = BundleWithdrawOrchestrator(execution_adapter=mock_adapter)
    with pytest.raises(BundleWithdrawOrchestratorError) as exc:
        orch.withdraw_from_bundle(
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
            full_withdraw=True,
        )
    assert str(exc.value) == "invest_lock_active"


def test_cash_only_withdraw_releases_to_self_trading(db: Session):
    pe = make_linked_client(db)
    usdc_instr = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc_instr.id, Decimal("13"), Decimal("11"))
    BundleOrchestrator._credit_cash_leg(
        db, portfolio.id, usdc_instr.id, Decimal("10"), Decimal("8.6"),
    )
    db.commit()

    mock_adapter = MagicMock()
    mock_adapter.provider_name = "exchange"
    mock_adapter.execute_leg = _MockSyncSellProvider().execute_leg

    orch = BundleWithdrawOrchestrator(execution_adapter=mock_adapter)
    result = orch.withdraw_from_bundle(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        withdraw_amount=Decimal("10"),
    )
    db.commit()

    assert result["release"]["released"] is True
    assert result["sell_results"] == []

    direct_atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == direct_pf.id,
            PositionAtom.instrument_id == usdc_instr.id,
            PositionAtom.position_type == POSITION_TYPE_SPOT,
        )
        .first()
    )
    cash = resolve_bundle_cash_leg_available(
        db, portfolio_id=portfolio.id, entry_instrument_id=usdc_instr.id,
    )
    assert Decimal(str(direct_atom.quantity)) == Decimal("23")
    assert cash == Decimal("0")


@pytest.fixture(autouse=True)
def _exchange_provider(monkeypatch):
    monkeypatch.setenv("BUNDLE_EXECUTION_PROVIDER", "exchange")


def test_full_withdraw_unwinds_spots_then_releases(db: Session):
    pe = make_linked_client(db)
    usdc_instr = _instrument_usdc(db)
    link_instr = _instrument_for_asset(db, "LINK")
    portfolio = _bundle_portfolio(db, pe.id)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc_instr.id, Decimal("13"), Decimal("11"))

    BundleOrchestrator._sync_pe_position(
        db, portfolio.id, link_instr.id, Decimal("4"), Decimal("40"),
    )
    BundleOrchestrator._credit_cash_leg(
        db, portfolio.id, usdc_instr.id, Decimal("6"), Decimal("5.16"),
    )
    db.commit()

    mock_adapter = MagicMock()
    mock_adapter.provider_name = "exchange"
    mock_adapter.execute_leg = _MockSyncSellProvider().execute_leg

    orch = BundleWithdrawOrchestrator(execution_adapter=mock_adapter)
    result = orch.withdraw_from_bundle(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        full_withdraw=True,
    )
    db.commit()

    assert result["status"] == "released"
    assert len(result["sell_results"]) == 1
    assert result["sell_results"][0]["status"] == "completed"

    spot = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.instrument_id == link_instr.id,
            PositionAtom.position_type == POSITION_TYPE_SPOT,
        )
        .first()
    )
    cash = resolve_bundle_cash_leg_available(
        db, portfolio_id=portfolio.id, entry_instrument_id=usdc_instr.id,
    )
    direct_atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == direct_pf.id,
            PositionAtom.instrument_id == usdc_instr.id,
            PositionAtom.position_type == POSITION_TYPE_SPOT,
        )
        .first()
    )
    assert Decimal(str(spot.quantity)) == Decimal("0")
    assert cash == Decimal("0")
    assert Decimal(str(direct_atom.quantity)) == Decimal("23")


def test_partial_withdraw_leaves_residual_exposure(db: Session):
    pe = make_linked_client(db)
    usdc_instr = _instrument_usdc(db)
    link_instr = _instrument_for_asset(db, "LINK")
    portfolio = _bundle_portfolio(db, pe.id)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc_instr.id, Decimal("13"), Decimal("11"))

    BundleOrchestrator._sync_pe_position(
        db, portfolio.id, link_instr.id, Decimal("10"), Decimal("100"),
    )
    BundleOrchestrator._credit_cash_leg(
        db, portfolio.id, usdc_instr.id, Decimal("6"), Decimal("5.16"),
    )
    db.commit()

    mock_adapter = MagicMock()
    mock_adapter.provider_name = "exchange"
    mock_adapter.execute_leg = _MockSyncSellProvider().execute_leg

    orch = BundleWithdrawOrchestrator(execution_adapter=mock_adapter)
    result = orch.withdraw_from_bundle(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        withdraw_amount=Decimal("4"),
    )
    db.commit()

    assert result["needed_from_sells"] == 0.0
    assert result["release"]["released"] is True
    spot = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.instrument_id == link_instr.id,
            PositionAtom.position_type == POSITION_TYPE_SPOT,
        )
        .first()
    )
    assert Decimal(str(spot.quantity)) == Decimal("10")
    cash = resolve_bundle_cash_leg_available(
        db, portfolio_id=portfolio.id, entry_instrument_id=usdc_instr.id,
    )
    assert cash == Decimal("2")
    direct_atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == direct_pf.id,
            PositionAtom.instrument_id == usdc_instr.id,
            PositionAtom.position_type == POSITION_TYPE_SPOT,
        )
        .first()
    )
    assert Decimal(str(direct_atom.quantity)) == Decimal("17")


def test_release_blocked_when_cash_leg_insufficient_for_requested_amount(db: Session):
    pe = make_linked_client(db)
    usdc_instr = _instrument_usdc(db)
    link_instr = _instrument_for_asset(db, "LINK")
    portfolio = _bundle_portfolio(db, pe.id)

    BundleOrchestrator._sync_pe_position(
        db, portfolio.id, link_instr.id, Decimal("10"), Decimal("100"),
    )
    db.commit()

    class _PartialMockProvider:
        name = "exchange"

        def execute_leg(self, db, leg, actor):
            return ExecutionResult(
                leg_id=leg.leg_id,
                status="completed",
                from_asset=leg.from_asset,
                to_asset=leg.to_asset,
                amount_from=leg.amount_from,
                amount_to=Decimal("3"),
                raw={"reference_value_net": Decimal("3")},
            )

    mock_adapter = MagicMock()
    mock_adapter.provider_name = "exchange"
    mock_adapter.execute_leg = _PartialMockProvider().execute_leg

    orch = BundleWithdrawOrchestrator(execution_adapter=mock_adapter)
    result = orch.withdraw_from_bundle(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        withdraw_amount=Decimal("10"),
    )
    db.commit()

    assert result["release"]["released"] is False
    assert result["release"]["reason"] == "insufficient_cash_leg_for_requested_amount"

    spot = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.instrument_id == link_instr.id,
            PositionAtom.position_type == POSITION_TYPE_SPOT,
        )
        .first()
    )
    assert Decimal(str(spot.quantity)) == Decimal("9")


def test_fund_and_release_no_double_counting(db: Session):
    """Invariant : direct + bundle_cash ≈ self-trading après fund puis release."""
    pe = make_linked_client(db)
    usdc_instr = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, pe.id)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc_instr.id, Decimal("100"), Decimal("86"))
    db.commit()

    fund_bundle_cash_leg_from_self_trading(
        db,
        client_id=pe.id,
        person_id=None,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc_instr.id,
        amount=Decimal("40"),
        batch_id="roundtrip-fund",
    )
    release_bundle_cash_leg_to_self_trading(
        db,
        client_id=pe.id,
        person_id=None,
        portfolio_id=portfolio.id,
        entry_asset="USDC",
        entry_instrument_id=usdc_instr.id,
        amount=Decimal("40"),
        batch_id="roundtrip-release",
    )
    db.commit()

    direct_qty = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == direct_pf.id,
            PositionAtom.instrument_id == usdc_instr.id,
            PositionAtom.position_type == POSITION_TYPE_SPOT,
        )
        .first()
    )
    cash_qty = resolve_bundle_cash_leg_available(
        db, portfolio_id=portfolio.id, entry_instrument_id=usdc_instr.id,
    )
    assert Decimal(str(direct_qty.quantity)) == Decimal("100")
    assert cash_qty == Decimal("0")
