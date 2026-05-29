"""Tests Phase 5A — buffer, quotes parallèles, settlement réel."""
from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.allocations.models import TargetAllocation
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundle_execution.allocation_config import (
    compute_allocatable_amount,
    compute_execution_buffer,
)
from services.portfolio_engine.bundle_execution.allocation_planner import plan_allocation_legs
from services.portfolio_engine.bundle_execution.allocation_settlement import (
    resolve_allocation_leg_settlement_amounts,
)
from services.portfolio_engine.bundle_execution.bundle_funding import (
    fund_bundle_cash_leg_from_self_trading,
)
from services.portfolio_engine.bundle_execution.pe_settlement import apply_allocation_leg_atoms
from services.portfolio_engine.bundle_execution.types import ExecutionLeg
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

from conftest import make_linked_client
from tests.test_bundle_lifi_funding import _bundle_portfolio, _instrument_usdc


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


def _bundle_with_allocations(
    db: Session,
    client_id,
    weights: dict[str, Decimal],
) -> tuple[Portfolio, Instrument]:
    usdc = _instrument_usdc(db)
    portfolio = _bundle_portfolio(db, client_id)
    for asset_sym, weight in weights.items():
        instr = _instrument_for_asset(db, asset_sym)
        db.add(
            TargetAllocation(
                portfolio_id=portfolio.id,
                instrument_id=instr.id,
                target_weight=weight,
            )
        )
    db.flush()
    return portfolio, usdc


def test_allocation_execution_buffer_reduces_plan(db: Session, monkeypatch):
    monkeypatch.setenv("BUNDLE_ALLOC_EXECUTION_BUFFER_USDC", "1.0")
    monkeypatch.delenv("BUNDLE_ALLOC_EXECUTION_BUFFER_BPS", raising=False)

    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(
        db,
        pe.id,
        {"BTC": Decimal("0.6"), "ETH": Decimal("0.4")},
    )

    planned, allocatable, buffer, _remaining = plan_allocation_legs(
        db,
        allocations=db.query(TargetAllocation).filter(
            TargetAllocation.portfolio_id == portfolio.id
        ).all(),
        fund_amount=Decimal("1000"),
        batch_id="batch-buffer",
        normalize_asset_fn=lambda s: s,
    )

    assert buffer == Decimal("1.000000")
    assert allocatable == Decimal("999.000000")
    assert len(planned) == 2
    total_planned = sum(p.alloc_entry_amount for p in planned)
    assert total_planned <= allocatable
    assert planned[0].alloc_entry_amount == Decimal("599.400000")
    assert planned[1].alloc_entry_amount == Decimal("399.600000")


def test_allocation_parallel_quotes_created(db: Session, monkeypatch):
    monkeypatch.setenv("BUNDLE_EXECUTION_PROVIDER", "lifi_base")
    monkeypatch.setenv("BUNDLE_LIFI_SYNC_MOCK", "1")
    monkeypatch.setenv("LIFI_SWAPS_MOCK", "1")
    monkeypatch.setenv("BUNDLE_ALLOC_PARALLEL_QUOTES_ENABLED", "true")
    monkeypatch.setenv("BUNDLE_ALLOC_EXECUTION_BUFFER_USDC", "0")

    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("2000"), Decimal("1720"))
    portfolio, _ = _bundle_with_allocations(
        db,
        pe.id,
        {
            "BTC": Decimal("0.34"),
            "ETH": Decimal("0.33"),
            "LINK": Decimal("0.33"),
        },
    )
    db.commit()

    from services.portfolio_engine.bundle_execution.allocation_parallel import (
        run_allocation_legs_parallel,
    )

    orchestrator = BundleOrchestrator()
    with patch(
        "services.portfolio_engine.bundle_execution.allocation_parallel.run_allocation_legs_parallel",
        wraps=run_allocation_legs_parallel,
    ) as parallel_runner:
        result = orchestrator.invest_into_bundle(
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
            funding_asset="USDC",
            funding_amount=Decimal("900"),
        )
    db.commit()

    parallel_runner.assert_called_once()
    assert result.get("parallel_quotes") is True
    assert len(result["allocation_details"]) == 3


