"""Enums transaction_outbox (Phase 2 S1)."""
from __future__ import annotations

from enum import Enum


class OutboxEventStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    DEAD_LETTER = "dead_letter"


class OutboxEventType(str, Enum):
    INTENT_CREATED = "intent.created"
    INTENT_PROVIDER_SUBMITTED = "intent.provider_submitted"
    INTENT_SETTLE = "intent.settle"
    INTENT_RECONCILE = "intent.reconcile"
    DEPOSIT_OBSERVED = "deposit.observed"
    BUNDLE_V3_REBALANCE_REQUESTED = "bundle.v3_rebalance_requested"
