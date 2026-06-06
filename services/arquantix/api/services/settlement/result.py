"""SettlementResult — états fermés Settlement Layer Contract v1."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from uuid import UUID


class SettlementOutcome(str, Enum):
    SUCCESS = "SUCCESS"
    RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
    TERMINAL_FAILURE = "TERMINAL_FAILURE"
    NOOP_ALREADY_SETTLED = "NOOP_ALREADY_SETTLED"


@dataclass(frozen=True)
class SettlementResult:
    outcome: SettlementOutcome
    intent_id: UUID
    settlement_receipt_hash: str | None = None
    error_code: str | None = None
    error_message: str | None = None
