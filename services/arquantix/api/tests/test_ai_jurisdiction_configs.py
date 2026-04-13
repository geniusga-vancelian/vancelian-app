"""
Tests for AI Jurisdiction Configs Builder
"""
import pytest
import json
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from database import FieldDefinition
from services.ai_jurisdiction_configs.agent import (
    compose_jurisdiction_config_spec,
    list_fields,
    resolve_slug,
    search_field_candidates,
)
import uuid


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API response"""
    return {
        "choices": [
            {
                "message": {
                    "content": '{"assistant_text": "Created KYC config", "spec": {"jurisdiction": "Vancelian_EU_MICA", "purpose": "KYC", "version": 1, "status": "draft", "steps": [{"step_id": "step1", "title_en": "Basic Info", "description_en": "Provide basic information", "blocks": [{"block_id": "block1", "fields": ["first-name", "last-name"], "layout": "two_columns", "required": True}]}]}}'
                }
            }
        ]
    }


@pytest.fixture
def field_definitions(db: Session):
    """Create test field definitions"""
    fields = [
        FieldDefinition(
            id=uuid.uuid4(),
            slug="first-name",
            field_name_en="First Name",
            field_type="string",
            category="identity",
            is_active=True,
        ),
        FieldDefinition(
            id=uuid.uuid4(),
            slug="last-name",
            field_name_en="Last Name",
            field_type="string",
            category="identity",
            is_active=True,
        ),
        FieldDefinition(
            id=uuid.uuid4(),
            slug="pep-status",
            field_name_en="PEP Status",
            field_type="boolean",
            category="aml",
            is_active=True,
        ),
    ]
    for field in fields:
        db.add(field)
    db.commit()
    return fields


@pytest.fixture
def canonical_field_definitions(db: Session):
    """Create canonical field definitions for alias tests"""
    fields = [
        FieldDefinition(
            id=uuid.uuid4(),
            slug="nationality-primary",
            field_name_en="Nationality (Primary)",
            field_type="string",
            category="identity",
            is_active=True,
        ),
        FieldDefinition(
            id=uuid.uuid4(),
            slug="residential-address-line1",
            field_name_en="Residential Address Line 1",
            field_type="string",
            category="address",
            is_active=True,
        ),
        FieldDefinition(
            id=uuid.uuid4(),
            slug="residential-address-city",
            field_name_en="Residential City",
            field_type="string",
            category="address",
            is_active=True,
        ),
        FieldDefinition(
            id=uuid.uuid4(),
            slug="residential-address-country",
            field_name_en="Residential Country",
            field_type="string",
            category="address",
            is_active=True,
        ),
        FieldDefinition(
            id=uuid.uuid4(),
            slug="tax-residency-country-primary",
            field_name_en="Tax Residency Country (Primary)",
            field_type="string",
            category="tax",
            is_active=True,
        ),
        FieldDefinition(
            id=uuid.uuid4(),
            slug="tax-identification-number",
            field_name_en="Tax Identification Number",
            field_type="string",
            category="tax",
            is_active=True,
        ),
        FieldDefinition(
            id=uuid.uuid4(),
            slug="occupation-title",
            field_name_en="Occupation Title",
            field_type="string",
            category="employment",
            is_active=True,
        ),
    ]
    for field in fields:
        db.add(field)
    db.commit()
    return fields


def test_list_fields(db: Session, field_definitions):
    """Test list_fields helper function"""
    fields = list_fields(db, category="identity")
    assert len(fields) >= 2
    slugs = [f["slug"] for f in fields]
    assert "first-name" in slugs
    assert "last-name" in slugs


def test_list_fields_with_search(db: Session, field_definitions):
    """Test list_fields with search"""
    fields = list_fields(db, search="name")
    slugs = [f["slug"] for f in fields]
    assert "first-name" in slugs or "last-name" in slugs


def test_search_field_candidates(db: Session, field_definitions):
    """Test search_field_candidates"""
    candidates = search_field_candidates(db, "name", limit=10)
    assert len(candidates) >= 2
    slugs = [c["slug"] for c in candidates]
    assert "first-name" in slugs or "last-name" in slugs


def test_resolve_slug_aliases(db: Session, canonical_field_definitions):
    """Regression: Resolve slug aliases to canonical slugs"""
    # Test nationality -> nationality-primary
    slug, candidates = resolve_slug(db, "nationality")
    assert slug == "nationality-primary"
    assert len(candidates) > 0
    
    # Test tax-id-number -> tax-identification-number
    slug, candidates = resolve_slug(db, "tax-id-number")
    assert slug == "tax-identification-number"
    assert len(candidates) > 0
    
    # Test residential-address-line-1 -> residential-address-line1
    slug, candidates = resolve_slug(db, "residential-address-line-1")
    assert slug == "residential-address-line1"
    
    # Test residential-city -> residential-address-city
    slug, candidates = resolve_slug(db, "residential-city")
    assert slug == "residential-address-city"
    
    # Test residential-country -> residential-address-country
    slug, candidates = resolve_slug(db, "residential-country")
    assert slug == "residential-address-country"
    
    # Test tax-residency-country -> tax-residency-country-primary
    slug, candidates = resolve_slug(db, "tax-residency-country")
    assert slug == "tax-residency-country-primary"
    
    # Test occupation -> occupation-title
    slug, candidates = resolve_slug(db, "occupation")
    assert slug == "occupation-title"


@patch("services.ai_jurisdiction_configs.agent.httpx.Client")
def test_compose_jurisdiction_config_spec_kyc(mock_client, db: Session, field_definitions, mock_openai_response):
    """Test compose_jurisdiction_config_spec for KYC"""
    # Mock httpx client
    mock_response = Mock()
    mock_response.json.return_value = mock_openai_response
    mock_response.raise_for_status = Mock()
    mock_client.return_value.__enter__.return_value.post.return_value = mock_response

    assistant_text, spec, warnings, questions, value_suggestions = compose_jurisdiction_config_spec(
        db=db,
        jurisdiction="Vancelian_EU_MICA",
        purpose="KYC",
        prompt="Create a basic onboarding flow",
    )

    assert assistant_text
    assert isinstance(spec, dict)
    assert "steps" in spec
    assert spec["purpose"] == "KYC"
    assert spec["jurisdiction"] == "Vancelian_EU_MICA"


def test_resolve_slug_handles_residential_postal_code_variations(db: Session, field_definitions):
    """Test that resolve_slug handles residential-address-postal-code variations and suggests residential-postal-code"""
    # Ensure residential-postal-code exists
    postal_field = db.query(FieldDefinition).filter(FieldDefinition.slug == "residential-postal-code").first()
    if not postal_field:
        postal_field = FieldDefinition(
            id=uuid.uuid4(),
            slug="residential-postal-code",
            field_name_en="Residential Postal Code",
            field_type="string",
            category="address",
            is_active=True,
        )
        db.add(postal_field)
        db.flush()
    
    # Test that residential-address-postal-code resolves or suggests residential-postal-code
    slug, candidates = resolve_slug(db, "residential-address-postal-code")
    # Should either resolve directly or suggest residential-postal-code
    assert slug == "residential-postal-code" or any(
        c["slug"] == "residential-postal-code" for c in candidates
    ), f"residential-address-postal-code should resolve to or suggest residential-postal-code (got: {slug}, candidates: {[c['slug'] for c in candidates]})"


@patch("services.ai_jurisdiction_configs.agent.httpx.Client")
def test_compose_jurisdiction_config_spec_aml_risk(mock_client, db: Session, field_definitions):
    """Test compose_jurisdiction_config_spec for AML_RISK"""
    mock_response_content = '{"assistant_text": "Created AML config", "spec": {"jurisdiction": "Vancelian_EU_MICA", "purpose": "AML_RISK", "version": 1, "status": "draft", "rules": [{"rule_id": "rule1", "when": {"field": "pep-status", "op": "equals", "value": true}, "effect": {"type": "add_score", "value": 20}}], "outputs": {"min_score": 0, "max_score": 100, "tiers": [{"tier": "low", "min": 0, "max": 30}, {"tier": "medium", "min": 31, "max": 70}, {"tier": "high", "min": 71, "max": 100}]}}}'
    
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": mock_response_content}}]
    }
    mock_response.raise_for_status = Mock()
    mock_client.return_value.__enter__.return_value.post.return_value = mock_response

    assistant_text, spec, warnings, questions, value_suggestions = compose_jurisdiction_config_spec(
        db=db,
        jurisdiction="Vancelian_EU_MICA",
        purpose="AML_RISK",
        prompt="Create risk scoring rules",
    )

    assert assistant_text
    assert isinstance(spec, dict)
    assert "rules" in spec
    assert spec["purpose"] == "AML_RISK"


@patch("services.ai_jurisdiction_configs.agent.httpx.Client")
def test_compose_rewrites_to_canonical_slugs(mock_client, db: Session, field_definitions, canonical_field_definitions):
    """Regression: Compose rewrites non-canonical slugs to canonical ones"""
    # Mock OpenAI response with non-canonical slugs
    mock_response_content = '{"assistant_text": "Created KYC config", "spec": {"jurisdiction": "Vancelian_EU_MICA", "purpose": "KYC", "version": 1, "status": "draft", "steps": [{"step_id": "step1", "title_en": "Basic Info", "description_en": "Provide basic information", "blocks": [{"block_id": "block1", "fields": ["nationality", "tax-id-number"], "layout": "two_columns", "required": True}]}]}}'
    
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": mock_response_content}}]
    }
    mock_response.raise_for_status = Mock()
    mock_client.return_value.__enter__.return_value.post.return_value = mock_response

    assistant_text, spec, warnings, questions, value_suggestions = compose_jurisdiction_config_spec(
        db=db,
        jurisdiction="Vancelian_EU_MICA",
        purpose="KYC",
        prompt="Create a config with nationality and tax ID",
    )

    assert assistant_text
    assert isinstance(spec, dict)
    assert "steps" in spec
    
    # Check that slugs were rewritten to canonical
    fields = spec["steps"][0]["blocks"][0]["fields"]
    assert "nationality-primary" in fields
    assert "tax-identification-number" in fields
    assert "nationality" not in fields
    assert "tax-id-number" not in fields


@patch("services.ai_jurisdiction_configs.agent.httpx.Client")
def test_compose_returns_questions_when_unknown(mock_client, db: Session, field_definitions):
    """Regression: Compose returns questions (and null spec) when unknown slugs exist"""
    # Mock OpenAI response with unknown field slug
    mock_response_content = '{"assistant_text": "Created KYC config", "spec": {"jurisdiction": "Vancelian_EU_MICA", "purpose": "KYC", "version": 1, "status": "draft", "steps": [{"step_id": "step1", "title_en": "Basic Info", "description_en": "Provide basic information", "blocks": [{"block_id": "block1", "fields": ["first-name", "unknown-field-that-does-not-exist"], "layout": "two_columns", "required": True}]}]}}'
    
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": mock_response_content}}]
    }
    mock_response.raise_for_status = Mock()
    mock_client.return_value.__enter__.return_value.post.return_value = mock_response

    assistant_text, spec, warnings, questions, value_suggestions = compose_jurisdiction_config_spec(
        db=db,
        jurisdiction="Vancelian_EU_MICA",
        purpose="KYC",
        prompt="Create a config with unknown field",
    )

    # Should return questions and null spec
    assert spec is None
    assert len(questions) > 0
    assert any(q.get("term") == "unknown-field-that-does-not-exist" for q in questions)
    assert "could not find" in assistant_text.lower() or "unknown" in assistant_text.lower()


@pytest.mark.asyncio
async def test_ai_jurisdiction_validate_rejects_unknown_field(db: Session):
    """Test validate logic rejects unknown field slugs"""
    from services.ai_jurisdiction_configs.routes import validate_jurisdiction_config
    from services.ai_jurisdiction_configs.schemas import ValidateJurisdictionConfigRequest
    from auth import AdminUser
    
    # Create a mock admin user for auth
    mock_user = AdminUser(id=1, email="test@example.com", hashed_password="dummy")
    
    # Create a config with unknown field
    invalid_spec = {
        "jurisdiction": "Vancelian_EU_MICA",
        "purpose": "KYC",
        "version": 1,
        "status": "draft",
        "steps": [
            {
                "step_id": "step1",
                "title_en": "Test",
                "blocks": [
                    {
                        "block_id": "block1",
                        "fields": ["unknown-field-slug"],
                        "layout": "single_column",
                        "required": True,
                    }
                ],
            }
        ],
    }
    
    request = ValidateJurisdictionConfigRequest(
        jurisdiction="Vancelian_EU_MICA",
        purpose="KYC",
        spec=invalid_spec,
    )
    
    # Call validate function directly (not via HTTP)
    result = await validate_jurisdiction_config(request, current_user=mock_user, db=db)
    
    assert result.ok == False
    assert len(result.errors) > 0
    assert any("unknown-field-slug" in error for error in result.errors)


def test_compose_returns_spec_with_jurisdiction_purpose_version(db: Session, field_definitions):
    """Regression: Compose must return spec with jurisdiction, purpose, version"""
    assistant_text, spec, warnings, questions, value_suggestions = compose_jurisdiction_config_spec(
        db=db,
        jurisdiction="Vancelian_EU_MICA",
        purpose="KYC",
        prompt="Create a basic onboarding flow",
    )
    
    assert isinstance(spec, dict)
    assert spec.get("jurisdiction") == "Vancelian_EU_MICA"
    assert spec.get("purpose") == "KYC"
    assert spec.get("version") == 1
    assert "steps" in spec


@pytest.mark.asyncio
async def test_validate_rejects_condition_missing_when_then(db: Session):
    """Regression: Validate must reject condition objects missing when/then"""
    from services.ai_jurisdiction_configs.routes import validate_jurisdiction_config
    from services.ai_jurisdiction_configs.schemas import ValidateJurisdictionConfigRequest
    from auth import AdminUser
    
    mock_user = AdminUser(id=1, email="test@example.com", hashed_password="dummy")
    
    # Create a config with invalid condition (missing when/then)
    invalid_spec = {
        "jurisdiction": "Vancelian_EU_MICA",
        "purpose": "KYC",
        "version": 1,
        "status": "draft",
        "steps": [
            {
                "step_id": "step1",
                "title_en": "Test",
                "blocks": [
                    {
                        "block_id": "block1",
                        "fields": ["first-name"],
                        "layout": "single_column",
                        "required": True,
                        "conditions": [
                            {
                                "field": "some-field",
                                "operator": "equals",
                                "value": "test"
                                # Missing "when" and "then"
                            }
                        ],
                    }
                ],
            }
        ],
    }
    
    request = ValidateJurisdictionConfigRequest(
        jurisdiction="Vancelian_EU_MICA",
        purpose="KYC",
        spec=invalid_spec,
    )
    
    result = await validate_jurisdiction_config(request, current_user=mock_user, db=db)
    
    assert result.ok == False
    assert len(result.errors) > 0
    # Should fail schema validation due to invalid condition structure


@patch("services.ai_jurisdiction_configs.agent.httpx.Client")
def test_compose_handles_special_characters_in_prompt(mock_client, db: Session, field_definitions, mock_openai_response):
    """Regression: Compose must handle prompts with special characters like : and {}"""
    # Mock httpx client
    mock_response = Mock()
    mock_response.json.return_value = mock_openai_response
    mock_response.raise_for_status = Mock()
    mock_client.return_value.__enter__.return_value.post.return_value = mock_response

    # Test with prompt containing special characters that could break f-string formatting
    prompt_with_special_chars = 'Create config with fields: {first-name, last-name} and value: 100:200'
    
    assistant_text, spec, warnings, questions, value_suggestions = compose_jurisdiction_config_spec(
        db=db,
        jurisdiction="Vancelian_EU_MICA",
        purpose="KYC",
        prompt=prompt_with_special_chars,
    )

    assert assistant_text
    assert isinstance(spec, dict)
    assert "steps" in spec
    assert spec["purpose"] == "KYC"
    assert spec["jurisdiction"] == "Vancelian_EU_MICA"


@patch("services.ai_jurisdiction_configs.agent.httpx.Client")
def test_compose_parses_correct_json(mock_client, db: Session, field_definitions):
    """Test A: OpenAI returns correct JSON -> agent returns spec"""
    correct_json = {
        "jurisdiction": "Vancelian_EU_MICA",
        "purpose": "KYC",
        "version": 1,
        "status": "draft",
        "steps": [
            {
                "step_id": "step1",
                "title_en": "Basic Info",
                "description_en": "Provide basic information",
                "blocks": [
                    {
                        "block_id": "block1",
                        "fields": ["first-name", "last-name"],
                        "layout": "two_columns",
                        "required": True,
                        "conditions": []
                    }
                ]
            }
        ],
        "entry_rules": None
    }
    
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(correct_json)}}]
    }
    mock_response.raise_for_status = Mock()
    mock_client.return_value.__enter__.return_value.post.return_value = mock_response
    
    assistant_text, spec, warnings, questions, value_suggestions = compose_jurisdiction_config_spec(
        db=db,
        jurisdiction="Vancelian_EU_MICA",
        purpose="KYC",
        prompt="Create a basic onboarding flow",
    )
    
    assert assistant_text
    assert isinstance(spec, dict)
    assert "steps" in spec
    assert len(spec["steps"]) == 1
    assert spec["steps"][0]["step_id"] == "step1"


@patch("services.ai_jurisdiction_configs.agent.httpx.Client")
def test_compose_extracts_json_from_markdown(mock_client, db: Session, field_definitions):
    """Test B: OpenAI returns text containing JSON in markdown -> extractor succeeds"""
    correct_json = {
        "jurisdiction": "Vancelian_EU_MICA",
        "purpose": "KYC",
        "version": 1,
        "status": "draft",
        "steps": [
            {
                "step_id": "step1",
                "title_en": "Basic Info",
                "description_en": "Provide basic information",
                "blocks": [
                    {
                        "block_id": "block1",
                        "fields": ["first-name", "last-name"],
                        "layout": "two_columns",
                        "required": True,
                        "conditions": []
                    }
                ]
            }
        ],
        "entry_rules": None
    }
    
    # Simulate OpenAI returning JSON wrapped in markdown
    markdown_response = f"""Here is the configuration:

