"""
Tests for jurisdiction configs CRUD operations
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from database import JurisdictionConfig
from services.jurisdiction_configs import (
    create_jurisdiction_config,
    get_config_by_id,
    delete_jurisdiction_config,
)


@pytest.fixture
def sample_kyc_config_json():
    """Sample KYC config JSON for testing"""
    return {
        "jurisdiction": "TEST_JURISDICTION",
        "purpose": "KYC",
        "version": 1,
        "status": "draft",
        "steps": [
            {
                "step_id": "step1",
                "title_en": "Test Step",
                "blocks": [
                    {
                        "block_id": "block1",
                        "fields": ["first-name", "last-name"],
                        "layout": "single_column",
                        "required": True,
                        "conditions": []
                    }
                ]
            }
        ],
        "entry_rules": None
    }


def test_create_jurisdiction_config_returns_id(db: Session, sample_kyc_config_json):
    """Test that create_jurisdiction_config returns a config with an ID"""
    config = create_jurisdiction_config(
        db=db,
        jurisdiction="TEST_JURISDICTION",
        purpose="KYC",
        config_json=sample_kyc_config_json,
    )
    
    assert config is not None
    assert config.id is not None
    assert isinstance(config.id, uuid.UUID)
    assert config.jurisdiction == "TEST_JURISDICTION"
    assert config.purpose == "KYC"
    assert config.version == 1
    assert config.status == "draft"
    assert config.config_json == sample_kyc_config_json


def test_get_jurisdiction_config_by_id_returns_json_serializable(db: Session, sample_kyc_config_json):
    """Test that get_config_by_id returns a config that can be serialized to JSON"""
    # Create a config
    created = create_jurisdiction_config(
        db=db,
        jurisdiction="TEST_JURISDICTION",
        purpose="KYC",
        config_json=sample_kyc_config_json,
    )
    
    # Get it back
    config = get_config_by_id(db=db, config_id=created.id)
    
    assert config is not None
    assert config.id == created.id
    
    # Verify it can be converted to dict (simulating FastAPI response)
    config_dict = {
        "id": str(config.id),
        "jurisdiction": config.jurisdiction,
        "purpose": config.purpose,
        "version": config.version,
        "status": config.status,
        "config_json": config.config_json if isinstance(config.config_json, dict) else dict(config.config_json),
        "created_at": config.created_at.isoformat() if config.created_at else "",
        "updated_at": config.updated_at.isoformat() if config.updated_at else "",
    }
    
    # Verify all fields are JSON-serializable
    import json
    json_str = json.dumps(config_dict)
    assert json_str is not None
    
    # Verify UUID is string
    assert isinstance(config_dict["id"], str)
    
    # Verify datetimes are strings
    assert isinstance(config_dict["created_at"], str)
    assert isinstance(config_dict["updated_at"], str)
    
    # Verify config_json is dict
    assert isinstance(config_dict["config_json"], dict)


def test_get_unknown_id_returns_none(db: Session):
    """Test that get_config_by_id returns None for unknown ID"""
    unknown_id = uuid.uuid4()
    config = get_config_by_id(db=db, config_id=unknown_id)
    assert config is None


def test_delete_jurisdiction_config_removes_from_db(db: Session, sample_kyc_config_json):
    """Test that delete_jurisdiction_config removes the config from the database"""
    # Create a config
    created = create_jurisdiction_config(
        db=db,
        jurisdiction="TEST_JURISDICTION",
        purpose="KYC",
        config_json=sample_kyc_config_json,
    )
    
    config_id = created.id
    
    # Verify it exists
    config = get_config_by_id(db=db, config_id=config_id)
    assert config is not None
    
    # Delete it
    delete_jurisdiction_config(db=db, config_id=config_id)
    
    # Verify it's gone
    config = get_config_by_id(db=db, config_id=config_id)
    assert config is None


def test_delete_unknown_id_raises_value_error(db: Session):
    """Test that delete_jurisdiction_config raises ValueError for unknown ID"""
    unknown_id = uuid.uuid4()
    with pytest.raises(ValueError, match="not found"):
        delete_jurisdiction_config(db=db, config_id=unknown_id)
