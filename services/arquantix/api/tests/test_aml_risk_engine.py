"""
Tests for AML risk scoring engine
"""
import pytest
import uuid
from sqlalchemy.orm import Session

from database import Person, FieldDefinition, JurisdictionConfig, AuditEvent
from services.jurisdiction_configs import create_jurisdiction_config, publish_jurisdiction_config
from services.aml_risk_engine import compute_aml_risk, get_latest_risk
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
    """Create or update test field definitions"""
    field_specs = [
        ("country-of-residence", "Country of Residence", "string", "identity"),
        ("pep-status", "PEP Status", "enum", "aml"),
        ("vpn-detected", "VPN Detected", "boolean", "security"),
        ("risk-score-current", "Risk Score Current", "number", "derived"),
        ("risk-tier-current", "Risk Tier Current", "string", "derived"),
        ("aml-flags", "AML Flags", "array", "derived"),
        ("aml-required-actions", "AML Required Actions", "array", "derived"),
    ]
    fields = []
    for slug, name, field_type, category in field_specs:
        field = db.query(FieldDefinition).filter(FieldDefinition.slug == slug).first()
        if field:
            # Update existing field if type/category differs
            if field.field_type != field_type or field.category != category:
                field.field_type = field_type
                field.category = category
                field.field_name_en = name
        else:
            field = FieldDefinition(
                id=uuid.uuid4(),
                slug=slug,
                field_name_en=name,
                field_type=field_type,
                category=category,
                is_active=True,
            )
            db.add(field)
        fields.append(field)
    db.flush()
    return fields


@pytest.fixture
def person(db: Session):
    """Create a test person"""
    p = Person(
        id=uuid.uuid4(),
        status="active",
        jurisdiction="FR",
        profile_json={},
    )
    db.add(p)
    db.flush()
    return p


