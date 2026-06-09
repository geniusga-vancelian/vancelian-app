"""Audit read-only — drift snapshot pilote (vue gérant de portefeuille)."""
from __future__ import annotations

import json
from decimal import Decimal
from datetime import datetime, timezone
from typing import Any

from database import SessionLocal
from services.portfolio_engine.bundles.drift_engine import compute_bundle_drift_snapshot

CLIENT_ID = "080358a8-4519-4acf-b5da-25485446c967"
PORTFOLIOS = (
    ("ab4ae920-f3e8-481b-8f82-a41a81d5779d", "Crypto Majors"),
    ("daea3720-e58e-410f-a796-3bbd541ac608", "Two Crypto Kings"),
)

EXPECTED = {
    "Crypto Majors": {
        "cash_usdc_approx": Decimal("29.87"),
        "cash_tolerance_usdc": Decimal("0.5"),
        "assets": {
            "BTC": {"allowed_hints": frozenset({"sell", "hold"})},
            "ETH": {"allowed_hints": frozenset({"buy"})},
            "LINK": {"allowed_hints": frozenset({"hold", "buy", "sell"})},
            "AAVE": {"allowed_hints": frozenset({"hold", "buy", "sell"})},
            "UNI": {"allowed_hints": frozenset({"buy", "hold"})},
        },
        "expect_sell_plan_empty": True,
        "expect_buy_assets": frozenset({"ETH", "UNI"}),
    },
    "Two Crypto Kings": {
        "cash_usdc_approx": Decimal("30.90"),
        "cash_tolerance_usdc": Decimal("0.5"),
        "assets": {
            # Sur base investie, BTC peut être légèrement surpondéré (cash à part).
            "BTC": {"allowed_hints": frozenset({"sell", "hold"})},
            "ETH": {"allowed_hints": frozenset({"buy"})},
        },
        "expect_sell_plan_empty": True,
        "expect_buy_assets": frozenset({"ETH"}),
    },
}


def _pct_from_bps(bps: int) -> float:
    return round(bps / 100.0, 2)


def _portfolio_manager_view(snap: dict[str, Any]) -> dict[str, Any]:
    rows = []
    for row in snap.get("target_assets") or []:
        delta = Decimal(str(row.get("delta_value_usdc") or "0"))
        rows.append({
            "asset": row.get("asset"),
            "target_weight_pct": _pct_from_bps(int(row.get("target_weight_bps") or 0)),
            "current_weight_pct": _pct_from_bps(int(row.get("current_weight_bps") or 0)),
            "drift_pct": _pct_from_bps(int(row.get("drift_bps") or 0)),
            "current_value_usdc": row.get("current_value_usdc"),
            "target_value_usdc": row.get("target_value_usdc"),
            "delta_usdc": format(delta.quantize(Decimal("0.01")), "f"),
            "action_hint": row.get("action_hint"),
        })
    rows.sort(key=lambda r: str(r.get("asset") or ""))

    non_target = []
    for row in snap.get("non_target_assets") or []:
        non_target.append({
            "asset": row.get("asset"),
            "current_weight_pct": _pct_from_bps(int(row.get("current_weight_bps") or 0)),
            "current_value_usdc": row.get("current_value_usdc"),
            "action_hint": row.get("action_hint"),
        })

    return {
        "portfolio_id": snap.get("portfolio_id"),
        "weight_basis": snap.get("weight_basis"),
        "invested_value_usdc": snap.get("invested_value_usdc"),
        "portfolio_value_usdc": snap.get("portfolio_value_usdc"),
        "cash_leg_usdc": snap.get("cash_value_usdc"),
        "entry_asset": snap.get("entry_asset"),
        "snapshot_hash": snap.get("snapshot_hash"),
        "computed_at": snap.get("computed_at"),
        "price_source": snap.get("price_source"),
        "target_assets": rows,
        "non_target_assets": non_target,
        "warnings": snap.get("warnings") or [],
    }


