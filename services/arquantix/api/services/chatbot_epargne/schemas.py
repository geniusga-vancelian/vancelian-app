"""
Request/Response schemas for Bot IA épargne routes.
"""
from typing import Any, Optional

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    user_id: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str


class SessionDetailResponse(BaseModel):
    session_id: str
    meta: dict[str, Any] = Field(default_factory=dict)
    last_turns: list[dict[str, Any]] = Field(default_factory=list)


class TurnRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class TurnResponse(BaseModel):
    reply: str
    profile_diff: Optional[dict[str, Any]] = None
    state: str = "coach"  # welcome|project|goals|horizon|...|restitution|repair_*
    disclaimers_shown: list[str] = Field(default_factory=list)
    proposal_preview: Optional[dict[str, Any]] = None
    completeness_score: Optional[float] = None
    project_summary: Optional[str] = None  # Carte Résumé Projet (live), null en restitution
    conversation_summary: Optional[str] = None
    conversation_facts: list[str] = Field(default_factory=list)
    profile: Optional[dict[str, Any]] = None
    next_question_id: Optional[str] = None
    goal_phase: Optional[str] = None
    goal_locked: Optional[bool] = None
    goal_confidence: Optional[float] = None
    goal_attempts: Optional[int] = None
    debug: Optional[dict[str, Any]] = None  # Only if DEBUG_CHATBOT=true


class ProfileResponse(BaseModel):
    profile: dict[str, Any] = Field(default_factory=dict)
    completeness_score: float = 0.0
    missing_fields: list[str] = Field(default_factory=list)
