"""
Tests for jurisdiction configs publish-time validation
"""
import pytest
import uuid
from sqlalchemy.orm import Session

from database import Person, FieldDefinition, JurisdictionConfig
from services.jurisdiction_configs import create_jurisdiction_config, publish_jurisdiction_config
from schemas_jurisdiction import JurisdictionConfigSchema, Step, Block
from schemas_aml_risk import (
    AMLRiskConfig,
    AMLRiskRule,
    AMLRiskCondition,
    AMLRiskEffect,
    AMLRiskOutputs,
    AMLRiskOutputTier,
)


@pytest.fixture
def field_definitions(db: Session):
    """Create or get test field definitions"""
    slugs = ["first-name", "last-name", "email", "country-of-residence"]
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


def test_publish_config_with_unknown_slug_fails(db: Session, field_definitions):
    """Test that publishing config with unknown field slug fails"""
    config_schema = JurisdictionConfigSchema(
        jurisdiction="TEST",
        purpose="KYC",
        version=1,
        steps=[
            Step(
                step_id="step1",
                title_en="Step 1",
                blocks=[
                    Block(
                        block_id="block1",
                        fields=["first-name", "unknown-field-slug"],  # unknown-field-slug doesn't exist
                        layout="single_column",
                        required=True,
                    ),
                ],
            ),
        ],
        status="draft",
    )
    
    config = create_jurisdiction_config(
        db=db,
        jurisdiction="TEST",
        purpose="KYC",
        config_json=config_schema,
    )
    
    # Publish should fail
    with pytest.raises(ValueError, match="Invalid field slugs in config"):
        publish_jurisdiction_config(db=db, config_id=config.id)
    
    # Config should remain draft
    db.refresh(config)
    assert config.status == "draft"


def test_publish_config_with_inactive_slug_fails(db: Session, field_definitions):
    """Test that publishing config with inactive field slug fails"""
    # Create an inactive field
    inactive_field = FieldDefinition(
        id=uuid.uuid4(),
        slug="inactive-field",
        field_name_en="Inactive Field",
        field_type="string",
        category="identity",
        is_active=False,  # Inactive
    )
    db.add(inactive_field)
    db.flush()
    
    config_schema = JurisdictionConfigSchema(
        jurisdiction="TEST",
        purpose="KYC",
        version=1,
        steps=[
            Step(
                step_id="step1",
                title_en="Step 1",
                blocks=[
                    Block(
                        block_id="block1",
                        fields=["first-name", "inactive-field"],  # inactive-field is inactive
                        layout="single_column",
                        required=True,
                    ),
                ],
            ),
        ],
        status="draft",
    )
    
    config = create_jurisdiction_config(
        db=db,
        jurisdiction="TEST",
        purpose="KYC",
        config_json=config_schema,
    )
    
    # Publish should fail
    with pytest.raises(ValueError, match="Invalid field slugs in config"):
        publish_jurisdiction_config(db=db, config_id=config.id)
    
    # Config should remain draft
    db.refresh(config)
    assert config.status == "draft"


def test_publish_aml_risk_config_with_overlapping_tiers_fails(db: Session, field_definitions):
    """Test that publishing AML_RISK config with overlapping tiers fails"""
    config_schema = AMLRiskConfig(
        jurisdiction="TEST",
        purpose="AML_RISK",
        version=1,
        status="draft",
        rules=[
            AMLRiskRule(
                rule_id="rule1",
                description_en="Test rule",
                when=AMLRiskCondition(
                    field_slug="country-of-residence",
                    operator="equals",
                    value="XX",
                ),
                effect=AMLRiskEffect(
                    add_score=25,
                ),
            ),
        ],
        outputs=AMLRiskOutputs(
            min_score=0,
            max_score=100,
            tiers=[
                AMLRiskOutputTier(tier="low", min=0, max=50),  # Overlaps with medium
                AMLRiskOutputTier(tier="medium", min=40, max=100),  # Overlaps with low
            ],
        ),
    )
    
    config = create_jurisdiction_config(
        db=db,
        jurisdiction="TEST",
        purpose="AML_RISK",
        config_json=config_schema,
    )
    
    # Publish should fail
    with pytest.raises(ValueError, match="overlaps"):
        publish_jurisdiction_config(db=db, config_id=config.id)
    
    # Config should remain draft
    db.refresh(config)
    assert config.status == "draft"


