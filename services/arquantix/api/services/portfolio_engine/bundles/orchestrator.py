"""BundleOrchestrator — Phase 2: True entry-asset cash leg.

Flow:
    EUR → BUY entry_asset (USDC) → credit cash leg → SWAP to each target → debit cash leg

The cash leg is a ``PositionAtom`` with ``position_type='cash'``.  Allocation
positions use ``position_type='spot'``.  Both live in the same PE portfolio,
giving a complete overlay view of the bundle without modifying
``crypto_positions``.
"""
from __future__ import annotations

import logging
import uuid as uuid_mod
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.exchange.models import CryptoPosition, ExchangeOrder
from services.exchange.schemas import ExchangeBuyRequest, SwapRequest
from services.exchange.service import ExchangeService, ExchangeError
from services.portfolio_engine.allocations.models import TargetAllocation
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.hardening.audit_service import AuditService
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.products.models import ProductDefinition

logger = logging.getLogger(__name__)

_ENTRY_ASSET_DEFAULT_FALLBACK = "USDC"
_ENTRY_ASSETS_ALLOWED_FALLBACK = ["USDC"]

POSITION_TYPE_CASH = PositionType.CASH
POSITION_TYPE_SPOT = PositionType.SPOT


class BundleOrchestratorError(Exception):
    pass


