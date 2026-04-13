"""Enums for the Ledger Accounts module (Portfolio Engine — accounting layer)."""
from enum import Enum


class LedgerAccountType(str, Enum):
    CLIENT = "client"
    RL_INTERNAL = "rl_internal"
    TREASURY = "treasury"
    FEE = "fee"


class LedgerAccountStatus(str, Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"
