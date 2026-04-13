"""Pydantic schemas for Bundle Engine v1.

Strict payload validation for bundle creation, listing, and detail.
Weight tolerance: 0.005 (0.5%).
Supported rebalance frequencies: weekly, monthly, quarterly.
"""
import re
from decimal import Decimal
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

PRODUCT_CODE_PATTERN = re.compile(r"^[A-Z0-9_]{1,100}$")
SUPPORTED_REBALANCE_FREQUENCIES = frozenset({"weekly", "monthly", "quarterly"})
WEIGHT_TOLERANCE = Decimal("0.005")


class BundleAllocationCreate(BaseModel):
    instrument_id: UUID
    target_weight: Decimal = Field(ge=0, le=1)
    min_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    max_weight: Optional[Decimal] = Field(default=None, ge=0, le=1)
    allocation_priority: int = 100

    @model_validator(mode="after")
    def _validate_weight_ordering(self) -> "BundleAllocationCreate":
        if self.min_weight is not None and self.min_weight > self.target_weight:
            raise ValueError("min_weight must be <= target_weight")
        if self.max_weight is not None and self.max_weight < self.target_weight:
            raise ValueError("max_weight must be >= target_weight")
        if (
            self.min_weight is not None
            and self.max_weight is not None
            and self.min_weight > self.max_weight
        ):
            raise ValueError("min_weight must be <= max_weight")
        return self


class BundleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    product_code: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    risk_label: Optional[str] = Field(default="high")
    base_currency: str = Field(default="USD", max_length=20)
    is_public: bool = True
    allocations: list[BundleAllocationCreate] = Field(..., min_length=1)
    available_rebalance_frequencies: list[str] = Field(
        default_factory=lambda: ["weekly", "monthly", "quarterly"]
    )
    entry_asset_default: str = Field(default="USDC", max_length=20)
    entry_assets_allowed: list[str] = Field(default_factory=lambda: ["USDC"])
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("product_code")
    @classmethod
    def _validate_product_code_format(cls, v: str) -> str:
        if not PRODUCT_CODE_PATTERN.match(v):
            raise ValueError(
                f"product_code must match ^[A-Z0-9_]{{1,100}}$, got '{v}'"
            )
        return v

    @field_validator("available_rebalance_frequencies")
    @classmethod
    def _validate_frequencies(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("available_rebalance_frequencies must not be empty")
        seen: set[str] = set()
        for freq in v:
            if freq not in SUPPORTED_REBALANCE_FREQUENCIES:
                raise ValueError(
                    f"Unsupported rebalance frequency '{freq}'. "
                    f"Allowed: {sorted(SUPPORTED_REBALANCE_FREQUENCIES)}"
                )
            if freq in seen:
                raise ValueError(f"Duplicate rebalance frequency '{freq}'")
            seen.add(freq)
        return v

    @model_validator(mode="after")
    def _validate_allocations(self) -> "BundleCreate":
        instrument_ids = [a.instrument_id for a in self.allocations]
        if len(instrument_ids) != len(set(instrument_ids)):
            raise ValueError("Duplicate instrument_id in allocations")

        total = sum(a.target_weight for a in self.allocations)
        if abs(total - Decimal("1")) > WEIGHT_TOLERANCE:
            raise ValueError(
                f"Sum of target_weight must be 1.0 ± {WEIGHT_TOLERANCE} "
                f"(got {total})"
            )
        return self


class BundleVisibilityUpdate(BaseModel):
    is_public: bool


class BundleVisibilityResponse(BaseModel):
    id: UUID
    product_code: str
    is_public: bool
    action: str


class BundleAllocationSummary(BaseModel):
    instrument_id: UUID
    instrument_code: str
    asset_symbol: str
    target_weight: Decimal


class BundleAllocationDetail(BaseModel):
    id: UUID
    instrument_id: UUID
    instrument_code: str
    instrument_name: str
    asset_symbol: str
    target_weight: Decimal
    min_weight: Optional[Decimal] = None
    max_weight: Optional[Decimal] = None
    allocation_priority: int


class BundleListItem(BaseModel):
    id: UUID
    product_code: str
    name: str
    status: str
    is_public: bool
    product_type: str
    template_id: Optional[UUID] = None
    allocations_count: int
    allocation_summary: list[BundleAllocationSummary] = Field(default_factory=list)
    available_rebalance_frequencies: list[str] = Field(default_factory=list)


class BundleListResponse(BaseModel):
    items: list[BundleListItem]
    total: int


class BundleDetailResponse(BaseModel):
    id: UUID
    product_code: str
    name: str
    description: Optional[str] = None
    product_type: str
    risk_label: Optional[str] = None
    base_currency: str
    is_public: bool
    status: str
    template_id: UUID
    template_code: str
    allocations: list[BundleAllocationDetail] = Field(default_factory=list)
    available_rebalance_frequencies: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime
