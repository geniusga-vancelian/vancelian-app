"""Enums for the Orders module (Portfolio Engine — transaction layer)."""
from enum import Enum


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    FX_CONVERSION = "fx_conversion"
    INTEREST_PAYMENT = "interest_payment"
    INTERNAL_TRANSFER = "internal_transfer"
    FEE_CHARGE = "fee_charge"


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXECUTING = "executing"
    PARTIALLY_FILLED = "partially_filled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.ACCEPTED, OrderStatus.REJECTED},
    OrderStatus.ACCEPTED: {OrderStatus.EXECUTING, OrderStatus.CANCELLED},
    OrderStatus.EXECUTING: {OrderStatus.COMPLETED, OrderStatus.PARTIALLY_FILLED, OrderStatus.CANCELLED},
    OrderStatus.PARTIALLY_FILLED: {OrderStatus.COMPLETED, OrderStatus.CANCELLED},
    OrderStatus.REJECTED: set(),
    OrderStatus.COMPLETED: set(),
    OrderStatus.CANCELLED: set(),
}
