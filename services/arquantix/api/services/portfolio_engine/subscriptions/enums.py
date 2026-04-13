"""Enums for the Subscriptions module (Portfolio Engine — product subscription layer)."""
from enum import Enum


class SubscriptionStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    REDEEMED = "redeemed"
    CANCELLED = "cancelled"
