"""Enums for the Rebalance Orchestrator (Phase 8)."""
from enum import Enum


class RebalanceExecutionMode(str, Enum):
    MANUAL = "manual"
    ASSISTED = "assisted"
    AUTOMATIC = "automatic"


class OrchestrationStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"
