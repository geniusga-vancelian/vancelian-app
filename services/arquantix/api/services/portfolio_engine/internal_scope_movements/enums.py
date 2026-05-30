"""Scopes and movement types — internal portfolio accounting (dry-run spec)."""
from __future__ import annotations

from enum import Enum


class InternalScope(str, Enum):
    TRADING_AVAILABLE = "trading_available"
    TRADING_LOCKED_COLLATERAL = "trading_locked_collateral"
    BUNDLE_CASH = "bundle_cash"
    BUNDLE_POSITION = "bundle_position"
    VAULT_POSITION = "vault_position"
    LIABILITY = "liability"


class InternalMovementType(str, Enum):
    FUND = "fund"
    RELEASE = "release"
    LOCK = "lock"
    UNLOCK = "unlock"
    BORROW = "borrow"
    REPAY = "repay"
    ALLOCATE = "allocate"
