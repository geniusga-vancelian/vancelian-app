"""
Jurisdiction configs service
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime

from database import JurisdictionConfig
from schemas_jurisdiction import JurisdictionConfigSchema


def create_jurisdiction_config(
    db: Session,
    jurisdiction: str,
    purpose: str,
    config_json: JurisdictionConfigSchema,
) -> JurisdictionConfig:
    """
    Create a new jurisdiction config (draft).
    """
    # Get next version for this jurisdiction+purpose
    existing = db.query(JurisdictionConfig).filter(
        JurisdictionConfig.jurisdiction == jurisdiction,
        JurisdictionConfig.purpose == purpose,
    ).order_by(JurisdictionConfig.version.desc()).first()
    
    next_version = (existing.version + 1) if existing else 1
    
    config = JurisdictionConfig(
        id=uuid.uuid4(),
        jurisdiction=jurisdiction,
        purpose=purpose,
        version=next_version,
        status="draft",
        config_json=config_json.model_dump(),
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def publish_jurisdiction_config(
    db: Session,
    config_id: uuid.UUID,
) -> JurisdictionConfig:
    """
    Publish a config (set active) and archive previous active for same jurisdiction+purpose.
    """
    config = db.query(JurisdictionConfig).filter(JurisdictionConfig.id == config_id).first()
    if not config:
        raise ValueError(f"Config not found: {config_id}")
    
    if config.status != "draft":
        raise ValueError(f"Only draft configs can be published. Current status: {config.status}")
    
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
