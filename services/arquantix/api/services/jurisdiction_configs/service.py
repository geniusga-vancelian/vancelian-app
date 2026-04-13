"""
Jurisdiction configs service
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List, Set, Tuple
import uuid
from datetime import datetime

from database import JurisdictionConfig, FieldDefinition
from schemas_jurisdiction import JurisdictionConfigSchema
from schemas_aml_risk import AMLRiskConfig


def validate_jurisdiction_format(jurisdiction: str) -> Tuple[bool, Optional[str]]:
    """
    Optional validation helper for jurisdiction format.
    
    Returns:
        (is_valid, error_message)
        - is_valid: True if jurisdiction is non-empty string
        - error_message: None if valid, error description if invalid
    
    Note: This is non-blocking. Backend accepts any non-empty string.
    This helper is for logging/warning purposes only.
    """
    if not jurisdiction:
        return False, "Jurisdiction cannot be empty"
    if not isinstance(jurisdiction, str):
        return False, "Jurisdiction must be a string"
    if not jurisdiction.strip():
        return False, "Jurisdiction cannot be whitespace only"
    return True, None


def create_jurisdiction_config(
    db: Session,
    jurisdiction: str,
    purpose: str,
    config_json: Dict[str, Any],  # Accept dict (from API or validated schema)
) -> JurisdictionConfig:
    """
    Create a new jurisdiction config (draft).
    Uses SELECT FOR UPDATE to prevent race conditions when auto-incrementing version.
    """
    from sqlalchemy import func
    from sqlalchemy.exc import IntegrityError
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # Get next version for this jurisdiction+purpose with row-level lock
            # This prevents race conditions when multiple requests try to create configs simultaneously
            existing = db.query(JurisdictionConfig).filter(
                JurisdictionConfig.jurisdiction == jurisdiction,
                JurisdictionConfig.purpose == purpose,
            ).with_for_update().order_by(JurisdictionConfig.version.desc()).first()
            
            next_version = (existing.version + 1) if existing else 1
            
            config = JurisdictionConfig(
                id=uuid.uuid4(),
                jurisdiction=jurisdiction,
                purpose=purpose,
                version=next_version,
                status="draft",
                config_json=config_json if isinstance(config_json, dict) else config_json.model_dump(),
            )
            db.add(config)
            db.commit()
            db.refresh(config)
            return config
            
        except IntegrityError as e:
            # Race condition: another request created the same version
            db.rollback()
            if attempt < max_retries - 1:
                # Retry: re-read max version
                continue
            else:
                # Max retries reached, re-raise
                raise


def _collect_field_slugs_from_config(config_json: Dict[str, Any], purpose: str) -> Set[str]:
    """
    Collect all field slugs referenced in a config.
    Returns set of field slugs.
    """
    slugs = set()
    
    if purpose == "AML_RISK":
        # Parse as AML_RISK config
        try:
            aml_config = AMLRiskConfig(**config_json)
            for rule in aml_config.rules:
                slugs.add(rule.when.field_slug)
        except Exception:
            # If parsing fails, skip validation (will fail elsewhere)
            pass
    else:
        # Parse as onboarding config
        try:
            onboarding_config = JurisdictionConfigSchema(**config_json)
            for step in onboarding_config.steps:
                for block in step.blocks:
                    slugs.update(block.fields)
                    # Also check conditions
                    if block.conditions:
                        for condition in block.conditions:
                            slugs.add(condition.when.field_slug)
        except Exception:
            # If parsing fails, skip validation (will fail elsewhere)
            pass
    
    return slugs


def _validate_aml_risk_tiers(outputs: Dict[str, Any]) -> None:
    """
    Validate AML_RISK tier configuration:
    - Tiers must cover full range [min_score, max_score] without gaps
    - Tiers must not overlap
    """
    min_score = outputs.get("min_score", 0)
    max_score = outputs.get("max_score", 100)
    tiers = outputs.get("tiers", [])
    
    if not tiers:
        raise ValueError("AML_RISK config must have at least one tier")
    
    # Sort tiers by min
    sorted_tiers = sorted(tiers, key=lambda t: t["min"])
    
    # Check coverage starts at min_score
    if sorted_tiers[0]["min"] != min_score:
        raise ValueError(f"First tier must start at min_score ({min_score}), got {sorted_tiers[0]['min']}")
    
    # Check coverage ends at max_score
    if sorted_tiers[-1]["max"] != max_score:
        raise ValueError(f"Last tier must end at max_score ({max_score}), got {sorted_tiers[-1]['max']}")
    
    # Check no gaps and no overlaps
    for i in range(len(sorted_tiers)):
        tier = sorted_tiers[i]
        tier_min = tier["min"]
        tier_max = tier["max"]
        
        # Validate tier range
        if tier_min > tier_max:
            raise ValueError(f"Tier {tier.get('tier', i)} has min ({tier_min}) > max ({tier_max})")
        
        # Check overlap/gap with next tier
        if i < len(sorted_tiers) - 1:
            next_tier = sorted_tiers[i + 1]
            next_min = next_tier["min"]
            
            if tier_max >= next_min:
                raise ValueError(f"Tier {tier.get('tier', i)} overlaps with next tier: max ({tier_max}) >= next min ({next_min})")
            
            if tier_max + 1 != next_min:
                raise ValueError(f"Gap between tier {tier.get('tier', i)} and next tier: max ({tier_max}) + 1 != next min ({next_min})")


def delete_jurisdiction_config(
    db: Session,
    config_id: uuid.UUID,
) -> None:
    """
    Delete a jurisdiction config by ID.
    Raises ValueError if config not found.
    """
    config = db.query(JurisdictionConfig).filter(JurisdictionConfig.id == config_id).first()
    if not config:
        raise ValueError(f"Jurisdiction config with id {config_id} not found")
    
    db.delete(config)
    db.commit()


def publish_jurisdiction_config(
    db: Session,
    config_id: uuid.UUID,
) -> JurisdictionConfig:
    """
    Publish a config (set active) and archive previous active for same jurisdiction+purpose.
    Validates field slugs and AML_RISK tiers at publish time.
    """
    config = db.query(JurisdictionConfig).filter(JurisdictionConfig.id == config_id).first()
    if not config:
        raise ValueError(f"Config not found: {config_id}")
    
    if config.status != "draft":
        raise ValueError(f"Only draft configs can be published. Current status: {config.status}")
    
    # Publish-time validation: collect and validate field slugs
    field_slugs = _collect_field_slugs_from_config(config.config_json, config.purpose)
    
    if field_slugs:
        # Verify each slug exists and is active
        invalid_slugs = []
        for slug in field_slugs:
            field_def = db.query(FieldDefinition).filter(FieldDefinition.slug == slug).first()
            if not field_def:
                invalid_slugs.append(f"{slug} (not found)")
            elif not field_def.is_active:
                invalid_slugs.append(f"{slug} (inactive)")
        
        if invalid_slugs:
            raise ValueError(f"Invalid field slugs in config: {', '.join(invalid_slugs)}")
    
    # Publish-time validation: AML_RISK tier coverage
    if config.purpose == "AML_RISK":
        if "outputs" in config.config_json:
            _validate_aml_risk_tiers(config.config_json["outputs"])
    
    # Archive previous active configs
    previous_active = db.query(JurisdictionConfig).filter(
        JurisdictionConfig.jurisdiction == config.jurisdiction,
        JurisdictionConfig.purpose == config.purpose,
        JurisdictionConfig.status == "active",
    ).all()
    
    for prev in previous_active:
        prev.status = "archived"
    
    # Set this config as active
    config.status = "active"
    config.config_json["status"] = "active"
    
    db.commit()
    db.refresh(config)
    return config


def get_active_config(
    db: Session,
    jurisdiction: str,
    purpose: str,
) -> Optional[JurisdictionConfig]:
    """
    Get active config for jurisdiction+purpose.
    """
    return db.query(JurisdictionConfig).filter(
        JurisdictionConfig.jurisdiction == jurisdiction,
        JurisdictionConfig.purpose == purpose,
        JurisdictionConfig.status == "active",
    ).first()


def get_config_by_id(
    db: Session,
    config_id: uuid.UUID,
) -> Optional[JurisdictionConfig]:
    """
    Get config by ID.
    """
    return db.query(JurisdictionConfig).filter(JurisdictionConfig.id == config_id).first()
