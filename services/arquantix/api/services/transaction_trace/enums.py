"""Types d'événements transaction trace (observabilité, pas source of truth)."""
from __future__ import annotations

from enum import Enum


class TraceEventType(str, Enum):
    INTENT_CREATED = "intent_created"
    INTENT_STATUS_CHANGED = "intent_status_changed"
    ATTEMPT_PREPARED = "attempt_prepared"
    ATTEMPT_SIGNED = "attempt_signed"
    ATTEMPT_SUBMITTED = "attempt_submitted"
    ATTEMPT_CONFIRMED = "attempt_confirmed"
    ATTEMPT_FAILED = "attempt_failed"
    LEGACY_RECORD_LINKED = "legacy_record_linked"
    LEDGER_POSTED = "ledger_posted"
    RECONCILIATION_GAP_DETECTED = "reconciliation_gap_detected"
    REPLAY_BACKFILL_CANDIDATE = "replay_backfill_candidate"
    REPLAY_BACKFILL_APPLIED = "replay_backfill_applied"
