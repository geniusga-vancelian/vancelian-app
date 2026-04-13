"""Pydantic schemas for scheduled jobs (Hardening Subphase 4)."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ScheduledJobCreate(BaseModel):
    job_name: str
    job_type: str
    scope_type: str
    scope_id: Optional[str] = None
    schedule_type: str = "interval"
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    is_enabled: bool = True
    metadata: dict = Field(default_factory=dict)


class ScheduledJobUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    next_run_at: Optional[datetime] = None
    metadata: Optional[dict] = None


class ScheduledJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    job_name: str
    job_type: str
    scope_type: str
    scope_id: Optional[str] = None
    schedule_type: str
    cron_expression: Optional[str] = None
    interval_seconds: Optional[int] = None
    is_enabled: bool
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class ScheduledJobListResponse(BaseModel):
    items: list[ScheduledJobRead]
    total: int


class SchedulerRunSummary(BaseModel):
    jobs_found: int
    jobs_run: int
    jobs_succeeded: int
    jobs_failed: int
    warnings: list[str] = Field(default_factory=list)