def test_publish_aml_risk_config_with_missing_coverage_fails(db: Session, field_definitions):
    """Test that publishing AML_RISK config with missing tier coverage fails"""
    config_schema = AMLRiskConfig(
        jurisdiction="TEST",
        purpose="AML_RISK",
        version=1,
        status="draft",
        rules=[
            AMLRiskRule(
                rule_id="rule1",
                description_en="Test rule",
                when=AMLRiskCondition(
                    field_slug="country-of-residence",
                    operator="equals",
                    value="XX",
                ),
                effect=AMLRiskEffect(
                    add_score=25,
                ),
            ),
        ],
        outputs=AMLRiskOutputs(
            min_score=0,
            max_score=100,
            tiers=[
                AMLRiskOutputTier(tier="low", min=0, max=30),
                AMLRiskOutputTier(tier="medium", min=31, max=70),
                # Missing coverage: 71-100 is not covered
            ],
        ),
    )
    
    config = create_jurisdiction_config(
        db=db,
        jurisdiction="TEST",
        purpose="AML_RISK",
        config_json=config_schema,
    )
    
    # Publish should fail
    with pytest.raises(ValueError, match="must end at max_score"):
        publish_jurisdiction_config(db=db, config_id=config.id)
    
    # Config should remain draft
    db.refresh(config)
    assert config.status == "draft"


def test_publish_aml_risk_config_with_gap_fails(db: Session, field_definitions):
    """Test that publishing AML_RISK config with gap between tiers fails"""
    config_schema = AMLRiskConfig(
        jurisdiction="TEST",
        purpose="AML_RISK",
        version=1,
        status="draft",
        rules=[
            AMLRiskRule(
                rule_id="rule1",
                description_en="Test rule",
                when=AMLRiskCondition(
                    field_slug="country-of-residence",
                    operator="equals",
                    value="XX",
                ),
                effect=AMLRiskEffect(
                    add_score=25,
                ),
            ),
        ],
        outputs=AMLRiskOutputs(
            min_score=0,
            max_score=100,
            tiers=[
                AMLRiskOutputTier(tier="low", min=0, max=30),
                AMLRiskOutputTier(tier="medium", min=35, max=100),  # Gap: 31-34 not covered
            ],
        ),
    )
    
    config = create_jurisdiction_config(
        db=db,
        jurisdiction="TEST",
        purpose="AML_RISK",
        config_json=config_schema,
    )
    
    # Publish should fail
    with pytest.raises(ValueError, match="Gap between tier"):
        publish_jurisdiction_config(db=db, config_id=config.id)
    
    # Config should remain draft
    db.refresh(config)
    assert config.status == "draft"


def test_publish_aml_risk_config_with_valid_tiers_succeeds(db: Session, field_definitions):
    """Test that publishing AML_RISK config with valid tier coverage succeeds"""
    config_schema = AMLRiskConfig(
        jurisdiction="TEST",
        purpose="AML_RISK",
        version=1,
        status="draft",
        rules=[
            AMLRiskRule(
                rule_id="rule1",
                description_en="Test rule",
                when=AMLRiskCondition(
                    field_slug="country-of-residence",
                    operator="equals",
                    value="XX",
                ),
                effect=AMLRiskEffect(
                    add_score=25,
                ),
            ),
        ],
        outputs=AMLRiskOutputs(
            min_score=0,
            max_score=100,
            tiers=[
                AMLRiskOutputTier(tier="low", min=0, max=30),
                AMLRiskOutputTier(tier="medium", min=31, max=70),
                AMLRiskOutputTier(tier="high", min=71, max=100),
            ],
        ),
    )
    
    config = create_jurisdiction_config(
        db=db,
        jurisdiction="TEST",
        purpose="AML_RISK",
        config_json=config_schema,
    )
    
    # Publish should succeed
    published = publish_jurisdiction_config(db=db, config_id=config.id)
    assert published.status == "active"


def test_publish_onboarding_config_with_valid_slugs_succeeds(db: Session, field_definitions):
    """Test that publishing onboarding config with valid field slugs succeeds"""
    config_schema = JurisdictionConfigSchema(
        jurisdiction="TEST",
        purpose="KYC",
        version=1,
        steps=[
            Step(
                step_id="step1",
                title_en="Step 1",
                blocks=[
                    Block(
                        block_id="block1",
                        fields=["first-name", "last-name"],  # Both exist and are active
                        layout="single_column",
                        required=True,
                    ),
                ],
            ),
        ],
        status="draft",
    )
    
    config = create_jurisdiction_config(
        db=db,
        jurisdiction="TEST",
        purpose="KYC",
        config_json=config_schema,
    )
    
    # Publish should succeed
    published = publish_jurisdiction_config(db=db, config_id=config.id)
    assert published.status == "active"
