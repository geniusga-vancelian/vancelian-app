"""
Pydantic schemas for Bundles API
"""
from pydantic import BaseModel, Field, field_validator, model_validator, Discriminator
from typing import List, Optional, Literal, Dict, Any, Union, Annotated
from datetime import datetime, date
from decimal import Decimal


# Bundle Type Enum
BundleTypeEnum = Literal["fixed_instruments", "composite_fixed", "dynamic"]


class InstrumentComponentBase(BaseModel):
    """Instrument component - discriminated union variant for component_type='instrument'"""
    component_type: Literal["instrument"] = Field(..., description="Component type discriminator")
    instrument_code: str = Field(..., min_length=1, max_length=50, description="Instrument symbol (required for instrument component)")
    weight: Decimal = Field(..., ge=0, le=100, decimal_places=4, description="Weight percentage (0-100)")
    position_order: Optional[int] = Field(None, description="Optional ordering")
    
    model_config = {
        "extra": "forbid",  # Reject any extra fields including child_bundle_id
    }
    
    @field_validator('instrument_code')
    @classmethod
    def validate_instrument_code_not_null(cls, v: str) -> str:
        """Ensure instrument_code is not empty or null"""
        if not v or v.strip() == "":
            raise ValueError("instrument_code cannot be null or empty for instrument component")
        return v.strip()


class BundleComponentBase(BaseModel):
    """Bundle component - discriminated union variant for component_type='bundle'"""
    component_type: Literal["bundle"] = Field(..., description="Component type discriminator")
    child_bundle_id: int = Field(..., gt=0, description="Child bundle ID (required for bundle component, must be > 0)")
    weight: Decimal = Field(..., ge=0, le=100, decimal_places=4, description="Weight percentage (0-100)")
    position_order: Optional[int] = Field(None, description="Optional ordering")
    
    model_config = {
        "extra": "forbid",  # Reject any extra fields including instrument_code
    }
    
    @field_validator('child_bundle_id')
    @classmethod
    def validate_bundle_id_not_null(cls, v: int) -> int:
        """Ensure child_bundle_id is not null or zero"""
        if v is None or v <= 0:
            raise ValueError("child_bundle_id cannot be null or <= 0 for bundle component")
        return v


# Discriminated union: BundleComponentIn can be either InstrumentComponentBase or BundleComponentBase
# The discriminator is 'component_type' field
# Pydantic will automatically use component_type to determine which variant to use
BundleComponentIn = Annotated[
    Union[InstrumentComponentBase, BundleComponentBase],
    Discriminator('component_type')
]


class BundleComponentOut(BaseModel):
    """Component output with resolved IDs"""
    id: int
    component_type: str
    instrument_id: Optional[int] = None
    instrument_code: Optional[str] = None
    child_bundle_id: Optional[int] = None
    child_bundle_name: Optional[str] = None
    weight: Decimal
    position_order: Optional[int] = None


