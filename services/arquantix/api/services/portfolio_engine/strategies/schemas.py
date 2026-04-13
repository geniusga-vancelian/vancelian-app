"""Pydantic schemas for the Strategies module (Portfolio Engine — strategy layer).

Covers both StrategyDefinition and StrategyInstance.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import StrategyType, InstanceStatus


# ---------------------------------------------------------------------------
# StrategyDefinition schemas
# ---------------------------------------------------------------------------

class DefinitionCreate(BaseModel):
    code: str
    name: str
    strategy_type: StrategyType
    description: Optional[str] = None
    parameters_schema: dict = Field(default_factory=dict)


class DefinitionUpdate(BaseModel):
    name: Optional[str] = None
    strategy_type: Optional[StrategyType] = None
    description: Optional[str] = None
    parameters_schema: Optional[dict] = None


class DefinitionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    strategy_type: str
    description: Optional[str] = None
    parameters_schema: dict
    created_at: datetime
    updated_at: datetime


class DefinitionListResponse(BaseModel):
    items: list[DefinitionRead]
    total: int


# ---------------------------------------------------------------------------
# StrategyInstance schemas
# ---------------------------------------------------------------------------

class InstanceCreate(BaseModel):
    portfolio_id: UUID
    sleeve_id: Optional[UUID] = None
    strategy_definition_id: UUID
    name: Optional[str] = None
    status: InstanceStatus = InstanceStatus.ACTIVE
    priority: int = 100
    parameters: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)


class InstanceUpdate(BaseModel):
    sleeve_id: Optional[UUID] = None
    name: Optional[str] = None
    status: Optional[InstanceStatus] = None
    priority: Optional[int] = None
    parameters: Optional[dict] = None
    metadata: Optional[dict] = None


class InstanceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    portfolio_id: UUID
    sleeve_id: Optional[UUID] = None
    strategy_definition_id: UUID
    name: Optional[str] = None
    status: str
    priority: int
    parameters: dict
    metadata: dict = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class InstanceListResponse(BaseModel):
    items: list[InstanceRead]
    total: int
