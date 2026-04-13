"""
Tests for KYC config structure validation
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from database import FieldDefinition
from services.jurisdiction_configs.validators import validate_kyc_config_structure
import uuid


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def field_definitions(db: Session):
    """Create test field definitions"""
    slugs = ["first-name", "last-name", "tax-residency-country", "fatca-us-indicia"]
    fields = []
    for slug in slugs:
        field = db.query(FieldDefinition).filter(FieldDefinition.slug == slug).first()
        if not field:
            field = FieldDefinition(
                id=uuid.uuid4(),
                slug=slug,
                field_name_en=slug.replace("-", " ").title(),
                field_type="string" if slug != "fatca-us-indicia" else "boolean",
                category="identity" if slug in ["first-name", "last-name"] else "tax",
                is_active=True,
            )
            db.add(field)
        fields.append(field)
    db.flush()
    return fields


def test_validate_rejects_step_conditions(client, field_definitions):
    """Test that validation fails if step has 'conditions' key"""
    invalid_config = {
        "jurisdiction": "TEST",
        "purpose": "KYC",
        "version": 1,
        "status": "draft",
        "steps": [
            {
                "step_id": "step1",
                "title_en": "Step 1",
                "conditions": [  # FORBIDDEN: conditions at step level
                    {
                        "when": {"field": "first-name", "op": "equals", "value": "test"},
                        "then": [{"action": "show_block", "block_id": "block1"}]
                    }
                ],
                "blocks": [
                    {
                        "block_id": "block1",
                        "fields": ["first-name"],
                        "layout": "single_column",
                        "required": True,
                    }
                ],
            }
        ],
    }

    response = client.post("/api/jurisdiction-configs", json={
        "jurisdiction": "TEST",
        "purpose": "KYC",
        "config_json": invalid_config,
    })

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
    data = response.json()
    error_detail = data.get("detail", {})
    if isinstance(error_detail, dict):
        error_msg = error_detail.get("message", "")
        assert "conditions" in error_msg.lower() or "step" in error_msg.lower()


def test_validate_rejects_cross_step_block_reference(client, field_definitions):
    """Test that validation fails if show_block references block_id from different step"""
    invalid_config = {
        "jurisdiction": "TEST",
        "purpose": "KYC",
        "version": 1,
        "status": "draft",
        "steps": [
            {
                "step_id": "step1",
                "title_en": "Step 1",
                "blocks": [
                    {
                        "block_id": "block1",
                        "fields": ["first-name"],
                        "layout": "single_column",
                        "required": True,
                        "conditions": [
                            {
                                "when": {"field": "first-name", "op": "equals", "value": "test"},
                                "then": [
                                    {"action": "show_block", "block_id": "block2"}  # block2 is in step2, not step1
                                ]
                            }
                        ],
                    }
                ],
            },
            {
                "step_id": "step2",
                "title_en": "Step 2",
                "blocks": [
                    {
                        "block_id": "block2",
                        "fields": ["last-name"],
                        "layout": "single_column",
                        "required": True,
                    }
                ],
            }
        ],
    }

    response = client.post("/api/jurisdiction-configs", json={
        "jurisdiction": "TEST",
        "purpose": "KYC",
        "config_json": invalid_config,
    })

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
    data = response.json()
    error_detail = data.get("detail", {})
    if isinstance(error_detail, dict):
        error_msg = error_detail.get("message", "")
        assert "not in the same step" in error_msg or "cross-step" in error_msg.lower()


def test_validate_accepts_valid_tax_step_with_fatca_condition(client, field_definitions):
    """Test that validation passes for tax step containing both tax and fatca blocks with correct condition"""
    valid_config = {
        "jurisdiction": "TEST",
        "purpose": "KYC",
        "version": 1,
        "status": "draft",
        "steps": [
            {
                "step_id": "step1",
                "title_en": "Identity",
                "blocks": [
                    {
                        "block_id": "block_identity",
                        "fields": ["first-name", "last-name"],
                        "layout": "two_columns",
                        "required": True,
                    }
                ],
            },
            {
                "step_id": "step3",
                "title_en": "Tax Information",
                "blocks": [
                    {
                        "block_id": "block_tax",
                        "fields": ["tax-residency-country"],
                        "layout": "single_column",
                        "required": True,
                    },
                    {
                        "block_id": "block_fatca",
                        "fields": ["fatca-us-indicia"],
                        "layout": "single_column",
                        "required": False,
                        "conditions": [
                            {
                                "when": {"field": "tax-residency-country", "op": "equals", "value": "US"},
                                "then": [
                                    {"action": "show_block", "block_id": "block_fatca"}  # Same step, valid
                                ]
                            }
                        ],
                    }
                ],
            },
            {
                "step_id": "step4",
                "title_en": "Employment & Source of Funds",
                "blocks": [
                    {
                        "block_id": "block_employment",
                        "fields": ["first-name"],  # Using existing field for test
                        "layout": "single_column",
                        "required": True,
                    }
                ],
            }
        ],
    }

    response = client.post("/api/jurisdiction-configs", json={
        "jurisdiction": "TEST",
        "purpose": "KYC",
        "config_json": valid_config,
    })

    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["jurisdiction"] == "TEST"
    assert data["purpose"] == "KYC"
    
    # Verify step3 contains both block_tax and block_fatca
    config_json = data["config_json"]
    step3 = next((s for s in config_json["steps"] if s["step_id"] == "step3"), None)
    assert step3 is not None
    block_ids = [b["block_id"] for b in step3["blocks"]]
    assert "block_tax" in block_ids
    assert "block_fatca" in block_ids
    
    # Verify step4 does NOT contain fatca blocks
    step4 = next((s for s in config_json["steps"] if s["step_id"] == "step4"), None)
    assert step4 is not None
    step4_block_ids = [b["block_id"] for b in step4["blocks"]]
    assert "block_fatca" not in step4_block_ids


def test_validator_function_rejects_step_conditions():
    """Test validator function directly rejects step.conditions"""
    invalid_config = {
        "steps": [
            {
                "step_id": "step1",
                "title_en": "Step 1",
                "conditions": [{"when": {}, "then": []}],  # FORBIDDEN
                "blocks": []
            }
        ]
    }
    
    is_valid, errors = validate_kyc_config_structure(invalid_config)
    assert not is_valid
    assert any("must not have 'conditions' key" in err for err in errors)


def test_validator_function_rejects_cross_step_reference():
    """Test validator function directly rejects cross-step block references"""
    invalid_config = {
        "steps": [
            {
                "step_id": "step1",
                "title_en": "Step 1",
                "blocks": [
                    {
                        "block_id": "block1",
                        "fields": [],
                        "layout": "single_column",
                        "required": True,
                        "conditions": [
                            {
                                "when": {"field": "test", "op": "equals", "value": "x"},
                                "then": [{"action": "show_block", "block_id": "block2"}]  # block2 not in step1
                            }
                        ],
                    }
                ],
            },
            {
                "step_id": "step2",
                "title_en": "Step 2",
                "blocks": [
                    {"block_id": "block2", "fields": [], "layout": "single_column", "required": True}
                ],
            }
        ]
    }
    
    is_valid, errors = validate_kyc_config_structure(invalid_config)
    assert not is_valid
    assert any("not in the same step" in err for err in errors)


def test_validator_function_accepts_valid_same_step_reference():
    """Test validator function accepts show_block within same step"""
    valid_config = {
        "steps": [
            {
                "step_id": "step1",
                "title_en": "Step 1",
                "blocks": [
                    {
                        "block_id": "block1",
                        "fields": [],
                        "layout": "single_column",
                        "required": True,
                        "conditions": [
                            {
                                "when": {"field": "test", "op": "equals", "value": "x"},
                                "then": [{"action": "show_block", "block_id": "block2"}]  # block2 is in same step
                            }
                        ],
                    },
                    {
                        "block_id": "block2",
                        "fields": [],
                        "layout": "single_column",
                        "required": True,
                    }
                ],
            }
        ]
    }
    
    is_valid, errors = validate_kyc_config_structure(valid_config)
    assert is_valid, f"Expected valid, got errors: {errors}"
