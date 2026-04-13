"""
Pydantic schemas for Finance Strategy Chat V1.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal, List


class StartRequest(BaseModel):
    locale: Optional[str] = "fr"


class UserInput(BaseModel):
    type: Literal["single_choice", "free_text", "number", "allocation"]
    value: Any


class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class UIState(BaseModel):
    type: Literal["quick_replies", "free_text"]
    quick_replies: Optional[List[str]] = None
    allow_free_text: Optional[bool] = True


class StepRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    user_input: UserInput


class ClientProfile(BaseModel):
    project_summary: Optional[str] = None
    intent: Optional[str] = None
    goal: Dict[str, Any] = Field(default_factory=dict)
    timeline: Dict[str, Any] = Field(default_factory=dict)
    capacity: Dict[str, Any] = Field(default_factory=dict)
    risk: Dict[str, Any] = Field(default_factory=dict)
    knowledge_level: Optional[str] = None
    notes: Optional[str] = None
    confidence: Dict[str, float] = Field(default_factory=dict)


class Patch(BaseModel):
    updates: Dict[str, Any] = Field(default_factory=dict)
    confidence: Dict[str, float] = Field(default_factory=dict)
    routed_to: Optional[str] = None
    routing_reason: Optional[str] = None
    notes: Optional[str] = None


class PatchUpdate(BaseModel):
    path: str
    value: Any
    confidence: float = Field(..., ge=0, le=1)
    source: str


class PatchNormalized(BaseModel):
    money: Optional[Dict[str, Any]] = None


class PatchResult(BaseModel):
    updates: List[PatchUpdate] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    normalized: Optional[PatchNormalized] = None


class LastQuestion(BaseModel):
    id: Optional[str] = None
    text: str
    expected_fields: List[str] = Field(default_factory=list)


class NextQuestion(BaseModel):
    id: str
    topic: str
    question: str
    suggestions: List[str] = Field(default_factory=list)
    allow_free_text: bool = True
    ui_type: Literal["quick_replies", "free_text"] = "free_text"
    expected_fields: List[str] = Field(default_factory=list)


class AuditEvent(BaseModel):
    event_type: str
    payload: Dict[str, Any]
    created_at: str


class StepResponse(BaseModel):
    session_id: str
    messages: List[Message]
    ui: UIState
    progress: Dict[str, int]
    state: Dict[str, Any]


class StartResponse(StepResponse):
    pass


class StateResponse(BaseModel):
    session_id: str
    state: Dict[str, Any]
