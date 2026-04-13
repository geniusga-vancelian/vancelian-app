"""
Pydantic models for Bot IA épargne / InvestorProfile.
Strict adherence to AUDIT_ET_ARCHITECTURE_BOT_EPARGNE_WEALTHTECH.md §7.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# --- Enums (spec §7.1) ---

class GoalType(str, Enum):
    apport = "apport"
    retraite = "retraite"
    revenus = "revenus"
    patrimoine = "patrimoine"
    precaution = "precaution"
    autre = "autre"

class ProjectType(str, Enum):
    buy_something = "buy_something"
    live_better = "live_better"
    prepare_future = "prepare_future"
    protect_family = "protect_family"
    experiences = "experiences"
    grow_money = "grow_money"
    other = "other"


class HorizonBucket(str, Enum):
    short = "short"
    medium = "medium"
    long = "long"


class LiquidityNeeds(str, Enum):
    none = "none"
    low = "low"
    medium = "medium"
    high = "high"
    immediate = "immediate"


class IncomeBucket(str, Enum):
    under_2k = "<2k"
    between_2_4k = "2-4k"
    between_4_6k = "4-6k"
    over_6k = ">6k"


class KnowledgeLevel(str, Enum):
    none = "none"
    basic = "basic"
    intermediate = "intermediate"
    advanced = "advanced"


class LossCapacity(str, Enum):
    none = "none"
    partial = "partial"
    total = "total"


# --- Sub-models ---

class Goal(BaseModel):
    type: Optional[GoalType] = None
    priority: Optional[int] = Field(None, ge=1, le=3)
    target_amount: Optional[float] = Field(None, ge=0)
    target_date: Optional[str] = None  # ISO date
    narrative: Optional[str] = None


class RegulatoryFlags(BaseModel):
    pep: Optional[bool] = None
    sanctions: Optional[bool] = None
    jurisdiction: Optional[str] = None


# ConfidenceMap: additionalProperties 0-1
ConfidenceMap = dict[str, float]


def horizon_from_bucket(b: HorizonBucket) -> tuple[int, int]:
    if b == HorizonBucket.short:
        return (1, 36)
    if b == HorizonBucket.medium:
        return (37, 84)
    return (85, 600)


# --- InvestorProfile ---

class InvestorProfile(BaseModel):
    project_type: Optional[ProjectType] = None
    project_type_confidence: Optional[float] = Field(None, ge=0, le=1)
    project_type_source: Optional[str] = None
    goal_confidence: Optional[float] = Field(None, ge=0, le=1)
    goal_attempts: int = Field(0, ge=0)
    goal_locked: bool = False
    goal_phase: Optional[str] = None
    goal: Optional[Goal] = None
    horizon_months: Optional[int] = Field(None, ge=1, le=600)
    horizon_bucket: Optional[HorizonBucket] = None
    liquidity_needs: Optional[LiquidityNeeds] = None
    income_monthly: Optional[float] = Field(None, ge=0)
    income_bucket: Optional[IncomeBucket] = None
    expenses_monthly: Optional[float] = Field(None, ge=0)
    emergency_fund: Optional[bool] = None
    initial_amount: Optional[float] = Field(None, ge=0)
    monthly_contribution: Optional[float] = Field(None, ge=0)
    knowledge_level: Optional[KnowledgeLevel] = None
    experience_assets: Optional[list[str]] = None
    risk_tolerance_score: Optional[int] = Field(None, ge=1, le=10)
    max_drawdown_accept: Optional[float] = None  # e.g. -15 means -15%
    loss_capacity: Optional[LossCapacity] = None
    constraints: Optional[list[str]] = None
    preferences: Optional[list[str]] = None
    regulatory_flags: Optional[RegulatoryFlags] = None
    completeness_score: float = Field(0.0, ge=0, le=1)
    missing_fields: list[str] = Field(default_factory=list)
    confidence: Optional[ConfidenceMap] = None
    asked_questions: Optional[list[str]] = Field(default_factory=list, alias="asked_questions")

    model_config = {"populate_by_name": True, "extra": "ignore"}

    @field_validator("risk_tolerance_score")
    @classmethod
    def risk_in_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 1 or v > 10):
            raise ValueError("risk_tolerance_score must be between 1 and 10")
        return v

    @model_validator(mode="after")
    def consistency_horizon_bucket(self) -> "InvestorProfile":
        if self.horizon_months is not None and self.horizon_bucket is not None:
            lo, hi = horizon_from_bucket(self.horizon_bucket)
            if not (lo <= self.horizon_months <= hi):
                raise ValueError(
                    f"horizon_months ({self.horizon_months}) inconsistent with "
                    f"horizon_bucket {self.horizon_bucket.value} (expected {lo}-{hi})"
                )
        return self

    @model_validator(mode="after")
    def consistency_risk_drawdown(self) -> "InvestorProfile":
        """risk_tolerance_score and max_drawdown_accept coherence (spec §7.3)."""
        rt = self.risk_tolerance_score
        mdd = self.max_drawdown_accept
        if rt is not None and mdd is not None:
            # score 1-3 -> drawdown should be >= -10% (e.g. -5, 0)
            if rt <= 3 and mdd < -10:
                raise ValueError(
                    f"risk_tolerance_score {rt} (low) inconsistent with "
                    f"max_drawdown_accept {mdd}% (expected >= -10)"
                )
            # score 8-10 -> drawdown typically <= -15
            if rt >= 8 and mdd > -5 and mdd != 0:
                pass  # soft: high risk can still say -5; we don't force
        return self

    def consistency_errors(self) -> list[str]:
        """Return list of coherence errors without raising."""
        err: list[str] = []
        if self.horizon_months is not None and self.horizon_bucket is not None:
            lo, hi = horizon_from_bucket(self.horizon_bucket)
            if not (lo <= self.horizon_months <= hi):
                err.append("horizon_months vs horizon_bucket")
        rt, mdd = self.risk_tolerance_score, self.max_drawdown_accept
        if rt is not None and mdd is not None and rt <= 3 and mdd < -10:
            err.append("risk_tolerance_score vs max_drawdown_accept")
        return err


def investor_profile_to_dict(p: InvestorProfile) -> dict[str, Any]:
    return p.model_dump(by_alias=True, exclude_none=True)


def dict_to_investor_profile(d: dict[str, Any]) -> InvestorProfile:
    return InvestorProfile.model_validate(d)
