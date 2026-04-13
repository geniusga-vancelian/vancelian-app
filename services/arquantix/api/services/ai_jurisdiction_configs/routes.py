"""
FastAPI routes for AI Jurisdiction Configs Builder
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List
import sys
import logging
import uuid
from pathlib import Path

# Add api directory to path for auth import
api_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(api_dir))
from auth import get_current_user, AdminUser
from database import get_db
from .schemas import (
    ComposeJurisdictionConfigRequest,
    ComposeJurisdictionConfigResponse,
    ValidateJurisdictionConfigRequest,
    ValidateJurisdictionConfigResponse,
)
from .agent import compose_jurisdiction_config_spec, normalize_spec
from services.jurisdiction_configs.service import (
    _collect_field_slugs_from_config,
    _validate_aml_risk_tiers,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ai/jurisdiction-configs", tags=["ai-jurisdiction-configs"])


@router.post("/compose", response_model=ComposeJurisdictionConfigResponse)
async def compose_jurisdiction_config(
    request: ComposeJurisdictionConfigRequest,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Compose jurisdiction config from prompt using OpenAI.
    Returns spec JSON and assistant text.
    If unknown field slugs are found, returns questions instead of spec.
    """
    trace_id = str(uuid.uuid4())
    try:
        # Validate prompt length
        if len(request.prompt) > 2000:
            raise HTTPException(status_code=400, detail="Prompt too long (max 2000 chars)")
        
        # Call agent
        assistant_text, spec, warnings, questions, value_suggestions = compose_jurisdiction_config_spec(
            db=db,
            jurisdiction=request.jurisdiction,
            purpose=request.purpose,
            prompt=request.prompt,
            previous_spec=request.previous_spec,
            messages=request.messages,
        )
        
        # If questions exist (unknown slugs), spec should be None
        if questions:
            return ComposeJurisdictionConfigResponse(
                spec=None,
                assistant_text=assistant_text,
                warnings=warnings if warnings else None,
                questions=questions,
                value_suggestions=value_suggestions if value_suggestions else None,
            )
        
        # Ensure spec has required fields
        if spec:
            if "jurisdiction" not in spec:
                spec["jurisdiction"] = request.jurisdiction
            if "purpose" not in spec:
                spec["purpose"] = request.purpose
            if "version" not in spec:
                spec["version"] = 1
            if request.purpose == "KYC" and "steps" not in spec:
                spec["steps"] = []
        
        return ComposeJurisdictionConfigResponse(
            spec=spec,
            assistant_text=assistant_text,
            warnings=warnings if warnings else None,
            questions=questions if questions else None,
            value_suggestions=value_suggestions if value_suggestions else None,
        )
        
    except ValueError as e:
        # ValueError from agent indicates OpenAI response parsing/generation failure
        logger.warning(f"OpenAI generation/parsing failed (trace_id={trace_id}): {str(e)}")
        raise HTTPException(
            status_code=502,
            detail={
                "error": "openai_generation_failed",
                "detail": str(e),
                "trace_id": trace_id,
                "message": "OpenAI returned invalid or incomplete response. Please try again."
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Compose failed (trace_id={trace_id})")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "compose_failed",
                "detail": str(e),
                "trace_id": trace_id
            }
        )


