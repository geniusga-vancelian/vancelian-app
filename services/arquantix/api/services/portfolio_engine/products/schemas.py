"""Pydantic schemas for the Products module (Portfolio Engine — catalog layer)."""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import ProductStatus, ProductType, RiskLabel


class ProductCreate(BaseModel):
    product_code: str = Field(..., max_length=100)
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    product_type: ProductType
    risk_label: Optional[RiskLabel] = None
    base_currency: str = Field("EUR", max_length=20)
    is_public: bool = False
    status: ProductStatus = ProductStatus.DRAFT
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    product_type: Optional[ProductType] = None
    risk_label: Optional[RiskLabel] = None
    base_currency: Optional[str] = Field(None, max_length=20)
    is_public: Optional[bool] = None
    status: Optional[ProductStatus] = None
    metadata: Optional[dict[str, Any]] = None


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    product_code: str
    name: str
    description: Optional[str] = None
    product_type: str
    risk_label: Optional[str] = None
    base_currency: str
    is_public: bool
    status: str
    metadata: dict[str, Any] = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class ProductListResponse(BaseModel):
    items: list[ProductRead]
    total: int
