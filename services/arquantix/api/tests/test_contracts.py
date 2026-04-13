"""
Contract tests for core system invariants
"""
import pytest
import uuid
from sqlalchemy.orm import Session

from database import FieldDefinition, Person, JurisdictionConfig, AuditEvent
from services.jurisdiction_configs import create_jurisdiction_config, publish_jurisdiction_config, get_active_config
from services.aml_risk_engine import compute_aml_risk
from schemas_jurisdiction import JurisdictionConfigSchema, Step, Block
from schemas_aml_risk import (
    AMLRiskConfig,
    AMLRiskRule,
    AMLRiskCondition,
    AMLRiskEffect,
    AMLRiskOutputs,
    AMLRiskOutputTier,
)


def test_field_definitions_contains_required_derived_slugs(db: Session):
    """Contract: field_definitions must contain required derived slugs"""
    required_slugs = [
        ("risk-score-current", "number"),
        ("risk-tier-current", "string"),
        ("aml-flags", "array"),
        ("aml-required-actions", "array"),
    ]
    
    for slug, field_type in required_slugs:
        field = db.query(FieldDefinition).filter(FieldDefinition.slug == slug).first()
        if not field:
            # Create if missing (for contract test in isolated transaction)
            field = FieldDefinition(
                id=uuid.uuid4(),
                slug=slug,
                field_name_en=slug.replace("-", " ").title(),
                field_type=field_type,
                category="derived",
                is_active=True,
            )
            db.add(field)
            db.flush()
        
        assert field is not None, f"Required derived field '{slug}' not found in field_definitions"
        assert field.category == "derived", f"Field '{slug}' must have category 'derived', got '{field.category}'"
        assert field.is_active is True, f"Field '{slug}' must be active"
        assert field.field_type == field_type, f"Field '{slug}' must have type '{field_type}', got '{field.field_type}'"


def test_field_definitions_contains_required_ai_kyc_slugs(db: Session):
    """Contract: field_definitions must contain required AI KYC config generation fields"""
    required_slugs = [
        ("investment-experience-level", "enum", "knowledge"),
        ("investment-time-horizon", "enum", "objectives"),
        ("id-document-type", "enum", "identity"),
        ("id-document-front-file", "file", "identity"),
        ("id-document-selfie-file", "file", "identity"),
        ("proof-of-address-file", "file", "address"),
        ("consent-kyc-processing", "boolean", "consents"),
        ("consent-data-sharing-providers", "boolean", "consents"),
        ("terms-accepted-at", "datetime", "consents"),
        ("privacy-policy-accepted-at", "datetime", "consents"),
        ("fatca-us-indicia", "boolean", "tax"),
        ("fatca-status", "enum", "tax"),
    ]
    
    for slug, field_type, category in required_slugs:
        field = db.query(FieldDefinition).filter(FieldDefinition.slug == slug).first()
        assert field is not None, f"Required AI KYC field '{slug}' not found in field_definitions"
        assert field.field_type == field_type, f"Field '{slug}' must have type '{field_type}', got '{field.field_type}'"
        assert field.category == category, f"Field '{slug}' must have category '{category}', got '{field.category}'"
        assert field.is_active is True, f"Field '{slug}' must be active"


def test_field_definitions_contains_difc_vara_mica_kyc_slugs(db: Session):
    """Contract: field_definitions must contain DIFC/VARA/MiCA KYC required fields"""
    required_slugs = [
        ("fatca-us-indicia", "boolean", "tax"),
        ("fatca-status", "enum", "tax"),
        ("investment-experience-level", "enum", "knowledge"),
        ("investment-time-horizon", "enum", "objectives"),
        ("id-document-type", "enum", "identity"),
        ("id-document-front-file", "file", "identity"),
        ("id-document-selfie-file", "file", "identity"),
        ("proof-of-address-file", "file", "address"),
        ("consent-kyc-processing", "boolean", "consents"),
        ("consent-data-sharing-providers", "boolean", "consents"),
        ("terms-accepted-at", "datetime", "consents"),
        ("privacy-policy-accepted-at", "datetime", "consents"),
    ]
    
    for slug, field_type, category in required_slugs:
        field = db.query(FieldDefinition).filter(FieldDefinition.slug == slug).first()
        assert field is not None, f"Required DIFC/VARA/MiCA KYC field '{slug}' not found in field_definitions"
        assert field.field_type == field_type, f"Field '{slug}' must have type '{field_type}', got '{field.field_type}'"
        assert field.category == category, f"Field '{slug}' must have category '{category}', got '{field.category}'"
        assert field.is_active is True, f"Field '{slug}' must be active"


def test_field_definitions_contains_expected_activity_fields(db: Session):
    """Contract: field_definitions must contain expected activity fields for AI KYC configs"""
    required_slugs = [
        ("expected-deposit-range", "enum", "financial"),
        ("expected-monthly-volume-range", "enum", "financial"),
    ]
    
    for slug, field_type, category in required_slugs:
        field = db.query(FieldDefinition).filter(FieldDefinition.slug == slug).first()
        assert field is not None, f"Required expected activity field '{slug}' not found in field_definitions"
        assert field.field_type == field_type, f"Field '{slug}' must have type '{field_type}', got '{field.field_type}'"
        assert field.category == category, f"Field '{slug}' must have category '{category}', got '{field.category}'"
        assert field.is_active is True, f"Field '{slug}' must be active"