class BundleDynamicRuleIn(BaseModel):
    """Dynamic rule input"""
    rule_json: Dict[str, Any] = Field(..., description="DSL JSON rule")
    rule_type: Literal["formula_dsl"] = Field(default="formula_dsl", description="Rule type")

    @field_validator('rule_json')
    @classmethod
    def validate_rule_json(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        """Validate rule JSON structure"""
        if not isinstance(v, dict):
            raise ValueError("rule_json must be a JSON object")
        
        # Check for explicit normalization
        if v.get('type') != 'weights':
            raise ValueError("rule_json.type must be 'weights'")
        
        post_op = v.get('post', {})
        if post_op.get('op') != 'normalize_to_one':
            raise ValueError("rule_json.post.op must be 'normalize_to_one' (explicit normalization required)")
        
        items = v.get('items', [])
        if not items:
            raise ValueError("rule_json.items must be a non-empty array")
        
        return v


class BundleDynamicRuleOut(BaseModel):
    """Dynamic rule output"""
    id: int
    rule_type: str
    rule_json: Dict[str, Any]
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BundleBase(BaseModel):
    """Base bundle schema"""
    name: str = Field(..., min_length=1, max_length=200, description="Bundle name")
    asset_class: Literal["crypto", "etf", "equity", "commodities", "index", "forex"] = Field(..., description="Asset class")
    type: BundleTypeEnum = Field(default="fixed_instruments", description="Bundle type")
    description: Optional[str] = Field(None, max_length=1000, description="Optional description")
    is_active: bool = Field(default=True, description="Whether bundle is active")


class BundleCreate(BundleBase):
    """Request to create a bundle"""
    components: List[BundleComponentIn] = Field(..., min_length=1, description="List of components")
    dynamic_rule: Optional[BundleDynamicRuleIn] = Field(None, description="Dynamic rule (required if type='dynamic')")

    @field_validator('components')
    @classmethod
    def validate_weights_sum(cls, v: List[BundleComponentIn]) -> List[BundleComponentIn]:
        """Validate that weights sum to 100 (with tolerance 0.01)"""
        total = sum(float(item.weight) for item in v)
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Component weights must sum to 100.0 (current sum: {total:.4f}, tolerance: 0.01)")
        return v

    @field_validator('components')
    @classmethod
    def validate_weights_positive(cls, v: List[BundleComponentIn]) -> List[BundleComponentIn]:
        """Validate all weights are positive"""
        for idx, item in enumerate(v):
            if float(item.weight) <= 0:
                raise ValueError(f"Component at index {idx}: weight must be > 0 (got {item.weight})")
        return v

    @field_validator('dynamic_rule')
    @classmethod
    def validate_dynamic_rule_required(cls, v: Optional[BundleDynamicRuleIn], info) -> Optional[BundleDynamicRuleIn]:
        """Validate dynamic_rule is required if type='dynamic'"""
        bundle_type = info.data.get('type')
        if bundle_type == 'dynamic' and v is None:
            raise ValueError("dynamic_rule is required when bundle type is 'dynamic'")
        if bundle_type != 'dynamic' and v is not None:
            raise ValueError("dynamic_rule should only be provided when bundle type is 'dynamic'")
        return v
    
    @model_validator(mode='after')
    def validate_component_integrity(self):
        """
        Additional validation at BundleCreate level:
        - Ensure discriminated union integrity (Pydantic handles most of this via Discriminator, but we double-check)
        - Provide clear error messages with component index for each invalid component
        """
        # Import here to avoid issues with forward references (classes are defined above)
        # InstrumentComponentBase and BundleComponentBase are defined in this file
        for idx, comp in enumerate(self.components):
            # Check discriminated union integrity - Pydantic should have already validated via Discriminator, but we double-check
            if comp.component_type == 'instrument':
                # Verify it's actually an InstrumentComponentBase instance (discriminated union should guarantee this)
                if not isinstance(comp, InstrumentComponentBase):
                    raise ValueError(f"Component at index {idx}: invalid structure for instrument component (discriminated union mismatch)")
                # Verify required fields are present (should already be validated by Pydantic, but explicit check for clarity)
                # instrument_code is required by Field(..., min_length=1) so should be present, but check anyway
                if not hasattr(comp, 'instrument_code') or not comp.instrument_code or comp.instrument_code.strip() == "":
                    raise ValueError(f"Component at index {idx}: instrument_code is required and cannot be null/empty for instrument component")
                # Explicitly check that forbidden fields are NOT present (extra='forbid' should catch this, but double-check)
                if hasattr(comp, 'child_bundle_id') and comp.child_bundle_id is not None:
                    raise ValueError(f"Component at index {idx} (type=instrument): child_bundle_id must not be present")
            elif comp.component_type == 'bundle':
                # Verify it's actually a BundleComponentBase instance (discriminated union should guarantee this)
                if not isinstance(comp, BundleComponentBase):
                    raise ValueError(f"Component at index {idx}: invalid structure for bundle component (discriminated union mismatch)")
                # Verify required fields are present (child_bundle_id is required by Field(..., gt=0))
                if not hasattr(comp, 'child_bundle_id') or comp.child_bundle_id is None or comp.child_bundle_id <= 0:
                    raise ValueError(f"Component at index {idx}: child_bundle_id is required and must be > 0 for bundle component")
                # Explicitly check that forbidden fields are NOT present
                if hasattr(comp, 'instrument_code') and comp.instrument_code is not None:
                    raise ValueError(f"Component at index {idx} (type=bundle): instrument_code must not be present")
            else:
                raise ValueError(f"Component at index {idx}: invalid component_type '{comp.component_type}' (must be 'instrument' or 'bundle')")
        
        return self


class BundleUpdate(BaseModel):
    """Request to update a bundle"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None
    components: Optional[List[BundleComponentIn]] = Field(None, min_length=1)
    dynamic_rule: Optional[BundleDynamicRuleIn] = None

    @field_validator('components')
    @classmethod
    def validate_weights_sum(cls, v: Optional[List[BundleComponentIn]]) -> Optional[List[BundleComponentIn]]:
        """Validate that weights sum to 100 (with tolerance 0.01)"""
        if v is None:
            return v
        total = sum(float(item.weight) for item in v)
        if abs(total - 100.0) > 0.01:
            raise ValueError(f"Component weights must sum to 100.0 (current sum: {total:.4f}, tolerance: 0.01)")
        return v

    @field_validator('components')
    @classmethod
    def validate_weights_positive(cls, v: Optional[List[BundleComponentIn]]) -> Optional[List[BundleComponentIn]]:
        """Validate all weights are positive"""
        if v is None:
            return v
        for item in v:
            if float(item.weight) <= 0:
                raise ValueError(f"Component weight must be > 0 (got {item.weight})")
        return v


class BundleListItem(BaseModel):
    """Bundle list item (summary)"""
    id: int
    name: str
    asset_class: str
    type: str
    is_active: bool
    updated_at: datetime
    components_count: int = Field(..., description="Number of components in bundle")
    has_dynamic_rule: bool = Field(default=False, description="Whether bundle has an active dynamic rule")


class BundleDetail(BaseModel):
    """Bundle detail with components and rule"""
    id: int
    name: str
    asset_class: str
    type: str
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by_email: Optional[str] = None
    components: List[BundleComponentOut]
    dynamic_rule: Optional[BundleDynamicRuleOut] = None

    class Config:
        from_attributes = True


class BundlePreviewWeight(BaseModel):
    """Effective weight for an instrument in preview"""
    instrument_id: int
    instrument_code: str
    weight_pct: Decimal = Field(..., description="Weight as percentage (0-100)")


class BundlePreviewResponse(BaseModel):
    """Response for bundle preview endpoint"""
    bundle_id: int
    bundle_name: str
    bundle_type: str
    preview_date: date
    weights_effective: List[BundlePreviewWeight]
    warnings: List[str] = Field(default_factory=list, description="Warnings (e.g., missing data)")


# Legacy schemas for backward compatibility
class BundleAllocationItem(BaseModel):
    """Single allocation in a bundle (legacy)"""
    instrument_code: str = Field(..., min_length=1, max_length=20, description="Instrument symbol (e.g., BTCUSD)")
    weight: Decimal = Field(..., ge=0, le=100, description="Weight percentage (0-100)")


class BundleAllocationResponse(BaseModel):
    """Allocation response with instrument details (legacy)"""
    instrument_id: int
    instrument_code: str
    instrument_name: Optional[str] = None
    weight: Decimal
    position_order: Optional[int] = None
