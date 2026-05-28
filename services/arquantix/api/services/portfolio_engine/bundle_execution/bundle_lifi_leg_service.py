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

from .bundle_lifi_quote_service import BundleLifiQuoteService
from .bundle_lifi_validation import BundleLifiValidationError, validate_bundle_lifi_leg
from .lifi_base_config import BUNDLE_LIFI_CHAIN_KEY, normalize_bundle_asset
from .pe_settlement import (
    BundlePeSettlementError,
    apply_allocation_leg_atoms_lifi_spot_only,
    apply_rebalance_buy_atoms,
    apply_rebalance_sell_atoms,
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
        )
        person_id = self._person_id_for_client(db, leg.client_id)
        quote = self._quote.create_bundle_quote(
            db,
            person_id=person_id,
            from_asset=from_sym,
            to_asset=to_sym,
            amount=str(leg.amount_from),
        )
        return ExecutionQuote(
            leg_id=leg.leg_id,
            from_asset=from_sym,
            to_asset=to_sym,
            amount_from=leg.amount_from,
            estimated_amount_to=Decimal(str(quote.estimated_receive or 0)),
            reference_value_net=leg.amount_from,
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
        )
        person_id = self._person_id_for_client(db, leg.client_id)

        quote_resp = self._quote.create_bundle_quote(
            db,
            person_id=person_id,
            from_asset=from_sym,
            to_asset=to_sym,
            amount=str(leg.amount_from),
        )
        swap = self._swap_repo.get_for_person(db, swap_id=quote_resp.swap_id, person_id=person_id)
        if swap is None:
            raise BundleLifiValidationError("bundle.lifi.swap_missing", "Swap introuvable après quote")

        self._attach_bundle_context(swap, leg)
        from services.transaction_intents.bundle_intent_sync import sync_bundle_leg_from_swap

        sync_bundle_leg_from_swap(db, person_id=person_id, swap=swap, leg=leg)
        db.commit()
        db.refresh(swap)

        if swaps_mock_mode() and bundle_lifi_sync_mock():
            return self._auto_complete_mock(db, leg, swap_id=swap.id, person_id=person_id)

        prepare = self._execute.prepare_execute(db, person_id=person_id, swap_id=swap.id)
        return ExecutionResult(
            leg_id=leg.leg_id,
            status="pending",
            from_asset=from_sym,
            to_asset=to_sym,
            amount_from=leg.amount_from,
            amount_to=None,
            tx_hash=None,
            provider_order_id=str(swap.id),
            fees={},
            raw={
                "swap_id": str(swap.id),
                "prepare": prepare.model_dump(),
                "requires_client_signature": True,
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
        audit = swap.audit_log
        if isinstance(audit, list):
            return any(
                isinstance(e, dict) and e.get("event") == "bundle_pe_atoms_applied"
                for e in audit
            )
        return False

    def _apply_post_confirmation(self, db: Session, *, leg: ExecutionLeg, swap) -> None:
        """Privy ledger puis atoms PE — jamais avant CONFIRMED."""
        if not swap_confirmed(swap):
            raise BundlePeSettlementError("swap_not_confirmed")

        if self._pe_atoms_already_applied(swap):
            return

        if not swap_settlement_already_applied(swap):
            apply_swap_settlement(db, swap, sync_source="bundle_lifi_leg")
            self._swap_repo.append_audit(
                swap,
                {"event": "swap_settled", "source": "bundle_lifi_leg", "leg_id": leg.leg_id},
            )

        self._apply_pe_atoms_for_leg(db, leg=leg, swap=swap)
        self._swap_repo.append_audit(swap, {"event": "bundle_pe_atoms_applied", "leg_id": leg.leg_id})
        db.commit()

    def _apply_pe_atoms_for_leg(self, db: Session, *, leg: ExecutionLeg, swap) -> None:
        meta = leg.metadata or {}
        entry_instrument_id = meta.get("entry_instrument_id")
        target_instrument_id = meta.get("target_instrument_id")
        if not entry_instrument_id or not target_instrument_id:
            if leg.action in ("allocation", "rebalance_buy", "rebalance_sell"):
                raise BundlePeSettlementError("missing_instrument_ids_in_leg_metadata")
            return

        entry_inst = UUID(str(entry_instrument_id))
        target_inst = UUID(str(target_instrument_id))
        amount_in = Decimal(str(swap.amount_in))
        amount_out = Decimal(str(swap.estimated_receive or 0))
        cost_basis = amount_in

        if leg.action == "allocation":
            apply_allocation_leg_atoms_lifi_spot_only(
                db,
                portfolio_id=leg.portfolio_id,
                target_instrument_id=target_inst,
                crypto_received=amount_out,
                cost_basis_eur=cost_basis,
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
