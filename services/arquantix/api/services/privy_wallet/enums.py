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
