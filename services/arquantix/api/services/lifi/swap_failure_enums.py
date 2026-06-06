"""Codes et phases d'échec swap LI.FI — audit trail."""
from __future__ import annotations

from enum import Enum


class SwapFailurePhase(str, Enum):
    QUOTE = "quote"
    CONFIRM_EXECUTE = "confirm_execute"
    APPROVAL = "approval"
    SIGNING = "signing"
    SUBMITTING = "submitting"
    POLLING = "polling"
    SETTLEMENT = "settlement"


class SwapFailureCode(str, Enum):
    USER_REJECTED_SIGNATURE = "user_rejected_signature"
    USER_REJECTED_APPROVAL = "user_rejected_approval"
    USER_ABANDONED = "user_abandoned"
    WALLET_ERROR = "wallet_error"
    WALLET_MISMATCH = "wallet_mismatch"
    RPC_ERROR = "rpc_error"
    LIFI_ERROR = "lifi_error"
    QUOTE_EXPIRED = "quote_expired"
    INSUFFICIENT_FUNDS = "insufficient_funds"
    PRICE_CHANGED = "price_changed"
    UNKNOWN_ERROR = "unknown_error"
