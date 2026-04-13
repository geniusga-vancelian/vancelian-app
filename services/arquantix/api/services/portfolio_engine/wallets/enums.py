"""Enums for the Wallet Containers module (Portfolio Engine — ledger layer)."""
from enum import Enum


class WalletType(str, Enum):
    SPOT_WALLET = "spot_wallet"
    STAKING_WALLET = "staking_wallet"
    COLLATERAL_WALLET = "collateral_wallet"
    LOAN_WALLET = "loan_wallet"
    VAULT_ACCOUNT = "vault_account"
    PRIVATE_DEAL_ACCOUNT = "private_deal_account"
    CASH_WALLET = "cash_wallet"
    FEE_WALLET = "fee_wallet"
    STRATEGY_EXECUTION_WALLET = "strategy_execution_wallet"


class WalletStatus(str, Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"
