"""Pydantic schemas for job runs and rebuild results (Hardening Subphase 2)."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_type: str
    scope_type: str
    scope_id: Optional[str] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: dict = Field(default_factory=dict, alias="metadata_")
    created_at: datetime


class JobRunListResponse(BaseModel):
    items: list[JobRunRead]
    total: int


class RebuildResult(BaseModel):
    job_run_id: UUID
    portfolio_id: UUID
    job_type: str
    status: str
    records_processed: int = 0
    warnings: list[str] = Field(default_factory=list)
    error_message: Optional[str] = None
