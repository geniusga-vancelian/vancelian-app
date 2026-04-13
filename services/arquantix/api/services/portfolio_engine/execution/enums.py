"""Enums for the Execution module (Portfolio Engine — execution layer)."""
from enum import Enum


class ExecutionType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    MANUAL = "manual"
    BANK_TRANSFER = "bank_transfer"
    CUSTODIAN_TRANSFER = "custodian_transfer"
    INTERNAL = "internal"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    FAILED = "failed"


TERMINAL_STATUSES: set[ExecutionStatus] = {
    ExecutionStatus.FILLED,
    ExecutionStatus.REJECTED,
    ExecutionStatus.EXPIRED,
    ExecutionStatus.CANCELLED,
    ExecutionStatus.FAILED,
}

VALID_TRANSITIONS: dict[ExecutionStatus, set[ExecutionStatus]] = {
    ExecutionStatus.PENDING: {ExecutionStatus.SENT, ExecutionStatus.CANCELLED, ExecutionStatus.FAILED},
    ExecutionStatus.SENT: {ExecutionStatus.ACKNOWLEDGED, ExecutionStatus.REJECTED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED},
    ExecutionStatus.ACKNOWLEDGED: {ExecutionStatus.PARTIALLY_FILLED, ExecutionStatus.FILLED, ExecutionStatus.REJECTED, ExecutionStatus.EXPIRED, ExecutionStatus.CANCELLED},
    ExecutionStatus.PARTIALLY_FILLED: {ExecutionStatus.FILLED, ExecutionStatus.CANCELLED, ExecutionStatus.EXPIRED, ExecutionStatus.FAILED},
    ExecutionStatus.FILLED: set(),
    ExecutionStatus.REJECTED: set(),
    ExecutionStatus.EXPIRED: set(),
    ExecutionStatus.CANCELLED: set(),
    ExecutionStatus.FAILED: set(),
}


class ExecutionVenue(str, Enum):
    BINANCE = "binance"
    BANK_FX = "bank_fx"
    INTERNAL = "internal"
    MANUAL = "manual"
