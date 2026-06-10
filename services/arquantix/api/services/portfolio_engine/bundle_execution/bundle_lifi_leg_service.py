"""Orchestration LI.FI d'un leg bundle (quote → sign → confirm → PE atoms)."""
from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.config import build_lifi_client, swaps_mock_mode
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_execute_service import LifiExecuteService
from services.lifi.lifi_swap_settlement import apply_swap_settlement, swap_settlement_already_applied
from services.lifi.lifi_validation_service import SwapValidationError
from services.lifi.swap_repository import PersonWalletSwapRepository
from services.portfolio_engine.clients.models import Client
from services.transaction_intents.bundle_intent_sync import sync_bundle_leg_from_swap

from .bundle_cost_basis import reference_cost_basis_eur
from .bundle_lifi_quote_service import BundleLifiQuoteService
from .bundle_lifi_validation import BundleLifiValidationError, validate_bundle_lifi_leg
from .lifi_base_config import BUNDLE_LIFI_CHAIN_KEY, normalize_bundle_asset
from .pe_settlement import (
    BundlePeSettlementError,
    apply_allocation_leg_atoms,
    apply_rebalance_buy_atoms,
    apply_rebalance_sell_atoms,
    apply_withdraw_sell_atoms,
    swap_confirmed,
)
from .types import ExecutionLeg, ExecutionQuote, ExecutionResult

logger = logging.getLogger(__name__)


