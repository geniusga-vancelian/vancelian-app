"""Énumérations du journal bundle (Phase 4A — shadow mode)."""
from __future__ import annotations

from enum import Enum


class BundleLedgerEventType(str, Enum):
    BUNDLE_DEPOSIT = "BUNDLE_DEPOSIT"
    BUNDLE_WITHDRAWAL = "BUNDLE_WITHDRAWAL"
    BUNDLE_ALLOCATION_BUY = "BUNDLE_ALLOCATION_BUY"
    BUNDLE_ALLOCATION_SELL = "BUNDLE_ALLOCATION_SELL"
    BUNDLE_REBALANCE_BUY = "BUNDLE_REBALANCE_BUY"
    BUNDLE_REBALANCE_SELL = "BUNDLE_REBALANCE_SELL"
    BUNDLE_CASH_RESERVED = "BUNDLE_CASH_RESERVED"
    BUNDLE_CASH_RELEASED = "BUNDLE_CASH_RELEASED"
    BUNDLE_FEE = "BUNDLE_FEE"
    BUNDLE_RECOVERY_ADJUSTMENT = "BUNDLE_RECOVERY_ADJUSTMENT"


class BundleLedgerDirection(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"
    INFO = "info"


class BundleLedgerSourceSystem(str, Enum):
    PE_TRANSFER = "pe_transfer"
    LIFI = "lifi"
    EXCHANGE = "exchange"
    MANUAL_RECOVERY = "manual_recovery"


class BundleLedgerStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REVERSED = "reversed"
