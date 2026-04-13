"""Pydantic schemas for the Strategy Engine (Phase 7)."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class StrategySignalResult(BaseModel):
    strategy_instance_id: UUID
    strategy_type: str
    signal_type: str
    action_type: str
    severity: str
    details: dict = Field(default_factory=dict)


class PortfolioEvaluationResponse(BaseModel):
    portfolio_id: UUID
    evaluated_at: datetime
    strategies_evaluated: int
    signals: list[StrategySignalResult]
    warnings: list[str]


class StrategyEvaluationLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    portfolio_id: UUID
    strategy_instance_id: UUID
    strategy_type: str
    signal_type: str
    action_type: str
    severity: str
    details: dict
    evaluation_timestamp: datetime
    created_at: datetime


class StrategySignalListResponse(BaseModel):
    items: list[StrategyEvaluationLogRead]
    total: int
