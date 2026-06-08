"""Enums — S4 product locks (ADR 001 §5bis)."""
from __future__ import annotations

from enum import Enum


class ProductLockScope(str, Enum):
    """Scope économique verrouillé sur un asset wallet."""

    TRADING_AVAILABLE = "trading_available"
    BUNDLE = "bundle"
    VAULT = "vault"
    LOMBARD_COLLATERAL = "lombard_collateral"
    LOMBARD_BORROW = "lombard_borrow"
    FINANCIAL_TRANSACTION = "financial_transaction"


class ProductLockStatus(str, Enum):
    ACTIVE = "active"
    RELEASED = "released"
    EXPIRED = "expired"
