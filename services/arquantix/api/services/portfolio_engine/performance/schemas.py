"""Pydantic schemas for the Performance & Benchmark Engine (Phase 9)."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReturnSeriesPoint(BaseModel):
    timestamp: datetime
    nav: str
    period_return: Optional[str] = None
    cumulative_return: Optional[str] = None
    drawdown: Optional[str] = None


class PerformanceSeriesResponse(BaseModel):
    portfolio_id: UUID
    series: list[ReturnSeriesPoint]
    total_return: Optional[str] = None
    max_drawdown: Optional[str] = None
    data_points: int


class PerformanceSummary(BaseModel):
    portfolio_id: UUID
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    total_return: Optional[str] = None
    max_drawdown: Optional[str] = None
    volatility: Optional[str] = None
    winning_days_ratio: Optional[str] = None
    data_points: int
    warnings: list[str] = Field(default_factory=list)


class BenchmarkComparison(BaseModel):
    portfolio_id: UUID
    benchmark_label: Optional[str] = None
    benchmark_instrument_id: Optional[UUID] = None
    portfolio_return: Optional[str] = None
    benchmark_return: Optional[str] = None
    alpha: Optional[str] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    warnings: list[str] = Field(default_factory=list)


class ReturnSeriesSnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    portfolio_id: UUID
    valuation_id: Optional[UUID] = None
    timestamp: datetime
    nav: str
    period_return: Optional[str] = None
    cumulative_return: Optional[str] = None
    drawdown: Optional[str] = None
    metadata: dict = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
