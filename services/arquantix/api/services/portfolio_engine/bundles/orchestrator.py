"""BundleOrchestrator — Phase 2: True entry-asset cash leg.

Flow (modèle Vancelian — fund PE first, allocate on-chain ensuite)::

    1. Fund comptable : direct_portfolio(entry) → bundle cash leg (Privy inchangé)
    2. Allocation   : cash leg → bundle spot via swap (Privy bouge à confirmation LI.FI)

Legacy Exchange::

    EUR → BUY entry_asset → fund cash leg → SWAP to each target → debit cash leg

The cash leg is a ``PositionAtom`` with ``position_type='cash'``.  Allocation
positions use ``position_type='spot'``.  Both live in the same PE portfolio,
giving a complete overlay view of the bundle without modifying
``crypto_positions`` until on-chain execution.
"""
from __future__ import annotations

import logging
import uuid as uuid_mod
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.exchange.models import CryptoPosition, ExchangeOrder
from services.exchange.service import ExchangeError, ExchangeService
from services.portfolio_engine.bundle_execution import BundleExecutionAdapter
from services.portfolio_engine.bundle_execution.bundle_cost_basis import reference_cost_basis_eur
from services.portfolio_engine.bundle_execution.lifi_base_config import (
    display_bundle_asset,
    normalize_bundle_asset,
)
from services.portfolio_engine.bundle_execution.types import ExecutionLeg
from services.portfolio_engine.invariants.invariant_g import check_invariant_g
from services.portfolio_engine.allocations.models import TargetAllocation
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.hardening.audit_service import AuditService
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom
from services.portfolio_engine.products.models import ProductDefinition

