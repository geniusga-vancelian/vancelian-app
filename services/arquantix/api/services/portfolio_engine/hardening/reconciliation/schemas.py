"""Pydantic schemas for reconciliation reports (Hardening Subphase 3)."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReconciliationReportRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    reconciliation_type: str
    scope_type: str
    scope_id: Optional[str] = None
    status: str
    differences_found: int
    metadata: dict = Field(default_factory=dict, alias="metadata_")
    created_at: datetime


class ReconciliationReportListResponse(BaseModel):
    items: list[ReconciliationReportRead]
    total: int


class ReconciliationResult(BaseModel):
    job_run_id: UUID
    reconciliation_report_id: UUID
    reconciliation_type: str
    scope_type: str
    scope_id: Optional[str] = None
    status: str
    differences_found: int
    warnings: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
