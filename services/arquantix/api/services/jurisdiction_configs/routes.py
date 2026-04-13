"""
FastAPI routes for jurisdiction configs
"""
from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, Dict, Any
import uuid
import logging
import copy
from datetime import datetime
from pydantic import ValidationError

from database import get_db, JurisdictionConfig
from services.jurisdiction_configs import (
    create_jurisdiction_config,
    publish_jurisdiction_config,
    get_active_config,
    get_config_by_id,
    delete_jurisdiction_config,
    validate_jurisdiction_format,
)
from schemas_jurisdiction import (
    JurisdictionConfigCreate,
    JurisdictionConfigResponse,
    JurisdictionConfigSchema,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jurisdiction-configs", tags=["jurisdiction-configs"])


def _config_to_dict(config: JurisdictionConfig) -> Dict[str, Any]:
    """
    Convert SQLAlchemy JurisdictionConfig to JSON-serializable dict.
    Handles UUID -> str, datetime -> ISO string conversions.
    """
    return {
        "id": str(config.id),
        "jurisdiction": config.jurisdiction,
        "purpose": config.purpose,
        "version": config.version,
        "status": config.status,
        "config_json": config.config_json if isinstance(config.config_json, dict) else dict(config.config_json),
        "created_at": config.created_at.isoformat() if config.created_at else "",
        "updated_at": config.updated_at.isoformat() if config.updated_at else "",
    }


@router.post("", response_model=JurisdictionConfigResponse, status_code=status.HTTP_201_CREATED)
def create_config(
    request: JurisdictionConfigCreate,
    db: Session = Depends(get_db),
    # current_user: AdminUser = Depends(get_current_user),  # TODO: wire auth
):
    """
    Create a new jurisdiction config (draft).
    Accepts: { jurisdiction: str, purpose: str, config_json: dict }
    Version is auto-incremented server-side.
    Status defaults to "draft".
    """
    trace_id = str(uuid.uuid4())
    
    # Log incoming request for debugging
    logger.info(f"Creating jurisdiction config (trace_id={trace_id}): jurisdiction={request.jurisdiction}, purpose={request.purpose}")
    logger.debug(f"Request config_json type: {type(request.config_json)}, keys: {list(request.config_json.keys()) if isinstance(request.config_json, dict) else 'N/A'}")
    
    try:
        # Optional validation: log warning if jurisdiction format is unexpected (non-blocking)
        is_valid, error_msg = validate_jurisdiction_format(request.jurisdiction)
        if not is_valid:
            # Log warning but don't block (backward compatibility)
            logger.warning(f"Jurisdiction format validation warning: {error_msg} (jurisdiction: {request.jurisdiction})")
        
        # Validate config_json structure based on purpose
        if request.purpose == "KYC":
            # Pre-validate structure (step.conditions, cross-step references)
            from services.jurisdiction_configs.validators import validate_kyc_config_structure
            try:
                is_valid, structure_errors = validate_kyc_config_structure(request.config_json)
                if not is_valid:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail={
                            "error": "invalid_config_json",
                            "details": [{"field": "structure", "message": err} for err in structure_errors],
                            "message": f"Invalid KYC config_json structure: {', '.join(structure_errors)}"
                        }
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.exception(f"Error in structure validation (trace_id={trace_id})")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={
                        "error": "structure_validation_failed",
                        "trace_id": trace_id,
                        "detail": str(e)
                    }
                )
            
            # Normalize config_json format before validation (convert field -> field_slug, op -> operator)
            # Use deep copy to avoid mutating original
            try:
                normalized_config = copy.deepcopy(request.config_json)
            except Exception as e:
                logger.exception(f"Error deep copying config_json (trace_id={trace_id})")
                normalized_config = request.config_json
            try:
                for step in normalized_config.get("steps", []):
                    for block in step.get("blocks", []):
                        for cond in block.get("conditions", []):
                            if not isinstance(cond, dict) or "when" not in cond:
                                continue
                            when = cond.get("when", {})
                            if not isinstance(when, dict):
                                continue
                            # Convert field -> field_slug if needed
                            if "field" in when and "field_slug" not in when:
                                when["field_slug"] = when.pop("field")
                            # Convert op -> operator if needed
                            if "op" in when and "operator" not in when:
                                when["operator"] = when.pop("op")
                            
                            # Convert then actions
                            then_list = cond.get("then", [])
                            if isinstance(then_list, list):
                                for then_item in then_list:
                                    if not isinstance(then_item, dict):
                                        continue
                                    if "block_id" in then_item and "target" not in then_item:
                                        then_item["target"] = then_item.pop("block_id")
                                    elif "field" in then_item and "target" not in then_item:
                                        then_item["target"] = then_item.pop("field")
            except Exception as normalize_error:
                logger.exception(f"Error normalizing config_json format (trace_id={trace_id})")
                # Continue with original config_json if normalization fails
                normalized_config = request.config_json
            
            # Validate as JurisdictionConfigSchema
            try:
                validated = JurisdictionConfigSchema(**normalized_config)
                config_json_dict = validated.model_dump()
            except ValidationError as e:
                # Return 400 with clear error details
                error_details = []
                for err in e.errors():
                    error_details.append({
                        "field": ".".join(str(loc) for loc in err["loc"]),
                        "message": err["msg"],
                        "type": err["type"]
                    })
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "invalid_config_json",
                        "details": error_details,
                        "message": f"Invalid KYC config_json schema: {str(e)}"
                    }
                )
            except Exception as e:
                # Catch any other validation errors
                logger.exception("Unexpected error validating KYC config_json")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "invalid_config_json",
                        "details": [{"message": str(e)}],
                        "message": f"Invalid KYC config_json: {str(e)}"
                    }
                )
        elif request.purpose == "AML_RISK":
            # Validate as AMLRiskConfig (import needed)
            from schemas_aml_risk import AMLRiskConfig
            try:
                validated = AMLRiskConfig(**request.config_json)
                config_json_dict = validated.model_dump()
            except ValidationError as e:
                # Return 400 with clear error details
                error_details = []
                for err in e.errors():
                    error_details.append({
                        "field": ".".join(str(loc) for loc in err["loc"]),
                        "message": err["msg"],
                        "type": err["type"]
                    })
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "invalid_config_json",
                        "details": error_details,
                        "message": f"Invalid AML_RISK config_json schema: {str(e)}"
                    }
                )
            except Exception as e:
                # Catch any other validation errors
                logger.exception("Unexpected error validating AML_RISK config_json")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "invalid_config_json",
                        "details": [{"message": str(e)}],
                        "message": f"Invalid AML_RISK config_json: {str(e)}"
                    }
                )
        else:
            config_json_dict = request.config_json
        
        # Create config (version auto-incremented, status defaults to "draft")
        try:
            config = create_jurisdiction_config(
                db=db,
                jurisdiction=request.jurisdiction,
                purpose=request.purpose,
                config_json=config_json_dict,
            )
            # Convert to dict for JSON serialization
            return _config_to_dict(config)
        except Exception as create_error:
            db.rollback()
            logger.exception(f"Error in create_jurisdiction_config (trace_id={trace_id})")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "create_config_failed",
                    "trace_id": trace_id,
                    "detail": str(create_error),
                    "error_type": type(create_error).__name__
                }
            )
        
    except HTTPException:
        raise
    except IntegrityError as e:
        # Database integrity errors (unique constraint violations, etc.)
        db.rollback()
        logger.warning(f"IntegrityError creating jurisdiction config (trace_id={trace_id}): {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "db_integrity_error",
                "detail": str(e.orig) if hasattr(e, 'orig') else str(e),
                "trace_id": trace_id
            }
        )
    except Exception as e:
        # Log true server errors with full stack trace
        db.rollback()
        logger.exception(f"Unexpected error creating jurisdiction config (trace_id={trace_id}): {type(e).__name__}: {str(e)}")
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Full traceback (trace_id={trace_id}):\n{error_traceback}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "create_failed",
                "trace_id": trace_id,
                "detail": str(e),
                "error_type": type(e).__name__
            }
        )


