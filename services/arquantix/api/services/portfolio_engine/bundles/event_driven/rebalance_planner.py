"""B3b — Rebalance planner pur : portfolio_after_funding → rebalance_to_target.

Aucun runtime · aucun I/O · module pur (hors pipeline event-driven).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from typing import Any, Mapping, Sequence

USDC_ASSET = "USDC"
BPS_SCALE = Decimal("10000")


def _normalize_asset(asset: str) -> str:
    return str(asset).strip().upper()


def _d(value: Decimal | str | int | float) -> Decimal:
    return Decimal(str(value))


def _quantize_usdc(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)


def _format_decimal(value: Decimal) -> str:
    text = f"{_quantize_usdc(value):f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


@dataclass(frozen=True)
class PositionSnapshot:
    asset: str
    quantity: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset", _normalize_asset(self.asset))
        object.__setattr__(self, "quantity", _d(self.quantity))


@dataclass(frozen=True)
class PortfolioSnapshot:
    bundle_cash_usdc: Decimal
    positions: tuple[PositionSnapshot, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "bundle_cash_usdc", _d(self.bundle_cash_usdc))

    def position_quantity(self, asset: str) -> Decimal:
        asset_norm = _normalize_asset(asset)
        for row in self.positions:
            if row.asset == asset_norm:
                return row.quantity
        return Decimal("0")

    def position_value_usdc(self, asset: str, prices_used: Mapping[str, Decimal]) -> Decimal:
        asset_norm = _normalize_asset(asset)
        price = prices_used.get(asset_norm)
        if price is None:
            return Decimal("0")
        return _quantize_usdc(self.position_quantity(asset_norm) * _d(price))

    def total_value_usdc(self, prices_used: Mapping[str, Decimal]) -> Decimal:
        total = self.bundle_cash_usdc
        for row in self.positions:
            price = prices_used.get(row.asset)
            if price is None:
                continue
            total += _quantize_usdc(row.quantity * _d(price))
        return _quantize_usdc(total)


@dataclass(frozen=True)
class TargetAllocationInput:
    asset: str
    weight_bps: int

    def __post_init__(self) -> None:
        object.__setattr__(self, "asset", _normalize_asset(self.asset))
        object.__setattr__(self, "weight_bps", int(self.weight_bps))


@dataclass(frozen=True)
class RebalancePolicies:
    min_trade_usdc: Decimal = Decimal("5")
    execution_buffer_usdc: Decimal = Decimal("1")
    drift_tolerance_bps: int = 50
    dust_policy: str = "retain_in_cash"
    allow_sell: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "min_trade_usdc", _d(self.min_trade_usdc))
        object.__setattr__(self, "execution_buffer_usdc", _d(self.execution_buffer_usdc))
        object.__setattr__(self, "drift_tolerance_bps", int(self.drift_tolerance_bps))


@dataclass(frozen=True)
class RebalanceLeg:
    leg_index: int
    direction: str
    asset: str
    notional_usdc: Decimal
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "leg_index": self.leg_index,
            "direction": self.direction,
            "asset": self.asset,
            "notional_usdc": _format_decimal(self.notional_usdc),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class SkippedAsset:
    asset: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {"asset": self.asset, "reason": self.reason}


@dataclass(frozen=True)
class ExpectedPortfolioSnapshot:
    bundle_cash_usdc: Decimal
    positions: dict[str, str]
    weights_bps: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "bundle_cash": {USDC_ASSET: _format_decimal(self.bundle_cash_usdc)},
            "bundle_position": dict(sorted(self.positions.items())),
            "weights_bps": dict(sorted(self.weights_bps.items())),
        }


@dataclass(frozen=True)
class RebalancePlan:
    legs: tuple[RebalanceLeg, ...]
    skipped: tuple[SkippedAsset, ...]
    expected_portfolio_after_execution: ExpectedPortfolioSnapshot
    residual_usdc: Decimal
    weights_before: dict[str, int]
    weights_after_funding: dict[str, int]
    weights_expected_after_execution: dict[str, int]
    prices_used: dict[str, str]
    plan_hash: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "legs": [leg.to_dict() for leg in self.legs],
            "skipped": [row.to_dict() for row in self.skipped],
            "expected_portfolio_after_execution": self.expected_portfolio_after_execution.to_dict(),
            "residual_usdc": _format_decimal(self.residual_usdc),
            "weights_before": dict(sorted(self.weights_before.items())),
            "weights_after_funding": dict(sorted(self.weights_after_funding.items())),
            "weights_expected_after_execution": dict(
                sorted(self.weights_expected_after_execution.items())
            ),
            "prices_used": dict(sorted(self.prices_used.items())),
            "plan_hash": self.plan_hash,
            "warnings": list(self.warnings),
        }


def compute_plan_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _normalize_prices(prices_used: Mapping[str, Decimal | str]) -> dict[str, Decimal]:
    out: dict[str, Decimal] = {USDC_ASSET: Decimal("1")}
    for asset, price in prices_used.items():
        asset_norm = _normalize_asset(asset)
        if asset_norm == USDC_ASSET:
            out[USDC_ASSET] = Decimal("1")
            continue
        out[asset_norm] = _d(price)
    return out


def _asset_weights_bps(
    portfolio: PortfolioSnapshot,
    target_assets: Sequence[str],
    prices_used: Mapping[str, Decimal],
) -> dict[str, int]:
    total = portfolio.total_value_usdc(prices_used)
    if total <= 0:
        return {asset: 0 for asset in target_assets}
    weights: dict[str, int] = {}
    for asset in target_assets:
        value = portfolio.position_value_usdc(asset, prices_used)
        weights[asset] = int((value * BPS_SCALE / total).to_integral_value(rounding=ROUND_DOWN))
    return weights


def _drift_bps(delta_usdc: Decimal, total_usdc: Decimal) -> int:
    if total_usdc <= 0:
        return 0
    return int((abs(delta_usdc) * BPS_SCALE / total_usdc).to_integral_value(rounding=ROUND_DOWN))


@dataclass
class _Slot:
    asset: str
    target_value_usdc: Decimal
    current_value_usdc: Decimal
    delta_usdc: Decimal
    current_quantity: Decimal
    price_usdc: Decimal | None


def plan_rebalance_after_funding(
    *,
    portfolio_before: PortfolioSnapshot,
    funding_usdc: Decimal | str,
    portfolio_after_funding: PortfolioSnapshot,
    target_allocation: Sequence[TargetAllocationInput],
    prices_used: Mapping[str, Decimal | str],
    policies: RebalancePolicies | None = None,
) -> RebalancePlan:
    """Plan rebalance-to-target après funding — fonction pure."""
    policies = policies or RebalancePolicies()
    funding = _d(funding_usdc)
    prices = _normalize_prices(prices_used)
    warnings: list[str] = []
    skipped: list[SkippedAsset] = []
    legs: list[RebalanceLeg] = []

    target_assets = tuple(row.asset for row in target_allocation)
    weights_before = _asset_weights_bps(portfolio_before, target_assets, prices)
    weights_after_funding = _asset_weights_bps(portfolio_after_funding, target_assets, prices)

    total_after = portfolio_after_funding.total_value_usdc(prices)
    if total_after <= 0:
        warnings.append("portfolio_total_value_zero")
        empty_expected = ExpectedPortfolioSnapshot(
            bundle_cash_usdc=portfolio_after_funding.bundle_cash_usdc,
            positions={},
            weights_bps={asset: 0 for asset in target_assets},
        )
        plan_body = {
            "legs": [],
            "skipped": [{"asset": a, "reason": "no_portfolio_value"} for a in target_assets],
            "residual_usdc": _format_decimal(portfolio_after_funding.bundle_cash_usdc),
            "weights_after_funding": weights_after_funding,
        }
        return RebalancePlan(
            legs=(),
            skipped=tuple(SkippedAsset(asset=a, reason="no_portfolio_value") for a in target_assets),
            expected_portfolio_after_execution=empty_expected,
            residual_usdc=portfolio_after_funding.bundle_cash_usdc,
            weights_before=weights_before,
            weights_after_funding=weights_after_funding,
            weights_expected_after_execution={asset: 0 for asset in target_assets},
            prices_used={k: _format_decimal(v) for k, v in sorted(prices.items())},
            plan_hash=compute_plan_hash(plan_body),
            warnings=tuple(warnings),
        )

    slots: list[_Slot] = []
    for row in target_allocation:
        price = prices.get(row.asset)
        if price is None:
            skipped.append(SkippedAsset(asset=row.asset, reason="no_price"))
            warnings.append(f"missing_price:{row.asset}")
            continue
        current_value = portfolio_after_funding.position_value_usdc(row.asset, prices)
        target_value = _quantize_usdc(total_after * _d(row.weight_bps) / BPS_SCALE)
        delta = _quantize_usdc(target_value - current_value)
        slots.append(
            _Slot(
                asset=row.asset,
                target_value_usdc=target_value,
                current_value_usdc=current_value,
                delta_usdc=delta,
                current_quantity=portfolio_after_funding.position_quantity(row.asset),
                price_usdc=price,
            )
        )

    simulated_cash = portfolio_after_funding.bundle_cash_usdc
    simulated_qty: dict[str, Decimal] = {
        row.asset: portfolio_after_funding.position_quantity(row.asset) for row in slots
    }

    drift_only = funding <= 0

    if policies.allow_sell:
        for slot in sorted(slots, key=lambda s: s.delta_usdc):
            if slot.delta_usdc >= 0:
                continue
            drift = _drift_bps(slot.delta_usdc, total_after)
            if drift_only and drift <= policies.drift_tolerance_bps:
                skipped.append(SkippedAsset(asset=slot.asset, reason="within_drift_tolerance"))
                continue
            if slot.price_usdc is None or slot.price_usdc <= 0:
                continue
            sell_notional = min(abs(slot.delta_usdc), slot.current_value_usdc)
            if sell_notional < policies.min_trade_usdc:
                skipped.append(SkippedAsset(asset=slot.asset, reason="below_min_trade"))
                continue
            legs.append(
                RebalanceLeg(
                    leg_index=len(legs),
                    direction="sell",
                    asset=slot.asset,
                    notional_usdc=sell_notional,
                    reason="overweight",
                )
            )
            simulated_cash += sell_notional
            qty_sold = _quantize_usdc(sell_notional / slot.price_usdc)
            simulated_qty[slot.asset] = max(Decimal("0"), simulated_qty[slot.asset] - qty_sold)
    else:
        for slot in slots:
            if slot.delta_usdc < 0:
                drift = _drift_bps(slot.delta_usdc, total_after)
                if drift > policies.drift_tolerance_bps:
                    skipped.append(SkippedAsset(asset=slot.asset, reason="overweight_buy_only_mode"))
                else:
                    skipped.append(SkippedAsset(asset=slot.asset, reason="within_drift_tolerance"))

    tradable_cash = max(Decimal("0"), simulated_cash - policies.execution_buffer_usdc)
    underweight = [slot for slot in slots if slot.delta_usdc > 0]
    underweight.sort(key=lambda s: s.delta_usdc, reverse=True)

    remaining_cash = tradable_cash
    for slot in underweight:
        if slot.price_usdc is None or slot.price_usdc <= 0:
            continue
        drift = _drift_bps(slot.delta_usdc, total_after)
        if drift_only and drift <= policies.drift_tolerance_bps:
            skipped.append(SkippedAsset(asset=slot.asset, reason="within_drift_tolerance"))
            continue
        if slot.delta_usdc <= 0:
            skipped.append(SkippedAsset(asset=slot.asset, reason="overweight"))
            continue
        buy_notional = min(slot.delta_usdc, remaining_cash)
        if buy_notional < policies.min_trade_usdc:
            skipped.append(SkippedAsset(asset=slot.asset, reason="below_min_trade"))
            continue
        legs.append(
            RebalanceLeg(
                leg_index=len(legs),
                direction="buy",
                asset=slot.asset,
                notional_usdc=buy_notional,
                reason="underweight",
            )
        )
        remaining_cash -= buy_notional
        qty_bought = _quantize_usdc(buy_notional / slot.price_usdc)
        simulated_qty[slot.asset] = simulated_qty.get(slot.asset, Decimal("0")) + qty_bought

    final_cash = simulated_cash
    for leg in legs:
        if leg.direction == "buy":
            final_cash -= leg.notional_usdc
    residual_usdc = _quantize_usdc(final_cash)

    expected_positions = {
        asset: _format_decimal(qty)
        for asset, qty in sorted(simulated_qty.items())
        if qty > 0
    }
    expected_weights = _asset_weights_bps(
        PortfolioSnapshot(
            bundle_cash_usdc=residual_usdc,
            positions=tuple(
                PositionSnapshot(asset=asset, quantity=qty)
                for asset, qty in simulated_qty.items()
                if qty > 0
            ),
        ),
        target_assets,
        prices,
    )

    expected = ExpectedPortfolioSnapshot(
        bundle_cash_usdc=residual_usdc,
        positions=expected_positions,
        weights_bps=expected_weights,
    )

    plan_body = {
        "legs": [leg.to_dict() for leg in legs],
        "skipped": [row.to_dict() for row in skipped],
        "residual_usdc": _format_decimal(residual_usdc),
        "weights_after_funding": weights_after_funding,
        "weights_expected_after_execution": expected_weights,
        "prices_used": {k: _format_decimal(v) for k, v in sorted(prices.items())},
    }
    plan_hash = compute_plan_hash(plan_body)

    return RebalancePlan(
        legs=tuple(legs),
        skipped=tuple(skipped),
        expected_portfolio_after_execution=expected,
        residual_usdc=residual_usdc,
        weights_before=weights_before,
        weights_after_funding=weights_after_funding,
        weights_expected_after_execution=expected_weights,
        prices_used={k: _format_decimal(v) for k, v in sorted(prices.items())},
        plan_hash=plan_hash,
        warnings=tuple(warnings),
    )
