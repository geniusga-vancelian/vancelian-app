"""Enums for the Rebalance Policies module (Portfolio Engine)."""
from enum import Enum


class RebalanceMethod(str, Enum):
    PERIODIC = "periodic"
    THRESHOLD = "threshold"
    HYBRID = "hybrid"
    MANUAL = "manual"
    CASH_FLOW = "cash_flow"


class RebalanceFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    ON_DEMAND = "on_demand"
