"""Tests Phase 5A.5 — validation allocation engine."""
from __future__ import annotations

import json
import logging
import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap
from services.portfolio_engine.allocations.models import TargetAllocation
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundle_execution.allocation_config import compute_allocatable_amount
from services.portfolio_engine.bundle_execution.allocation_observability import log_allocation_event
from services.portfolio_engine.bundle_execution.allocation_parallel import (
    run_allocation_legs_parallel,
    run_allocation_legs_sequential,
)
from services.portfolio_engine.bundle_execution.allocation_planner import plan_allocation_legs
from services.portfolio_engine.bundle_execution.allocation_smoke import (
    run_smoke_bundle_allocation_phase5a,
)
from services.portfolio_engine.bundle_execution.pe_settlement import apply_allocation_leg_atoms
from services.portfolio_engine.bundle_ledger.models import BundleLedgerEntry
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.instruments.models import Instrument

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


def _bundle_with_allocations(db: Session, client_id, weights: dict[str, Decimal]):
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


def test_parallel_quotes_fallback_to_sequential_on_error(db: Session, monkeypatch):
    monkeypatch.setenv("BUNDLE_EXECUTION_PROVIDER", "lifi_base")
    monkeypatch.setenv("BUNDLE_ALLOC_EXECUTION_BUFFER_USDC", "0")

    pe = make_linked_client(db)
    usdc = _instrument_usdc(db)
    direct_pf = ensure_direct_portfolio(db, pe.id)
    sync_direct_atom(db, direct_pf.id, usdc.id, Decimal("500"), Decimal("430"))
    portfolio, _ = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.5"), "ETH": Decimal("0.5")},
    )

    orchestrator = BundleOrchestrator()
    planned, allocatable, _, _ = plan_allocation_legs(
        db,
        allocations=db.query(TargetAllocation).filter(
            TargetAllocation.portfolio_id == portfolio.id
        ).all(),
        fund_amount=Decimal("200"),
        batch_id="batch-fallback",
        normalize_asset_fn=orchestrator._normalize_asset_symbol,
    )
    actor = ActorContext(actor_type="system", actor_id="test")

    sequential_calls: list[str] = []
    real_sequential = run_allocation_legs_sequential

    def _counting_sequential(*args, **kwargs):
        sequential_calls.append("called")
        return real_sequential(*args, **kwargs)

    with patch(
        "services.portfolio_engine.bundle_execution.allocation_parallel.run_allocation_legs_sequential",
        side_effect=_counting_sequential,
    ):
        with patch(
            "services.portfolio_engine.bundle_execution.allocation_parallel.ThreadPoolExecutor",
            side_effect=RuntimeError("parallel_pool_failed"),
        ):
            run_allocation_legs_parallel(
                orchestrator,
                db,
                client_id=pe.id,
                portfolio_id=portfolio.id,
                entry_asset="USDC",
                entry_instrument_id=usdc.id,
                batch_id="batch-fallback",
                actor=actor,
                planned_legs=planned,
                initial_cash_available=allocatable,
            )

    assert sequential_calls == ["called"]


def test_parallel_quotes_preserve_target_order(db: Session, monkeypatch):
    monkeypatch.setenv("BUNDLE_ALLOC_EXECUTION_BUFFER_USDC", "0")

    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(
        db,
        pe.id,
        {"BTC": Decimal("0.34"), "ETH": Decimal("0.33"), "LINK": Decimal("0.33")},
    )
    orchestrator = BundleOrchestrator()
    planned, allocatable, _, _ = plan_allocation_legs(
        db,
        allocations=db.query(TargetAllocation).filter(
            TargetAllocation.portfolio_id == portfolio.id
        ).all(),
        fund_amount=Decimal("900"),
        batch_id="batch-order",
        normalize_asset_fn=orchestrator._normalize_asset_symbol,
    )
    expected_order = [p.lifi_target for p in planned]

    def _fake_job(job):
        return job.index, {
            "status": "pending",
            "record": {"asset": job.planned.lifi_target, "status": "pending"},
        }

    with patch(
        "services.portfolio_engine.bundle_execution.allocation_parallel._run_parallel_leg_job",
        side_effect=_fake_job,
    ):
        alloc_results, _ = run_allocation_legs_parallel(
            orchestrator,
            db,
            client_id=pe.id,
            portfolio_id=portfolio.id,
            entry_asset="USDC",
            entry_instrument_id=usdc.id,
            batch_id="batch-order",
            actor=ActorContext(actor_type="system", actor_id="test"),
            planned_legs=planned,
            initial_cash_available=allocatable,
        )

    assert [r["asset"] for r in alloc_results] == expected_order