from .preview_warnings import (
    build_exchange_preview_warning,
    build_lifi_preview_warning,
    build_lifi_preview_warning_from_exc,
)
from .bundle_invest_lock import (
    acquire_invest_lock,
    assert_no_active_invest_lock,
    clear_invest_lock,
    get_invest_lock,
    load_portfolio_for_invest_lock,
    reconcile_idle_invest_lock_for_invest,
    release_invest_lock,
    update_invest_lock_status,
)

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

    def __init__(
        self,
        execution_adapter: Optional[BundleExecutionAdapter] = None,
        exchange_service: Optional[ExchangeService] = None,
    ):
        self._execution = execution_adapter or BundleExecutionAdapter()
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

        entry_instrument = self._resolve_or_create_instrument(db, entry_asset)

        if self._execution.provider_name == "lifi_base":
            is_direct_entry = funding_asset.upper() == entry_asset.upper()
            if is_direct_entry:
                return self._invest_via_lifi(
                    db,
                    client_id=client_id,
                    portfolio_id=portfolio_id,
                    portfolio=portfolio,
                    entry_asset=entry_asset,
                    entry_instrument=entry_instrument,
                    funding_amount=funding_amount,
                    allocations=allocations,
                )

        actor = ActorContext(
            actor_type="system",
            actor_id=f"bundle-orchestrator-{portfolio_id}",
        )
        batch_id = str(uuid_mod.uuid4())

        from services.portfolio_engine.bundle_execution.bundle_funding import (
            BundleFundingError,
            fund_bundle_cash_leg_from_self_trading,
        )
        from services.portfolio_engine.clients.models import Client as _Client

        _client_row = db.query(_Client).filter(_Client.id == client_id).first()
        person_id = _client_row.person_id if _client_row is not None else None

        # ── Step 1: Funding — acquire entry asset ────────────────────────
        is_fiat_funding = funding_asset.upper() in ("EUR", "USD")
        is_direct_entry = funding_asset.upper() == entry_asset.upper()

        funding_result: dict = {}
        entry_qty_received = Decimal("0")

        if is_fiat_funding:
            ext_ref = f"bundle-fund-{batch_id}"
            buy_result = self._execute_buy_from_fiat(
                db, client_id, entry_asset, funding_amount,
                funding_asset, ext_ref, portfolio_id, batch_id, actor,
            )
            entry_qty_received = Decimal(str(buy_result.get("amount_crypto", 0)))
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
            funding_result = {
                "action": "direct_entry_asset",
                "entry_asset": entry_asset,
                "amount": float(funding_amount),
            }
        else:
            raise BundleOrchestratorError(
                f"unsupported_funding_path: {funding_asset} → {entry_asset}"
            )

        if entry_qty_received <= 0:
            raise BundleOrchestratorError("entry_asset_quantity_zero")

        try:
            pe_funding = fund_bundle_cash_leg_from_self_trading(
                db,
                client_id=client_id,
                person_id=person_id,
                portfolio_id=portfolio_id,
                entry_asset=entry_asset,
                entry_instrument_id=entry_instrument.id,
                amount=entry_qty_received,
                batch_id=batch_id,
            )
            funding_result = {**funding_result, **pe_funding, "funding_path": funding_result.get("action")}
        except BundleFundingError as exc:
            raise BundleOrchestratorError(str(exc)) from exc

        # ── Step 2: Allocate from cash leg ───────────────────────────────
        from services.portfolio_engine.bundle_execution.allocation_planner import (
            plan_allocation_legs,
        )
        from services.portfolio_engine.bundle_execution.allocation_parallel import (
            run_allocation_legs_sequential,
        )

        planned_legs, allocatable, execution_buffer, plan_cash_remaining = plan_allocation_legs(
            db,
            allocations=allocations,
            fund_amount=entry_qty_received,
            batch_id=batch_id,
            normalize_asset_fn=self._normalize_asset_symbol,
        )
        cash_available = plan_cash_remaining + execution_buffer
        alloc_results, leg_stats = run_allocation_legs_sequential(
            self,
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            entry_asset=entry_asset,
            entry_instrument_id=entry_instrument.id,
            batch_id=batch_id,
            actor=actor,
            planned_legs=planned_legs,
            initial_cash_available=allocatable,
        )
        succeeded = leg_stats.succeeded
        failed = leg_stats.failed
        total_entry_consumed = leg_stats.total_entry_consumed
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

        result = {
            "status": status,
            "batch_id": batch_id,
            "portfolio_id": str(portfolio_id),
            "entry_asset": entry_asset,
            "funding": funding_result,
            "total_entry_asset_received": float(entry_qty_received),
            "total_entry_asset_consumed": float(total_entry_consumed),
            "cash_leg_remaining": float(cash_leg_remaining),
            "execution_buffer": float(execution_buffer),
            "allocatable_amount": float(allocatable),
            "legs_succeeded": succeeded,
            "legs_failed": failed,
            "allocation_details": alloc_results,
            "execution_provider": self._execution.provider_name,
        }
        if any(r.get("status") == "pending" for r in alloc_results):
            result["status"] = "pending_signature" if succeeded == 0 else "partial_pending"
        return result

    def _invest_via_lifi(
        self,
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
        portfolio: Portfolio,
        entry_asset: str,
        entry_instrument: Instrument,
        funding_amount: Decimal,
        allocations: list[TargetAllocation],
    ) -> dict:
        """Investissement Base LI.FI — fund PE first, allocate on-chain ensuite.

        1. Transfert comptable self-trading → cash leg (Privy inchangé).
        2. Legs Li.FI : à confirmation, débit cash leg + crédit spot + settlement Privy.
        """
        import uuid as _uuid

        from services.portfolio_engine.bundle_execution.bundle_funding import (
            BundleFundingError,
            fund_bundle_cash_leg_from_self_trading,
        )

        portfolio_locked = load_portfolio_for_invest_lock(
            db, client_id=client_id, portfolio_id=portfolio_id,
        )
        reconcile_idle_invest_lock_for_invest(
            db, client_id=client_id, portfolio_id=portfolio_id,
        )
        db.refresh(portfolio_locked)
        assert_no_active_invest_lock(portfolio_locked, client_id)

        batch_id = str(_uuid.uuid4())
        acquire_invest_lock(
            db,
            portfolio_locked,
            client_id=client_id,
            batch_id=batch_id,
            entry_instrument_id=str(entry_instrument.id),
            status="pending_signature",
            funding_asset=entry_asset.upper(),
            funding_amount=str(funding_amount),
        )

        from services.portfolio_engine.clients.models import Client as _Client
        from services.transaction_intents.bundle_intent_sync import ensure_bundle_parent_intent

        _client_row = db.query(_Client).filter(_Client.id == client_id).first()
        person_id = _client_row.person_id if _client_row is not None else None
        if person_id is not None:
            ensure_bundle_parent_intent(
                db,
                person_id=person_id,
                bundle_id=str(portfolio_id),
                batch_id=batch_id,
                extra_metadata={
                    "funding_asset": entry_asset.upper(),
                    "funding_amount": str(funding_amount),
                    "portfolio_name": portfolio.name,
                },
            )

        try:
            funding_result = fund_bundle_cash_leg_from_self_trading(
                db,
                client_id=client_id,
                person_id=person_id,
                portfolio_id=portfolio_id,
                entry_asset=entry_asset,
                entry_instrument_id=entry_instrument.id,
                amount=funding_amount,
                batch_id=batch_id,
            )
        except BundleFundingError as exc:
            release_invest_lock(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                terminal_status="failed",
            )
            raise BundleOrchestratorError(str(exc)) from exc

        actor = ActorContext(
            actor_type="system",
            actor_id=f"bundle-orchestrator-lifi-{portfolio_id}",
        )
        entry_qty_received = funding_amount
        from services.portfolio_engine.bundle_execution.allocation_config import (
            bundle_alloc_parallel_quotes_enabled,
        )
        from services.portfolio_engine.bundle_execution.allocation_parallel import (
            run_allocation_legs_parallel,
            run_allocation_legs_sequential,
        )
        from services.portfolio_engine.bundle_execution.allocation_planner import (
            plan_allocation_legs,
        )

        planned_legs, allocatable, execution_buffer, plan_cash_remaining = plan_allocation_legs(
            db,
            allocations=allocations,
            fund_amount=funding_amount,
            batch_id=batch_id,
            normalize_asset_fn=self._normalize_asset_symbol,
        )
        cash_available = plan_cash_remaining + execution_buffer
        alloc_results: list[dict] = []

        from services.portfolio_engine.bundle_execution.allocation_observability import (
            log_allocation_event,
        )

        person_id_str = str(person_id) if person_id is not None else None
        log_allocation_event(
            "plan_created",
            person_id=person_id_str,
            portfolio_id=str(portfolio_id),
            batch_id=batch_id,
            fund_amount=float(funding_amount),
            buffer_amount=float(execution_buffer),
            allocatable_amount=float(allocatable),
            legs_count=len(planned_legs),
            parallel_enabled=bundle_alloc_parallel_quotes_enabled(),
        )

        use_parallel = (
            bundle_alloc_parallel_quotes_enabled()
            and self._execution.provider_name == "lifi_base"
            and len(planned_legs) > 1
        )
        if use_parallel:
            alloc_results, leg_stats = run_allocation_legs_parallel(
                self,
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                entry_asset=entry_asset,
                entry_instrument_id=entry_instrument.id,
                batch_id=batch_id,
                actor=actor,
                planned_legs=planned_legs,
                initial_cash_available=allocatable,
                person_id=person_id_str,
                fund_amount=funding_amount,
                buffer_amount=execution_buffer,
                allocatable_amount=allocatable,
            )
        else:
            alloc_results, leg_stats = run_allocation_legs_sequential(
                self,
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                entry_asset=entry_asset,
                entry_instrument_id=entry_instrument.id,
                batch_id=batch_id,
                actor=actor,
                planned_legs=planned_legs,
                initial_cash_available=allocatable,
                execution_asset_from_planned=True,
            )

        succeeded = leg_stats.succeeded
        failed = leg_stats.failed
        pending = leg_stats.pending
        total_entry_consumed = leg_stats.total_entry_consumed
        cash_leg_remaining = cash_available
        log_allocation_event(
            "residual_cash",
            person_id=person_id_str,
            portfolio_id=str(portfolio_id),
            batch_id=batch_id,
            fund_amount=float(funding_amount),
            buffer_amount=float(execution_buffer),
            allocatable_amount=float(allocatable),
            legs_count=len(planned_legs),
            parallel_enabled=use_parallel,
            residual_cash=float(cash_leg_remaining),
            legs_succeeded=succeeded,
            legs_failed=failed,
            legs_pending=pending,
        )
        if succeeded > 0 and pending == 0 and failed == 0:
            status = "completed"
        elif pending > 0:
            status = "pending_signature" if succeeded == 0 else "partial_pending"
        elif succeeded > 0:
            status = "partial"
        else:
            status = "failed"

        if status == "completed":
            clear_invest_lock(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
            )
        elif status == "failed":
            release_invest_lock(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                terminal_status="failed",
            )
        elif pending == 0:
            # État récupérable — partial ou échec sans legs en attente (cash leg intacte).
            if status == "partial" and succeeded > 0:
                clear_invest_lock(
                    db,
                    client_id=client_id,
                    portfolio_id=portfolio_id,
                    batch_id=batch_id,
                )
            else:
                release_invest_lock(
                    db,
                    client_id=client_id,
                    portfolio_id=portfolio_id,
                    batch_id=batch_id,
                    terminal_status="failed",
                )
        else:
            update_invest_lock_status(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                status=status,
            )

        invariant_g = check_invariant_g(db, client_id, dry_run=True)

        if _client_row is not None and _client_row.person_id is not None:
            from services.transaction_intents.bundle_intent_sync import (
                recompute_bundle_parent_intent,
                sync_bundle_parent_from_batch_status,
            )

            if status == "completed":
                recompute_bundle_parent_intent(
                    db,
                    person_id=_client_row.person_id,
                    bundle_id=str(portfolio_id),
                    batch_id=batch_id,
                )
            else:
                sync_bundle_parent_from_batch_status(
                    db,
                    person_id=_client_row.person_id,
                    bundle_id=str(portfolio_id),
                    batch_id=batch_id,
                    batch_status=status,
                )

        return {
            "status": status,
            "batch_id": batch_id,
            "portfolio_id": str(portfolio_id),
            "entry_asset": entry_asset,
            "entry_instrument_id": str(entry_instrument.id),
            "funding": {
                **funding_result,
                "funding_path": "direct_entry_asset_lifi",
                "entry_asset": entry_asset,
                "amount": float(funding_amount),
            },
            "total_entry_asset_received": float(entry_qty_received),
            "total_entry_asset_consumed": float(total_entry_consumed),
            "cash_leg_remaining": float(cash_leg_remaining),
            "execution_buffer": float(execution_buffer),
            "allocatable_amount": float(allocatable),
            "parallel_quotes": use_parallel,
            "legs_succeeded": succeeded,
            "legs_failed": failed,
            "legs_pending": pending,
            "allocation_details": alloc_results,
            "execution_provider": "lifi_base",
            "invariant_g": invariant_g,
        }

    def _run_allocation_leg(
        self,
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
        entry_asset: str,
        entry_instrument_id: UUID,
        target_asset: str,
        target_instrument_id: UUID,
        alloc_entry_amount: Decimal,
        ext_ref: str,
        batch_id: str,
        actor: ActorContext,
    ) -> dict:
        leg = ExecutionLeg(
            leg_id=ext_ref,
            portfolio_id=portfolio_id,
            client_id=client_id,
            action="allocation",
            from_asset=entry_asset.upper(),
            to_asset=target_asset.upper(),
            amount_from=alloc_entry_amount,
            batch_id=batch_id,
            bundle_action="allocation",
            chain="base",
            metadata={
                "entry_instrument_id": str(entry_instrument_id),
                "target_instrument_id": str(target_instrument_id),
                "planned_amount_in": str(alloc_entry_amount),
            },
        )
        result = self._execution.execute_leg(db, leg, actor)

        if result.status == "pending":
            est_receive = float(result.amount_to or 0)
            record = {
                "asset": target_asset,
                "instrument_id": str(target_instrument_id),
                "target_weight": None,
                "entry_asset_consumed": float(alloc_entry_amount),
                "crypto_received": est_receive,
                "status": "pending",
                "swap_id": result.provider_order_id,
                "leg_id": ext_ref,
                "signing": result.raw.get("prepare"),
            }
            return {"status": "pending", "record": record}

        if self._execution.provider_name == "lifi_base":
            record = {
                "asset": target_asset,
                "instrument_id": str(target_instrument_id),
                "entry_asset_consumed": float(alloc_entry_amount),
                "crypto_received": float(result.amount_to or 0),
                "status": "completed",
                "swap_id": result.provider_order_id,
                "tx_hash": result.tx_hash,
            }
            return {"status": "completed", "record": record}

        swap_result = result.to_swap_legacy_dict()
        crypto_received = Decimal(str(swap_result.get("amount_to", 0)))
        ref_value_net = Decimal(
            str(swap_result.get("reference_value_net", alloc_entry_amount))
        )
        self._sync_pe_position(
            db, portfolio_id, target_instrument_id,
            crypto_received, ref_value_net,
        )
        self._debit_cash_leg(
            db, portfolio_id, entry_instrument_id,
            alloc_entry_amount, ref_value_net,
        )
        record = {
            "asset": target_asset,
            "instrument_id": str(target_instrument_id),
            "entry_asset_consumed": float(alloc_entry_amount),
            "crypto_received": float(crypto_received),
            "status": "completed",
            "swap_group_id": str(swap_result.get("swap_group_id", "")),
        }
        return {"status": "completed", "record": record}

    def finalize_lifi_batch(
        self,
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
        batch_id: str,
        entry_instrument_id: UUID,
        planned_entry_total: Decimal,
        entry_consumed: Decimal,
    ) -> dict:
        """Finalise un batch LI.FI après legs confirmés (cash leg déjà alimenté au fund).

        Les USDC non alloués restent en cash leg — état récupérable, non bloquant.
        """
        from services.portfolio_engine.bundles.bundle_invest_lock import (
            get_invest_lock,
            load_portfolio_for_invest_lock,
            reconcile_or_expire_idle_invest_lock,
        )

        portfolio_locked = load_portfolio_for_invest_lock(
            db, client_id=client_id, portfolio_id=portfolio_id,
        )
        lock = get_invest_lock(portfolio_locked.metadata_)
        if lock is not None and str(lock.get("batch_id")) == batch_id:
            update_invest_lock_status(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                status="finalizing",
            )

        remaining = planned_entry_total - entry_consumed
        invariant_g = check_invariant_g(db, client_id, dry_run=True)
        from services.portfolio_engine.clients.models import Client as _Client
        from services.transaction_intents.bundle_intent_sync import recompute_bundle_parent_intent

        _client_row = db.query(_Client).filter(_Client.id == client_id).first()
        if _client_row is not None and _client_row.person_id is not None:
            recompute_bundle_parent_intent(
                db,
                person_id=_client_row.person_id,
                bundle_id=str(portfolio_id),
                batch_id=batch_id,
            )

        clear_invest_lock(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
        )
        reconcile_or_expire_idle_invest_lock(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            portfolio=portfolio_locked,
        )
        return {
            "batch_id": batch_id,
            "cash_leg_remaining": float(remaining),
            "cash_leg_credited": 0.0,
            "recoverable_cash_in_bundle": float(remaining) if remaining > 0 else 0.0,
            "invariant_g": invariant_g,
        }

    def resume_lifi_invest_batch(
        self,
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
    ) -> dict:
        """Reconstruit le payload invest pour reprendre les legs LI.FI pending d'un batch."""
        from uuid import UUID as _UUID

        from services.lifi.enums import SwapSessionStatus
        from services.lifi.models import PersonWalletSwap
        from services.portfolio_engine.bundle_execution.bundle_funding import (
            resolve_bundle_cash_leg_available,
        )
        from services.portfolio_engine.bundle_execution.bundle_lifi_leg_service import (
            BundleLifiLegService,
        )
        from services.portfolio_engine.clients.models import Client as _Client
        from services.transaction_intents.bundle_intent_sync import bundle_context_from_swap_audit

        portfolio = self._load_and_validate_portfolio(db, portfolio_id, client_id)
        portfolio_locked = load_portfolio_for_invest_lock(
            db, client_id=client_id, portfolio_id=portfolio_id,
        )
        lock = get_invest_lock(portfolio_locked.metadata_)
        if lock is None:
            raise BundleOrchestratorError("no_active_invest_lock")

        batch_id = str(lock.get("batch_id") or "").strip()
        if not batch_id:
            raise BundleOrchestratorError("invalid_invest_lock_batch")

        product = self._load_product(db, portfolio)
        entry_config = self._resolve_entry_config(product)
        entry_asset = entry_config["entry_asset_default"]
        entry_instrument = self._resolve_or_create_instrument(db, entry_asset)

        _client_row = db.query(_Client).filter(_Client.id == client_id).first()
        person_id = _client_row.person_id if _client_row is not None else None
        if person_id is None:
            raise BundleOrchestratorError("client_has_no_person_id")

        pending_statuses = {
            SwapSessionStatus.PENDING.value,
            SwapSessionStatus.QUOTE_RECEIVED.value,
            SwapSessionStatus.AWAITING_SIGNATURE.value,
            SwapSessionStatus.SUBMITTED.value,
        }
        swaps = (
            db.query(PersonWalletSwap)
            .filter(
                PersonWalletSwap.person_id == person_id,
                PersonWalletSwap.status.in_(list(pending_statuses)),
            )
            .all()
        )
        leg_svc = BundleLifiLegService()
        alloc_results: list[dict] = []
        pending = 0
        for swap in swaps:
            ctx = bundle_context_from_swap_audit(swap)
            if not ctx or str(ctx.get("batch_id")) != batch_id:
                continue
            action = str(ctx.get("bundle_action") or "")
            if action not in ("allocation", "invest", ""):
                continue
            leg_id = str(ctx.get("leg_id") or "")
            asset = str(swap.to_asset or "")
            signing = None
            try:
                signing = leg_svc.prepare_signing(
                    db, person_id=person_id, swap_id=swap.id,
                ).model_dump()
            except Exception:
                signing = None
            alloc_results.append({
                "asset": asset,
                "instrument_id": str(ctx.get("target_instrument_id") or ""),
                "entry_asset_consumed": float(swap.amount_in or 0),
                "crypto_received": float(swap.estimated_receive or 0),
                "status": "pending",
                "swap_id": str(swap.id),
                "leg_id": leg_id,
                "signing": signing,
            })
            pending += 1

        if pending == 0:
            raise BundleOrchestratorError("no_pending_invest_legs")

        cash_leg_remaining = resolve_bundle_cash_leg_available(
            db,
            portfolio_id=portfolio_id,
            entry_instrument_id=entry_instrument.id,
        )
        funding_amount = lock.get("funding_amount")
        total_received = float(funding_amount) if funding_amount is not None else float(cash_leg_remaining)

        return {
            "status": str(lock.get("status") or "pending_signature"),
            "batch_id": batch_id,
            "portfolio_id": str(portfolio_id),
            "entry_asset": entry_asset,
            "entry_instrument_id": str(entry_instrument.id),
            "total_entry_asset_received": total_received,
            "total_entry_asset_consumed": 0.0,
            "cash_leg_remaining": float(cash_leg_remaining),
            "legs_succeeded": 0,
            "legs_failed": 0,
            "legs_pending": pending,
            "allocation_details": alloc_results,
            "execution_provider": "lifi_base",
            "resumed": True,
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

        Uses Li.FI on-chain quotes when ``BUNDLE_EXECUTION_PROVIDER=lifi_base`` (no Binance
        fallback). Legacy ``exchange`` provider uses ExchangeService pricing only.
        Creates no orders, atoms, or audit entries.
        """
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

        from services.portfolio_engine.bundle_execution.allocation_config import (
            compute_allocatable_amount,
        )

        allocatable_amount, execution_buffer = compute_allocatable_amount(estimated_entry_amount)

        alloc_previews: list[dict] = []
        total_consumed = Decimal("0")
        legs_ok = 0
        legs_warn = 0
        use_lifi_preview = self._execution.provider_name == "lifi_base"
        person_id = self._resolve_person_id(db, client_id) if use_lifi_preview else None

        for alloc in allocations:
            instrument = alloc.instrument
            if instrument is None:
                instrument = db.query(Instrument).filter(
                    Instrument.id == alloc.instrument_id
                ).first()
            asset_obj = db.query(Asset).filter(
                Asset.id == instrument.asset_id
            ).first()
            raw_symbol = self._normalize_asset_symbol(asset_obj.symbol.upper())
            lifi_target = normalize_bundle_asset(raw_symbol)
            display_asset = display_bundle_asset(lifi_target)

            alloc_input = (
                allocatable_amount * alloc.target_weight
            ).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)

            if alloc_input <= 0:
                alloc_previews.append({
                    "asset": lifi_target,
                    "asset_display": display_asset,
                    "target_weight": str(alloc.target_weight),
                    "estimated_input_amount": "0",
                    "estimated_output_quantity": "0",
                    "status": "skipped",
                })
                continue

            leg_preview = self._preview_allocation_leg(
                db,
                entry_asset=entry_asset,
                lifi_target=lifi_target,
                display_asset=display_asset,
                alloc_input=alloc_input,
                target_weight=alloc.target_weight,
                reference_currency=reference_currency,
                use_lifi_preview=use_lifi_preview,
                person_id=person_id,
            )
            alloc_previews.append(leg_preview["row"])
            if leg_preview["status"] == "ok":
                total_consumed += alloc_input
                legs_ok += 1
            else:
                legs_warn += 1
                if leg_preview.get("warning"):
                    warnings.append(leg_preview["warning"])

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
            "execution_buffer": str(execution_buffer),
            "allocatable_amount": str(allocatable_amount),
            "estimated_remaining_entry_asset": str(remaining),
            "allocations": alloc_previews,
            "warnings": warnings,
        }

    def _preview_allocation_leg(
        self,
        db: Session,
        *,
        entry_asset: str,
        lifi_target: str,
        display_asset: str,
        alloc_input: Decimal,
        target_weight: Decimal,
        reference_currency: str,
        use_lifi_preview: bool,
        person_id: UUID | None,
    ) -> dict:
        """Estimate one allocation leg.

        ``lifi_base`` : quote LI.FI on-chain (même modèle que le swap portail) — pas de repli
        Exchange/Binance. ``exchange`` (legacy) : ``ExchangeService.preview_swap`` uniquement.
        """
        base_row = {
            "asset": lifi_target,
            "asset_display": display_asset,
            "target_weight": str(target_weight),
            "estimated_input_amount": str(alloc_input),
            "estimated_output_quantity": "0",
            "status": "unavailable",
        }

        if use_lifi_preview:
            if person_id is None:
                return {
                    "status": "unavailable",
                    "warning": build_lifi_preview_warning(
                        asset=lifi_target,
                        display=display_asset,
                        code="bundle.lifi.no_person_id",
                        detail="Client sans person_id — wallet Privy requis",
                    ),
                    "row": {**base_row, "status": "unavailable"},
                }
            try:
                from services.portfolio_engine.bundle_execution.bundle_lifi_quote_service import (
                    BundleLifiQuoteService,
                )

                quote_svc = BundleLifiQuoteService()
                estimated_out = quote_svc.preview_bundle_quote(
                    db,
                    person_id=person_id,
                    from_asset=entry_asset,
                    to_asset=lifi_target,
                    amount=str(alloc_input),
                )
                return {
                    "status": "ok",
                    "row": {
                        **base_row,
                        "estimated_output_quantity": str(estimated_out),
                        "status": "ok",
                    },
                }
            except Exception as exc:
                logger.warning(
                    "Li.FI bundle preview failed for %s → %s: %s",
                    entry_asset,
                    lifi_target,
                    exc,
                )
                return {
                    "status": "unavailable",
                    "warning": build_lifi_preview_warning_from_exc(
                        asset=lifi_target,
                        display=display_asset,
                        exc=exc,
                    ),
                    "row": {**base_row, "status": "unavailable"},
                }

        from services.exchange.schemas import SwapPreviewRequest

        try:
            swap_preview = self._exchange.preview_swap(
                db,
                SwapPreviewRequest(
                    from_asset=entry_asset,
                    to_asset=lifi_target,
                    amount_from=alloc_input,
                ),
                currency=reference_currency,
            )
            estimated_out = Decimal(str(swap_preview.get("estimated_to_amount", 0)))
            return {
                "status": "ok",
                "row": {
                    **base_row,
                    "estimated_output_quantity": str(estimated_out),
                    "status": "ok",
                },
            }
        except Exception as exc:
            return {
                "status": "unavailable",
                "warning": build_exchange_preview_warning(
                    asset=lifi_target,
                    display=display_asset,
                    detail=str(exc),
                ),
                "row": {**base_row, "status": "unavailable"},
            }

    @staticmethod
    def _resolve_person_id(db: Session, client_id: UUID) -> UUID | None:
        from services.portfolio_engine.clients.models import Client

        client = db.query(Client).filter(Client.id == client_id).first()
        if client is None or client.person_id is None:
            return None
        return client.person_id

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
    def _asset_symbol_for_instrument(db: Session, instrument_id: UUID) -> str:
        instrument = db.query(Instrument).filter(Instrument.id == instrument_id).first()
        if instrument is None:
            raise BundleOrchestratorError(f"instrument_not_found:{instrument_id}")
        asset = db.query(Asset).filter(Asset.id == instrument.asset_id).first()
        if asset is None:
            raise BundleOrchestratorError(f"asset_not_found_for_instrument:{instrument_id}")
        return asset.symbol.upper()

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
        leg = ExecutionLeg(
            leg_id=ext_ref,
            portfolio_id=portfolio_id,
            client_id=client_id,
            action="funding",
            from_asset=currency.upper(),
            to_asset=target_asset.upper(),
            amount_from=fiat_amount,
            batch_id=batch_id,
            bundle_action="funding",
            currency=currency.upper(),
        )
        result = self._execution.execute_leg(db, leg, actor)
        return result.to_buy_legacy_dict()

    def _execute_swap_from_entry(
        self, db, client_id, from_asset, to_asset,
        amount_from, ext_ref, portfolio_id, batch_id, actor,
    ) -> dict:
        leg = ExecutionLeg(
            leg_id=ext_ref,
            portfolio_id=portfolio_id,
            client_id=client_id,
            action="allocation",
            from_asset=from_asset.upper(),
            to_asset=to_asset.upper(),
            amount_from=amount_from,
            batch_id=batch_id,
            bundle_action="allocation",
        )
        result = self._execution.execute_leg(db, leg, actor)
        return result.to_swap_legacy_dict()

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
        meta.setdefault("execution_provider", "exchange")
        meta.setdefault("batch_id", batch_id)
        meta.setdefault("leg_id", ext_ref)
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
