"""Enums for the Clients module (Portfolio Engine — ownership layer)."""
from enum import Enum


class ClientStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class KycStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReferenceCurrency(str, Enum):
    EUR = "EUR"
    USD = "USD"