@router.post("/validate", response_model=ValidateJurisdictionConfigResponse)
async def validate_jurisdiction_config(
    request: ValidateJurisdictionConfigRequest,
    current_user: AdminUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Validate jurisdiction config spec using the SAME strict schema validation as create/publish.
    Normalizes the spec before validation and returns the normalized version.
    """
    errors: List[str] = []
    normalized_spec = None
    
    try:
        # Normalize spec first (for KYC only)
        spec_to_validate = request.spec.copy()
        if request.purpose == "KYC":
            spec_to_validate = normalize_spec(spec_to_validate, request.purpose)
        
        # Use the SAME validation as create_config endpoint
        if request.purpose == "KYC":
            # Pre-validate structure (step.conditions, cross-step references)
            from services.jurisdiction_configs.validators import validate_kyc_config_structure
            is_valid, structure_errors = validate_kyc_config_structure(spec_to_validate)
            if not is_valid:
                errors.extend(structure_errors)
            
            from schemas_jurisdiction import JurisdictionConfigSchema
            try:
                # Convert normalized spec back to Pydantic format for validation
                # Pydantic expects field_slug/operator/target, but normalized has field/op/block_id|field
                validation_spec = spec_to_validate.copy()
                
                # Convert conditions back to Pydantic format
                for step in validation_spec.get("steps", []):
                    for block in step.get("blocks", []):
                        for cond in block.get("conditions", []):
                            when = cond.get("when", {})
                            if "field" in when:
                                when["field_slug"] = when.pop("field")
                            if "op" in when:
                                when["operator"] = when.pop("op")
                            
                            for then_item in cond.get("then", []):
                                if "block_id" in then_item:
                                    then_item["target"] = then_item.pop("block_id")
                                elif "field" in then_item and "action" in then_item:
                                    action = then_item["action"]
                                    if action in ["require_field", "optional_field"]:
                                        then_item["target"] = then_item.pop("field")
                
                # Validate using Pydantic schema (same as create endpoint)
                validated = JurisdictionConfigSchema(**validation_spec)
                # Return normalized spec (not Pydantic dump) for consistency
                normalized_spec = spec_to_validate
            except ValidationError as e:
                for err in e.errors():
                    errors.append(f"{'.'.join(str(loc) for loc in err['loc'])}: {err['msg']}")
            except Exception as e:
                errors.append(f"Invalid KYC config_json schema: {str(e)}")
        elif request.purpose == "AML_RISK":
            from schemas_aml_risk import AMLRiskConfig
            try:
                # Validate using Pydantic schema (same as create endpoint)
                validated = AMLRiskConfig(**spec_to_validate)
                normalized_spec = validated.model_dump()
            except Exception as e:
                errors.append(f"Invalid AML_RISK config_json schema: {str(e)}")
        else:
            errors.append(f"Unknown purpose: {request.purpose}")
        
        # If schema validation passed, check field slugs exist and are active
        if not errors and normalized_spec:
            # For validation, use the Pydantic format to extract slugs
            validation_spec_for_slugs = normalized_spec.copy()
            if request.purpose == "KYC":
                # Convert back to Pydantic format for slug extraction
                for step in validation_spec_for_slugs.get("steps", []):
                    for block in step.get("blocks", []):
                        for cond in block.get("conditions", []):
                            when = cond.get("when", {})
                            if "field" in when:
                                when["field_slug"] = when.pop("field")
                            if "op" in when:
                                when["operator"] = when.pop("op")
            
            field_slugs = _collect_field_slugs_from_config(validation_spec_for_slugs, request.purpose)
            
            if field_slugs:
                from database import FieldDefinition
                invalid_slugs = []
                for slug in field_slugs:
                    field_def = db.query(FieldDefinition).filter(FieldDefinition.slug == slug).first()
                    if not field_def:
                        invalid_slugs.append(f"{slug} (not found)")
                    elif not field_def.is_active:
                        invalid_slugs.append(f"{slug} (inactive)")
                
                if invalid_slugs:
                    errors.append(f"Invalid field slugs: {', '.join(invalid_slugs)}")
            
            # Validate AML_RISK tier coverage
            if request.purpose == "AML_RISK" and "outputs" in normalized_spec:
                try:
                    _validate_aml_risk_tiers(normalized_spec["outputs"])
                except ValueError as e:
                    errors.append(f"AML tier validation failed: {str(e)}")
        
        return ValidateJurisdictionConfigResponse(
            ok=len(errors) == 0,
            errors=errors,
            normalized_spec=normalized_spec,
        )
        
    except Exception as e:
        return ValidateJurisdictionConfigResponse(
            ok=False,
            errors=[f"Validation error: {str(e)}"],
            normalized_spec=None,
        )