@router.post("/{config_id}/publish", response_model=JurisdictionConfigResponse)
def publish_config(
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
    # current_user: AdminUser = Depends(get_current_user),  # TODO: wire auth
):
    """
    Publish a config (set active) and archive previous active.
    """
    try:
        config = publish_jurisdiction_config(db=db, config_id=config_id)
        return _config_to_dict(config)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error publishing jurisdiction config")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/active", response_model=JurisdictionConfigResponse)
def get_active(
    jurisdiction: str = Query(...),
    purpose: str = Query(...),
    db: Session = Depends(get_db),
):
    """
    Get active config for jurisdiction+purpose.
    """
    config = get_active_config(db=db, jurisdiction=jurisdiction, purpose=purpose)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": "not_found",
                "message": f"No active config found for jurisdiction={jurisdiction}, purpose={purpose}"
            }
        )
    return _config_to_dict(config)


@router.get("", response_model=list[JurisdictionConfigResponse])
def list_configs(
    jurisdiction: Optional[str] = Query(None),
    purpose: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    List all configs with optional filters.
    """
    query = db.query(JurisdictionConfig)
    if jurisdiction:
        query = query.filter(JurisdictionConfig.jurisdiction == jurisdiction)
    if purpose:
        query = query.filter(JurisdictionConfig.purpose == purpose)
    if status:
        query = query.filter(JurisdictionConfig.status == status)
    
    configs = query.order_by(
        JurisdictionConfig.jurisdiction,
        JurisdictionConfig.purpose,
        JurisdictionConfig.version.desc()
    ).all()
    
    # Convert to response format
    result = []
    for config in configs:
        result.append({
            "id": config.id,
            "jurisdiction": config.jurisdiction,
            "purpose": config.purpose,
            "version": config.version,
            "status": config.status,
            "config_json": config.config_json,
            "created_at": config.created_at.isoformat() if config.created_at else "",
            "updated_at": config.updated_at.isoformat() if config.updated_at else "",
        })
    return result


@router.get("/{config_id}", response_model=JurisdictionConfigResponse)
def get_config(
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """
    Get config by ID.
    """
    try:
        config = get_config_by_id(db=db, config_id=config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": "not_found",
                    "message": f"Jurisdiction config with id {config_id} not found"
                }
            )
        # Convert to dict for JSON serialization
        return _config_to_dict(config)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error fetching jurisdiction config {config_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "fetch_failed",
                "detail": str(e),
                "error_type": type(e).__name__
            }
        )


@router.delete("/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_config(
    config_id: uuid.UUID,
    db: Session = Depends(get_db),
    # current_user: AdminUser = Depends(get_current_user),  # TODO: wire auth
):
    """
    Delete a jurisdiction config by ID.
    """
    try:
        delete_jurisdiction_config(db=db, config_id=config_id)
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.exception(f"Error deleting jurisdiction config {config_id}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "delete_failed",
                "detail": str(e)
            }
        )


@router.put("/{config_id}", response_model=JurisdictionConfigResponse)
def update_config(
    config_id: uuid.UUID,
    request: JurisdictionConfigCreate,
    db: Session = Depends(get_db),
):
    """
    Update a draft config.
    """
    config = get_config_by_id(db=db, config_id=config_id)
    if not config:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Config not found")
    
    if config.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft configs can be updated"
        )
    
    try:
        # Validate config_json structure based on purpose
        if request.purpose == "KYC":
            try:
                validated = JurisdictionConfigSchema(**request.config_json)
                config_json_dict = validated.model_dump()
            except ValidationError as e:
                # Return 400 with clear error details
                error_details = []
                for err in e.errors():
                    error_details.append({
                        "field": ".".join(str(loc) for loc in err["loc"]),
                        "message": err["msg"],
                        "type": err["type"]
                    })
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "invalid_config_json",
                        "details": error_details,
                        "message": f"Invalid KYC config_json schema: {str(e)}"
                    }
                )
            except Exception as e:
                logger.exception("Unexpected error validating KYC config_json")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "invalid_config_json",
                        "details": [{"message": str(e)}],
                        "message": f"Invalid KYC config_json: {str(e)}"
                    }
                )
        elif request.purpose == "AML_RISK":
            from schemas_aml_risk import AMLRiskConfig
            try:
                validated = AMLRiskConfig(**request.config_json)
                config_json_dict = validated.model_dump()
            except ValidationError as e:
                # Return 400 with clear error details
                error_details = []
                for err in e.errors():
                    error_details.append({
                        "field": ".".join(str(loc) for loc in err["loc"]),
                        "message": err["msg"],
                        "type": err["type"]
                    })
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "invalid_config_json",
                        "details": error_details,
                        "message": f"Invalid AML_RISK config_json schema: {str(e)}"
                    }
                )
            except Exception as e:
                logger.exception("Unexpected error validating AML_RISK config_json")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "error": "invalid_config_json",
                        "details": [{"message": str(e)}],
                        "message": f"Invalid AML_RISK config_json: {str(e)}"
                    }
                )
        else:
            config_json_dict = request.config_json
        
        config.jurisdiction = request.jurisdiction
        config.purpose = request.purpose
        config.config_json = config_json_dict
        db.commit()
        db.refresh(config)
        return _config_to_dict(config)
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("Unexpected error updating jurisdiction config")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "server_error",
                "message": str(e)
            }
        )
