"""BundleRebalanceOrchestrator — sell-then-buy rebalancing engine.

Flow:
    1. Compute target vs actual allocation deltas in EUR
    2. Consume available cash leg to reduce required sells
    3. Execute SELL phase: overweight assets → entry asset (cash leg credit)
    4. Execute BUY phase: entry asset (cash leg debit) → underweight assets
    5. Persist residual cash leg
"""
from __future__ import annotations

import logging
import uuid as uuid_mod
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_DOWN
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.exchange.assets import SUPPORTED_ASSETS
from services.exchange.service import ExchangeError, ExchangeService
from services.portfolio_engine.bundle_execution import BundleExecutionAdapter
from services.portfolio_engine.bundle_execution.lifi_base_config import normalize_bundle_asset
from services.portfolio_engine.bundle_execution.types import ExecutionLeg
from services.portfolio_engine.invariants.invariant_g import check_invariant_g
from services.portfolio_engine.allocations.models import TargetAllocation
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.hardening.audit_service import AuditService
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.models import PositionAtom

from .orchestrator import (
    BundleOrchestrator,
    BundleOrchestratorError,
    POSITION_TYPE_CASH,
    POSITION_TYPE_SPOT,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configurable thresholds
# ---------------------------------------------------------------------------

MIN_DRIFT_BPS = 200
"""Minimum allocation drift in basis points to trigger a trade (2%)."""

MIN_TRADE_EUR = Decimal("5")
"""Minimum trade value in EUR below which the trade is skipped."""

RESIDUAL_BUFFER_EUR = Decimal("0.50")
"""Small buffer kept in the cash leg to avoid dust issues."""


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class AllocationSlot:
    """One asset slot in the rebalance plan."""
    asset: str
    instrument_id: UUID
    target_weight: Decimal
    current_value_eur: Decimal
    target_value_eur: Decimal = Decimal("0")
    delta_eur: Decimal = Decimal("0")
    action: str = "hold"
    trade_amount_eur: Decimal = Decimal("0")
    trade_quantity: Decimal = Decimal("0")
    current_quantity: Decimal = Decimal("0")
    price_eur: Decimal = Decimal("0")
    status: str = "pending"
    error: str = ""


@dataclass
class RebalancePlan:
    """Complete rebalance plan produced by preview_rebalance."""
    portfolio_id: str
    base_value_eur: Decimal = Decimal("0")
    cash_leg_value_eur: Decimal = Decimal("0")
    entry_asset: str = "USDC"
    entry_instrument_id: Optional[UUID] = None
    slots: list[AllocationSlot] = field(default_factory=list)
    sell_plan: list[dict] = field(default_factory=list)
    buy_plan: list[dict] = field(default_factory=list)
    estimated_residual_cash_eur: Decimal = Decimal("0")
    warnings: list[str] = field(default_factory=list)
    status: str = "ok"


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class BundleRebalanceOrchestrator:
    """Computes and executes sell-then-buy rebalance plans for bundle portfolios."""

    def __init__(
        self,
        execution_adapter: Optional[BundleExecutionAdapter] = None,
        exchange_service: Optional[ExchangeService] = None,
    ):
        self._execution = execution_adapter or BundleExecutionAdapter()
        self._exchange = exchange_service or ExchangeService()

    # ------------------------------------------------------------------
    # preview_rebalance (read-only)
    # ------------------------------------------------------------------

    def preview_rebalance(
        self,
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
    ) -> dict:
        """Compute a rebalance plan without executing anything."""
        plan = self._compute_plan(db, client_id=client_id, portfolio_id=portfolio_id)
        return self._plan_to_dict(plan)

    # ------------------------------------------------------------------
    # execute_rebalance
    # ------------------------------------------------------------------

    def execute_rebalance(
        self,
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
    ) -> dict:
        """Execute a full rebalance: sell overweight → buy underweight via cash leg."""
        plan = self._compute_plan(db, client_id=client_id, portfolio_id=portfolio_id)

        if plan.status in ("no_action", "invalid"):
            return {
                "portfolio_id": plan.portfolio_id,
                "status": plan.status,
                "sell_results": [],
                "buy_results": [],
                "cash_leg_before": float(plan.cash_leg_value_eur),
                "cash_leg_after": float(plan.cash_leg_value_eur),
                "message": "No rebalance needed" if plan.status == "no_action" else plan.warnings[0] if plan.warnings else "Invalid",
            }

        actor = ActorContext(
            actor_type="system",
            actor_id=f"bundle-rebalance-{portfolio_id}",
        )
        batch_id = str(uuid_mod.uuid4())
        entry_asset = plan.entry_asset
        entry_instrument_id = plan.entry_instrument_id

        cash_leg_before_eur = plan.cash_leg_value_eur
        current_cash_qty = self._get_cash_leg_quantity(db, portfolio_id, entry_instrument_id)

        sell_results: list[dict] = []
        buy_results: list[dict] = []

        # ── SELL PHASE ─────────────────────────────────────────────────
        for sell_item in plan.sell_plan:
            asset = sell_item["asset"]
            sell_qty = Decimal(str(sell_item["quantity"]))
            instrument_id = UUID(sell_item["instrument_id"])

            ext_ref = f"bundle-rebal-sell-{batch_id}-{asset}"
            lifi_asset = normalize_bundle_asset(asset)
            try:
                swap_result = self._execute_swap(
                    db, client_id, lifi_asset, entry_asset,
                    sell_qty, ext_ref, portfolio_id, batch_id, actor,
                    leg_action="rebalance_sell",
                    entry_instrument_id=entry_instrument_id,
                    spot_instrument_id=instrument_id,
                )
                if swap_result.get("status") == "pending":
                    sell_results.append({
                        "asset": asset,
                        "quantity_sold": 0,
                        "entry_asset_received": 0,
                        "value_eur": 0,
                        "status": "pending",
                        "swap_id": swap_result.get("swap_id"),
                        "leg_id": ext_ref,
                    })
                    continue
                entry_received = Decimal(str(swap_result.get("amount_to", 0)))
                ref_value = Decimal(str(swap_result.get("reference_value_net", 0)))

                if self._execution.provider_name != "lifi_base":
                    self._debit_spot_atom(db, portfolio_id, instrument_id, sell_qty, ref_value)
                    BundleOrchestrator._credit_cash_leg(
                        db, portfolio_id, entry_instrument_id,
                        entry_received, ref_value,
                    )
                current_cash_qty += entry_received

                sell_results.append({
                    "asset": asset,
                    "quantity_sold": float(sell_qty),
                    "entry_asset_received": float(entry_received),
                    "value_eur": float(ref_value),
                    "status": "completed",
                })
            except Exception as exc:
                logger.warning("Rebalance SELL leg failed: asset=%s err=%s", asset, exc)
                sell_results.append({
                    "asset": asset,
                    "quantity_sold": 0,
                    "entry_asset_received": 0,
                    "value_eur": 0,
                    "status": "failed",
                    "error": str(exc),
                })

        # ── BUY PHASE ──────────────────────────────────────────────────
        for buy_item in plan.buy_plan:
            asset = buy_item["asset"]
            buy_entry_amount = Decimal(str(buy_item["entry_asset_amount"]))
            instrument_id = UUID(buy_item["instrument_id"])

            if buy_entry_amount > current_cash_qty:
                buy_entry_amount = current_cash_qty
            if buy_entry_amount < Decimal("0.01"):
                buy_results.append({
                    "asset": asset,
                    "quantity_bought": 0,
                    "entry_asset_spent": 0,
                    "value_eur": 0,
                    "status": "skipped",
                    "error": "insufficient_cash_leg",
                })
                continue

            ext_ref = f"bundle-rebal-buy-{batch_id}-{asset}"
            lifi_asset = normalize_bundle_asset(asset)
            try:
                swap_result = self._execute_swap(
                    db, client_id, entry_asset, lifi_asset,
                    buy_entry_amount, ext_ref, portfolio_id, batch_id, actor,
                    leg_action="rebalance_buy",
                    entry_instrument_id=entry_instrument_id,
                    spot_instrument_id=instrument_id,
                )
                if swap_result.get("status") == "pending":
                    buy_results.append({
                        "asset": asset,
                        "quantity_bought": 0,
                        "entry_asset_spent": 0,
                        "value_eur": 0,
                        "status": "pending",
                        "swap_id": swap_result.get("swap_id"),
                        "leg_id": ext_ref,
                    })
                    continue
                crypto_received = Decimal(str(swap_result.get("amount_to", 0)))
                ref_value = Decimal(str(swap_result.get("reference_value_net", buy_entry_amount)))

                if self._execution.provider_name != "lifi_base":
                    BundleOrchestrator._sync_pe_position(
                        db, portfolio_id, instrument_id,
                        crypto_received, ref_value,
                    )
                    BundleOrchestrator._debit_cash_leg(
                        db, portfolio_id, entry_instrument_id,
                        buy_entry_amount, ref_value,
                    )
                current_cash_qty -= buy_entry_amount

                buy_results.append({
                    "asset": asset,
                    "quantity_bought": float(crypto_received),
                    "entry_asset_spent": float(buy_entry_amount),
                    "value_eur": float(ref_value),
                    "status": "completed",
                })
            except Exception as exc:
                logger.warning("Rebalance BUY leg failed: asset=%s err=%s", asset, exc)
                buy_results.append({
                    "asset": asset,
                    "quantity_bought": 0,
                    "entry_asset_spent": 0,
                    "value_eur": 0,
                    "status": "failed",
                    "error": str(exc),
                })

        # ── Final status ───────────────────────────────────────────────
        all_sell_ok = all(r["status"] == "completed" for r in sell_results)
        all_buy_ok = all(r["status"] in ("completed", "skipped") for r in buy_results)
        any_sell_ok = any(r["status"] == "completed" for r in sell_results)
        any_buy_ok = any(r["status"] == "completed" for r in buy_results)

        if all_sell_ok and all_buy_ok:
            exec_status = "completed"
        elif any_sell_ok or any_buy_ok:
            exec_status = "partial"
        else:
            exec_status = "failed"

        cash_leg_after_qty = self._get_cash_leg_quantity(db, portfolio_id, entry_instrument_id)
        cash_leg_after_eur = self._value_entry_asset_eur(db, entry_asset, cash_leg_after_qty)

        AuditService.log_success(
            db,
            entity_type="bundle_rebalance",
            entity_id=batch_id,
            action="execute_rebalance",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata={
                "portfolio_id": str(portfolio_id),
                "batch_id": batch_id,
                "status": exec_status,
                "sell_count": len(sell_results),
                "buy_count": len(buy_results),
                "cash_leg_before_eur": str(cash_leg_before_eur),
                "cash_leg_after_eur": str(cash_leg_after_eur),
            },
        )

        invariant_g = check_invariant_g(db, client_id, dry_run=True)
        any_pending = any(
            r.get("status") == "pending" for r in sell_results + buy_results
        )
        if any_pending and exec_status == "completed":
            exec_status = "pending_signature"

        return {
            "portfolio_id": str(portfolio_id),
            "status": exec_status,
            "batch_id": batch_id,
            "sell_results": sell_results,
            "buy_results": buy_results,
            "cash_leg_before": float(cash_leg_before_eur),
            "cash_leg_after": float(cash_leg_after_eur),
            "message": f"Rebalance {exec_status}",
            "execution_provider": self._execution.provider_name,
            "invariant_g": invariant_g,
        }

    # ------------------------------------------------------------------
    # Internal: plan computation
    # ------------------------------------------------------------------

    def _compute_plan(
        self,
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
    ) -> RebalancePlan:
        """Build a RebalancePlan from current positions vs target allocations."""
        portfolio = BundleOrchestrator._load_and_validate_portfolio(db, portfolio_id, client_id)
        product = BundleOrchestrator._load_product(db, portfolio)
        entry_config = BundleOrchestrator._resolve_entry_config(product)
        entry_asset = entry_config["entry_asset_default"]

        plan = RebalancePlan(
            portfolio_id=str(portfolio_id),
            entry_asset=entry_asset,
        )

        allocations = BundleOrchestrator._load_target_allocations(db, portfolio_id)
        if not allocations:
            plan.status = "invalid"
            plan.warnings.append("no_target_allocations_found")
            return plan

        entry_instrument = BundleOrchestrator._resolve_or_create_instrument(db, entry_asset)
        plan.entry_instrument_id = entry_instrument.id

        atoms = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id == portfolio_id,
                PositionAtom.status == "open",
            )
            .all()
        )

        instrument_cache: dict[UUID, tuple[Instrument, Asset]] = {}
        for atom in atoms:
            if atom.instrument_id not in instrument_cache:
                instr = db.query(Instrument).filter(Instrument.id == atom.instrument_id).first()
                asset_obj = db.query(Asset).filter(Asset.id == instr.asset_id).first() if instr else None
                if instr and asset_obj:
                    instrument_cache[atom.instrument_id] = (instr, asset_obj)

        cash_leg_qty = Decimal("0")
        spot_positions: dict[UUID, tuple[Decimal, str]] = {}

        for atom in atoms:
            if atom.instrument_id not in instrument_cache:
                continue
            _, asset_obj = instrument_cache[atom.instrument_id]
            symbol = BundleOrchestrator._normalize_asset_symbol(asset_obj.symbol.upper())
            qty = Decimal(str(atom.quantity))

            if atom.position_type == POSITION_TYPE_CASH:
                cash_leg_qty += qty
            elif atom.position_type == POSITION_TYPE_SPOT:
                spot_positions[atom.instrument_id] = (qty, symbol)

        cash_leg_eur = self._value_entry_asset_eur(db, entry_asset, cash_leg_qty)
        plan.cash_leg_value_eur = cash_leg_eur

        total_spot_eur = Decimal("0")
        price_cache: dict[str, Decimal] = {}

        for alloc in allocations:
            _, asset_obj = instrument_cache.get(alloc.instrument_id, (None, None))
            if asset_obj is None:
                instr = db.query(Instrument).filter(Instrument.id == alloc.instrument_id).first()
                asset_obj = db.query(Asset).filter(Asset.id == instr.asset_id).first() if instr else None
                if instr and asset_obj:
                    instrument_cache[alloc.instrument_id] = (instr, asset_obj)
            if asset_obj is None:
                plan.warnings.append(f"instrument_not_found:{alloc.instrument_id}")
                continue

            symbol = BundleOrchestrator._normalize_asset_symbol(asset_obj.symbol.upper())
            qty, _ = spot_positions.get(alloc.instrument_id, (Decimal("0"), symbol))

            try:
                price_eur = self._resolve_asset_price_eur(db, symbol)
                price_cache[symbol] = price_eur
            except Exception as exc:
                plan.warnings.append(f"price_unavailable:{symbol}: {exc}")
                price_eur = Decimal("0")

            current_value = qty * price_eur
            total_spot_eur += current_value

            plan.slots.append(AllocationSlot(
                asset=symbol,
                instrument_id=alloc.instrument_id,
                target_weight=Decimal(str(alloc.target_weight)),
                current_value_eur=current_value,
                current_quantity=qty,
                price_eur=price_eur,
            ))

        base_value_eur = total_spot_eur + cash_leg_eur
        plan.base_value_eur = base_value_eur

        if base_value_eur <= MIN_TRADE_EUR:
            plan.status = "no_action"
            plan.warnings.append("base_value_too_small")
            return plan

        # Compute target values and deltas
        for slot in plan.slots:
            slot.target_value_eur = (base_value_eur * slot.target_weight).quantize(
                Decimal("0.01"), rounding=ROUND_DOWN,
            )
            slot.delta_eur = slot.target_value_eur - slot.current_value_eur

        # Phase 1: determine sells and buys
        sells: list[AllocationSlot] = []
        buys: list[AllocationSlot] = []

        for slot in plan.slots:
            drift_bps = (
                abs(slot.delta_eur) / slot.target_value_eur * Decimal("10000")
                if slot.target_value_eur > 0
                else Decimal("0")
            )
            if slot.delta_eur < -MIN_TRADE_EUR and drift_bps >= MIN_DRIFT_BPS:
                slot.action = "sell"
                slot.trade_amount_eur = abs(slot.delta_eur)
                sells.append(slot)
            elif slot.delta_eur > MIN_TRADE_EUR and drift_bps >= MIN_DRIFT_BPS:
                slot.action = "buy"
                slot.trade_amount_eur = slot.delta_eur
                buys.append(slot)
            else:
                slot.action = "hold"

        if not sells and not buys:
            plan.status = "no_action"
            return plan

        # Phase 2: cash leg reduces buys needed → reduces sells needed
        total_buy_needed_eur = sum(s.trade_amount_eur for s in buys)
        total_sell_eur = sum(s.trade_amount_eur for s in sells)
        cash_available_for_buys = cash_leg_eur

        funding_from_sells = max(Decimal("0"), total_buy_needed_eur - cash_available_for_buys)

        if funding_from_sells < total_sell_eur:
            scale = funding_from_sells / total_sell_eur if total_sell_eur > 0 else Decimal("0")
            for slot in sells:
                slot.trade_amount_eur = (slot.trade_amount_eur * scale).quantize(
                    Decimal("0.01"), rounding=ROUND_DOWN,
                )
                if slot.trade_amount_eur < MIN_TRADE_EUR:
                    slot.action = "hold"
                    slot.trade_amount_eur = Decimal("0")

        sells = [s for s in sells if s.action == "sell"]

        # Compute quantities
        for slot in sells:
            if slot.price_eur > 0:
                slot.trade_quantity = (slot.trade_amount_eur / slot.price_eur).quantize(
                    Decimal("0.00000001"), rounding=ROUND_DOWN,
                )
                if slot.trade_quantity > slot.current_quantity:
                    slot.trade_quantity = slot.current_quantity

        actual_sell_eur = sum(s.trade_amount_eur for s in sells)
        total_cash_available_eur = cash_available_for_buys + actual_sell_eur

        if total_buy_needed_eur > total_cash_available_eur:
            scale = total_cash_available_eur / total_buy_needed_eur if total_buy_needed_eur > 0 else Decimal("0")
            for slot in buys:
                slot.trade_amount_eur = (slot.trade_amount_eur * scale).quantize(
                    Decimal("0.01"), rounding=ROUND_DOWN,
                )
                if slot.trade_amount_eur < MIN_TRADE_EUR:
                    slot.action = "hold"
                    slot.trade_amount_eur = Decimal("0")

        buys = [s for s in buys if s.action == "buy"]

        total_buy_eur = sum(s.trade_amount_eur for s in buys)
        plan.estimated_residual_cash_eur = max(
            Decimal("0"),
            total_cash_available_eur - total_buy_eur,
        )

        # Convert buy amounts to entry asset quantities
        entry_price_eur = self._resolve_asset_price_eur(db, entry_asset) if entry_asset not in ("EUR",) else Decimal("1")

        for slot in buys:
            if entry_price_eur > 0:
                entry_qty = (slot.trade_amount_eur / entry_price_eur).quantize(
                    Decimal("0.000001"), rounding=ROUND_DOWN,
                )
            else:
                entry_qty = Decimal("0")
            slot.trade_quantity = entry_qty

        # Build structured plans
        plan.sell_plan = [
            {
                "asset": s.asset,
                "instrument_id": str(s.instrument_id),
                "quantity": float(s.trade_quantity),
                "estimated_value_eur": float(s.trade_amount_eur),
            }
            for s in sells
        ]
        plan.buy_plan = [
            {
                "asset": s.asset,
                "instrument_id": str(s.instrument_id),
                "entry_asset_amount": float(s.trade_quantity),
                "estimated_value_eur": float(s.trade_amount_eur),
            }
            for s in buys
        ]

        plan.status = "ok" if not plan.warnings else "partial"
        return plan

    # ------------------------------------------------------------------
    # Internal: helpers
    # ------------------------------------------------------------------

    def _resolve_asset_price_eur(self, db: Session, asset: str) -> Decimal:
        """Get the current EUR price for an asset via ExchangeService._resolve_price."""
        return self._exchange._resolve_price(db, asset, override_price=None, side="sell")

    def _value_entry_asset_eur(self, db: Session, entry_asset: str, qty: Decimal) -> Decimal:
        if qty <= 0:
            return Decimal("0")
        try:
            price = self._resolve_asset_price_eur(db, entry_asset)
            return (qty * price).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
        except Exception:
            return Decimal("0")

    @staticmethod
    def _get_cash_leg_quantity(
        db: Session, portfolio_id: UUID, entry_instrument_id: UUID,
    ) -> Decimal:
        cash = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id == portfolio_id,
                PositionAtom.instrument_id == entry_instrument_id,
                PositionAtom.position_type == POSITION_TYPE_CASH,
                PositionAtom.status == "open",
            )
            .first()
        )
        if cash is None:
            return Decimal("0")
        return Decimal(str(cash.quantity))

    def _execute_swap(
        self,
        db: Session,
        client_id: UUID,
        from_asset: str,
        to_asset: str,
        amount_from: Decimal,
        ext_ref: str,
        portfolio_id: UUID,
        batch_id: str,
        actor: ActorContext,
        *,
        leg_action: str,
        entry_instrument_id: UUID,
        spot_instrument_id: UUID,
    ) -> dict:
        leg = ExecutionLeg(
            leg_id=ext_ref,
            portfolio_id=portfolio_id,
            client_id=client_id,
            action=leg_action,
            from_asset=from_asset.upper(),
            to_asset=to_asset.upper(),
            amount_from=amount_from,
            batch_id=batch_id,
            bundle_action="rebalance",
            chain="base",
            metadata={
                "entry_instrument_id": str(entry_instrument_id),
                "target_instrument_id": str(spot_instrument_id),
            },
        )
        result = self._execution.execute_leg(db, leg, actor)
        if result.status == "pending":
            return {
                "status": "pending",
                "swap_id": result.provider_order_id,
                "amount_to": 0,
                "reference_value_net": 0,
            }
        out = result.to_swap_legacy_dict()
        out["status"] = result.status
        return out

    @staticmethod
    def _debit_spot_atom(
        db: Session,
        portfolio_id: UUID,
        instrument_id: UUID,
        quantity: Decimal,
        cost_basis: Decimal,
    ) -> None:
        atom = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id == portfolio_id,
                PositionAtom.instrument_id == instrument_id,
                PositionAtom.position_type == POSITION_TYPE_SPOT,
                PositionAtom.status == "open",
            )
            .first()
        )
        if atom is None:
            logger.warning("Spot atom not found for debit: instrument=%s", instrument_id)
            return
        atom.quantity = max(Decimal("0"), Decimal(str(atom.quantity)) - quantity)
        atom.available_quantity = max(Decimal("0"), Decimal(str(atom.available_quantity)) - quantity)
        atom.cost_basis = max(Decimal("0"), Decimal(str(atom.cost_basis or 0)) - cost_basis)
        if atom.quantity > 0:
            atom.average_entry_price = atom.cost_basis / atom.quantity
        else:
            atom.average_entry_price = Decimal("0")
        db.flush()

    # ------------------------------------------------------------------
    # Plan serialization
    # ------------------------------------------------------------------

    @staticmethod
    def _plan_to_dict(plan: RebalancePlan) -> dict:
        current_allocs = []
        target_allocs = []
        for slot in plan.slots:
            current_pct = (
                float(slot.current_value_eur / plan.base_value_eur * 100)
                if plan.base_value_eur > 0 else 0
            )
            current_allocs.append({
                "asset": slot.asset,
                "current_value_eur": float(slot.current_value_eur),
                "current_weight_pct": round(current_pct, 2),
                "quantity": float(slot.current_quantity),
            })
            target_allocs.append({
                "asset": slot.asset,
                "target_value_eur": float(slot.target_value_eur),
                "target_weight_pct": round(float(slot.target_weight * 100), 2),
                "delta_eur": float(slot.delta_eur),
                "action": slot.action,
            })

        return {
            "portfolio_id": plan.portfolio_id,
            "status": plan.status,
            "base_value_eur": float(plan.base_value_eur),
            "cash_leg_value_eur": float(plan.cash_leg_value_eur),
            "current_allocations": current_allocs,
            "target_allocations": target_allocs,
            "sell_plan": plan.sell_plan,
            "buy_plan": plan.buy_plan,
            "estimated_residual_cash_leg": float(plan.estimated_residual_cash_eur),
            "warnings": plan.warnings,
        }
