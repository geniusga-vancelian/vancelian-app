"""Single entry point for bundle orchestrators → execution backends."""
from __future__ import annotations

from sqlalchemy.orm import Session

from services.portfolio_engine.hardening.security.context import ActorContext

from .providers import ExecutionProvider, get_execution_provider
from .types import ExecutionLeg, ExecutionQuote, ExecutionResult


class BundleExecutionAdapter:
    """Routes bundle legs to the configured ``ExecutionProvider``."""

    def __init__(self, provider: ExecutionProvider | None = None) -> None:
        self._provider = provider or get_execution_provider()

    @property
    def provider_name(self) -> str:
        return self._provider.name

    def quote_leg(self, db: Session, leg: ExecutionLeg) -> ExecutionQuote:
        return self._provider.quote_leg(db, leg)

    def execute_leg(
        self,
        db: Session,
        leg: ExecutionLeg,
        actor: ActorContext,
    ) -> ExecutionResult:
        result = self._provider.execute_leg(db, leg, actor)
        if result.status == "failed":
            raise BundleExecutionLegFailedError(
                leg.leg_id,
                result.raw.get("failure_reason") or result.raw.get("reason"),
            )
        # pending = quote/sign/submit en cours — pas d'exception, pas d'atoms PE
        return result


class BundleExecutionLegFailedError(Exception):
    def __init__(self, leg_id: str, reason: str | None = None) -> None:
        self.leg_id = leg_id
        self.reason = reason
        msg = f"execution_leg_failed: {leg_id}"
        if reason:
            msg = f"{msg}: {reason}"
        super().__init__(msg)
