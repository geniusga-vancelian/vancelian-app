"""Execution provider factory."""
from __future__ import annotations

from typing import Protocol

from sqlalchemy.orm import Session

from services.portfolio_engine.hardening.security.context import ActorContext

from .config import get_bundle_execution_provider_name
from .types import ExecutionLeg, ExecutionQuote, ExecutionResult


class ExecutionProvider(Protocol):
    @property
    def name(self) -> str: ...

    def quote_leg(self, db: Session, leg: ExecutionLeg) -> ExecutionQuote: ...

    def execute_leg(
        self,
        db: Session,
        leg: ExecutionLeg,
        actor: ActorContext,
    ) -> ExecutionResult: ...


def get_execution_provider(provider_name: str | None = None) -> ExecutionProvider:
    name = provider_name or get_bundle_execution_provider_name()
    if name in ("lifi_base", "lifi"):
        from .lifi_provider import LifiExecutionProvider

        return LifiExecutionProvider()
    from .exchange_provider import ExchangeExecutionProvider

    return ExchangeExecutionProvider()
