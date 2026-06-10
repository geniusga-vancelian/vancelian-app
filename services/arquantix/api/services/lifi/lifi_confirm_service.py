"""Confirm execute — refresh quote LI.FI + vérif slippage + prepare (ADR 007 → Swap Core)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.lifi_execute_service import LifiExecuteService
from services.lifi.lifi_quote_service import LifiQuoteService
from services.lifi.schemas import SwapConfirmExecuteResponse
from services.swap_core import SwapCoreConfirmPoll


class LifiConfirmService:
    def __init__(
        self,
        *,
        quote_service: LifiQuoteService | None = None,
        execute_service: LifiExecuteService | None = None,
        core: SwapCoreConfirmPoll | None = None,
    ):
        self._core = core or SwapCoreConfirmPoll(
            quote_service=quote_service,
            execute_service=execute_service,
        )

    def confirm_execute(
        self,
        db: Session,
        *,
        person_id: UUID,
        swap_id: UUID,
        review_estimated_receive: str,
        review_amount_in: str | None = None,
    ) -> SwapConfirmExecuteResponse:
        return self._core.confirm_and_execute(
            db,
            person_id=person_id,
            swap_id=swap_id,
            review_estimated_receive=review_estimated_receive,
            review_amount_in=review_amount_in,
        )
