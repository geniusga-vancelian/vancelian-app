"""
Pydantic schemas for jurisdiction configs
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal, Union
import uuid


# Condition operators
ConditionOperator = Literal["equals", "not_equals", "in", "not_in", "exists", "not_exists"]


class ConditionExpression(BaseModel):
    """Condition expression: when field matches criteria"""
    field_slug: str
    operator: ConditionOperator
    value: Union[Any, List[Any]]  # For in/not_in: list, for others: single value


class ConditionAction(BaseModel):
    """Action to take when condition is true"""
    action: Literal["show_block", "hide_block", "require_field", "optional_field", "skip_step", "goto_step"]
    target: str  # block_id, field_slug, or step_id depending on action


class Condition(BaseModel):
    """Condition: when expression is true, execute actions"""
    when: ConditionExpression
    then: List[ConditionAction]


class Block(BaseModel):
    """Block: group of fields with layout and conditions"""
    block_id: str
    fields: List[str]  # field slugs
    layout: Literal["single_column", "two_columns", "cards"]
    required: bool = True
    conditions: Optional[List[Condition]] = None


class Step(BaseModel):
    """Step: collection of blocks. Conditions must be on Block.conditions, not Step."""
    step_id: str
    title_en: str
    description_en: Optional[str] = None
    blocks: List[Block]
    
    class Config:
        extra = "forbid"


class EntryRule(BaseModel):
    """Entry rule: condition to select this config"""
    field_slug: str
    operator: ConditionOperator
    value: Union[Any, List[Any]]


class JurisdictionConfigSchema(BaseModel):
    """Schema for config_json in jurisdiction_configs table"""
    jurisdiction: str
    purpose: str
    version: int
    steps: List[Step]
    entry_rules: Optional[List[EntryRule]] = None
    status: Literal["draft", "active", "archived"] = "draft"


class JurisdictionConfigCreate(BaseModel):
    """Request to create a jurisdiction config"""
    jurisdiction: str
    purpose: str
    config_json: Dict[str, Any]  # Accept dict for flexibility (UI sends dict)


class JurisdictionConfigResponse(BaseModel):
    """Response for jurisdiction config"""
    id: uuid.UUID
    jurisdiction: str
    purpose: str
    version: int
    status: str
    config_json: Dict[str, Any]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class NextStepResponse(BaseModel):
    """Response for next-step endpoint"""
    config_id: str
    version: int
    step: Optional[Dict[str, Any]] = None
    completion: Dict[str, Any]


class SubmitStepRequest(BaseModel):
    """Request to submit step values"""
    step_id: str
    values: Dict[str, Any]
    correlation_id: Optional[uuid.UUID] = None


class SubmitStepResponse(BaseModel):
    """Response after submitting step"""
    person_id: str
    step_id: str
    audit_event_ids: List[str]
    next_step: Optional[Dict[str, Any]] = None
    completion: Dict[str, Any]
