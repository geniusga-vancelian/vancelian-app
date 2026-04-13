"""
Pydantic schemas for AML risk scoring configs
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Any, Union


class AMLRiskCondition(BaseModel):
    """Condition expression for AML risk rules"""
    field_slug: str
    operator: Literal["equals", "not_equals", "in", "not_in", "exists", "not_exists"]
    value: Union[Any, List[Any]]


class AMLRiskEffect(BaseModel):
    """Effect when rule condition matches"""
    add_score: int
    set_flag: Optional[str] = None
    require_action: Optional[str] = None
    stop: bool = False


class AMLRiskRule(BaseModel):
    """AML risk scoring rule"""
    rule_id: str
    description_en: str
    when: AMLRiskCondition
    effect: AMLRiskEffect
    weight: float = 1.0


class AMLRiskOutputTier(BaseModel):
    """Risk tier definition"""
    tier: Literal["low", "medium", "high"]
    min: int
    max: int


class AMLRiskOutputs(BaseModel):
    """Output configuration for AML risk scoring"""
    min_score: int = 0
    max_score: int = 100
    tiers: List[AMLRiskOutputTier]


class AMLRiskConfig(BaseModel):
    """Schema for AML risk config_json in jurisdiction_configs table"""
    jurisdiction: str
    purpose: Literal["AML_RISK"]
    version: int
    status: Literal["draft", "active", "archived"]
    rules: List[AMLRiskRule]
    outputs: AMLRiskOutputs


class ComputeRiskResponse(BaseModel):
    """Response from compute risk endpoint"""
    person_id: str
    jurisdiction: str
    config_id: str
    version: int
    score: int
    tier: str
    flags: List[str]
    required_actions: List[str]
    reasons: List[dict]
    audit_event_id: str


class LatestRiskResponse(BaseModel):
    """Response from latest risk endpoint"""
    person_id: str
    risk_score_current: Optional[float] = None
    risk_tier_current: Optional[str] = None
    aml_flags: List[str] = []
    aml_required_actions: List[str] = []
    last_computed_at: Optional[str] = None
    last_config_version: Optional[int] = None
