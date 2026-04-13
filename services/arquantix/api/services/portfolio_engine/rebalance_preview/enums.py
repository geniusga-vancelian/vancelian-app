"""Enums for the Rebalance Preview module (Portfolio Engine)."""
from enum import Enum


class PreviewStatus(str, Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    STALE = "stale"


class TradeDirection(str, Enum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
