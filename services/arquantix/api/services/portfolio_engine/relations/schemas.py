"""Pydantic schemas for the Position Relations module (Portfolio Engine — relation layer)."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from .enums import RelationType


class RelationCreate(BaseModel):
    source_position_id: UUID
    target_position_id: UUID
    relation_type: RelationType
    parameters: dict = Field(default_factory=dict)


class RelationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_position_id: UUID
    target_position_id: UUID
    relation_type: str
    parameters: dict
    created_at: datetime


class RelationListResponse(BaseModel):
    items: list[RelationRead]
    total: int
