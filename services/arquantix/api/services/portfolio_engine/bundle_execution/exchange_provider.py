"""Exchange Engine backend for bundle execution legs (Phase 1 default)."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from services.exchange.schemas import ExchangeBuyRequest, SwapRequest
from services.exchange.service import ExchangeError, ExchangeService
from services.portfolio_engine.hardening.security.context import ActorContext

from .order_tagging import tag_order_by_external_reference, tag_swap_leg_orders
from .types import ExecutionLeg, ExecutionQuote, ExecutionResult


class ExchangeExecutionProvider:
    """Delegates to ``ExchangeService`` without changing its internals."""

    name = "exchange"

    def __init__(self, exchange_service: ExchangeService | None = None) -> None:
        self._exchange = exchange_service or ExchangeService()

    def quote_leg(self, db: Session, leg: ExecutionLeg) -> ExecutionQuote:
        if leg.action == "funding":
            currency = (leg.currency or leg.from_asset or "EUR").upper()
            preview = self._exchange.preview_buy(
                db, leg.to_asset, leg.amount_from, currency,
            )
            estimated = Decimal(str(preview.get("estimated_crypto_net", 0)))
            return ExecutionQuote(
                leg_id=leg.leg_id,
                from_asset=leg.from_asset,
                to_asset=leg.to_asset,
                amount_from=leg.amount_from,
                estimated_amount_to=estimated,
                reference_value_net=leg.amount_from,
                fees={"fee_eur": preview.get("fee_eur")},
                raw=preview,
            )

        from services.exchange.schemas import SwapPreviewRequest

        preview = self._exchange.preview_swap(
            db,
            SwapPreviewRequest(
                from_asset=leg.from_asset,
                to_asset=leg.to_asset,
                amount_from=leg.amount_from,
            ),
            currency=(leg.currency or "EUR"),
        )
        estimated = Decimal(str(preview.get("estimated_to_amount", 0)))
        ref_net = preview.get("reference_value_net")
        return ExecutionQuote(
            leg_id=leg.leg_id,
            from_asset=leg.from_asset,
            to_asset=leg.to_asset,
            amount_from=leg.amount_from,
            estimated_amount_to=estimated,
            reference_value_net=(
                Decimal(str(ref_net)) if ref_net is not None else None
            ),
            fees={"fee_in_reference_currency": preview.get("fee_in_reference_currency")},
            raw=preview,
        )

    def execute_leg(
        self,
        db: Session,
        leg: ExecutionLeg,
        actor: ActorContext,
    ) -> ExecutionResult:
        if leg.action == "funding":
            return self._execute_funding(db, leg, actor)
        return self._execute_swap(db, leg, actor)

    def _execute_funding(
        self,
        db: Session,
        leg: ExecutionLeg,
        actor: ActorContext,
    ) -> ExecutionResult:
        currency = (leg.currency or leg.from_asset or "EUR").upper()
        payload = ExchangeBuyRequest(
            client_id=leg.client_id,
            asset=leg.to_asset,
            fiat_amount=leg.amount_from,
            currency=currency,
            external_reference=leg.leg_id,
        )
        try:
            raw = self._exchange.buy(db, payload, actor)
        except ExchangeError:
            raise

        tag_order_by_external_reference(
            db,
            external_reference=leg.leg_id,
            leg=leg,
            execution_provider=self.name,
        )

        status = _map_exchange_status(raw)
        amount_crypto = raw.get("amount_crypto")
        return ExecutionResult(
            leg_id=leg.leg_id,
            status=status,
            from_asset=leg.from_asset,
            to_asset=leg.to_asset,
            amount_from=leg.amount_from,
            amount_to=(
                Decimal(str(amount_crypto)) if amount_crypto is not None else None
            ),
            provider_order_id=str(raw.get("order_id", "") or ""),
            fees={"fee_crypto": raw.get("fee_crypto")},
            raw=raw,
        )

    def _execute_swap(
        self,
        db: Session,
        leg: ExecutionLeg,
        actor: ActorContext,
    ) -> ExecutionResult:
        payload = SwapRequest(
            from_asset=leg.from_asset,
            to_asset=leg.to_asset,
            amount_from=leg.amount_from,
            external_reference=leg.leg_id,
        )
        try:
            raw = self._exchange.swap(db, leg.client_id, payload, actor)
        except ExchangeError:
            raise

        tag_swap_leg_orders(
            db,
            external_reference=leg.leg_id,
            leg=leg,
            execution_provider=self.name,
        )

        status = _map_exchange_status(raw)
        amount_to = raw.get("amount_to")
        return ExecutionResult(
            leg_id=leg.leg_id,
            status=status,
            from_asset=leg.from_asset,
            to_asset=leg.to_asset,
            amount_from=leg.amount_from,
            amount_to=Decimal(str(amount_to)) if amount_to is not None else None,
            provider_order_id=str(raw.get("swap_group_id", "") or ""),
            fees={"fee_in_reference_currency": raw.get("fee_in_reference_currency")},
            raw=raw,
        )


def _map_exchange_status(raw: dict) -> str:
    st = (raw.get("status") or "completed").lower()
    if st in ("completed", "ignored"):
        return "completed"
    if st == "partial":
        return "partial"
    if st in ("failed", "error"):
        return "failed"
    if st == "pending":
        return "pending"
    return "completed"
