"""Enums for the Strategy Engine (Phase 7)."""
from enum import Enum


class StrategySignalType(str, Enum):
    REBALANCE_REQUIRED = "rebalance_required"
    PERIODIC_REBALANCE = "periodic_rebalance"
    DRIFT_WARNING = "drift_warning"
    RISK_LIMIT_EXCEEDED = "risk_limit_exceeded"
    NO_SIGNAL = "no_signal"


class StrategyActionType(str, Enum):
    CREATE_REBALANCE_PREVIEW = "create_rebalance_preview"
    ALERT_RISK = "alert_risk"
    NO_ACTION = "no_action"


class SignalSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