def test_field_definitions_contains_language_preference(db: Session):
    """Contract: field_definitions must contain language-preference field for AI KYC configs"""
    field = db.query(FieldDefinition).filter(FieldDefinition.slug == "language-preference").first()
    assert field is not None, "Required field 'language-preference' not found in field_definitions"
    assert field.field_type == "enum", f"Field 'language-preference' must have type 'enum', got '{field.field_type}'"
    assert field.category == "contact", f"Field 'language-preference' must have category 'contact', got '{field.category}'"
    assert field.is_active is True, "Field 'language-preference' must be active"


def test_jurisdiction_configs_publish_enforces_single_active(db: Session):
    """Contract: publish enforces single active per jurisdiction+purpose"""
    jurisdiction = "TEST"
    purpose = "KYC"
    
    # Create first draft config
    config1_schema = JurisdictionConfigSchema(
        jurisdiction=jurisdiction,
        purpose=purpose,
        version=1,
        steps=[
            Step(
                step_id="step1",
                title_en="Step 1",
                blocks=[
                    Block(
                        block_id="block1",
                        fields=["first-name"],
                        layout="single_column",
                        required=True,
                    ),
                ],
            ),
        ],
        status="draft",
    )
    
    config1 = create_jurisdiction_config(
        db=db,
        jurisdiction=jurisdiction,
        purpose=purpose,
        config_json=config1_schema,
    )
    
    # Publish first config
    published1 = publish_jurisdiction_config(db=db, config_id=config1.id)
    assert published1.status == "active"
    
    # Verify only one active exists
    active_configs = db.query(JurisdictionConfig).filter(
        JurisdictionConfig.jurisdiction == jurisdiction,
        JurisdictionConfig.purpose == purpose,
        JurisdictionConfig.status == "active",
    ).all()
    assert len(active_configs) == 1, "Must have exactly one active config"
    assert active_configs[0].id == config1.id
    
    # Create second draft config
    config2_schema = JurisdictionConfigSchema(
        jurisdiction=jurisdiction,
        purpose=purpose,
        version=2,
        steps=[
            Step(
                step_id="step1",
                title_en="Step 1 Updated",
                blocks=[
                    Block(
                        block_id="block1",
                        fields=["first-name"],
                        layout="single_column",
                        required=True,
                    ),
                ],
            ),
        ],
        status="draft",
    )
    
    config2 = create_jurisdiction_config(
        db=db,
        jurisdiction=jurisdiction,
        purpose=purpose,
        config_json=config2_schema,
    )
    
    # Publish second config
    published2 = publish_jurisdiction_config(db=db, config_id=config2.id)
    assert published2.status == "active"
    
    # Verify first config is archived
    db.refresh(config1)
    assert config1.status == "archived", "Previous active config must be archived"
    
    # Verify only one active exists (the second one)
    active_configs = db.query(JurisdictionConfig).filter(
        JurisdictionConfig.jurisdiction == jurisdiction,
        JurisdictionConfig.purpose == purpose,
        JurisdictionConfig.status == "active",
    ).all()
    assert len(active_configs) == 1, "Must have exactly one active config after publish"
    assert active_configs[0].id == config2.id


