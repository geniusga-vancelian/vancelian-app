"""Enums transaction_intents (Phase 7)."""
from __future__ import annotations

from enum import Enum


class IntentProductType(str, Enum):
    LIFI_SWAP = "lifi_swap"
    MORPHO_EARN = "morpho_earn"
    LEDGITY_VAULT = "ledgity_vault"
    LOMBARD_BORROW = "lombard_borrow"
    BUNDLE_INVEST = "bundle_invest"
    BUNDLE_WITHDRAW = "bundle_withdraw"
    PRIVY_DEPOSIT = "privy_deposit"


class IntentOperationType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    SWAP = "swap"
    SUPPLY = "supply"
    BORROW = "borrow"
    REPAY = "repay"
    BUNDLE_LEG = "bundle_leg"
    INVEST = "invest"


class IntentStatus(str, Enum):
    CREATED = "created"
    AWAITING_SIGNATURE = "awaiting_signature"
    SUBMITTED = "submitted"
    CONFIRMING = "confirming"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    PARTIAL = "partial"
    RECONCILIATION_REQUIRED = "reconciliation_required"
    # Lombard multi-step terminal / retry (Phase 3B-R2 — String(32), pas de CHECK DB)
    RETRYABLE_FAILED = "retryable_failed"
    SUPERSEDED = "superseded"
    FAILED_FINAL = "failed_final"
