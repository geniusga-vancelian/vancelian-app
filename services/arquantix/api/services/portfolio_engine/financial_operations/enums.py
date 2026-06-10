"""Enums — Portfolio Financial Operation Guard (PR-4)."""
from __future__ import annotations

from enum import Enum


class PortfolioFinancialOperationType(str, Enum):
    BUNDLE_INVEST = "BUNDLE_INVEST"
    BUNDLE_REBALANCE_V3 = "BUNDLE_REBALANCE_V3"
    BUNDLE_TRANSACTION_V3 = "BUNDLE_TRANSACTION_V3"
    BUNDLE_WITHDRAW = "BUNDLE_WITHDRAW"
    INTERNAL_SWAP = "INTERNAL_SWAP"
    LOMBARD_OPEN = "LOMBARD_OPEN"
    LOMBARD_CLOSE = "LOMBARD_CLOSE"
    VAULT_DEPOSIT = "VAULT_DEPOSIT"
    VAULT_WITHDRAW = "VAULT_WITHDRAW"


class PortfolioFinancialOperationStatus(str, Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"
