"""Pydantic schemas for the Rebalance Orchestrator (Phase 8)."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OrchestrationResult(BaseModel):
    run_id: UUID
    portfolio_id: UUID
    mode: str
    status: str
    signals_detected: int
    actions_taken: int
    rebalance_preview_id: Optional[UUID] = None
    abort_reason: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)


class OrchestrationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    portfolio_id: UUID
    mode: str
    signals_detected: int
    actions_taken: int
    rebalance_preview_id: Optional[UUID] = None
    status: str
    abort_reason: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict, alias="metadata_")
    created_at: datetime


class OrchestrationRunListResponse(BaseModel):
    items: list[OrchestrationRunRead]
    total: int
