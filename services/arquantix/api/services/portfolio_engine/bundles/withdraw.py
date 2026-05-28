"""BundleWithdrawOrchestrator — retrait bundle miroir du fund-first invest.

Phase 1 (unwind) : bundle_spot → bundle_cash_leg via Li.FI sell legs confirmés
Phase 2 (release) : bundle_cash_leg → direct_portfolio (Privy inchangé)
"""
from __future__ import annotations

import logging
import uuid as uuid_mod
from decimal import Decimal, ROUND_DOWN
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.bundle_execution import BundleExecutionAdapter
from services.portfolio_engine.bundle_execution.bundle_funding import (
    BundleFundingError,
    release_bundle_cash_leg_to_self_trading,
    resolve_bundle_cash_leg_available,
)
from services.portfolio_engine.bundle_execution.lifi_base_config import (
    normalize_bundle_asset,
    resolve_bundle_base_token,
)
from services.portfolio_engine.bundle_execution.types import ExecutionLeg
from services.portfolio_engine.assets.models import Asset
from services.portfolio_engine.hardening.audit_service import AuditService
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.portfolios.models import Portfolio
from services.portfolio_engine.positions.enums import PositionType
from services.portfolio_engine.positions.models import PositionAtom

from .bundle_invest_lock import reconcile_idle_invest_lock_for_withdraw
from .bundle_withdraw_lock import (
    WITHDRAW_PHASE_FAILED_PARTIAL,
    WITHDRAW_PHASE_PARTIALLY_UNWOUND,
    WITHDRAW_PHASE_READY_TO_RELEASE,
    WITHDRAW_PHASE_RELEASED,
    WITHDRAW_PHASE_REQUESTED,
    WITHDRAW_PHASE_UNWINDING,
    acquire_withdraw_lock,
    assert_no_active_withdraw_lock,
    clear_withdraw_lock,
    get_withdraw_lock,
    load_portfolio_for_withdraw_lock,
    update_withdraw_lock,
)
from .orchestrator import (
    BundleOrchestrator,
    BundleOrchestratorError,
    POSITION_TYPE_CASH,
    POSITION_TYPE_SPOT,
)

logger = logging.getLogger(__name__)

TOLERANCE = Decimal("0.000001")


class BundleWithdrawOrchestratorError(Exception):
    pass