def test_allocation_residual_cash_stays_in_cash_leg(db: Session, monkeypatch):
    monkeypatch.setenv("BUNDLE_EXECUTION_PROVIDER", "lifi_base")
    monkeypatch.setenv("BUNDLE_LIFI_SYNC_MOCK", "1")
    monkeypatch.setenv("LIFI_SWAPS_MOCK", "1")
    monkeypatch.setenv("BUNDLE_ALLOC_EXECUTION_BUFFER_USDC", "1.5")

    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("500"), Decimal("430"))
    portfolio, _ = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.5"), "ETH": Decimal("0.5")},
    )
    db.commit()

    fund_amount = Decimal("100")
    orchestrator = BundleOrchestrator()
    result = orchestrator.invest_into_bundle(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        funding_asset="USDC",
        funding_amount=fund_amount,
    )
    db.commit()

    assert result["execution_buffer"] == 1.5
    cash_atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.position_type == POSITION_TYPE_CASH,
        )
        .first()
    )
    assert cash_atom is not None
    cash_qty = Decimal(str(cash_atom.quantity))
    assert cash_qty >= Decimal("1.5")
    assert cash_qty <= fund_amount


def test_allocation_real_consume_diff_from_plan(db: Session, monkeypatch):
    monkeypatch.setenv("LIFI_SWAPS_MOCK", "1")

    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, {"BTC": Decimal("1")})
    btc = _instrument_for_asset(db, "BTC")

    planned_in = Decimal("100")
    actual_in = Decimal("100.08")
    actual_out = Decimal("0.00155")

    swap = PersonWalletSwap(
        id=uuid.uuid4(),
        person_id=pe.person_id,
        from_asset="USDC",
        to_asset="CBBTC",
        from_chain="base",
        to_chain="base",
        amount_in=planned_in,
        estimated_receive=Decimal("0.00150"),
        slippage_bps=50,
        status=SwapSessionStatus.CONFIRMED.value,
        tx_hash="0xabc123",
        audit_log=[
            {
                "event": "swap_settled",
                "actual_amount_in": str(actual_in),
                "actual_receive_amount": str(actual_out),
            }
        ],
    )
    db.add(swap)
    db.flush()

    BundleOrchestrator._credit_cash_leg(
        db, portfolio.id, usdc.id, Decimal("200"), Decimal("172"),
    )

    settlement = resolve_allocation_leg_settlement_amounts(
        db,
        swap,
        planned_amount_in=planned_in,
        allow_mock_quote_amount=True,
    )
    assert settlement.amount_in == actual_in
    assert settlement.amount_out == actual_out

    apply_allocation_leg_atoms(
        db,
        portfolio_id=portfolio.id,
        entry_instrument_id=usdc.id,
        target_instrument_id=btc.id,
        entry_asset_consumed=settlement.amount_in,
        crypto_received=settlement.amount_out,
        cost_basis_eur=Decimal("86"),
        ledger={
            "person_id": str(pe.person_id),
            "planned_amount_in": str(planned_in),
            "planned_amount_out": str(swap.estimated_receive),
            "batch_id": "batch-real",
            "leg_id": "leg-real",
            "swap_id": str(swap.id),
            "from_asset": "USDC",
            "to_asset": "CBBTC",
            "target_asset_symbol": "CBBTC",
            "entry_asset_symbol": "USDC",
        },
    )
    db.flush()

    cash_atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.position_type == POSITION_TYPE_CASH,
        )
        .first()
    )
    spot_atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.position_type == POSITION_TYPE_SPOT,
        )
        .first()
    )
    assert Decimal(str(cash_atom.quantity)) == Decimal("200") - actual_in
    assert Decimal(str(spot_atom.quantity)) == actual_out