def _validate_rebalance_plan(name: str, plan: dict[str, Any]) -> list[str]:
    spec = EXPECTED.get(name) or {}
    notes: list[str] = []

    if spec.get("expect_sell_plan_empty") and plan.get("sell_plan"):
        notes.append(f"plan_sell_unexpected:{plan.get('sell_plan')}")

    expected_buys = spec.get("expect_buy_assets")
    if expected_buys is not None:
        actual_buys = {r.get("asset") for r in plan.get("buy_plan") or []}
        if actual_buys != expected_buys:
            notes.append(
                f"plan_buy_mismatch: got {sorted(actual_buys)} expected {sorted(expected_buys)}"
            )
        else:
            notes.append(f"plan_buy_ok:{sorted(actual_buys)}")

    if spec.get("expect_sell_plan_empty") and not plan.get("sell_plan"):
        notes.append("plan_sell_empty_ok")

    return notes


def _validate_portfolio(name: str, view: dict[str, Any]) -> dict[str, Any]:
    spec = EXPECTED.get(name)
    if not spec:
        return {"coherent": None, "notes": ["no_expected_spec"]}

    notes: list[str] = []
    coherent = True

    cash = Decimal(str(view.get("cash_leg_usdc") or "0"))
    expected_cash = spec["cash_usdc_approx"]
    tol = spec["cash_tolerance_usdc"]
    if abs(cash - expected_cash) > tol:
        coherent = False
        notes.append(
            f"cash_mismatch: got {cash} expected ~{expected_cash} (±{tol})"
        )
    else:
        notes.append(f"cash_ok: {cash} USDC")

    by_asset = {r["asset"]: r for r in view.get("target_assets") or []}
    for asset, rules in spec["assets"].items():
        row = by_asset.get(asset)
        if row is None:
            coherent = False
            notes.append(f"missing_asset:{asset}")
            continue
        hint = str(row.get("action_hint") or "")
        allowed = rules["allowed_hints"]
        if hint not in allowed:
            coherent = False
            notes.append(
                f"action_mismatch:{asset} got {hint} expected one of {sorted(allowed)} "
                f"(delta_usdc={row.get('delta_usdc')})"
            )
        else:
            notes.append(
                f"action_ok:{asset} {hint} delta_usdc={row.get('delta_usdc')}"
            )

    eth = by_asset.get("ETH")
    if name == "Crypto Majors" and eth:
        eth_delta = Decimal(str(eth.get("delta_usdc") or "0"))
        if eth_delta <= 0:
            coherent = False
            notes.append(f"eth_buy_expected_but_delta={eth_delta}")

    return {"coherent": coherent, "notes": notes}


def main() -> None:
    from uuid import UUID

    from services.portfolio_engine.bundles.rebalance_planner import (
        plan_bundle_rebalance_from_drift,
    )

    db = SessionLocal()
    try:
        portfolio_reports: list[dict[str, Any]] = []
        all_coherent = True

        for portfolio_id, name in PORTFOLIOS:
            snap = compute_bundle_drift_snapshot(
                db,
                client_id=UUID(CLIENT_ID),
                portfolio_id=UUID(portfolio_id),
            )
            view = _portfolio_manager_view(snap)
            rebalance_plan = plan_bundle_rebalance_from_drift(snap)
            validation = _validate_portfolio(name, view)
            plan_notes = _validate_rebalance_plan(name, rebalance_plan)
            validation["notes"].extend(plan_notes)
            if any(
                n.startswith("plan_") and ("mismatch" in n or "unexpected" in n)
                for n in plan_notes
            ):
                validation["coherent"] = False
            if validation.get("coherent") is False:
                all_coherent = False

            portfolio_reports.append({
                "portfolio_name": name,
                "portfolio_manager_view": view,
                "rebalance_plan": rebalance_plan,
                "validation": validation,
                "drift_snapshot_raw": snap,
            })

        out = {
            "phase": "bundle_drift_engine_audit",
            "audit_iso": datetime.now(timezone.utc).isoformat(),
            "read_only": True,
            "verdict": "GO_PR2" if all_coherent else "REVIEW_PRICING_OR_WEIGHTS",
            "portfolios": portfolio_reports,
        }
        print(json.dumps(out, indent=2, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
