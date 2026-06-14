"""ADR 007 S3 — Swap Core confirm + poll (délègue execute existant)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.lifi_execute_service import LifiExecuteService
from services.lifi.lifi_quote_service import LifiQuoteService
from services.lifi.lifi_validation_service import SwapPriceChangedError, SwapValidationError
from services.lifi.orchestrator_allowlist import (
    lifi_enqueue_and_wait_enabled_for_person,
    lifi_intent_orchestrator_enabled_for_person,
)
from services.lifi.schemas import SwapConfirmExecuteResponse, SwapStatusResponse
from services.lifi.swap_quote_freshness import compare_receive_against_review
from services.lifi.swap_repository import PersonWalletSwapRepository
from services.portfolio_engine.bundle_execution.bundle_transaction_scope import is_bundle_internal_swap
from services.transaction_outbox.atomic import attach_orchestrator_intent_to_swap_atomic


class SwapCoreConfirmPoll:
    """Confirm / poll / refresh — façade ADR 007 sur services LI.FI existants."""

    def __init__(
        self,
        *,
        quote_service: LifiQuoteService | None = None,
        execute_service: LifiExecuteService | None = None,
    ) -> None:
        self._quote = quote_service or LifiQuoteService()
        self._execute = execute_service or LifiExecuteService()

    @staticmethod
    def _audit_confirm_prepare_failed(db: Session, swap_id: UUID, person_id: UUID, *, code: str) -> None:
        swap_row = PersonWalletSwapRepository.get_for_person(
            db,
            swap_id=swap_id,
            person_id=person_id,
        )
        if swap_row is None:
            return
        PersonWalletSwapRepository.append_audit(
            swap_row,
            {"event": "confirm_prepare_failed", "code": code},
        )
        db.commit()

    def confirm_and_execute(
        self,
        db: Session,
        *,
        person_id: UUID,
        swap_id: UUID,
        review_estimated_receive: str,
        review_amount_in: str | None = None,
    ) -> SwapConfirmExecuteResponse:
        fresh_quote = self._quote.refresh_quote(db, person_id=person_id, swap_id=swap_id)
        swap_row = PersonWalletSwapRepository.get_for_person(
            db,
            swap_id=swap_id,
            person_id=person_id,
        )
        bundle_internal = swap_row is not None and is_bundle_internal_swap(swap_row)

        try:
            comparison = compare_receive_against_review(
                review_estimated_receive=review_estimated_receive,
                fresh_estimated_receive=fresh_quote.estimated_receive,
                slippage_bps=fresh_quote.slippage_bps,
            )
            if not comparison.acceptable:
                raise SwapPriceChangedError(
                    quote=fresh_quote,
                    delta_bps=comparison.delta_bps,
                    slippage_bps=comparison.slippage_bps,
                )

            if review_amount_in is not None and review_amount_in.strip() and not bundle_internal:
                from services.lifi.lifi_validation_service import parse_human_amount

                try:
                    review_in = parse_human_amount(review_amount_in)
                    fresh_in = parse_human_amount(fresh_quote.amount_in)
                    if review_in != fresh_in:
                        raise SwapValidationError(
                            "swap.amount_changed",
                            "Le montant source a changé — refaites une estimation.",
                        )
                except SwapValidationError:
                    raise

            if lifi_intent_orchestrator_enabled_for_person(db, person_id):
                attach_orchestrator_intent_to_swap_atomic(
                    db,
                    person_id=person_id,
                    swap_id=swap_id,
                )

            # PR3 — enqueue-and-wait : ne pas acquérir le slot user au confirm (pas de 409
            # fail-fast). Le worker d'exécution acquiert le slot au moment d'exécuter ; un
            # 2e swap concurrent reste en file et démarre après terminalité du 1er.
            # Sinon (PR2 / legacy) : fail-fast 409 au confirm comme avant.
            if not lifi_enqueue_and_wait_enabled_for_person(db, person_id):
                from services.lifi.lifi_swap_global_lock import (
                    acquire_lifi_swap_global_lock_or_raise,
                )

                acquire_lifi_swap_global_lock_or_raise(
                    db,
                    person_id=person_id,
                    swap_id=swap_id,
                )

            execute = self._execute.prepare_execute(db, person_id=person_id, swap_id=swap_id)
            freshness = "refreshed" if comparison.delta_bps > 0 else "verified"

            # PR4 — signaler au front le mode autoritaire + l'intent_id pour le suivi.
            from services.lifi.orchestrator_allowlist import (
                lifi_authoritative_execution_enabled_for_person,
            )

            server_authoritative = lifi_authoritative_execution_enabled_for_person(
                db, person_id
            )
            intent_id = None
            if server_authoritative:
                from services.transaction_intents.repository import (
                    TransactionIntentRepository,
                )

                intent = TransactionIntentRepository.find_by_linked(
                    db,
                    linked_table="person_wallet_swaps",
                    linked_id=swap_id,
                )
                intent_id = intent.id if intent is not None else None

            return SwapConfirmExecuteResponse(
                freshness=freshness,
                quote=fresh_quote,
                execute=execute,
                server_authoritative=server_authoritative,
                intent_id=intent_id,
            )
        except SwapPriceChangedError as exc:
            self._audit_confirm_prepare_failed(db, swap_id, person_id, code=exc.code)
            raise
        except SwapValidationError as exc:
            self._audit_confirm_prepare_failed(db, swap_id, person_id, code=exc.code)
            raise
        except Exception as exc:
            code = getattr(exc, "code", None) or type(exc).__name__
            self._audit_confirm_prepare_failed(db, swap_id, person_id, code=str(code))
            raise

    def get_status(
        self,
        db: Session,
        *,
        person_id: UUID,
        swap_id: UUID,
    ) -> SwapStatusResponse:
        return self._execute.get_status(db, person_id=person_id, swap_id=swap_id)

    def refresh_lifi_status(self, db: Session, swap) -> None:
        self._execute.refresh_lifi_status(db, swap)
