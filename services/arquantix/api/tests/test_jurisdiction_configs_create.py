"""
Tests for jurisdiction configs create endpoint validation
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from main import app
from database import FieldDefinition, JurisdictionConfig
import uuid


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def field_definitions(db: Session):
    """Create test field definitions"""
    slugs = ["first-name", "last-name", "email"]
    fields = []
    for slug in slugs:
        field = db.query(FieldDefinition).filter(FieldDefinition.slug == slug).first()
        if not field:
            field = FieldDefinition(
                id=uuid.uuid4(),
                slug=slug,
                field_name_en=slug.replace("-", " ").title(),
                field_type="string",
                category="identity",
                is_active=True,
            )
            db.add(field)
        fields.append(field)
    db.flush()
    return fields


def test_create_config_with_invalid_schema_returns_400(client, field_definitions):
    """Test that creating config with invalid schema returns 400 (not 500)"""
    invalid_config = {
        "jurisdiction": "TEST",
        "purpose": "KYC",
        "config_json": {
            "jurisdiction": "TEST",
            "purpose": "KYC",
            "version": 1,
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
                            # Missing required field: conditions should be [] or null, but structure is wrong
                        }
                    ],
                }
            ],
            "status": "draft",
        },
    }

    response = client.post("/api/jurisdiction-configs", json=invalid_config)

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
    data = response.json()
    assert "error" in data.get("detail", {}) or "error" in data
    error_obj = data.get("detail", data)
    assert error_obj.get("error") == "invalid_config_json" or "invalid" in str(error_obj.get("error", "")).lower()


def test_create_config_with_invalid_condition_structure_returns_400(client, field_definitions):
    """Test that creating config with invalid condition structure returns 400"""
    invalid_config = {
        "jurisdiction": "TEST",
        "purpose": "KYC",
        "config_json": {
            "jurisdiction": "TEST",
            "purpose": "KYC",
            "version": 1,
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
                                    # Missing "when" and "then" keys
                                    "field": "first-name",
                                    "operator": "equals",
                                    "value": "test",
                                }
                            ],
                        }
                    ],
                }
            ],
            "status": "draft",
        },
    }

    response = client.post("/api/jurisdiction-configs", json=invalid_config)

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
    data = response.json()
    assert "error" in data.get("detail", {}) or "error" in data


def test_create_config_with_valid_schema_returns_201(client, field_definitions, db: Session):
    """Test that creating config with valid schema returns 201 and includes created config id"""
    valid_config = {
        "jurisdiction": "TEST",
        "purpose": "KYC",
        "config_json": {
            "jurisdiction": "TEST",
            "purpose": "KYC",
            "version": 1,
            "steps": [
                {
                    "step_id": "step1",
                    "title_en": "Step 1",
                    "blocks": [
                        {
                            "block_id": "block1",
                            "fields": ["first-name", "last-name"],
                            "layout": "single_column",
                            "required": True,
                        }
                    ],
                }
            ],
            "status": "draft",
        },
    }

    response = client.post("/api/jurisdiction-configs", json=valid_config)

    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["jurisdiction"] == "TEST"
    assert data["purpose"] == "KYC"
    assert data["status"] == "draft"
    assert "id" in data
    assert data["version"] == 1
    
    # Verify config was actually created in DB
    config = db.query(JurisdictionConfig).filter(JurisdictionConfig.id == uuid.UUID(data["id"])).first()
    assert config is not None
    assert config.jurisdiction == "TEST"
    assert config.purpose == "KYC"
    assert config.status == "draft"
    assert config.version == 1


def test_create_config_with_missing_required_fields_returns_400(client, field_definitions):
    """Test that creating config with missing required fields returns 400"""
    invalid_config = {
        "jurisdiction": "TEST",
        "purpose": "KYC",
        "config_json": {
            # Missing jurisdiction, purpose, version, steps
            "status": "draft",
        },
    }

    response = client.post("/api/jurisdiction-configs", json=invalid_config)

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
    data = response.json()
    assert "error" in data.get("detail", {}) or "error" in data


def test_create_aml_risk_config_with_invalid_schema_returns_400(client, field_definitions):
    """Test that creating AML_RISK config with invalid schema returns 400"""
    invalid_config = {
        "jurisdiction": "TEST",
        "purpose": "AML_RISK",
        "config_json": {
            "jurisdiction": "TEST",
            "purpose": "AML_RISK",
            "version": 1,
            "status": "draft",
            # Missing required "rules" and "outputs"
        },
    }

    response = client.post("/api/jurisdiction-configs", json=invalid_config)

    assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
    data = response.json()
    assert "error" in data.get("detail", {}) or "error" in data


def test_create_config_auto_increments_version(client, field_definitions, db: Session):
    """Test that creating multiple configs auto-increments version"""
    base_config = {
        "jurisdiction": "TEST_VERSION",
        "purpose": "KYC",
        "config_json": {
            "jurisdiction": "TEST_VERSION",
            "purpose": "KYC",
            "version": 1,
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
                        }
                    ],
                }
            ],
            "status": "draft",
        },
    }

    # Create first config
    response1 = client.post("/api/jurisdiction-configs", json=base_config)
    assert response1.status_code == 201
    data1 = response1.json()
    assert data1["version"] == 1

    # Create second config
    response2 = client.post("/api/jurisdiction-configs", json=base_config)
    assert response2.status_code == 201
    data2 = response2.json()
    assert data2["version"] == 2

    # Create third config
    response3 = client.post("/api/jurisdiction-configs", json=base_config)
    assert response3.status_code == 201
    data3 = response3.json()
    assert data3["version"] == 3

    # Verify all exist in DB
    configs = db.query(JurisdictionConfig).filter(
        JurisdictionConfig.jurisdiction == "TEST_VERSION",
        JurisdictionConfig.purpose == "KYC"
    ).order_by(JurisdictionConfig.version).all()
    assert len(configs) == 3
    assert configs[0].version == 1
    assert configs[1].version == 2
    assert configs[2].version == 3


def test_create_config_stores_exact_config_json(client, field_definitions, db: Session):
    """Test that create stores EXACTLY the config_json as provided (as JSONB)"""
    test_config_json = {
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
                    }
                ],
            }
        ],
        "entry_rules": None,
        "custom_field": "custom_value",  # Extra field that should be preserved
    }

    request_body = {
        "jurisdiction": "TEST",
        "purpose": "KYC",
        "config_json": test_config_json,
    }

    response = client.post("/api/jurisdiction-configs", json=request_body)
    assert response.status_code == 201
    data = response.json()

    # Verify stored config_json matches exactly (including extra fields)
    config = db.query(JurisdictionConfig).filter(JurisdictionConfig.id == uuid.UUID(data["id"])).first()
    assert config is not None
    assert config.config_json["custom_field"] == "custom_value"
    assert config.config_json["jurisdiction"] == "TEST"
    assert config.config_json["purpose"] == "KYC"