class BundleWithdrawOrchestrator:
    def __init__(
        self,
        execution_adapter: Optional[BundleExecutionAdapter] = None,
    ):
        self._execution = execution_adapter or BundleExecutionAdapter()
        self._bundle = BundleOrchestrator(execution_adapter=self._execution)

    def withdraw_from_bundle(
        self,
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
        withdraw_amount: Optional[Decimal] = None,
        full_withdraw: bool = False,
    ) -> dict:
        """Initie un retrait bundle : ventes spot si nécessaire, release différé."""
        portfolio = self._bundle._load_and_validate_portfolio(db, portfolio_id, client_id)
        product = self._bundle._load_product(db, portfolio)
        entry_config = self._bundle._resolve_entry_config(product)
        entry_asset = entry_config["entry_asset_default"]
        entry_instrument = self._bundle._resolve_or_create_instrument(db, entry_asset)

        portfolio_locked = load_portfolio_for_withdraw_lock(
            db, client_id=client_id, portfolio_id=portfolio_id,
        )
        if not reconcile_idle_invest_lock_for_withdraw(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            portfolio=portfolio_locked,
        ):
            raise BundleWithdrawOrchestratorError("invest_lock_active")
        assert_no_active_withdraw_lock(portfolio_locked, client_id)

        status = BundleOrchestrator.get_bundle_status(db, portfolio_id, client_id)
        cash_leg_qty = resolve_bundle_cash_leg_available(
            db,
            portfolio_id=portfolio_id,
            entry_instrument_id=entry_instrument.id,
        )
        spot_positions = self._list_spot_positions(db, portfolio_id)

        total_bundle_value = cash_leg_qty + sum(
            Decimal(str(p["quantity"])) for p in spot_positions
        )
        if total_bundle_value <= TOLERANCE:
            raise BundleWithdrawOrchestratorError("bundle_empty")

        if full_withdraw:
            requested = cash_leg_qty + sum(
                Decimal(str(p["quantity"])) for p in spot_positions
            )
        else:
            if withdraw_amount is None or withdraw_amount <= 0:
                raise BundleWithdrawOrchestratorError("invalid_withdraw_amount")
            requested = withdraw_amount
            if requested > total_bundle_value + TOLERANCE:
                raise BundleWithdrawOrchestratorError("withdraw_amount_exceeds_bundle")

        batch_id = str(uuid_mod.uuid4())
        acquire_withdraw_lock(
            db,
            portfolio_locked,
            client_id=client_id,
            batch_id=batch_id,
            entry_instrument_id=str(entry_instrument.id),
            entry_asset=entry_asset,
            requested_release_amount=str(requested),
            full_withdraw=full_withdraw,
        )

        from services.portfolio_engine.clients.models import Client as _Client
        from services.transaction_intents.bundle_withdraw_intent_sync import (
            ensure_bundle_withdraw_parent_intent,
        )

        _client_row = db.query(_Client).filter(_Client.id == client_id).first()
        person_id = _client_row.person_id if _client_row is not None else None
        if person_id is not None:
            ensure_bundle_withdraw_parent_intent(
                db,
                person_id=person_id,
                bundle_id=str(portfolio_id),
                batch_id=batch_id,
                withdraw_phase=WITHDRAW_PHASE_REQUESTED,
                requested_amount=str(requested),
                full_withdraw=full_withdraw,
            )

        needed_from_sells = max(Decimal("0"), requested - cash_leg_qty)
        sell_results: list[dict] = []
        pending = 0
        failed = 0
        confirmed = 0

        actor = ActorContext(
            actor_type="system",
            actor_id=f"bundle-withdraw-{portfolio_id}",
        )

        if needed_from_sells > TOLERANCE and spot_positions:
            update_withdraw_lock(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                status="unwinding",
                withdraw_phase=WITHDRAW_PHASE_UNWINDING,
            )
            sell_plan = self._build_sell_plan(
                spot_positions,
                needed_from_sells,
                full_withdraw=full_withdraw,
            )
            for item in sell_plan:
                ext_ref = f"bundle-withdraw-sell-{batch_id}-{item['asset']}"
                try:
                    exec_result = self._run_withdraw_sell_leg(
                        db,
                        client_id=client_id,
                        portfolio_id=portfolio_id,
                        entry_asset=entry_asset,
                        entry_instrument_id=entry_instrument.id,
                        spot_asset=item["asset"],
                        spot_instrument_id=UUID(item["instrument_id"]),
                        sell_qty=Decimal(str(item["quantity"])),
                        ext_ref=ext_ref,
                        batch_id=batch_id,
                        actor=actor,
                    )
                    sell_results.append(exec_result["record"])
                    if exec_result["status"] == "pending":
                        pending += 1
                    elif exec_result["status"] == "completed":
                        confirmed += 1
                    else:
                        failed += 1
                except Exception as exc:
                    failed += 1
                    sell_results.append({
                        "asset": item["asset"],
                        "quantity_sold": 0,
                        "status": "failed",
                        "error": str(exc),
                    })

            update_withdraw_lock(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                extra={
                    "sell_legs_total": len(sell_plan),
                    "sell_legs_confirmed": confirmed,
                    "sell_legs_failed": failed,
                },
            )
        else:
            update_withdraw_lock(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                withdraw_phase=WITHDRAW_PHASE_READY_TO_RELEASE,
                status="ready_to_release",
            )

        release_result: dict | None = None
        batch_status = "pending_signature"
        if pending == 0 and failed == 0:
            release_result = self.try_release_if_ready(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
            )
            if release_result and release_result.get("released"):
                batch_status = "released"
            elif needed_from_sells <= TOLERANCE:
                batch_status = "ready_to_release"
        elif pending > 0:
            batch_status = "pending_signature"
            update_withdraw_lock(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                status="pending_signature",
            )
        elif failed > 0 and confirmed == 0:
            batch_status = "failed_partial"
            update_withdraw_lock(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                status="failed_partial",
                withdraw_phase=WITHDRAW_PHASE_FAILED_PARTIAL,
            )

        AuditService.log_success(
            db,
            entity_type="bundle_withdrawal",
            entity_id=batch_id,
            action="withdraw_from_bundle",
            actor_type=actor.actor_type,
            actor_id=actor.actor_id,
            metadata={
                "client_id": str(client_id),
                "portfolio_id": str(portfolio_id),
                "requested_release": str(requested),
                "full_withdraw": full_withdraw,
                "sell_legs": len(sell_results),
                "status": batch_status,
            },
        )

        return {
            "status": batch_status,
            "batch_id": batch_id,
            "portfolio_id": str(portfolio_id),
            "entry_asset": entry_asset,
            "requested_release_amount": float(requested),
            "full_withdraw": full_withdraw,
            "cash_leg_before": float(cash_leg_qty),
            "needed_from_sells": float(needed_from_sells),
            "sell_results": sell_results,
            "release": release_result,
            "execution_provider": self._execution.provider_name,
            "bundle_status_before": status,
        }

    @staticmethod
    def try_release_if_ready(
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
        batch_id: str,
    ) -> dict:
        """Release comptable si le cash leg couvre le montant demandé."""
        portfolio = (
            db.query(Portfolio)
            .filter(Portfolio.id == portfolio_id, Portfolio.client_id == client_id)
            .first()
        )
        if portfolio is None:
            return {"released": False, "reason": "portfolio_not_found"}

        lock = get_withdraw_lock(portfolio.metadata_)
        if lock is None or str(lock.get("batch_id")) != batch_id:
            return {"released": False, "reason": "lock_not_found"}

        if lock.get("withdraw_phase") == WITHDRAW_PHASE_RELEASED:
            return {"released": True, "reason": "already_released"}

        entry_instrument_id = UUID(str(lock["entry_instrument_id"]))
        entry_asset = str(lock.get("entry_asset") or "USDC")
        requested = Decimal(str(lock.get("requested_release_amount") or "0"))
        full_withdraw = lock.get("full_withdraw") is True

        sell_total = int(lock.get("sell_legs_total") or 0)
        sell_confirmed = int(lock.get("sell_legs_confirmed") or 0)
        sell_failed = int(lock.get("sell_legs_failed") or 0)

        if sell_total > 0 and sell_confirmed + sell_failed < sell_total:
            return {"released": False, "reason": "pending_sell_legs"}

        if sell_failed > 0 and sell_confirmed == 0:
            update_withdraw_lock(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                status="failed_partial",
                withdraw_phase=WITHDRAW_PHASE_FAILED_PARTIAL,
            )
            return {"released": False, "reason": "all_sells_failed"}

        if sell_total > 0 and sell_confirmed > 0 and sell_confirmed < sell_total:
            update_withdraw_lock(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                withdraw_phase=WITHDRAW_PHASE_PARTIALLY_UNWOUND,
                status="partially_unwound",
            )

        cash_available = resolve_bundle_cash_leg_available(
            db,
            portfolio_id=portfolio_id,
            entry_instrument_id=entry_instrument_id,
        )

        if full_withdraw:
            release_amount = cash_available
        else:
            release_amount = min(requested, cash_available)

        if release_amount <= TOLERANCE:
            return {"released": False, "reason": "insufficient_cash_leg", "cash_available": float(cash_available)}

        if not full_withdraw and cash_available + TOLERANCE < requested:
            update_withdraw_lock(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
                withdraw_phase=WITHDRAW_PHASE_PARTIALLY_UNWOUND,
                status="partially_unwound",
            )
            return {
                "released": False,
                "reason": "insufficient_cash_leg_for_requested_amount",
                "cash_available": float(cash_available),
                "requested": float(requested),
            }

        try:
            release = release_bundle_cash_leg_to_self_trading(
                db,
                client_id=client_id,
                person_id=None,
                portfolio_id=portfolio_id,
                entry_asset=entry_asset,
                entry_instrument_id=entry_instrument_id,
                amount=release_amount,
                batch_id=batch_id,
            )
        except BundleFundingError as exc:
            return {"released": False, "reason": str(exc)}

        update_withdraw_lock(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
            status="released",
            withdraw_phase=WITHDRAW_PHASE_RELEASED,
            extra={"released_amount": str(release_amount)},
        )

        from services.portfolio_engine.clients.models import Client as _Client
        from services.transaction_intents.bundle_withdraw_intent_sync import (
            mark_bundle_withdraw_released,
        )

        _client_row = db.query(_Client).filter(_Client.id == client_id).first()
        if _client_row is not None and _client_row.person_id is not None:
            mark_bundle_withdraw_released(
                db,
                person_id=_client_row.person_id,
                bundle_id=str(portfolio_id),
                batch_id=batch_id,
                released_amount=str(release_amount),
            )

        clear_withdraw_lock(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
        )

        return {
            "released": True,
            "release": release,
            "amount": float(release_amount),
        }

    def finalize_withdraw_batch(
        self,
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
        batch_id: str,
    ) -> dict:
        """Point d'entrée explicite après confirmation des legs de vente."""
        update_withdraw_lock(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
            status="finalizing",
        )
        result = self.try_release_if_ready(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
        )
        return {"batch_id": batch_id, **result}

    @staticmethod
    def on_sell_leg_confirmed(
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
        batch_id: str,
        failed: bool = False,
    ) -> None:
        """Incrémente les compteurs lock après confirmation/échec d'un leg sell."""
        portfolio = load_portfolio_for_withdraw_lock(
            db, client_id=client_id, portfolio_id=portfolio_id,
        )
        lock = get_withdraw_lock(portfolio.metadata_)
        if lock is None or str(lock.get("batch_id")) != batch_id:
            return

        confirmed = int(lock.get("sell_legs_confirmed") or 0)
        sell_failed = int(lock.get("sell_legs_failed") or 0)
        if failed:
            sell_failed += 1
        else:
            confirmed += 1

        phase = WITHDRAW_PHASE_UNWINDING
        status = "unwinding"
        total = int(lock.get("sell_legs_total") or 0)
        if total > 0 and confirmed + sell_failed >= total:
            if sell_failed > 0 and confirmed == 0:
                phase = WITHDRAW_PHASE_FAILED_PARTIAL
                status = "failed_partial"
            elif confirmed < total:
                phase = WITHDRAW_PHASE_PARTIALLY_UNWOUND
                status = "partially_unwound"
            else:
                phase = WITHDRAW_PHASE_READY_TO_RELEASE
                status = "ready_to_release"

        update_withdraw_lock(
            db,
            client_id=client_id,
            portfolio_id=portfolio_id,
            batch_id=batch_id,
            status=status,
            withdraw_phase=phase,
            extra={
                "sell_legs_confirmed": confirmed,
                "sell_legs_failed": sell_failed,
            },
        )

        if not failed:
            BundleWithdrawOrchestrator.try_release_if_ready(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
                batch_id=batch_id,
            )

    def _run_withdraw_sell_leg(
        self,
        db: Session,
        *,
        client_id: UUID,
        portfolio_id: UUID,
        entry_asset: str,
        entry_instrument_id: UUID,
        spot_asset: str,
        spot_instrument_id: UUID,
        sell_qty: Decimal,
        ext_ref: str,
        batch_id: str,
        actor: ActorContext,
    ) -> dict:
        lifi_spot = normalize_bundle_asset(spot_asset)
        token = resolve_bundle_base_token(lifi_spot)
        sell_qty = sell_qty.quantize(
            Decimal(10) ** -token.decimals,
            rounding=ROUND_DOWN,
        )
        if sell_qty <= TOLERANCE:
            raise BundleWithdrawOrchestratorError(f"sell_qty_too_small:{spot_asset}")
        leg = ExecutionLeg(
            leg_id=ext_ref,
            portfolio_id=portfolio_id,
            client_id=client_id,
            action="withdraw_sell",
            from_asset=lifi_spot,
            to_asset=entry_asset.upper(),
            amount_from=sell_qty,
            batch_id=batch_id,
            bundle_action="withdraw",
            chain="base",
            metadata={
                "entry_instrument_id": str(entry_instrument_id),
                "target_instrument_id": str(spot_instrument_id),
            },
        )
        result = self._execution.execute_leg(db, leg, actor)

        if result.status == "pending":
            record = {
                "asset": spot_asset,
                "instrument_id": str(spot_instrument_id),
                "quantity_sold": float(sell_qty),
                "entry_asset_received": 0,
                "status": "pending",
                "swap_id": result.provider_order_id,
                "leg_id": ext_ref,
                "signing": result.raw.get("prepare") if isinstance(result.raw, dict) else None,
            }
            return {"status": "pending", "record": record}

        if self._execution.provider_name == "lifi_base":
            record = {
                "asset": spot_asset,
                "instrument_id": str(spot_instrument_id),
                "quantity_sold": float(sell_qty),
                "entry_asset_received": float(result.amount_to or 0),
                "status": "completed",
                "swap_id": result.provider_order_id,
                "tx_hash": result.tx_hash,
            }
            return {"status": "completed", "record": record}

        from services.portfolio_engine.bundle_execution.pe_settlement import apply_withdraw_sell_atoms

        entry_received = Decimal(str(result.amount_to or 0))
        ref_value = Decimal(str(result.raw.get("reference_value_net", sell_qty)))
        apply_withdraw_sell_atoms(
            db,
            portfolio_id=portfolio_id,
            instrument_id=spot_instrument_id,
            entry_instrument_id=entry_instrument_id,
            sell_qty=sell_qty,
            entry_received=entry_received,
            cost_basis_eur=ref_value,
        )
        record = {
            "asset": spot_asset,
            "instrument_id": str(spot_instrument_id),
            "quantity_sold": float(sell_qty),
            "entry_asset_received": float(entry_received),
            "status": "completed",
        }
        return {"status": "completed", "record": record}

    @staticmethod
    def _list_spot_positions(db: Session, portfolio_id: UUID) -> list[dict]:
        atoms = (
            db.query(PositionAtom)
            .filter(
                PositionAtom.portfolio_id == portfolio_id,
                PositionAtom.position_type == POSITION_TYPE_SPOT,
                PositionAtom.status == "open",
            )
            .all()
        )
        out: list[dict] = []
        for atom in atoms:
            qty = Decimal(str(atom.quantity or 0))
            if qty <= TOLERANCE:
                continue
            instrument = atom.instrument or db.query(Instrument).filter(
                Instrument.id == atom.instrument_id
            ).first()
            asset_obj = db.query(Asset).filter(Asset.id == instrument.asset_id).first()
            symbol = asset_obj.symbol if asset_obj else "?"
            out.append({
                "instrument_id": str(atom.instrument_id),
                "asset": symbol,
                "quantity": qty,
                "cost_basis": Decimal(str(atom.cost_basis or 0)),
            })
        return out

    @staticmethod
    def _build_sell_plan(
        spot_positions: list[dict],
        needed_from_sells: Decimal,
        *,
        full_withdraw: bool,
    ) -> list[dict]:
        if full_withdraw:
            return [
                {
                    "instrument_id": p["instrument_id"],
                    "asset": p["asset"],
                    "quantity": p["quantity"],
                }
                for p in spot_positions
            ]

        total_value = sum(
            Decimal(str(p.get("cost_basis") or 0)) for p in spot_positions
        )
        total_qty = sum(Decimal(str(p["quantity"])) for p in spot_positions)
        if total_value <= TOLERANCE:
            total_value = total_qty
        if total_value <= TOLERANCE:
            return []

        ratio = min(Decimal("1"), needed_from_sells / total_value)
        plan: list[dict] = []
        for p in spot_positions:
            qty = (Decimal(str(p["quantity"])) * ratio).quantize(
                Decimal("0.000001"), rounding=ROUND_DOWN,
            )
            if qty > TOLERANCE:
                plan.append({
                    "instrument_id": p["instrument_id"],
                    "asset": p["asset"],
                    "quantity": qty,
                })
        return plan