def test_aml_risk_engine_produces_bounded_score_and_tier(db: Session):
    """Contract: AML_RISK engine produces bounded score and sets tier correctly"""
    # Create required field definitions
    field_specs = [
        ("country-of-residence", "Country of Residence", "string", "identity"),
        ("risk-score-current", "Risk Score Current", "number", "derived"),
        ("risk-tier-current", "Risk Tier Current", "string", "derived"),
        ("aml-flags", "AML Flags", "array", "derived"),
        ("aml-required-actions", "AML Required Actions", "array", "derived"),
    ]
    
    for slug, name, field_type, category in field_specs:
        field = db.query(FieldDefinition).filter(FieldDefinition.slug == slug).first()
        if not field:
            field = FieldDefinition(
                id=uuid.uuid4(),
                slug=slug,
                field_name_en=name,
                field_type=field_type,
                category=category,
                is_active=True,
            )
            db.add(field)
    db.flush()
    
    # Create AML risk config with bounded outputs
    config_schema = AMLRiskConfig(
        jurisdiction="TEST",
        purpose="AML_RISK",
        version=1,
        status="draft",
        rules=[
            AMLRiskRule(
                rule_id="rule1",
                description_en="High risk country",
                when=AMLRiskCondition(
                    field_slug="country-of-residence",
                    operator="in",
                    value=["XX", "YY"],
                ),
                effect=AMLRiskEffect(
                    add_score=150,  # Exceeds max_score to test bounding
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
    publish_jurisdiction_config(db=db, config_id=config.id)
    
    # Create person
    person = Person(
        id=uuid.uuid4(),
        status="active",
        jurisdiction="TEST",
        profile_json={},
    )
    db.add(person)
    db.flush()
    
    # Set field value that triggers rule
    from services.person_fields import set_person_field_value
    set_person_field_value(
        db=db,
        person_id=person.id,
        slug="country-of-residence",
        value="XX",
        actor_type="system",
    )
    
    # Compute risk
    result = compute_aml_risk(
        db=db,
        person_id=person.id,
        jurisdiction="TEST",
    )
    
    # Contract: score must be bounded
    assert result["score"] >= 0, "Score must be >= min_score (0)"
    assert result["score"] <= 100, "Score must be <= max_score (100)"
    assert result["score"] == 100, "Score should be bounded to max_score (100) when rule adds 150"
    
    # Contract: tier must be correctly resolved
    assert result["tier"] in ["low", "medium", "high"], f"Tier must be one of low/medium/high, got '{result['tier']}'"
    assert result["tier"] == "high", "Score 100 should resolve to 'high' tier"
    
    # Contract: profile_json must contain derived fields
    db.refresh(person)
    assert "risk-score-current" in person.profile_json, "profile_json must contain risk-score-current"
    assert "risk-tier-current" in person.profile_json, "profile_json must contain risk-tier-current"
    assert "aml-flags" in person.profile_json, "profile_json must contain aml-flags"
    assert "aml-required-actions" in person.profile_json, "profile_json must contain aml-required-actions"
    
    score_data = person.profile_json["risk-score-current"]
    assert score_data["value"] == 100, "profile_json risk-score-current must match computed score"
    
    tier_data = person.profile_json["risk-tier-current"]
    assert tier_data["value"] == "high", "profile_json risk-tier-current must match computed tier"


def test_aml_risk_engine_writes_audit_event(db: Session):
    """Contract: AML_RISK engine writes AML_RISK_COMPUTED audit event"""
    # Create required field definitions
    field_specs = [
        ("country-of-residence", "Country of Residence", "string", "identity"),
        ("risk-score-current", "Risk Score Current", "number", "derived"),
        ("risk-tier-current", "Risk Tier Current", "string", "derived"),
        ("aml-flags", "AML Flags", "array", "derived"),
        ("aml-required-actions", "AML Required Actions", "array", "derived"),
    ]
    
    for slug, name, field_type, category in field_specs:
        field = db.query(FieldDefinition).filter(FieldDefinition.slug == slug).first()
        if not field:
            field = FieldDefinition(
                id=uuid.uuid4(),
                slug=slug,
                field_name_en=name,
                field_type=field_type,
                category=category,
                is_active=True,
            )
            db.add(field)
    db.flush()
    
    # Create AML risk config
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
                    value="FR",
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
    publish_jurisdiction_config(db=db, config_id=config.id)
    
    # Create person
    person = Person(
        id=uuid.uuid4(),
        status="active",
        jurisdiction="TEST",
        profile_json={},
    )
    db.add(person)
    db.flush()
    
    # Set field value
    from services.person_fields import set_person_field_value
    set_person_field_value(
        db=db,
        person_id=person.id,
        slug="country-of-residence",
        value="FR",
        actor_type="system",
    )
    
    # Count audit events before
    events_before = db.query(AuditEvent).filter(
        AuditEvent.person_id == person.id,
        AuditEvent.event_type == "AML_RISK_COMPUTED",
    ).count()
    
    # Compute risk
    result = compute_aml_risk(
        db=db,
        person_id=person.id,
        jurisdiction="TEST",
    )
    
    # Contract: AML_RISK_COMPUTED event must be written
    events_after = db.query(AuditEvent).filter(
        AuditEvent.person_id == person.id,
        AuditEvent.event_type == "AML_RISK_COMPUTED",
    ).count()
    
    assert events_after == events_before + 1, "Must write exactly one AML_RISK_COMPUTED event"
    
    # Verify event content
    event = db.query(AuditEvent).filter(
        AuditEvent.person_id == person.id,
        AuditEvent.event_type == "AML_RISK_COMPUTED",
    ).order_by(AuditEvent.created_at.desc()).first()
    
    assert event is not None, "AML_RISK_COMPUTED event must exist"
    assert event.person_id == person.id, "Event must reference correct person"
    assert event.actor_type == "system", "Event actor_type must be 'system'"
    
    payload = event.payload
    assert payload["jurisdiction"] == "TEST", "Event payload must contain jurisdiction"
    assert payload["config_id"] == str(config.id), "Event payload must contain config_id"
    assert payload["version"] == 1, "Event payload must contain version"
    assert payload["score"] == result["score"], "Event payload score must match computed score"
    assert payload["tier"] == result["tier"], "Event payload tier must match computed tier"
    assert "flags" in payload, "Event payload must contain flags"
    assert "required_actions" in payload, "Event payload must contain required_actions"
    assert "reasons" in payload, "Event payload must contain reasons"
