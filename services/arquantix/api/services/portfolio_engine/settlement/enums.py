"""Enums for the Settlement module (Portfolio Engine — settlement layer)."""
from enum import Enum


class SettlementType(str, Enum):
    INTERNAL = "internal"
    BANK_TRANSFER = "bank_transfer"
    CUSTODIAN_TRANSFER = "custodian_transfer"
    LP_SETTLEMENT = "lp_settlement"
    TREASURY_MOVE = "treasury_move"


class SettlementStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    SETTLED = "settled"
    FAILED = "failed"


VALID_TRANSITIONS: dict[SettlementStatus, set[SettlementStatus]] = {
    SettlementStatus.PENDING: {SettlementStatus.SETTLED, SettlementStatus.SCHEDULED, SettlementStatus.FAILED},
    SettlementStatus.SCHEDULED: {SettlementStatus.IN_PROGRESS, SettlementStatus.FAILED},
    SettlementStatus.IN_PROGRESS: {SettlementStatus.SETTLED, SettlementStatus.FAILED},
    SettlementStatus.SETTLED: set(),
    SettlementStatus.FAILED: set(),
}
