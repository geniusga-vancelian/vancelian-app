"""Schémas admin — job runs observabilité DeFi."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel


class DefiJobRunSummary(BaseModel):
    id: str
    job_name: str
    status: str
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    summary_json: Optional[dict[str, Any]] = None
    error_json: Optional[dict[str, Any]] = None


class DefiJobRunListResponse(BaseModel):
    items: list[DefiJobRunSummary]
    total: int
    skip: int
    limit: int
