"""Bundle Rebalancing Planner — V3 PR-2.

Drift sur actifs investis ; cash leg = source de financement séparée.
Produit sell_plan puis buy_plan, déterministe et idempotent.
"""
from __future__ import annotations

import hashlib
import json
import os
from decimal import Decimal, ROUND_DOWN
from typing import Any

from services.portfolio_engine.bundles.drift_engine import WEIGHT_BASIS_INVESTED_ASSETS

MIN_REBALANCE_DELTA_USDC = Decimal(
    os.getenv("MIN_REBALANCE_DELTA_USDC", "1"),
)
MIN_DRIFT_BPS = int(os.getenv("MIN_DRIFT_BPS", "200"))


def _dec(value: Decimal | str | float) -> Decimal:
    return Decimal(str(value))


def _dec_str(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.000001"), rounding=ROUND_DOWN), "f")


def _plan_hash(
    *,
    snapshot_hash: str,
    sell_plan: list[dict[str, Any]],
    buy_plan: list[dict[str, Any]],
) -> str:
    body = {
        "snapshot_hash": snapshot_hash,
        "sell_plan": sell_plan,
        "buy_plan": buy_plan,
    }
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def plan_bundle_rebalance_from_drift(drift_snapshot: dict[str, Any]) -> dict[str, Any]:
    """Construit sell_plan / buy_plan depuis un BundleDriftSnapshot (read-only)."""
    warnings: list[str] = []
    weight_basis = str(drift_snapshot.get("weight_basis") or WEIGHT_BASIS_INVESTED_ASSETS)
    invested = _dec(drift_snapshot.get("invested_value_usdc") or "0")
    cash = _dec(drift_snapshot.get("cash_value_usdc") or "0")
    entry_asset = str(drift_snapshot.get("entry_asset") or "USDC")
    snapshot_hash = str(drift_snapshot.get("snapshot_hash") or "")

    target_rows = list(drift_snapshot.get("target_assets") or [])
    non_target_rows = list(drift_snapshot.get("non_target_assets") or [])

    sell_candidates: list[dict[str, Any]] = []
    buy_candidates: list[dict[str, Any]] = []

    for row in target_rows:
        delta = _dec(row.get("delta_value_usdc") or "0")
        drift_bps = int(row.get("drift_bps") or 0)
        target_bps = int(row.get("target_weight_bps") or 0)
        asset = str(row.get("asset") or "")
        instrument_id = str(row.get("instrument_id") or "")

        if invested <= 0 and target_bps > 0 and cash > 0:
            buy_candidates.append({
                "asset": asset,
                "instrument_id": instrument_id,
                "delta_usdc": _dec_str(delta),
                "drift_bps": drift_bps,
                "target_weight_bps": target_bps,
                "ideal_amount_usdc": Decimal("0"),
                "deploy_from_cash": True,
            })
            continue

        if delta < 0 and abs(delta) >= MIN_REBALANCE_DELTA_USDC and abs(drift_bps) >= MIN_DRIFT_BPS:
            sell_candidates.append({
                "asset": asset,
                "instrument_id": instrument_id,
                "delta_usdc": _dec_str(delta),
                "drift_bps": drift_bps,
                "ideal_amount_usdc": abs(delta),
            })
        elif delta > 0 and delta >= MIN_REBALANCE_DELTA_USDC and abs(drift_bps) >= MIN_DRIFT_BPS:
            buy_candidates.append({
                "asset": asset,
                "instrument_id": instrument_id,
                "delta_usdc": _dec_str(delta),
                "drift_bps": drift_bps,
                "ideal_amount_usdc": delta,
                "deploy_from_cash": False,
            })

    for row in non_target_rows:
        value = _dec(row.get("current_value_usdc") or "0")
        if value >= MIN_REBALANCE_DELTA_USDC:
            sell_candidates.append({
                "asset": str(row.get("asset") or ""),
                "instrument_id": str(row.get("instrument_id") or ""),
                "delta_usdc": _dec_str(-value),
                "drift_bps": 0,
                "ideal_amount_usdc": value,
                "non_target": True,
            })

    sell_candidates.sort(key=lambda r: _dec(r["ideal_amount_usdc"]), reverse=True)
    buy_candidates.sort(key=lambda r: (
        int(r.get("target_weight_bps") or 0) if r.get("deploy_from_cash") else 0,
        _dec(r["ideal_amount_usdc"]),
    ), reverse=True)

    available_cash = cash
    buy_plan: list[dict[str, Any]] = []
    sell_plan: list[dict[str, Any]] = []

    if invested <= 0 and cash > 0 and buy_candidates:
        total_target_bps = sum(int(r.get("target_weight_bps") or 0) for r in buy_candidates)
        if total_target_bps <= 0:
            warnings.append("cash_deploy_no_target_weights")
        else:
            remaining = available_cash
            for idx, cand in enumerate(buy_candidates):
                if idx == len(buy_candidates) - 1:
                    amount = remaining
                else:
                    amount = (
                        available_cash
                        * Decimal(int(cand["target_weight_bps"]))
                        / Decimal(total_target_bps)
                    ).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
                    remaining -= amount
                if amount < MIN_REBALANCE_DELTA_USDC:
                    continue
                buy_plan.append({
                    "asset": cand["asset"],
                    "instrument_id": cand["instrument_id"],
                    "amount_usdc": _dec_str(amount),
                    "delta_usdc": cand["delta_usdc"],
                    "action": "buy",
                    "funded_by": "cash_leg",
                })
    else:
        total_buy_need = sum(_dec(c["ideal_amount_usdc"]) for c in buy_candidates)

        if buy_candidates and total_buy_need <= available_cash:
            remaining_cash = available_cash
            for idx, cand in enumerate(buy_candidates):
                ideal = _dec(cand["ideal_amount_usdc"])
                if idx == len(buy_candidates) - 1:
                    amount = min(ideal, remaining_cash)
                else:
                    share = (
                        available_cash * ideal / total_buy_need
                        if total_buy_need > 0
                        else Decimal("0")
                    ).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
                    amount = min(ideal, share)
                    remaining_cash -= amount
                if amount < MIN_REBALANCE_DELTA_USDC:
                    continue
                buy_plan.append({
                    "asset": cand["asset"],
                    "instrument_id": cand["instrument_id"],
                    "amount_usdc": _dec_str(amount),
                    "delta_usdc": cand["delta_usdc"],
                    "action": "buy",
                    "funded_by": "cash_leg",
                })
        elif buy_candidates and total_buy_need > available_cash:
            funding_gap = total_buy_need - available_cash
            if sell_candidates:
                funding_left = funding_gap
                for cand in sell_candidates:
                    if funding_left <= 0:
                        break
                    sell_amount = min(_dec(cand["ideal_amount_usdc"]), funding_left)
                    if sell_amount < MIN_REBALANCE_DELTA_USDC:
                        continue
                    sell_plan.append({
                        "asset": cand["asset"],
                        "instrument_id": cand["instrument_id"],
                        "amount_usdc": _dec_str(sell_amount),
                        "delta_usdc": cand["delta_usdc"],
                        "action": "sell",
                    })
                    funding_left -= sell_amount
                if funding_left > MIN_REBALANCE_DELTA_USDC:
                    warnings.append("insufficient_overweight_to_fund_buys")

            total_funding = available_cash + sum(
                _dec(s["amount_usdc"]) for s in sell_plan
            )
            scale = (
                min(Decimal("1"), total_funding / total_buy_need)
                if total_buy_need > 0
                else Decimal("0")
            )
            for cand in buy_candidates:
                amount = (_dec(cand["ideal_amount_usdc"]) * scale).quantize(
                    Decimal("0.000001"), rounding=ROUND_DOWN,
                )
                if amount < MIN_REBALANCE_DELTA_USDC:
                    continue
                funded_by = (
                    "cash_leg_and_sell_proceeds"
                    if sell_plan
                    else "cash_leg"
                )
                buy_plan.append({
                    "asset": cand["asset"],
                    "instrument_id": cand["instrument_id"],
                    "amount_usdc": _dec_str(amount),
                    "delta_usdc": cand["delta_usdc"],
                    "action": "buy",
                    "funded_by": funded_by,
                })

    status = "no_action" if not sell_plan and not buy_plan else "ok"
    plan_hash = _plan_hash(
        snapshot_hash=snapshot_hash,
        sell_plan=sell_plan,
        buy_plan=buy_plan,
    )

    return {
        "weight_basis": weight_basis,
        "cash_funding_source": "separate",
        "entry_asset": entry_asset,
        "invested_value_usdc": _dec_str(invested),
        "available_cash_usdc": _dec_str(available_cash),
        "min_rebalance_delta_usdc": _dec_str(MIN_REBALANCE_DELTA_USDC),
        "min_drift_bps": MIN_DRIFT_BPS,
        "sell_plan": sell_plan,
        "buy_plan": buy_plan,
        "plan_hash": plan_hash,
        "snapshot_hash": snapshot_hash,
        "status": status,
        "warnings": warnings,
    }