@pytest.fixture
def aml_risk_config(db: Session):
    """Create and publish a test AML risk config"""
    config_schema = AMLRiskConfig(
        jurisdiction="FR",
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
                    add_score=30,
                    set_flag="HIGH_RISK_COUNTRY",
                ),
            ),
            AMLRiskRule(
                rule_id="rule2",
                description_en="PEP detected",
                when=AMLRiskCondition(
                    field_slug="pep-status",
                    operator="equals",
                    value="yes",
                ),
                effect=AMLRiskEffect(
                    add_score=40,
                    set_flag="PEP",
                    require_action="MANUAL_REVIEW",
                ),
            ),
            AMLRiskRule(
                rule_id="rule3",
                description_en="VPN detected",
                when=AMLRiskCondition(
                    field_slug="vpn-detected",
                    operator="equals",
                    value=True,
                ),
                effect=AMLRiskEffect(
                    add_score=10,
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
        jurisdiction="FR",
        purpose="AML_RISK",
        config_json=config_schema,
    )
    
    published = publish_jurisdiction_config(db=db, config_id=config.id)
    return published


def test_basic_scoring(db: Session, person: Person, field_definitions, aml_risk_config: JurisdictionConfig):
    """Test basic scoring with one matching rule"""
    # Set field value
    from services.person_fields import set_person_field_value
    set_person_field_value(
        db=db,
        person_id=person.id,
        slug="country-of-residence",
        value="XX",
    )
    
    # Compute risk
    result = compute_aml_risk(
        db=db,
        person_id=person.id,
        jurisdiction="FR",
    )
    
    assert result["score"] == 30
    assert result["tier"] == "low"  # Score 30 is in the low tier (0-30)
    assert "HIGH_RISK_COUNTRY" in result["flags"]
    assert len(result["reasons"]) == 1
    assert result["reasons"][0]["rule_id"] == "rule1"


def test_negative_score_rule(db: Session, person: Person, field_definitions):
    """Test negative score rule"""
    config_schema = AMLRiskConfig(
        jurisdiction="FR",
        purpose="AML_RISK",
        version=1,
        status="draft",
        rules=[
            AMLRiskRule(
                rule_id="rule_negative",
                description_en="Low risk indicator",
                when=AMLRiskCondition(
                    field_slug="country-of-residence",
                    operator="equals",
                    value="FR",
                ),
                effect=AMLRiskEffect(
                    add_score=-10,
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
        jurisdiction="FR",
        purpose="AML_RISK",
        config_json=config_schema,
    )
    publish_jurisdiction_config(db=db, config_id=config.id)
    
    from services.person_fields import set_person_field_value
    set_person_field_value(
        db=db,
        person_id=person.id,
        slug="country-of-residence",
        value="FR",
    )
    
    result = compute_aml_risk(
        db=db,
        person_id=person.id,
        jurisdiction="FR",
    )
    
    assert result["score"] == 0  # Bounded to min_score


def test_stop_rule_short_circuit(db: Session, person: Person, field_definitions):
    """Test that stop rule prevents further evaluation"""
    config_schema = AMLRiskConfig(
        jurisdiction="FR",
        purpose="AML_RISK",
        version=1,
        status="draft",
        rules=[
            AMLRiskRule(
                rule_id="rule_stop",
                description_en="Critical stop",
                when=AMLRiskCondition(
                    field_slug="pep-status",
                    operator="equals",
                    value="yes",
                ),
                effect=AMLRiskEffect(
                    add_score=50,
                    stop=True,
                ),
            ),
            AMLRiskRule(
                rule_id="rule_after_stop",
                description_en="Should not execute",
                when=AMLRiskCondition(
                    field_slug="vpn-detected",
                    operator="equals",
                    value=True,
                ),
                effect=AMLRiskEffect(
                    add_score=20,
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
        jurisdiction="FR",
        purpose="AML_RISK",
        config_json=config_schema,
    )
    publish_jurisdiction_config(db=db, config_id=config.id)
    
    from services.person_fields import set_person_field_value
    set_person_field_value(
        db=db,
        person_id=person.id,
        slug="pep-status",
        value="yes",
    )
    set_person_field_value(
        db=db,
        person_id=person.id,
        slug="vpn-detected",
        value=True,
    )
    
    result = compute_aml_risk(
        db=db,
        person_id=person.id,
        jurisdiction="FR",
    )
    
    assert result["score"] == 50
    assert len(result["reasons"]) == 1
    assert result["reasons"][0]["rule_id"] == "rule_stop"


def test_bounding_min_max(db: Session, person: Person, field_definitions):
    """Test score bounding to min/max"""
    config_schema = AMLRiskConfig(
        jurisdiction="FR",
        purpose="AML_RISK",
        version=1,
        status="draft",
        rules=[
            AMLRiskRule(
                rule_id="rule_high",
                description_en="Very high score",
                when=AMLRiskCondition(
                    field_slug="pep-status",
                    operator="exists",
                    value=True,
                ),
                effect=AMLRiskEffect(
                    add_score=200,  # Exceeds max_score
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
        jurisdiction="FR",
        purpose="AML_RISK",
        config_json=config_schema,
    )
    publish_jurisdiction_config(db=db, config_id=config.id)
    
    from services.person_fields import set_person_field_value
    set_person_field_value(
        db=db,
        person_id=person.id,
        slug="pep-status",
        value="yes",
    )
    
    result = compute_aml_risk(
        db=db,
        person_id=person.id,
        jurisdiction="FR",
    )
    
    assert result["score"] == 100  # Bounded to max_score
    assert result["tier"] == "high"


def test_tier_resolution(db: Session, person: Person, field_definitions, aml_risk_config: JurisdictionConfig):
    """Test tier resolution"""
    from services.person_fields import set_person_field_value
    
    # Low tier
    set_person_field_value(
        db=db,
        person_id=person.id,
        slug="vpn-detected",
        value=True,
    )
    result = compute_aml_risk(
        db=db,
        person_id=person.id,
        jurisdiction="FR",
    )
    assert result["tier"] == "low"
    
    # Medium tier
    set_person_field_value(
        db=db,
        person_id=person.id,
        slug="country-of-residence",
        value="XX",
    )
    result = compute_aml_risk(
        db=db,
        person_id=person.id,
        jurisdiction="FR",
    )
    assert result["tier"] == "medium"
    
    # High tier
    set_person_field_value(
        db=db,
        person_id=person.id,
        slug="pep-status",
        value="yes",
    )
    result = compute_aml_risk(
        db=db,
        person_id=person.id,
        jurisdiction="FR",
    )
    assert result["tier"] == "high"


def test_audit_event_written(db: Session, person: Person, field_definitions, aml_risk_config: JurisdictionConfig):
    """Test that audit event is written"""
    from services.person_fields import set_person_field_value
    set_person_field_value(
        db=db,
        person_id=person.id,
        slug="pep-status",
        value="yes",
    )
    
    result = compute_aml_risk(
        db=db,
        person_id=person.id,
        jurisdiction="FR",
    )
    
    # Check audit event
    event = db.query(AuditEvent).filter(AuditEvent.id == uuid.UUID(result["audit_event_id"])).first()
    assert event is not None
    assert event.event_type == "AML_RISK_COMPUTED"
    assert event.payload["score"] == result["score"]
    assert event.payload["tier"] == result["tier"]
    assert event.payload["config_id"] == result["config_id"]


def test_profile_json_derived_fields_updated(db: Session, person: Person, field_definitions, aml_risk_config: JurisdictionConfig):
    """Test that derived fields are updated in profile_json"""
    from services.person_fields import set_person_field_value
    set_person_field_value(
        db=db,
        person_id=person.id,
        slug="pep-status",
        value="yes",
    )
    
    result = compute_aml_risk(
        db=db,
        person_id=person.id,
        jurisdiction="FR",
    )
    
    db.refresh(person)
    profile_json = person.profile_json
    
    # Check derived fields
    assert profile_json["risk-score-current"]["value"] == result["score"]
    assert profile_json["risk-tier-current"]["value"] == result["tier"]
    assert profile_json["aml-flags"]["value"] == result["flags"]
    assert profile_json["aml-required-actions"]["value"] == result["required_actions"]


def test_get_latest_risk(db: Session, person: Person, field_definitions, aml_risk_config: JurisdictionConfig):
    """Test get_latest_risk endpoint"""
    from services.person_fields import set_person_field_value
    set_person_field_value(
        db=db,
        person_id=person.id,
        slug="pep-status",
        value="yes",
    )
    
    compute_aml_risk(
        db=db,
        person_id=person.id,
        jurisdiction="FR",
    )
    
    latest = get_latest_risk(db=db, person_id=person.id)
    
    assert latest["risk_score_current"] is not None
    assert latest["risk_tier_current"] is not None
    assert isinstance(latest["aml_flags"], list)
    assert isinstance(latest["aml_required_actions"], list)
    assert latest["last_computed_at"] is not None
    assert latest["last_config_version"] == 1
