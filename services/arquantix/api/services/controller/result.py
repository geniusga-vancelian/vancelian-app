"""ReconciliationResult — états fermés Controller S3 v1 (LI.FI standalone)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any
from uuid import UUID


class ReconciliationOutcome(str, Enum):
    RECONCILED = "RECONCILED"
    RECONCILIATION_RETRYABLE_FAILURE = "RECONCILIATION_RETRYABLE_FAILURE"
    RECONCILIATION_TERMINAL_FAILURE = "RECONCILIATION_TERMINAL_FAILURE"
    NOOP_ALREADY_RECONCILED = "NOOP_ALREADY_RECONCILED"


@dataclass(frozen=True)
class ReconciliationResult:
    outcome: ReconciliationOutcome
    intent_id: UUID
    reconciliation_report_hash: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    projection: dict[str, Any] | None = None
