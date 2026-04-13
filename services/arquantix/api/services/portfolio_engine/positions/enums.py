"""Enums for the Position Atoms module (Portfolio Engine — position layer).

Phase 1:   SPOT, CASH
Phase 2A:  LENDING, BORROWING  (P2P internal lending)
Phase 2+:  STAKING, COLLATERAL (future)
"""
from enum import Enum


class PositionType(str, Enum):
    SPOT = "spot"
    CASH = "cash"

    # Phase 2A — P2P internal lending
    LENDING = "lending"
    BORROWING = "borrowing"

    # Phase 2+ — defined for forward-compatibility, NOT to be used yet.
    STAKING = "staking"
    COLLATERAL = "collateral"


# Phase 2A: lending and borrowing are now allowed alongside spot and cash.
ALLOWED_POSITION_TYPES = frozenset({
    PositionType.SPOT,
    PositionType.CASH,
    PositionType.LENDING,
    PositionType.BORROWING,
})


class PositionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    PENDING = "pending"
    LIQUIDATED = "liquidated"


class LockupStatus(str, Enum):
    NONE = "none"
    LOCKED = "locked"
    UNLOCKING = "unlocking"
    UNLOCKED = "unlocked"
