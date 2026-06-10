"""Confirm execute — refresh quote LI.FI + vérif slippage + prepare."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.lifi_execute_service import LifiExecuteService
from services.lifi.lifi_quote_service import LifiQuoteService
from services.lifi.lifi_validation_service import SwapPriceChangedError, SwapValidationError
from services.lifi.orchestrator_allowlist import lifi_intent_orchestrator_enabled_for_person
from services.lifi.schemas import SwapConfirmExecuteResponse
from services.lifi.swap_quote_freshness import compare_receive_against_review
from services.transaction_outbox.atomic import attach_orchestrator_intent_to_swap_atomic


class LifiConfirmService:
    def __init__(
        self,
        *,
        quote_service: LifiQuoteService | None = None,
        execute_service: LifiExecuteService | None = None,
    ):
        self._quote = quote_service or LifiQuoteService()
        self._execute = execute_service or LifiExecuteService()

    def confirm_execute(
        self,
        db: Session,
        *,
        person_id: UUID,
        swap_id: UUID,
        review_estimated_receive: str,
        review_amount_in: str | None = None,
    ) -> SwapConfirmExecuteResponse:
        fresh_quote = self._quote.refresh_quote(db, person_id=person_id, swap_id=swap_id)
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

        if review_amount_in is not None and review_amount_in.strip():
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

        from services.lifi.lifi_swap_global_lock import acquire_lifi_swap_global_lock_or_raise

        acquire_lifi_swap_global_lock_or_raise(
            db,
            person_id=person_id,
            swap_id=swap_id,
        )

        execute = self._execute.prepare_execute(db, person_id=person_id, swap_id=swap_id)
        freshness = "refreshed" if comparison.delta_bps > 0 else "verified"
        return SwapConfirmExecuteResponse(
            freshness=freshness,
            quote=fresh_quote,
            execute=execute,
        )
