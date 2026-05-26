"""LI.FI Base execution provider for bundle legs (Phase 2)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from services.portfolio_engine.hardening.security.context import ActorContext

from .bundle_lifi_leg_service import BundleLifiLegService
from .types import ExecutionLeg, ExecutionQuote, ExecutionResult


class LifiExecutionProvider:
    """On-chain legs via LI.FI + Privy — Base only; atoms après confirmation."""

    name = "lifi_base"

    def __init__(self, leg_service: BundleLifiLegService | None = None) -> None:
        self._legs = leg_service or BundleLifiLegService()

    def quote_leg(self, db: Session, leg: ExecutionLeg) -> ExecutionQuote:
        return self._legs.quote_leg(db, leg)

    def execute_leg(
        self,
        db: Session,
        leg: ExecutionLeg,
        actor: ActorContext,
    ) -> ExecutionResult:
        if leg.action == "funding" and (leg.from_asset or "").upper() in ("EUR", "USD"):
            from .exchange_provider import ExchangeExecutionProvider

            exchange = ExchangeExecutionProvider()
            result = exchange.execute_leg(db, leg, actor)
            result.raw["routed_funding_via"] = "exchange"
            return result

        return self._legs.execute_leg(db, leg, actor)
