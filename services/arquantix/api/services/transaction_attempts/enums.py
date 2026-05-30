"""Enums onchain_transaction_attempts (Phase 2)."""
from __future__ import annotations

from enum import Enum


class AttemptProtocol(str, Enum):
    LIFI = "lifi"
    INTERNAL_BUNDLE = "internal_bundle"
    MORPHO = "morpho"
    LEDGITY = "ledgity"
    LOMBARD = "lombard"
    # Optionnel futur — dépôts Privy observés sans intent obligatoire
    PRIVY = "privy"


class AttemptOperationType(str, Enum):
    SWAP = "swap"
    APPROVE = "approve"
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    BORROW = "borrow"
    INBOUND_DEPOSIT = "inbound_deposit"


class AttemptStepType(str, Enum):
    APPROVE = "approve"
    SWAP = "swap"
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    AUTHORIZE = "authorize"
    OPEN_LOAN = "open_loan"
    COLLATERAL_SUPPLY = "collateral_supply"
    INBOUND_DEPOSIT = "inbound_deposit"


class AttemptStatus(str, Enum):
    PREPARED = "prepared"
    SIGNED = "signed"
    SUBMITTED = "submitted"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    REVERTED = "reverted"
    REPLACED = "replaced"
    DROPPED = "dropped"
    UNKNOWN = "unknown"
    RECONCILIATION_REQUIRED = "reconciliation_required"
