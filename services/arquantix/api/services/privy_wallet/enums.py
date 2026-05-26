"""Enums for the Privy user-wallet ledger module."""
from __future__ import annotations

from enum import Enum


class PrivyWebhookEventStatus(str, Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    DUPLICATE = "duplicate"
    FAILED = "failed"
    IGNORED = "ignored"


class PersonWalletDepositStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class PersonWalletTransactionKind(str, Enum):
    PRIVY_DEPOSIT_IN = "privy_deposit_in"


class PersonWalletDirection(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class PrivyReconciliationRunStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    COMPLETED_WITH_ISSUES = "completed_with_issues"
    FAILED = "failed"


class PrivyReconciliationItemStatus(str, Enum):
    MATCHED = "matched"
    CHAIN_AHEAD = "chain_ahead"
    LEDGER_AHEAD = "ledger_ahead"
    MISMATCH = "mismatch"
    HEALED = "healed"
    UNRESOLVED = "unresolved"
