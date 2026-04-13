"""Pydantic schemas for authorization / ownership scoping."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AdvisorClientAssignmentCreate(BaseModel):
    advisor_actor_id: str
    client_id: UUID
    status: str = "active"
    metadata: dict = Field(default_factory=dict)


class AdvisorClientAssignmentUpdate(BaseModel):
    status: Optional[str] = None
    metadata: Optional[dict] = None


class AdvisorClientAssignmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    advisor_actor_id: str
    client_id: UUID
    status: str
    metadata: dict = Field(default_factory=dict, alias="metadata_")
    created_at: datetime
    updated_at: datetime


class AdvisorClientAssignmentListResponse(BaseModel):
    items: list[AdvisorClientAssignmentRead]
    total: int
