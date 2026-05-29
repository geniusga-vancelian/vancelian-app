"""Smoke validation Phase 5A.5 — allocation engine."""
from __future__ import annotations

import os
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.allocations.models import TargetAllocation
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.bundle_execution.allocation_config import (
    bundle_alloc_parallel_quotes_enabled,
)
from services.portfolio_engine.bundle_execution.allocation_planner import plan_allocation_legs
from services.portfolio_engine.bundle_execution.bundle_funding import (
    resolve_bundle_cash_leg_available,
)
from services.portfolio_engine.bundle_ledger.models import BundleLedgerEntry
from services.portfolio_engine.bundles.orchestrator import BundleOrchestrator
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.direct_overlay import ensure_direct_portfolio, sync_direct_atom
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.products.models import ProductDefinition


def _mock_execution_allowed() -> bool:
    raw_sync = (os.environ.get("BUNDLE_LIFI_SYNC_MOCK") or "").strip().lower()
    raw_lifi = (os.environ.get("LIFI_SWAPS_MOCK") or "").strip().lower()
    return raw_sync in {"1", "true", "yes", "on"} and raw_lifi in {"1", "true", "yes", "on"}


def run_smoke_bundle_allocation_phase5a(
    db: Session,
    *,
    person_id: UUID,
    portfolio_id: UUID,
    fund_amount: Decimal | None = None,
    execute_mock: bool = False,
) -> dict[str, Any]:
    """Smoke read-only (+ invest mock contrôlé si autorisé)."""
    checks: list[dict[str, Any]] = []
    parallel_enabled = bundle_alloc_parallel_quotes_enabled()

    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.portfolio_type == "bundle_portfolio",
        )
        .first()
    )
    if portfolio is None:
        return {"status": "FAIL", "reason": "portfolio_not_found", "checks": checks}

    client = db.query(Client).filter(Client.id == portfolio.client_id).first()
    if client is None or client.person_id != person_id:
        return {"status": "FAIL", "reason": "person_portfolio_mismatch", "checks": checks}

    product = (
        db.query(ProductDefinition)
        .filter(ProductDefinition.id == portfolio.origin_product_id)
        .first()
    )
    meta = product.metadata_ if product and isinstance(product.metadata_, dict) else {}
    entry_asset = str(meta.get("entry_asset_default") or "USDC").upper()

    if fund_amount is None:
        fund_amount = Decimal("1000")

    allocations = (
        db.query(TargetAllocation)
        .filter(TargetAllocation.portfolio_id == portfolio_id)
        .order_by(TargetAllocation.rebalance_priority)
        .all()
    )
    if not allocations:
        return {"status": "FAIL", "reason": "no_target_allocations", "checks": checks}

    orchestrator = BundleOrchestrator()
    entry_instr: Instrument | None = None
    asset_row = db.query(Asset).filter(Asset.symbol == entry_asset).first()
    if asset_row is not None:
        entry_instr = (
            db.query(Instrument)
            .filter(Instrument.asset_id == asset_row.id, Instrument.instrument_type == "spot")
            .first()
        )

    planned, allocatable, buffer, plan_remaining = plan_allocation_legs(
        db,
        allocations=allocations,
        fund_amount=fund_amount,
        batch_id="smoke-plan",
        normalize_asset_fn=orchestrator._normalize_asset_symbol,
    )
    total_planned = sum(p.alloc_entry_amount for p in planned)
    expected_residual_min = buffer + plan_remaining

    checks.append({
        "name": "plan_post_buffer",
        "ok": total_planned <= allocatable and allocatable + buffer <= fund_amount + Decimal("0.000001"),
        "fund_amount": float(fund_amount),
        "buffer_amount": float(buffer),
        "allocatable_amount": float(allocatable),
        "legs_count": len(planned),
    })
    checks.append({
        "name": "legs_sum_within_allocatable",
        "ok": total_planned <= allocatable,
        "total_planned": float(total_planned),
        "allocatable_amount": float(allocatable),
    })
    checks.append({
        "name": "expected_residual_cash",
        "ok": expected_residual_min >= buffer,
        "expected_residual_min": float(expected_residual_min),
        "buffer_amount": float(buffer),
    })
    checks.append({
        "name": "parallel_flag_state",
        "ok": True,
        "parallel_enabled": parallel_enabled,
        "provider": orchestrator._execution.provider_name,
    })

    invest_result: dict[str, Any] | None = None
    if execute_mock:
        if not _mock_execution_allowed():
            checks.append({
                "name": "mock_execute",
                "ok": False,
                "error": "mock_not_allowed_set_BUNDLE_LIFI_SYNC_MOCK_and_LIFI_SWAPS_MOCK",
            })
        else:
            if entry_instr is not None:
                direct_pf = ensure_direct_portfolio(db, client.id)
                sync_direct_atom(
                    db,
                    direct_pf.id,
                    entry_instr.id,
                    fund_amount + Decimal("100"),
                    fund_amount * Decimal("0.86"),
                )
            try:
                invest_result = orchestrator.invest_into_bundle(
                    db,
                    client_id=client.id,
                    portfolio_id=portfolio_id,
                    funding_asset=entry_asset,
                    funding_amount=fund_amount,
                )
                db.commit()
                used_parallel = bool(invest_result.get("parallel_quotes"))
                checks.append({
                    "name": "mock_invest_execution",
                    "ok": invest_result.get("status") not in (None, "failed"),
                    "invest_status": invest_result.get("status"),
                })
                checks.append({
                    "name": "parallel_vs_sequential_mode",
                    "ok": (
                        (parallel_enabled and used_parallel and len(planned) > 1)
                        or (not parallel_enabled and not used_parallel)
                        or len(planned) <= 1
                    ),
                    "parallel_enabled": parallel_enabled,
                    "parallel_quotes_used": used_parallel,
                })
                if entry_instr is not None:
                    cash_available = resolve_bundle_cash_leg_available(
                        db,
                        portfolio_id=portfolio_id,
                        entry_instrument_id=entry_instr.id,
                    )
                    checks.append({
                        "name": "cash_leg_residual_after_invest",
                        "ok": cash_available >= buffer,
                        "cash_leg_quantity": float(cash_available),
                        "buffer_amount": float(buffer),
                    })
            except Exception as exc:
                checks.append({
                    "name": "mock_invest_execution",
                    "ok": False,
                    "error": str(exc),
                })

    ledger_rows = (
        db.query(BundleLedgerEntry)
        .filter(
            BundleLedgerEntry.bundle_portfolio_id == portfolio_id,
            BundleLedgerEntry.person_id == person_id,
            BundleLedgerEntry.event_type == "BUNDLE_ALLOCATION_BUY",
        )
        .order_by(BundleLedgerEntry.created_at.desc())
        .limit(5)
        .all()
    )
    settlement_ok = True
    settlement_samples: list[dict[str, Any]] = []
    for row in ledger_rows:
        meta_row = row.metadata_ if isinstance(row.metadata_, dict) else {}
        has_planned = "planned_entry_consumed" in meta_row
        has_actual = "entry_consumed" in meta_row
        sample_ok = has_planned and has_actual
        settlement_ok = settlement_ok and sample_ok
        settlement_samples.append({
            "entry_id": str(row.id),
            "planned_entry_consumed": meta_row.get("planned_entry_consumed"),
            "actual_entry_consumed": meta_row.get("entry_consumed"),
            "ok": sample_ok,
        })

    if ledger_rows:
        checks.append({
            "name": "settlement_metadata_planned_vs_actual",
            "ok": settlement_ok,
            "samples": settlement_samples,
        })
    else:
        checks.append({
            "name": "settlement_metadata_planned_vs_actual",
            "ok": True,
            "skipped": "no_allocation_ledger_entries_yet",
        })

    recoverable_ok = True
    if invest_result and invest_result.get("status") == "failed":
        if entry_instr is not None:
            cash_available = resolve_bundle_cash_leg_available(
                db,
                portfolio_id=portfolio_id,
                entry_instrument_id=entry_instr.id,
            )
            recoverable_ok = cash_available >= fund_amount - Decimal("0.000001")
        checks.append({
            "name": "recoverable_after_all_legs_failed",
            "ok": recoverable_ok,
            "invest_status": invest_result.get("status"),
        })

    all_ok = all(c.get("ok") for c in checks)
    return {
        "status": "PASS" if all_ok else "FAIL",
        "person_id": str(person_id),
        "portfolio_id": str(portfolio_id),
        "parallel_enabled": parallel_enabled,
        "fund_amount": float(fund_amount),
        "buffer_amount": float(buffer),
        "allocatable_amount": float(allocatable),
        "legs_count": len(planned),
        "checks": checks,
        "invest_result": invest_result,
    }
