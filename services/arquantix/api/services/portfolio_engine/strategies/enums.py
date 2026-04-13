"""Enums for the Strategies module (Portfolio Engine — strategy layer)."""
from enum import Enum


class StrategyType(str, Enum):
    BUY_AND_HOLD = "buy_and_hold"
    TARGET_ALLOCATION = "target_allocation"
    PERIODIC_REBALANCE = "periodic_rebalance"
    THRESHOLD_REBALANCE = "threshold_rebalance"
    STAKING = "staking"
    COLLATERALIZED_BORROWING = "collateralized_borrowing"
    CPPI = "cppi"
    CORE_SATELLITE = "core_satellite"
    DISCRETIONARY_MANUAL = "discretionary_manual"
    MODEL_PORTFOLIO = "model_portfolio"


class InstanceStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