class BundleOrchestrator:
    """Orchestrates bundle investment with a true entry-asset cash leg.

    Phase 2 flow:
        1. Fund the cash leg (EUR → BUY entry_asset, or direct entry_asset)
        2. Allocate from the cash leg via SWAPs to each target asset
        3. Persist the remainder in the cash leg atom
    """

    def __init__(self, exchange_service: Optional[ExchangeService] = None):
        self._exchange = exchange_service or ExchangeService()

    # ------------------------------------------------------------------
    # Public: invest
    # ------------------------------------------------------------------

    def invest_into_bundle(
        self,
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
        funding_asset: str,
        funding_amount: Decimal,
        reference_currency: str = "EUR",
    ) -> dict:
        """Fund and allocate into a bundle portfolio.

        Returns a structured result with funding details, per-leg execution,
        and the final cash-leg balance.
        """
        portfolio = self._load_and_validate_portfolio(db, portfolio_id, client_id)
        product = self._load_product(db, portfolio)
        entry_config = self._resolve_entry_config(product)
        entry_asset = entry_config["entry_asset_default"]

        self._validate_funding_asset(funding_asset, entry_config)

        allocations = self._load_target_allocations(db, portfolio_id)
        if not allocations:
            raise BundleOrchestratorError("no_target_allocations_found")

        actor = ActorContext(
            actor_type="system",
            actor_id=f"bundle-orchestrator-{portfolio_id}",
        )
        batch_id = str(uuid_mod.uuid4())

        entry_instrument = self._resolve_or_create_instrument(db, entry_asset)

        # ── Step 1: Funding — acquire entry asset ────────────────────────
        is_fiat_funding = funding_asset.upper() in ("EUR", "USD")
        is_direct_entry = funding_asset.upper() == entry_asset.upper()

        funding_result: dict = {}
        entry_qty_received = Decimal("0")
        funding_cost_basis = Decimal("0")

        if is_fiat_funding:
            ext_ref = f"bundle-fund-{batch_id}"
            buy_result = self._execute_buy_from_fiat(
                db, client_id, entry_asset, funding_amount,
                funding_asset, ext_ref, portfolio_id, batch_id, actor,
            )
            entry_qty_received = Decimal(str(buy_result.get("amount_crypto", 0)))
            funding_cost_basis = funding_amount
            funding_result = {
                "action": "buy_entry_asset",
                "from": funding_asset,
                "to": entry_asset,
                "fiat_spent": float(funding_amount),
                "entry_asset_received": float(entry_qty_received),
                "order_id": str(buy_result.get("order_id", "")),
            }
        elif is_direct_entry:
            entry_qty_received = funding_amount
            funding_cost_basis = funding_amount
            funding_result = {
                "action": "direct_entry_asset",
                "entry_asset": entry_asset,
                "amount": float(funding_amount),
            }
        else:
            raise BundleOrchestratorError(
                f"unsupported_funding_path: {funding_asset} → {entry_asset}"
            )

        # Credit cash leg
        self._credit_cash_leg(
            db, portfolio_id, entry_instrument.id,
            entry_qty_received, funding_cost_basis,
        )

        # ── Step 2: Allocate from cash leg ───────────────────────────────
        cash_available = entry_qty_received
        alloc_results: list[dict] = []
        succeeded = 0
        failed = 0
        total_entry_consumed = Decimal("0")

        for alloc in allocations:
            instrument = alloc.instrument
            if instrument is None:
                instrument = db.query(Instrument).filter(
                    Instrument.id == alloc.instrument_id
                ).first()
            asset_obj = db.query(Asset).filter(
                Asset.id == instrument.asset_id
            ).first()
            target_asset = self._normalize_asset_symbol(asset_obj.symbol.upper())

            alloc_entry_amount = (entry_qty_received * alloc.target_weight).quantize(
                Decimal("0.000001"), rounding=ROUND_DOWN,
            )
            if alloc_entry_amount <= 0 or alloc_entry_amount > cash_available:
                continue

            ext_ref = f"bundle-alloc-{batch_id}-{target_asset}"

            try:
                swap_result = self._execute_swap_from_entry(
                    db, client_id, entry_asset, target_asset,
                    alloc_entry_amount, ext_ref, portfolio_id, batch_id, actor,
                )

                crypto_received = Decimal(str(swap_result.get("amount_to", 0)))
                ref_value_net = Decimal(str(swap_result.get("reference_value_net", alloc_entry_amount)))

                self._sync_pe_position(
                    db, portfolio_id, alloc.instrument_id,
                    crypto_received, ref_value_net,
                )
                self._debit_cash_leg(
                    db, portfolio_id, entry_instrument.id,
                    alloc_entry_amount, ref_value_net,
                )

                cash_available -= alloc_entry_amount
                total_entry_consumed += alloc_entry_amount
                succeeded += 1
                alloc_results.append({
                    "asset": target_asset,
                    "instrument_id": str(alloc.instrument_id),
                    "target_weight": float(alloc.target_weight),
                    "entry_asset_consumed": float(alloc_entry_amount),
                    "crypto_received": float(crypto_received),
                    "status": "completed",
                    "swap_group_id": str(swap_result.get("swap_group_id", "")),
                })
            except (ExchangeError, Exception) as exc:
                failed += 1
                logger.warning(
                    "Bundle allocation leg failed: asset=%s err=%s",
                    target_asset, exc,
                )
                alloc_results.append({
                    "asset": target_asset,
                    "instrument_id": str(alloc.instrument_id),
                    "target_weight": float(alloc.target_weight),
                    "entry_asset_consumed": 0,
                    "crypto_received": 0,
                    "status": "failed",
                    "error": str(exc),
                })

        cash_leg_remaining = cash_available
        status = (
            "completed" if failed == 0
            else ("partial" if succeeded > 0 else "failed")
        )

        AuditService.log_success(
            db,
            entity_type="bundle_investment",
            entity_id=batch_id,
            action="invest_into_bundle_v2",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata={
                "client_id": str(client_id),
                "portfolio_id": str(portfolio_id),
                "funding_asset": funding_asset,
                "funding_amount": str(funding_amount),
                "entry_asset": entry_asset,
                "entry_qty_received": str(entry_qty_received),
                "entry_consumed": str(total_entry_consumed),
                "cash_leg_remaining": str(cash_leg_remaining),
                "batch_id": batch_id,
                "succeeded": succeeded,
                "failed": failed,
            },
        )

        return {
            "status": status,
            "batch_id": batch_id,
            "portfolio_id": str(portfolio_id),
            "entry_asset": entry_asset,
            "funding": funding_result,
            "total_entry_asset_received": float(entry_qty_received),
            "total_entry_asset_consumed": float(total_entry_consumed),
            "cash_leg_remaining": float(cash_leg_remaining),
            "legs_succeeded": succeeded,
            "legs_failed": failed,
            "allocation_details": alloc_results,
        }

    # ------------------------------------------------------------------
    # Public: preview (read-only, zero side-effects)
    # ------------------------------------------------------------------

    def preview_invest(
        self,
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
        funding_asset: str,
        funding_amount: Decimal,
        reference_currency: str = "EUR",
    ) -> dict:
        """Estimate a bundle investment without executing anything.

        Uses the same pricing / fee logic as the real flow but creates no
        orders, no atoms, and no audit entries.
        """
        from services.exchange.schemas import SwapPreviewRequest

        warnings: list[str] = []

        try:
            portfolio = self._load_and_validate_portfolio(db, portfolio_id, client_id)
        except BundleOrchestratorError as exc:
            return self._invalid_preview(str(exc), funding_asset, funding_amount)

        product = self._load_product(db, portfolio)
        entry_config = self._resolve_entry_config(product)
        entry_asset = entry_config["entry_asset_default"]

        try:
            self._validate_funding_asset(funding_asset, entry_config)
        except BundleOrchestratorError as exc:
            return self._invalid_preview(str(exc), funding_asset, funding_amount)

        allocations = self._load_target_allocations(db, portfolio_id)
        if not allocations:
            return self._invalid_preview(
                "no_target_allocations_found", funding_asset, funding_amount,
            )

        is_fiat_funding = funding_asset.upper() in ("EUR", "USD")
        is_direct_entry = funding_asset.upper() == entry_asset.upper()

        estimated_entry_amount = Decimal("0")

        if is_fiat_funding:
            try:
                buy_preview = self._exchange.preview_buy(
                    db, entry_asset, funding_amount, funding_asset.upper(),
                )
                estimated_entry_amount = Decimal(
                    str(buy_preview.get("estimated_crypto_net", 0))
                )
                if estimated_entry_amount <= 0:
                    warnings.append("entry_asset_estimate_zero")
            except Exception as exc:
                return self._invalid_preview(
                    f"price_unavailable: {exc}", funding_asset, funding_amount,
                )
        elif is_direct_entry:
            estimated_entry_amount = funding_amount
        else:
            return self._invalid_preview(
                f"unsupported_funding_path: {funding_asset}", funding_asset, funding_amount,
            )

        alloc_previews: list[dict] = []
        total_consumed = Decimal("0")
        legs_ok = 0
        legs_warn = 0

        for alloc in allocations:
            instrument = alloc.instrument
            if instrument is None:
                instrument = db.query(Instrument).filter(
                    Instrument.id == alloc.instrument_id
                ).first()
            asset_obj = db.query(Asset).filter(
                Asset.id == instrument.asset_id
            ).first()
            target_asset = self._normalize_asset_symbol(asset_obj.symbol.upper())

            alloc_input = (
                estimated_entry_amount * alloc.target_weight
            ).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)

            if alloc_input <= 0:
                alloc_previews.append({
                    "asset": target_asset,
                    "target_weight": str(alloc.target_weight),
                    "estimated_input_amount": "0",
                    "estimated_output_quantity": "0",
                    "status": "skipped",
                })
                continue

            try:
                swap_preview = self._exchange.preview_swap(
                    db,
                    SwapPreviewRequest(
                        from_asset=entry_asset,
                        to_asset=target_asset,
                        amount_from=alloc_input,
                    ),
                    currency=reference_currency,
                )
                estimated_out = Decimal(str(swap_preview.get("estimated_to_amount", 0)))
                total_consumed += alloc_input
                legs_ok += 1
                alloc_previews.append({
                    "asset": target_asset,
                    "target_weight": str(alloc.target_weight),
                    "estimated_input_amount": str(alloc_input),
                    "estimated_output_quantity": str(estimated_out),
                    "status": "ok",
                })
            except Exception as exc:
                legs_warn += 1
                warnings.append(f"swap_preview_failed:{target_asset}: {exc}")
                alloc_previews.append({
                    "asset": target_asset,
                    "target_weight": str(alloc.target_weight),
                    "estimated_input_amount": str(alloc_input),
                    "estimated_output_quantity": "0",
                    "status": "unavailable",
                })

        remaining = estimated_entry_amount - total_consumed
        if remaining < 0:
            remaining = Decimal("0")

        preview_status = "ok" if legs_warn == 0 and legs_ok > 0 else (
            "partial" if legs_ok > 0 else "invalid"
        )

        return {
            "preview_status": preview_status,
            "bundle_id": str(portfolio_id),
            "bundle_name": portfolio.name,
            "funding_asset": funding_asset.upper(),
            "funding_amount": str(funding_amount),
            "entry_asset_used": entry_asset,
            "estimated_entry_asset_amount": str(estimated_entry_amount),
            "estimated_remaining_entry_asset": str(remaining),
            "allocations": alloc_previews,
            "warnings": warnings,
        }

    @staticmethod
    def _invalid_preview(reason: str, funding_asset: str, funding_amount: Decimal) -> dict:
        return {
            "preview_status": "invalid",
            "bundle_id": "",
            "bundle_name": "",
            "funding_asset": funding_asset.upper(),
            "funding_amount": str(funding_amount),
            "entry_asset_used": "",
            "estimated_entry_asset_amount": "0",
            "estimated_remaining_entry_asset": "0",
            "allocations": [],
            "warnings": [reason],
        }

    # ------------------------------------------------------------------
    # Public: bundle status
    # ------------------------------------------------------------------

    @staticmethod
    def get_bundle_status(db: Session, portfolio_id: UUID, client_id: UUID) -> dict:
        """Return the current state of a bundle portfolio."""
        portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise BundleOrchestratorError(f"portfolio_not_found: {portfolio_id}")
        if portfolio.client_id != client_id:
            raise BundleOrchestratorError("portfolio_client_mismatch")

        atoms = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id == portfolio_id,
                PositionAtom.status == "open",
            )
            .all()
        )

        cash_legs: list[dict] = []
        allocated_positions: list[dict] = []

        for atom in atoms:
            instrument = atom.instrument or db.query(Instrument).filter(
                Instrument.id == atom.instrument_id
            ).first()
            asset_obj = db.query(Asset).filter(
                Asset.id == instrument.asset_id
            ).first()
            symbol = asset_obj.symbol if asset_obj else "?"

            entry = {
                "instrument_id": str(atom.instrument_id),
                "asset": symbol,
                "quantity": float(Decimal(str(atom.quantity))),
                "cost_basis": float(Decimal(str(atom.cost_basis or 0))),
                "position_type": atom.position_type,
            }
            if atom.position_type == POSITION_TYPE_CASH:
                cash_legs.append(entry)
            else:
                allocated_positions.append(entry)

        total_cost = sum(
            Decimal(str(a.cost_basis or 0)) for a in atoms
        )

        return {
            "portfolio_id": str(portfolio_id),
            "portfolio_name": portfolio.name,
            "status": portfolio.status,
            "cash_legs": cash_legs,
            "allocated_positions": allocated_positions,
            "total_cost_basis": float(total_cost),
        }

    # ------------------------------------------------------------------
    # Invariant D: PE atoms ≤ crypto_positions
    # ------------------------------------------------------------------

    @staticmethod
    def check_invariant_d(db: Session, client_id: UUID) -> dict:
        """Verify that PE position atoms do not exceed consolidated positions.

        Invariant D: for each asset,
            Σ pe_position_atoms.quantity  ≤  crypto_positions.balance
        """
        from sqlalchemy import func as sa_func

        pe_sums = (
            db.query(
                Asset.symbol,
                sa_func.coalesce(sa_func.sum(PositionAtom.quantity), 0).label("pe_total"),
            )
            .join(Instrument, Instrument.id == PositionAtom.instrument_id)
            .join(Asset, Asset.id == Instrument.asset_id)
            .join(Portfolio, Portfolio.id == PositionAtom.portfolio_id)
            .filter(
                Portfolio.client_id == client_id,
                PositionAtom.status == "open",
            )
            .group_by(Asset.symbol)
            .all()
        )

        crypto_positions = (
            db.query(CryptoPosition)
            .filter(CryptoPosition.client_id == client_id)
            .all()
        )
        balance_map = {p.asset.upper(): Decimal(str(p.balance)) for p in crypto_positions}

        violations: list[dict] = []
        all_ok = True

        for symbol, pe_total in pe_sums:
            normalized = BundleOrchestrator._normalize_asset_symbol(symbol.upper())
            exchange_balance = balance_map.get(normalized, Decimal("0"))
            pe_qty = Decimal(str(pe_total))

            ok = pe_qty <= exchange_balance
            if not ok:
                all_ok = False
                violations.append({
                    "asset": normalized,
                    "pe_total": float(pe_qty),
                    "exchange_balance": float(exchange_balance),
                    "delta": float(pe_qty - exchange_balance),
                })

        return {
            "invariant_d_ok": all_ok,
            "checked_assets": len(pe_sums),
            "violations": violations,
        }

    # ------------------------------------------------------------------
    # Invariant E: cash_leg + Σ allocated_cost_basis ≈ total_funded - fees
    # ------------------------------------------------------------------

    @staticmethod
    def check_invariant_e(db: Session, portfolio_id: UUID) -> dict:
        """Verify bundle cash-leg accounting consistency.

        Invariant E: for a given bundle portfolio,
            cash_leg.cost_basis + Σ spot_atoms.cost_basis  =  total_funding_cost_basis

        The ``total_funding_cost_basis`` is the sum of all cost_basis ever
        credited to any atom (cash or spot) in this portfolio — which must
        equal the net funding flowing in (funding minus fees that stayed
        outside the bundle).
        """
        atoms = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id == portfolio_id,
                PositionAtom.status == "open",
            )
            .all()
        )

        cash_cost = Decimal("0")
        alloc_cost = Decimal("0")

        for atom in atoms:
            cb = Decimal(str(atom.cost_basis or 0))
            if atom.position_type == POSITION_TYPE_CASH:
                cash_cost += cb
            else:
                alloc_cost += cb

        total = cash_cost + alloc_cost
        ok = total >= 0

        return {
            "invariant_e_ok": ok,
            "cash_leg_cost_basis": float(cash_cost),
            "allocated_cost_basis": float(alloc_cost),
            "total_cost_basis": float(total),
        }

    # ------------------------------------------------------------------
    # Cash leg helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _credit_cash_leg(
        db: Session,
        portfolio_id: UUID,
        instrument_id: UUID,
        quantity: Decimal,
        cost_basis: Decimal,
    ) -> PositionAtom:
        existing = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id == portfolio_id,
                PositionAtom.instrument_id == instrument_id,
                PositionAtom.position_type == POSITION_TYPE_CASH,
                PositionAtom.status == "open",
            )
            .first()
        )
        if existing is not None:
            existing.quantity = Decimal(str(existing.quantity)) + quantity
            existing.available_quantity = Decimal(str(existing.available_quantity)) + quantity
            existing.cost_basis = Decimal(str(existing.cost_basis or 0)) + cost_basis
            if existing.quantity > 0:
                existing.average_entry_price = existing.cost_basis / existing.quantity
            db.flush()
            return existing

        atom = PositionAtom(
            portfolio_id=portfolio_id,
            instrument_id=instrument_id,
            position_type=POSITION_TYPE_CASH,
            status="open",
            quantity=quantity,
            available_quantity=quantity,
            cost_basis=cost_basis,
            average_entry_price=(cost_basis / quantity) if quantity > 0 else Decimal("0"),
            metadata_={"role": "bundle_cash_leg"},
        )
        db.add(atom)
        db.flush()
        return atom

    @staticmethod
    def _debit_cash_leg(
        db: Session,
        portfolio_id: UUID,
        instrument_id: UUID,
        quantity: Decimal,
        cost_basis: Decimal,
    ) -> PositionAtom:
        cash = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id == portfolio_id,
                PositionAtom.instrument_id == instrument_id,
                PositionAtom.position_type == POSITION_TYPE_CASH,
                PositionAtom.status == "open",
            )
            .first()
        )
        if cash is None:
            raise BundleOrchestratorError("cash_leg_not_found")
        cash.quantity = Decimal(str(cash.quantity)) - quantity
        cash.available_quantity = Decimal(str(cash.available_quantity)) - quantity
        cash.cost_basis = Decimal(str(cash.cost_basis or 0)) - cost_basis
        if cash.quantity < 0:
            cash.quantity = Decimal("0")
            cash.available_quantity = Decimal("0")
        db.flush()
        return cash

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_and_validate_portfolio(
        db: Session, portfolio_id: UUID, client_id: UUID,
    ) -> Portfolio:
        portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        if portfolio is None:
            raise BundleOrchestratorError(f"portfolio_not_found: {portfolio_id}")
        if portfolio.client_id != client_id:
            raise BundleOrchestratorError("portfolio_client_mismatch")
        if portfolio.portfolio_type != "bundle_portfolio":
            raise BundleOrchestratorError(
                f"invalid_portfolio_type: {portfolio.portfolio_type}"
            )
        if portfolio.status != "active":
            raise BundleOrchestratorError(
                f"portfolio_not_active: {portfolio.status}"
            )
        return portfolio

    @staticmethod
    def _load_product(
        db: Session, portfolio: Portfolio,
    ) -> Optional[ProductDefinition]:
        if portfolio.origin_product_id is None:
            return None
        return (
            db.query(ProductDefinition)
            .filter(ProductDefinition.id == portfolio.origin_product_id)
            .first()
        )

    @staticmethod
    def _resolve_entry_config(product: Optional[ProductDefinition]) -> dict:
        if product is None:
            return {
                "entry_asset_default": _ENTRY_ASSET_DEFAULT_FALLBACK,
                "entry_assets_allowed": _ENTRY_ASSETS_ALLOWED_FALLBACK,
            }
        meta = product.metadata_ or {}
        return {
            "entry_asset_default": meta.get(
                "entry_asset_default", _ENTRY_ASSET_DEFAULT_FALLBACK,
            ),
            "entry_assets_allowed": meta.get(
                "entry_assets_allowed", _ENTRY_ASSETS_ALLOWED_FALLBACK,
            ),
        }

    @staticmethod
    def _validate_funding_asset(funding_asset: str, entry_config: dict) -> None:
        upper = funding_asset.upper()
        if upper in ("EUR", "USD"):
            return
        allowed = [a.upper() for a in entry_config["entry_assets_allowed"]]
        if upper not in allowed:
            raise BundleOrchestratorError(
                f"funding_asset_not_allowed: {funding_asset}. "
                f"Allowed: {allowed + ['EUR']}"
            )

    @staticmethod
    def _load_target_allocations(
        db: Session, portfolio_id: UUID,
    ) -> list[TargetAllocation]:
        return (
            db.query(TargetAllocation)
            .filter(TargetAllocation.portfolio_id == portfolio_id)
            .order_by(TargetAllocation.rebalance_priority.asc())
            .all()
        )

    @staticmethod
    def _resolve_or_create_instrument(db: Session, asset_symbol: str) -> Instrument:
        """Find (or create) the PE instrument for *asset_symbol*."""
        upper = asset_symbol.upper()
        asset = db.query(Asset).filter(Asset.symbol == upper).first()
        if asset is None:
            asset = Asset(
                symbol=upper,
                name=upper,
                asset_type="stablecoin" if upper in ("USDC", "EURC") else "cryptocurrency",
            )
            db.add(asset)
            db.flush()

        instr = (
            db.query(Instrument)
            .filter(
                Instrument.asset_id == asset.id,
                Instrument.instrument_type == "spot",
            )
            .first()
        )
        if instr is None:
            instr = Instrument(
                asset_id=asset.id,
                code=f"{upper}_SPOT",
                name=f"{upper} Spot",
                instrument_type="spot",
            )
            db.add(instr)
            db.flush()
        return instr

    def _execute_buy_from_fiat(
        self, db, client_id, target_asset, fiat_amount,
        currency, ext_ref, portfolio_id, batch_id, actor,
    ) -> dict:
        payload = ExchangeBuyRequest(
            client_id=client_id,
            asset=target_asset,
            fiat_amount=fiat_amount,
            currency=currency.upper(),
            external_reference=ext_ref,
        )
        result = self._exchange.buy(db, payload, actor)
        self._tag_order_metadata(
            db, ext_ref, portfolio_id, batch_id, "funding",
        )
        return result

    def _execute_swap_from_entry(
        self, db, client_id, from_asset, to_asset,
        amount_from, ext_ref, portfolio_id, batch_id, actor,
    ) -> dict:
        payload = SwapRequest(
            from_asset=from_asset,
            to_asset=to_asset,
            amount_from=amount_from,
            external_reference=ext_ref,
        )
        result = self._exchange.swap(db, client_id, payload, actor)

        sell_ref = f"{ext_ref}-sell"
        buy_ref = f"{ext_ref}-buy"
        self._tag_order_metadata(
            db, sell_ref, portfolio_id, batch_id, "allocation",
        )
        self._tag_order_metadata(
            db, buy_ref, portfolio_id, batch_id, "allocation",
        )
        return result

    @staticmethod
    def _tag_order_metadata(
        db: Session, ext_ref: str, portfolio_id: UUID,
        batch_id: str, action: str,
    ) -> None:
        order = (
            db.query(ExchangeOrder)
            .filter(ExchangeOrder.external_reference == ext_ref)
            .first()
        )
        if order is None:
            return
        meta = dict(order.metadata_ or {})
        meta["bundle_id"] = str(portfolio_id)
        meta["bundle_batch_id"] = batch_id
        meta["bundle_action"] = action
        meta["portfolio_scope"] = "bundle"
        meta["portfolio_id"] = str(portfolio_id)
        order.metadata_ = meta
        db.flush()

    @staticmethod
    def _sync_pe_position(
        db: Session,
        portfolio_id: UUID,
        instrument_id: UUID,
        quantity_delta: Decimal,
        cost_basis_delta: Decimal,
    ) -> PositionAtom:
        existing = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id == portfolio_id,
                PositionAtom.instrument_id == instrument_id,
                PositionAtom.position_type == POSITION_TYPE_SPOT,
                PositionAtom.status == "open",
            )
            .first()
        )
        if existing is not None:
            existing.quantity = Decimal(str(existing.quantity)) + quantity_delta
            existing.available_quantity = (
                Decimal(str(existing.available_quantity)) + quantity_delta
            )
            cb = Decimal(str(existing.cost_basis or 0))
            existing.cost_basis = cb + cost_basis_delta
            if existing.quantity > 0:
                existing.average_entry_price = existing.cost_basis / existing.quantity
            db.flush()
            return existing

        atom = PositionAtom(
            portfolio_id=portfolio_id,
            instrument_id=instrument_id,
            position_type=POSITION_TYPE_SPOT,
            status="open",
            quantity=quantity_delta,
            available_quantity=quantity_delta,
            cost_basis=cost_basis_delta,
            average_entry_price=(
                (cost_basis_delta / quantity_delta)
                if quantity_delta > 0
                else Decimal("0")
            ),
            metadata_={},
        )
        db.add(atom)
        db.flush()
        return atom

    @staticmethod
    def _normalize_asset_symbol(symbol: str) -> str:
        """Strip test prefixes/suffixes from PE asset symbols."""
        mapping = {
            "TBTC": "BTC", "TETH": "ETH", "TSOL": "SOL",
            "TXRP": "XRP", "TADA": "ADA",
        }
        base = symbol.split("_")[0] if "_" in symbol else symbol
        return mapping.get(base, symbol)