def bundle_lifi_sync_mock() -> bool:
    raw = (os.environ.get("BUNDLE_LIFI_SYNC_MOCK") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


class BundleLifiLegService:
    def __init__(
        self,
        *,
        quote_service: Optional[BundleLifiQuoteService] = None,
        execute_service: Optional[LifiExecuteService] = None,
    ) -> None:
        client = build_lifi_client()
        self._quote = quote_service or BundleLifiQuoteService(lifi_client=client)
        self._execute = execute_service or LifiExecuteService(lifi_client=client)
        self._swap_repo = PersonWalletSwapRepository()

    def _person_id_for_client(self, db: Session, client_id: UUID) -> UUID:
        client = db.query(Client).filter(Client.id == client_id).first()
        if client is None or client.person_id is None:
            raise BundleLifiValidationError(
                "bundle.lifi.no_person",
                "Client sans person_id — wallet Privy requis pour LI.FI",
            )
        return client.person_id

    def _attach_bundle_context(self, swap, leg: ExecutionLeg) -> None:
        ctx = {
            "bundle_execution": True,
            "batch_id": leg.batch_id,
            "leg_id": leg.leg_id,
            "portfolio_id": str(leg.portfolio_id),
            "client_id": str(leg.client_id),
            "bundle_action": leg.bundle_action,
            "leg_action": leg.action,
            "execution_provider": "lifi_base",
        }
        ctx.update(leg.metadata or {})
        self._swap_repo.append_audit(swap, {"event": "bundle_leg_context", **ctx})

    def quote_leg(self, db: Session, leg: ExecutionLeg) -> ExecutionQuote:
        from_sym = normalize_bundle_asset(leg.from_asset)
        to_sym = normalize_bundle_asset(leg.to_asset)
        validate_bundle_lifi_leg(
            from_asset=from_sym,
            to_asset=to_sym,
            amount_from=leg.amount_from,
            chain=leg.chain or BUNDLE_LIFI_CHAIN_KEY,
            leg_action=leg.action,
        )
        person_id = self._person_id_for_client(db, leg.client_id)
        quote = self._quote.create_bundle_quote(
            db,
            person_id=person_id,
            from_asset=from_sym,
            to_asset=to_sym,
            amount=str(leg.amount_from),
            leg_action=leg.action,
        )
        return ExecutionQuote(
            leg_id=leg.leg_id,
            from_asset=from_sym,
            to_asset=to_sym,
            amount_from=leg.amount_from,
            estimated_amount_to=Decimal(str(quote.estimated_receive or 0)),
            reference_value_net=reference_cost_basis_eur(db, from_sym, leg.amount_from),
            fees={"swap_fee_bps": quote.swap_fee_bps},
            raw={"swap_id": str(quote.swap_id), "quote": quote.model_dump()},
        )

    def execute_leg(
        self,
        db: Session,
        leg: ExecutionLeg,
        actor: Any,
    ) -> ExecutionResult:
        """Crée la quote LI.FI et retourne ``pending`` — aucun atom PE touché."""
        from_sym = normalize_bundle_asset(leg.from_asset)
        to_sym = normalize_bundle_asset(leg.to_asset)
        validate_bundle_lifi_leg(
            from_asset=from_sym,
            to_asset=to_sym,
            amount_from=leg.amount_from,
            chain=leg.chain or BUNDLE_LIFI_CHAIN_KEY,
            leg_action=leg.action,
        )
        person_id = self._person_id_for_client(db, leg.client_id)

        quote_resp = self._quote.create_bundle_quote(
            db,
            person_id=person_id,
            from_asset=from_sym,
            to_asset=to_sym,
            amount=str(leg.amount_from),
            leg_action=leg.action,
        )
        swap = self._swap_repo.get_for_person(db, swap_id=quote_resp.swap_id, person_id=person_id)
        if swap is None:
            raise BundleLifiValidationError("bundle.lifi.swap_missing", "Swap introuvable après quote")

        self._attach_bundle_context(swap, leg)
        sync_bundle_leg_from_swap(db, person_id=person_id, swap=swap, leg=leg)
        db.commit()
        db.refresh(swap)

        if swaps_mock_mode() and bundle_lifi_sync_mock():
            return self._auto_complete_mock(db, leg, swap_id=swap.id, person_id=person_id)

        estimated_out = Decimal(str(quote_resp.estimated_receive or 0))
        return ExecutionResult(
            leg_id=leg.leg_id,
            status="pending",
            from_asset=from_sym,
            to_asset=to_sym,
            amount_from=leg.amount_from,
            amount_to=estimated_out,
            tx_hash=None,
            provider_order_id=str(swap.id),
            fees={},
            raw={
                "swap_id": str(swap.id),
                "estimated_receive": str(estimated_out),
                "requires_client_signature": True,
                "quote_freshness": "deferred_to_confirm_execute",
            },
        )

    def _auto_complete_mock(
        self,
        db: Session,
        leg: ExecutionLeg,
        *,
        swap_id: UUID,
        person_id: UUID,
    ) -> ExecutionResult:
        """Mode dev : prepare-sign optionnel puis submit mock (pas de signature Privy réelle)."""
        mock_hash = f"0xmock-bundle-{leg.leg_id[:24]}"
        swap = self._swap_repo.get_for_person(db, swap_id=swap_id, person_id=person_id)
        if swap is None:
            raise BundleLifiValidationError("bundle.lifi.swap_missing", "Swap introuvable")

        if swap.status == SwapSessionStatus.QUOTE_RECEIVED.value:
            try:
                self._execute.prepare_execute(db, person_id=person_id, swap_id=swap_id)
            except Exception:
                swap.status = SwapSessionStatus.AWAITING_SIGNATURE.value
                self._swap_repo.append_audit(
                    swap, {"event": "bundle_mock_skip_prepare", "leg_id": leg.leg_id},
                )
                db.commit()
                db.refresh(swap)

        result = self.submit_leg_tx(
            db,
            leg=leg,
            person_id=person_id,
            swap_id=swap_id,
            tx_hash=mock_hash,
        )
        return ExecutionResult(
            leg_id=leg.leg_id,
            status=result.status,
            from_asset=result.from_asset,
            to_asset=result.to_asset,
            amount_from=leg.amount_from,
            amount_to=result.amount_to,
            tx_hash=result.tx_hash,
            provider_order_id=str(swap_id),
            raw={"swap_id": str(swap_id), "mock": True},
        )

    def prepare_signing(
        self,
        db: Session,
        *,
        person_id: UUID,
        swap_id: UUID,
    ):
        from services.portfolio_engine.bundles.bundle_invest_lock import update_invest_lock_status
        from services.portfolio_engine.bundle_execution.bundle_lifi_api import leg_from_swap_audit

        swap = self._swap_repo.get_for_person(db, swap_id=swap_id, person_id=person_id)
        leg = leg_from_swap_audit(swap) if swap is not None else None
        if leg is not None and leg.bundle_action == "allocation" and leg.batch_id:
            update_invest_lock_status(
                db,
                client_id=leg.client_id,
                portfolio_id=leg.portfolio_id,
                batch_id=leg.batch_id,
                status="signature_requested",
            )
        return self._execute.prepare_execute(db, person_id=person_id, swap_id=swap_id)

    def submit_leg_tx(
        self,
        db: Session,
        *,
        leg: ExecutionLeg,
        person_id: UUID,
        swap_id: UUID,
        tx_hash: str,
    ) -> ExecutionResult:
        """Soumet la tx signée ; après CONFIRMED, settlement Privy + atoms PE."""
        from services.portfolio_engine.bundles.bundle_invest_lock import update_invest_lock_status

        if leg.bundle_action in ("allocation",) and leg.batch_id:
            update_invest_lock_status(
                db,
                client_id=leg.client_id,
                portfolio_id=leg.portfolio_id,
                batch_id=leg.batch_id,
                status="submitted",
            )

        self._execute.submit_signed_tx(
            db, person_id=person_id, swap_id=swap_id, tx_hash=tx_hash,
        )
        swap = self._swap_repo.get_for_person(db, swap_id=swap_id, person_id=person_id)
        from services.transaction_intents.bundle_intent_sync import (
            bundle_context_from_swap_audit,
            mark_bundle_leg_submitted,
        )

        if swap is not None:
            ctx = bundle_context_from_swap_audit(swap)
            if ctx and ctx.get("batch_id"):
                mark_bundle_leg_submitted(
                    db,
                    person_id=person_id,
                    bundle_id=str(ctx.get("portfolio_id") or leg.portfolio_id),
                    batch_id=str(ctx["batch_id"]),
                    swap_id=swap_id,
                    tx_hash=tx_hash,
                    leg_id=str(ctx.get("leg_id") or leg.leg_id),
                )
        if swap is None:
            raise BundleLifiValidationError("bundle.lifi.swap_missing", "Swap introuvable")

        if swap.status == SwapSessionStatus.SUBMITTED.value:
            self._execute.refresh_lifi_status(db, swap)
            db.refresh(swap)

        if not swap_confirmed(swap):
            if leg.bundle_action in ("allocation",) and leg.batch_id:
                update_invest_lock_status(
                    db,
                    client_id=leg.client_id,
                    portfolio_id=leg.portfolio_id,
                    batch_id=leg.batch_id,
                    status="pending_confirmation",
                )
            return ExecutionResult(
                leg_id=leg.leg_id,
                status="pending",
                from_asset=swap.from_asset,
                to_asset=swap.to_asset,
                amount_from=leg.amount_from,
                provider_order_id=str(swap.id),
                tx_hash=swap.tx_hash,
                raw={"swap_status": swap.status},
            )

        self._apply_post_confirmation(db, leg=leg, swap=swap)
        from services.transaction_intents.bundle_intent_sync import (
            bundle_context_from_swap_audit,
            mark_bundle_leg_confirmed,
            recompute_bundle_parent_intent,
        )

        ctx = bundle_context_from_swap_audit(swap)
        if ctx and ctx.get("batch_id"):
            mark_bundle_leg_confirmed(
                db,
                person_id=person_id,
                bundle_id=str(ctx.get("portfolio_id") or leg.portfolio_id),
                batch_id=str(ctx["batch_id"]),
                swap_id=swap.id,
                tx_hash=swap.tx_hash,
                leg_id=str(ctx.get("leg_id") or leg.leg_id),
            )
            recompute_bundle_parent_intent(
                db,
                person_id=person_id,
                bundle_id=str(ctx.get("portfolio_id") or leg.portfolio_id),
                batch_id=str(ctx["batch_id"]),
            )
            if leg.bundle_action == "withdraw" and leg.batch_id:
                from services.portfolio_engine.bundles.withdraw import BundleWithdrawOrchestrator

                BundleWithdrawOrchestrator.on_sell_leg_confirmed(
                    db,
                    client_id=leg.client_id,
                    portfolio_id=leg.portfolio_id,
                    batch_id=str(leg.batch_id),
                    failed=False,
                )
        amount_out = Decimal(str(swap.estimated_receive or 0))
        return ExecutionResult(
            leg_id=leg.leg_id,
            status="completed",
            from_asset=swap.from_asset,
            to_asset=swap.to_asset,
            amount_from=leg.amount_from,
            amount_to=amount_out,
            tx_hash=swap.tx_hash,
            provider_order_id=str(swap.id),
            raw={"swap_status": swap.status},
        )

    def _pe_atoms_already_applied(self, swap) -> bool:
        from .bundle_swap_pe_settlement import (
            SETTLEMENT_RECEIPT_EVENT,
            swap_has_pe_settlement_receipt,
        )

        audit = swap.audit_log
        if not isinstance(audit, list):
            return False
        has_flag = any(
            isinstance(e, dict) and e.get("event") == "bundle_pe_atoms_applied"
            for e in audit
        )
        if not has_flag:
            return False
        if swap_has_pe_settlement_receipt(swap):
            return True
        for entry in reversed(audit):
            if not isinstance(entry, dict):
                continue
            if entry.get("event") != SETTLEMENT_RECEIPT_EVENT:
                continue
            amount_in = Decimal(str(entry.get("amount_in") or "0"))
            amount_out = Decimal(str(entry.get("amount_out") or "0"))
            return amount_in > 0 and amount_out > 0
        return False

    def _validate_settlement_amounts(
        self,
        *,
        leg: ExecutionLeg,
        amount_in: Decimal,
        amount_out: Decimal,
    ) -> None:
        if leg.action in ("rebalance_buy", "allocation"):
            if amount_in <= 0:
                raise BundlePeSettlementError("settlement_amount_in_invalid")
            if amount_out <= 0:
                raise BundlePeSettlementError("settlement_amount_out_invalid")
        elif leg.action == "rebalance_sell":
            if amount_in <= 0 or amount_out <= 0:
                raise BundlePeSettlementError("settlement_amount_invalid")

    def _apply_post_confirmation(self, db: Session, *, leg: ExecutionLeg, swap) -> None:
        """Privy ledger puis atoms PE — jamais avant CONFIRMED."""
        if not swap_confirmed(swap):
            raise BundlePeSettlementError("swap_not_confirmed")

        if self._pe_atoms_already_applied(swap):
            return

        settlement_preview = self._resolve_settlement_amounts(db, leg=leg, swap=swap)
        self._validate_settlement_amounts(
            leg=leg,
            amount_in=settlement_preview.amount_in,
            amount_out=settlement_preview.amount_out,
        )

        if not swap_settlement_already_applied(swap):
            apply_swap_settlement(db, swap, sync_source="bundle_lifi_leg")
            self._swap_repo.append_audit(
                swap,
                {"event": "swap_settled", "source": "bundle_lifi_leg", "leg_id": leg.leg_id},
            )

        self._apply_pe_atoms_for_leg(db, leg=leg, swap=swap)
        self._swap_repo.append_audit(swap, {"event": "bundle_pe_atoms_applied", "leg_id": leg.leg_id})
        self._swap_repo.append_audit(
            swap,
            {
                "event": "bundle_pe_settlement_receipt",
                "leg_id": leg.leg_id,
                "leg_action": leg.action,
                "amount_in": str(settlement_preview.amount_in),
                "amount_out": str(settlement_preview.amount_out),
                "amount_in_source": settlement_preview.amount_in_source,
                "amount_out_source": settlement_preview.amount_out_source,
            },
        )
        self._ingest_bundle_cost_basis(db, leg=leg, swap=swap)
        db.commit()

    def _resolve_settlement_amounts(self, db: Session, *, leg: ExecutionLeg, swap):
        from services.lifi.config import swaps_mock_mode

        from .allocation_settlement import resolve_allocation_leg_settlement_amounts

        meta = leg.metadata or {}
        planned_in_raw = meta.get("planned_amount_in")
        planned_in = (
            Decimal(str(planned_in_raw)) if planned_in_raw is not None else Decimal(str(swap.amount_in))
        )
        return resolve_allocation_leg_settlement_amounts(
            db,
            swap,
            planned_amount_in=planned_in,
            allow_mock_quote_amount=swaps_mock_mode(),
        )

    def _ingest_bundle_cost_basis(self, db: Session, *, leg: ExecutionLeg, swap) -> None:
        """PRU scoped bundle pour charts / statistics (idempotent)."""
        from services.cost_basis.ingest_bundle_lifi import ingest_bundle_lifi_swap_settlement
        from services.cost_basis.lifi_swap_amounts import resolve_lifi_swap_amount_out
        from services.lifi.config import swaps_mock_mode
        from services.lifi.lifi_actual_receive import _resolve_swap_wallet

        try:
            wallet = _resolve_swap_wallet(db, swap)
            amount_out, _ = resolve_lifi_swap_amount_out(
                db,
                swap,
                allow_onchain_resolve=False,
                allow_mock_quote_amount=swaps_mock_mode(),
            )
            ingest_bundle_lifi_swap_settlement(
                db,
                swap,
                wallet=wallet,
                amount_out=amount_out,
                portfolio_id=leg.portfolio_id,
            )
        except Exception:
            import logging

            logging.getLogger(__name__).exception(
                "bundle_lifi cost_basis ingest failed swap=%s leg=%s",
                swap.id,
                leg.leg_id,
            )

    def _apply_pe_atoms_for_leg(self, db: Session, *, leg: ExecutionLeg, swap) -> None:
        from services.lifi.config import swaps_mock_mode

        from .allocation_settlement import resolve_allocation_leg_settlement_amounts

        meta = leg.metadata or {}
        entry_instrument_id = meta.get("entry_instrument_id")
        target_instrument_id = meta.get("target_instrument_id")
        if not entry_instrument_id or not target_instrument_id:
            if leg.action in ("allocation", "rebalance_buy", "rebalance_sell", "withdraw_sell"):
                raise BundlePeSettlementError("missing_instrument_ids_in_leg_metadata")
            return

        entry_inst = UUID(str(entry_instrument_id))
        target_inst = UUID(str(target_instrument_id))

        planned_in_raw = meta.get("planned_amount_in")
        planned_in = (
            Decimal(str(planned_in_raw)) if planned_in_raw is not None else Decimal(str(swap.amount_in))
        )
        settlement = resolve_allocation_leg_settlement_amounts(
            db,
            swap,
            planned_amount_in=planned_in,
            allow_mock_quote_amount=swaps_mock_mode(),
        )
        amount_in = settlement.amount_in
        amount_out = settlement.amount_out
        cost_basis = reference_cost_basis_eur(db, str(swap.from_asset), amount_in)

        from .allocation_observability import log_allocation_event

        log_allocation_event(
            "settlement_real_amounts",
            person_id=str(swap.person_id),
            portfolio_id=str(leg.portfolio_id),
            batch_id=leg.batch_id,
            leg_id=leg.leg_id,
            swap_id=str(swap.id),
            planned_amount_in=float(settlement.planned_amount_in),
            actual_amount_in=float(settlement.amount_in),
            planned_amount_out=float(settlement.planned_amount_out),
            actual_amount_out=float(settlement.amount_out),
            amount_in_source=settlement.amount_in_source,
            amount_out_source=settlement.amount_out_source,
        )

        ledger_ctx = {
            "person_id": str(swap.person_id),
            "batch_id": leg.batch_id,
            "leg_id": leg.leg_id,
            "swap_id": str(swap.id),
            "from_asset": str(swap.from_asset),
            "to_asset": str(swap.to_asset),
            "planned_amount_in": str(settlement.planned_amount_in),
            "planned_amount_out": str(settlement.planned_amount_out),
            "actual_amount_in_source": settlement.amount_in_source,
            "actual_amount_out_source": settlement.amount_out_source,
        }

        if leg.action == "allocation":
            apply_allocation_leg_atoms(
                db,
                portfolio_id=leg.portfolio_id,
                entry_instrument_id=entry_inst,
                target_instrument_id=target_inst,
                entry_asset_consumed=amount_in,
                crypto_received=amount_out,
                cost_basis_eur=cost_basis,
                ledger={
                    **ledger_ctx,
                    "entry_asset_symbol": str(swap.from_asset),
                    "target_asset_symbol": str(swap.to_asset),
                },
            )
        elif leg.action == "rebalance_sell":
            apply_rebalance_sell_atoms(
                db,
                portfolio_id=leg.portfolio_id,
                instrument_id=target_inst,
                entry_instrument_id=entry_inst,
                sell_qty=amount_in,
                entry_received=amount_out,
                cost_basis_eur=cost_basis,
                ledger={
                    **ledger_ctx,
                    "asset_symbol": str(swap.from_asset),
                    "entry_asset_symbol": str(swap.to_asset),
                },
            )
        elif leg.action == "withdraw_sell":
            apply_withdraw_sell_atoms(
                db,
                portfolio_id=leg.portfolio_id,
                instrument_id=target_inst,
                entry_instrument_id=entry_inst,
                sell_qty=amount_in,
                entry_received=amount_out,
                cost_basis_eur=cost_basis,
                ledger={
                    **ledger_ctx,
                    "entry_asset_symbol": str(swap.to_asset),
                },
            )
        elif leg.action == "rebalance_buy":
            apply_rebalance_buy_atoms(
                db,
                portfolio_id=leg.portfolio_id,
                instrument_id=target_inst,
                entry_instrument_id=entry_inst,
                entry_spent=amount_in,
                crypto_received=amount_out,
                cost_basis_eur=cost_basis,
                ledger={
                    **ledger_ctx,
                    "asset_symbol": str(swap.to_asset),
                    "entry_asset_symbol": str(swap.from_asset),
                },
            )

    def refresh_and_settle(
        self,
        db: Session,
        *,
        leg: ExecutionLeg,
        person_id: UUID,
        swap_id: UUID,
    ) -> ExecutionResult:
        swap = self._swap_repo.get_for_person(db, swap_id=swap_id, person_id=person_id)
        if swap is None:
            raise BundleLifiValidationError("bundle.lifi.swap_missing", "Swap introuvable")
        if swap.status == SwapSessionStatus.SUBMITTED.value:
            self._execute.refresh_lifi_status(db, swap)
            db.refresh(swap)
        if swap_confirmed(swap):
            self._apply_post_confirmation(db, leg=leg, swap=swap)
            return ExecutionResult(
                leg_id=leg.leg_id,
                status="completed",
                from_asset=swap.from_asset,
                to_asset=swap.to_asset,
                amount_from=leg.amount_from,
                amount_to=Decimal(str(swap.estimated_receive or 0)),
                tx_hash=swap.tx_hash,
                provider_order_id=str(swap.id),
                raw={},
            )
        if swap.status == SwapSessionStatus.FAILED.value:
            from services.transaction_intents.bundle_intent_sync import (
                bundle_context_from_swap_audit,
                mark_bundle_leg_failed,
                recompute_bundle_parent_intent,
            )

            ctx = bundle_context_from_swap_audit(swap)
            if ctx and ctx.get("batch_id"):
                mark_bundle_leg_failed(
                    db,
                    person_id=person_id,
                    bundle_id=str(ctx.get("portfolio_id") or leg.portfolio_id),
                    batch_id=str(ctx["batch_id"]),
                    swap_id=swap.id,
                    tx_hash=swap.tx_hash,
                    leg_id=str(ctx.get("leg_id") or leg.leg_id),
                    reason="swap_failed",
                )
                recompute_bundle_parent_intent(
                    db,
                    person_id=person_id,
                    bundle_id=str(ctx.get("portfolio_id") or leg.portfolio_id),
                    batch_id=str(ctx["batch_id"]),
                )
                if leg.bundle_action == "withdraw" and leg.batch_id:
                    from services.portfolio_engine.bundles.withdraw import BundleWithdrawOrchestrator

                    BundleWithdrawOrchestrator.on_sell_leg_confirmed(
                        db,
                        client_id=leg.client_id,
                        portfolio_id=leg.portfolio_id,
                        batch_id=str(leg.batch_id),
                        failed=True,
                    )
        return ExecutionResult(
            leg_id=leg.leg_id,
            status="pending" if swap.status != SwapSessionStatus.FAILED.value else "failed",
            from_asset=swap.from_asset,
            to_asset=swap.to_asset,
            amount_from=leg.amount_from,
            provider_order_id=str(swap.id),
            tx_hash=swap.tx_hash,
            raw={"error": swap.error_message},
        )
