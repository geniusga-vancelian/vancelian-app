"""Enums for the Custody module."""
from enum import Enum


class ProviderType(str, Enum):
    BANK = "bank"
    EMI = "emi"


class ProviderStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class CustodyAccountType(str, Enum):
    CLIENT_DEPOSIT = "client_deposit_account"
    COMPANY_SETTLEMENT = "company_settlement_account"


class CustodyAccountStatus(str, Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER_INTERNAL = "transfer_internal"


class TransactionKind(str, Enum):
    BANK_TRANSFER_IN = "bank_transfer_in"
    BANK_TRANSFER_OUT = "bank_transfer_out"
    INTERNAL_TRANSFER = "internal_transfer"
    EXCHANGE_BUY = "exchange_buy"
    EXCHANGE_SELL = "exchange_sell"


class TransactionDirection(str, Enum):
    CREDIT = "credit"
    DEBIT = "debit"


class TransactionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVERSED = "reversed"


class WebhookEventStatus(str, Enum):
    RECEIVED = "received"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"
    DUPLICATE = "duplicate"
    IGNORED = "ignored"


class NormalizedEventType(str, Enum):
    DEPOSIT_DETECTED = "deposit_detected"
    WITHDRAWAL_REQUESTED = "withdrawal_requested"
    WITHDRAWAL_COMPLETED = "withdrawal_completed"
    WITHDRAWAL_FAILED = "withdrawal_failed"
    INTERNAL_TRANSFER_COMPLETED = "internal_transfer_completed"
    REVERSAL_DETECTED = "reversal_detected"