```json
{json.dumps(correct_json, indent=2)}
```

This config includes basic identity fields."""
    
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": markdown_response}}]
    }
    mock_response.raise_for_status = Mock()
    mock_client.return_value.__enter__.return_value.post.return_value = mock_response
    
    assistant_text, spec, warnings, questions, value_suggestions = compose_jurisdiction_config_spec(
        db=db,
        jurisdiction="Vancelian_EU_MICA",
        purpose="KYC",
        prompt="Create a basic onboarding flow",
    )
    
    assert assistant_text
    assert isinstance(spec, dict)
    assert "steps" in spec
    assert len(spec["steps"]) == 1


@patch("services.ai_jurisdiction_configs.agent.httpx.Client")
def test_compose_raises_value_error_for_invalid_text(mock_client, db: Session, field_definitions):
    """Test C: OpenAI returns invalid text -> raises ValueError with clear error"""
    invalid_response = "I cannot generate a valid configuration at this time. Please try again later."
    
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": invalid_response}}]
    }
    mock_response.raise_for_status = Mock()
    mock_client.return_value.__enter__.return_value.post.return_value = mock_response
    
    with pytest.raises(ValueError) as exc_info:
        compose_jurisdiction_config_spec(
            db=db,
            jurisdiction="Vancelian_EU_MICA",
            purpose="KYC",
            prompt="Create a basic onboarding flow",
        )
    
    assert "Could not extract valid JSON" in str(exc_info.value) or "OpenAI response parsing failed" in str(exc_info.value)


@patch("services.ai_jurisdiction_configs.agent.httpx.Client")
def test_compose_raises_value_error_for_missing_steps(mock_client, db: Session, field_definitions):
    """Test: OpenAI returns JSON without 'steps' array -> raises ValueError"""
    invalid_json = {
        "jurisdiction": "Vancelian_EU_MICA",
        "purpose": "KYC",
        "version": 1,
        "status": "draft",
        # Missing "steps" array
    }
    
    mock_response = Mock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": json.dumps(invalid_json)}}]
    }
    mock_response.raise_for_status = Mock()
    mock_client.return_value.__enter__.return_value.post.return_value = mock_response
    
    with pytest.raises(ValueError) as exc_info:
        compose_jurisdiction_config_spec(
            db=db,
            jurisdiction="Vancelian_EU_MICA",
            purpose="KYC",
            prompt="Create a basic onboarding flow",
        )
    
    assert "steps" in str(exc_info.value).lower() or "must have" in str(exc_info.value).lower()