def test_allocation_leg_failed_others_succeed(db: Session, monkeypatch):
    monkeypatch.setenv("BUNDLE_EXECUTION_PROVIDER", "lifi_base")
    monkeypatch.setenv("BUNDLE_ALLOC_EXECUTION_BUFFER_USDC", "0")

    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("500"), Decimal("430"))
    portfolio, _ = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.5"), "ETH": Decimal("0.5")},
    )
    db.commit()

    calls: list[str] = []

    def _fake_run_leg(self, db, *, target_asset, **kwargs):
        calls.append(target_asset)
        if target_asset == "CBBTC":
            raise RuntimeError("quote_failed")
        return {
            "status": "pending",
            "record": {
                "asset": target_asset,
                "status": "pending",
                "swap_id": str(uuid.uuid4()),
            },
        }

    orchestrator = BundleOrchestrator()
    with patch.object(BundleOrchestrator, "_run_allocation_leg", _fake_run_leg):
        result = orchestrator.invest_into_bundle(
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
            funding_asset="USDC",
            funding_amount=Decimal("200"),
        )

    assert len(calls) == 2
    assert result["legs_failed"] == 1
    assert result["legs_pending"] == 1
    assert result["status"] in ("partial_pending", "partial", "pending_signature")


def test_allocation_partial_no_micro_retry(db: Session, monkeypatch):
    monkeypatch.setenv("BUNDLE_ALLOC_EXECUTION_BUFFER_USDC", "1.0")

    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    portfolio, _ = _bundle_with_allocations(db, pe.id, {"BTC": Decimal("1")})
    batch_id = "batch-no-retry"

    BundleOrchestrator._credit_cash_leg(
        db, portfolio.id, usdc.id, Decimal("100"), Decimal("86"),
    )
    apply_allocation_leg_atoms(
        db,
        portfolio_id=portfolio.id,
        entry_instrument_id=usdc.id,
        target_instrument_id=_instrument_for_asset(db, "BTC").id,
        entry_asset_consumed=Decimal("50"),
        crypto_received=Decimal("0.001"),
        cost_basis_eur=Decimal("43"),
    )
    db.flush()

    cash_before = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.position_type == POSITION_TYPE_CASH,
        )
        .first()
    )
    qty_before = Decimal(str(cash_before.quantity))

    orchestrator = BundleOrchestrator()
    finalize = orchestrator.finalize_lifi_batch(
        db,
        client_id=pe.id,
        portfolio_id=portfolio.id,
        batch_id=batch_id,
        entry_instrument_id=usdc.id,
        planned_entry_total=Decimal("100"),
        entry_consumed=Decimal("50"),
    )

    cash_after = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.position_type == POSITION_TYPE_CASH,
        )
        .first()
    )
    assert Decimal(str(cash_after.quantity)) == qty_before
    assert finalize["cash_leg_credited"] == 0.0
    assert finalize["recoverable_cash_in_bundle"] >= float(qty_before)


def test_bundle_recoverable_after_all_legs_failed(db: Session, monkeypatch):
    monkeypatch.setenv("BUNDLE_EXECUTION_PROVIDER", "lifi_base")
    monkeypatch.setenv("BUNDLE_ALLOC_EXECUTION_BUFFER_USDC", "0")

    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("500"), Decimal("430"))
    portfolio, _ = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.6"), "ETH": Decimal("0.4")},
    )
    db.commit()

    def _always_fail(self, db, **kwargs):
        raise RuntimeError("all_legs_failed")

    fund_amount = Decimal("250")
    orchestrator = BundleOrchestrator()
    with patch.object(BundleOrchestrator, "_run_allocation_leg", _always_fail):
        result = orchestrator.invest_into_bundle(
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
            funding_asset="USDC",
            funding_amount=fund_amount,
        )
    db.commit()

    assert result["status"] == "failed"
    assert result["legs_failed"] == 2
    cash_atom = (
        db.query(PositionAtom)
        .filter(
            PositionAtom.portfolio_id == portfolio.id,
            PositionAtom.position_type == POSITION_TYPE_CASH,
        )
        .first()
    )
    assert cash_atom is not None
    assert Decimal(str(cash_atom.quantity)) == fund_amount


def test_compute_execution_buffer_bps(monkeypatch):
    monkeypatch.setenv("BUNDLE_ALLOC_EXECUTION_BUFFER_USDC", "1.0")
    monkeypatch.setenv("BUNDLE_ALLOC_EXECUTION_BUFFER_BPS", "100")

    buffer = compute_execution_buffer(Decimal("1000"))
    assert buffer == Decimal("10.000000")

    allocatable, buf = compute_allocatable_amount(Decimal("1000"))
    assert buf == Decimal("10.000000")
    assert allocatable == Decimal("990.000000")