def test_buffer_not_applied_when_fund_too_small(monkeypatch):
    monkeypatch.setenv("BUNDLE_ALLOC_EXECUTION_BUFFER_USDC", "1.0")

    allocatable, buffer = compute_allocatable_amount(Decimal("0.50"))
    assert buffer == Decimal("0.500000")
    assert allocatable == Decimal("0")


def test_residual_cash_logged(caplog):
    caplog.set_level(logging.INFO)
    log_allocation_event(
        "residual_cash",
        person_id="p1",
        portfolio_id="pf1",
        batch_id="b1",
        fund_amount=1000.0,
        buffer_amount=1.0,
        allocatable_amount=999.0,
        legs_count=2,
        parallel_enabled=False,
        residual_cash=1.05,
    )
    assert any("bundle_allocation.residual_cash" in r.message for r in caplog.records)
    payload_line = next(r.message for r in caplog.records if "residual_cash" in r.message)
    assert "residual_cash" in payload_line
    assert "1.05" in payload_line


def test_real_settlement_metadata_contains_planned_and_actual(db: Session):
    pe = make_linked_client(db)
    portfolio, usdc = _bundle_with_allocations(db, pe.id, {"BTC": Decimal("1")})
    btc = _instrument_for_asset(db, "BTC")

    BundleOrchestrator._credit_cash_leg(
        db, portfolio.id, usdc.id, Decimal("200"), Decimal("172"),
    )
    apply_allocation_leg_atoms(
        db,
        portfolio_id=portfolio.id,
        entry_instrument_id=usdc.id,
        target_instrument_id=btc.id,
        entry_asset_consumed=Decimal("100.08"),
        crypto_received=Decimal("0.00155"),
        cost_basis_eur=Decimal("86"),
        ledger={
            "person_id": str(pe.person_id),
            "planned_amount_in": "100",
            "planned_amount_out": "0.00150",
            "batch_id": "batch-meta",
            "leg_id": "leg-meta",
            "swap_id": str(uuid.uuid4()),
            "from_asset": "USDC",
            "to_asset": "CBBTC",
            "target_asset_symbol": "CBBTC",
            "entry_asset_symbol": "USDC",
        },
    )
    db.flush()

    row = (
        db.query(BundleLedgerEntry)
        .filter(
            BundleLedgerEntry.bundle_portfolio_id == portfolio.id,
            BundleLedgerEntry.event_type == "BUNDLE_ALLOCATION_BUY",
        )
        .first()
    )
    assert row is not None
    meta = row.metadata_ if isinstance(row.metadata_, dict) else {}
    assert meta.get("planned_entry_consumed") == 100.0
    assert meta.get("entry_consumed") == 100.08
    assert meta.get("planned_crypto_received") == pytest.approx(0.0015)


def test_smoke_read_only_passes(db: Session, monkeypatch):
    monkeypatch.setenv("BUNDLE_ALLOC_EXECUTION_BUFFER_USDC", "1.0")
    monkeypatch.setenv("BUNDLE_ALLOC_PARALLEL_QUOTES_ENABLED", "false")

    pe = make_linked_client(db)
    portfolio, _ = _bundle_with_allocations(
        db, pe.id, {"BTC": Decimal("0.6"), "ETH": Decimal("0.4")},
    )

    result = run_smoke_bundle_allocation_phase5a(
        db,
        person_id=pe.person_id,
        portfolio_id=portfolio.id,
        fund_amount=Decimal("1000"),
        execute_mock=False,
    )
    assert result["status"] == "PASS"
    assert result["buffer_amount"] == 1.0
    assert result["parallel_enabled"] is False
