"""Enums for the P2P Lending module."""
from enum import Enum


class LoanStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    ACTIVE = "active"
    REPAID = "repaid"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    DEFAULT = "default"


VALID_TRANSITIONS: dict[LoanStatus, frozenset[LoanStatus]] = {
    LoanStatus.PENDING: frozenset({LoanStatus.ACCEPTED, LoanStatus.REJECTED, LoanStatus.CANCELLED}),
    LoanStatus.ACCEPTED: frozenset({LoanStatus.ACTIVE, LoanStatus.CANCELLED}),
    LoanStatus.ACTIVE: frozenset({LoanStatus.REPAID, LoanStatus.DEFAULT}),
    LoanStatus.REPAID: frozenset(),
    LoanStatus.REJECTED: frozenset(),
    LoanStatus.CANCELLED: frozenset(),
    LoanStatus.DEFAULT: frozenset(),
}
