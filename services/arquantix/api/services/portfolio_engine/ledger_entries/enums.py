"""Enums for the Ledger Entries module (Portfolio Engine — accounting layer)."""
from enum import Enum


class EntryType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class ReferenceType(str, Enum):
    TRADE = "trade"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    FEE = "fee"
    INTEREST = "interest"
    TRANSFER = "transfer"
    CORRECTION = "correction"
    SETTLEMENT = "settlement"
