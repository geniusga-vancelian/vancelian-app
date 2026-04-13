"""
Pydantic schemas for AI Jurisdiction Configs Builder
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal


class ComposeJurisdictionConfigRequest(BaseModel):
    """Request to compose jurisdiction config from prompt"""
    jurisdiction: str = Field(..., min_length=1)
    purpose: Literal["KYC", "AML_RISK"] = Field(...)
    prompt: str = Field(..., min_length=1, max_length=2000)
    previous_spec: Optional[Dict[str, Any]] = None
    messages: Optional[List[Dict[str, str]]] = None  # Chat history for context


class ComposeJurisdictionConfigResponse(BaseModel):
    """Response from compose endpoint"""
    spec: Optional[Dict[str, Any]] = None  # KYC or AML_RISK config JSON (null if questions exist)
    assistant_text: str
    warnings: Optional[List[str]] = None
    questions: Optional[List[Dict[str, Any]]] = None  # Blocking: [{term: str, suggestions: [slug, ...]}] for missing field slugs
    value_suggestions: Optional[List[Dict[str, Any]]] = None  # Non-blocking: [{field_slug: str, suggested_values: [...]}] for enum/value choices


class ValidateJurisdictionConfigRequest(BaseModel):
    """Request to validate jurisdiction config"""
    jurisdiction: str = Field(..., min_length=1)
    purpose: Literal["KYC", "AML_RISK"] = Field(...)
    spec: Dict[str, Any]


class ValidateJurisdictionConfigResponse(BaseModel):
    """Response from validate endpoint"""
    ok: bool
    errors: List[str]
    normalized_spec: Optional[Dict[str, Any]] = None  # If validation fixes were applied
