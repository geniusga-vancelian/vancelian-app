"""Enums swap LI.FI."""
from __future__ import annotations

from enum import Enum


class SwapSessionStatus(str, Enum):
    PENDING = "PENDING"
    QUOTE_RECEIVED = "QUOTE_RECEIVED"
    AWAITING_SIGNATURE = "AWAITING_SIGNATURE"
    SUBMITTED = "SUBMITTED"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
