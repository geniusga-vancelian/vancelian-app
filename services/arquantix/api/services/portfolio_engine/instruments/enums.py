"""Enums for the Instruments module (Portfolio Engine registry layer)."""
from enum import Enum


class InstrumentType(str, Enum):
    SPOT = "spot"
    STAKING_POSITION = "staking_position"
    VAULT_SHARE = "vault_share"
    PRIVATE_DEAL_SHARE = "private_deal_share"
    COLLATERAL_POSITION = "collateral_position"
    DEBT_LIABILITY = "debt_liability"
    YIELD_ACCRUAL = "yield_accrual"


class ValuationMethod(str, Enum):
    MARK_TO_MARKET = "mark_to_market"
    NAV = "nav"
    COST_BASIS = "cost_basis"
    AMORTIZED = "amortized"
    MANUAL = "manual"
