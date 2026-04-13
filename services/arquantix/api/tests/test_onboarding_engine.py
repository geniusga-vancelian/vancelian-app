"""
Tests for onboarding step engine
"""
import pytest
import uuid
from sqlalchemy.orm import Session

from database import Person, FieldDefinition, JurisdictionConfig
from services.jurisdiction_configs import create_jurisdiction_config, publish_jurisdiction_config
from services.onboarding_engine import get_next_step, submit_step
from schemas_jurisdiction import JurisdictionConfigSchema, Step, Block, Condition, ConditionExpression, ConditionAction


@pytest.fixture
def field_definitions(db: Session):
    """Create test field definitions"""
    slugs = ["first-name", "last-name", "email", "date-of-birth"]
    fields = []
    for slug in slugs:
        field = FieldDefinition(
            id=uuid.uuid4(),
            slug=slug,
            field_name_en=slug.replace("-", " ").title(),
            field_type="string" if slug != "date-of-birth" else "date",
            category="identity" if slug != "email" else "contact",
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
def jurisdiction_config(db: Session):
    """Create and publish a test jurisdiction config"""
    config_schema = JurisdictionConfigSchema(
        jurisdiction="FR",
        purpose="KYC",
        version=1,
        steps=[
            Step(
                step_id="step1",
                title_en="Personal Information",
                description_en="Enter your personal details",
                blocks=[
                    Block(
                        block_id="block1",
                        fields=["first-name", "last-name"],
                        layout="two_columns",
                        required=True,
                    ),
                ],
            ),
            Step(
                step_id="step2",
                title_en="Contact Information",
                description_en="Enter your contact details",
                blocks=[
                    Block(
                        block_id="block2",
                        fields=["email"],
                        layout="single_column",
                        required=True,
                        conditions=[
                            Condition(
                                when=ConditionExpression(
                                    field_slug="first-name",
                                    operator="exists",
                                    value=True,
                                ),
                                then=[
                                    ConditionAction(action="show_block", target="block2"),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
        status="draft",
    )
    
    config = create_jurisdiction_config(
        db=db,
        jurisdiction="FR",
        purpose="KYC",
        config_json=config_schema,
    )
    
    published = publish_jurisdiction_config(db=db, config_id=config.id)
    return published


def test_get_next_step_returns_first_step(db: Session, person: Person, jurisdiction_config: JurisdictionConfig):
    """Test that next-step returns step1 when profile is empty"""
    result = get_next_step(db=db, person_id=person.id, jurisdiction="FR", purpose="KYC")
    
    assert result["config_id"] == str(jurisdiction_config.id)
    assert result["step"] is not None
    assert result["step"]["step_id"] == "step1"
    assert len(result["step"]["blocks"]) == 1
    assert result["completion"]["completed"] is False


def test_submit_step_creates_audit_events(db: Session, person: Person, jurisdiction_config: JurisdictionConfig):
    """Test that submit-step creates audit events and updates profile_json"""
    result = submit_step(
        db=db,
        person_id=person.id,
        step_id="step1",
        values={"first-name": "John", "last-name": "Doe"},
        jurisdiction="FR",
        purpose="KYC",
    )
    
    assert len(result["audit_event_ids"]) == 2
    assert result["next_step"] is not None
    assert result["next_step"]["step_id"] == "step2"
    
    db.refresh(person)
    assert person.profile_json["first-name"]["value"] == "John"
    assert person.profile_json["last-name"]["value"] == "Doe"


def test_next_step_returns_step2_after_step1_completed(
    db: Session, person: Person, jurisdiction_config: JurisdictionConfig
):
    """Test that next-step returns step2 after step1 is completed"""
    # Complete step1
    submit_step(
        db=db,
        person_id=person.id,
        step_id="step1",
        values={"first-name": "John", "last-name": "Doe"},
        jurisdiction="FR",
        purpose="KYC",
    )
    
    # Get next step
    result = get_next_step(db=db, person_id=person.id, jurisdiction="FR", purpose="KYC")
    
    assert result["step"] is not None
    assert result["step"]["step_id"] == "step2"
    assert result["completion"]["completed"] is False


def test_next_step_returns_none_when_all_completed(
    db: Session, person: Person, jurisdiction_config: JurisdictionConfig
):
    """Test that next-step returns None when all steps are completed"""
    # Complete step1
    submit_step(
        db=db,
        person_id=person.id,
        step_id="step1",
        values={"first-name": "John", "last-name": "Doe"},
        jurisdiction="FR",
        purpose="KYC",
    )
    
    # Complete step2
    submit_step(
        db=db,
        person_id=person.id,
        step_id="step2",
        values={"email": "john@example.com"},
        jurisdiction="FR",
        purpose="KYC",
    )
    
    # Get next step
    result = get_next_step(db=db, person_id=person.id, jurisdiction="FR", purpose="KYC")
    
    assert result["step"] is None
    assert result["completion"]["completed"] is True


def test_condition_hides_block(db: Session, person: Person):
    """Test that condition evaluation hides blocks based on field values"""
    # Create config with conditional block
    config_schema = JurisdictionConfigSchema(
        jurisdiction="FR",
        purpose="KYC",
        version=1,
        steps=[
            Step(
                step_id="step1",
                title_en="Step 1",
                blocks=[
                    Block(
                        block_id="block1",
                        fields=["first-name", "last-name"],  # Two fields so block1 isn't complete with just first-name
                        layout="single_column",
                        required=True,
                    ),
                    Block(
                        block_id="block2",
                        fields=["email"],
                        layout="single_column",
                        required=False,
                        conditions=[
                            Condition(
                                when=ConditionExpression(
                                    field_slug="first-name",
                                    operator="equals",
                                    value="John",
                                ),
                                then=[
                                    ConditionAction(action="hide_block", target="block2"),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        ],
        status="draft",
    )
    
    config = create_jurisdiction_config(
        db=db,
        jurisdiction="FR",
        purpose="KYC",
        config_json=config_schema,
    )
    publish_jurisdiction_config(db=db, config_id=config.id)
    
    # First, check next step before setting first-name - both blocks should be visible
    result = get_next_step(db=db, person_id=person.id, jurisdiction="FR", purpose="KYC")
    assert result["step"] is not None
    visible_blocks = result["step"]["blocks"]
    block_ids = [b["block_id"] for b in visible_blocks]
    assert "block1" in block_ids
    assert "block2" in block_ids  # Visible initially
    
    # Set first-name to "Jane" first (should NOT hide block2)
    from services.person_fields import set_person_field_value
    set_person_field_value(
        db=db,
        person_id=person.id,
        slug="first-name",
        value="Jane",  # This should NOT trigger condition (only "John" hides block2)
        actor_type="system",
    )
    
    # Get next step - block2 should still be visible
    result = get_next_step(db=db, person_id=person.id, jurisdiction="FR", purpose="KYC")
    assert result["step"] is not None  # Step incomplete (block1 needs last-name too)
    visible_blocks = result["step"]["blocks"]
    block_ids = [b["block_id"] for b in visible_blocks]
    assert "block1" in block_ids
    assert "block2" in block_ids  # Still visible because first-name != "John"
    
    # Now set first-name to "John" (should hide block2)
    set_person_field_value(
        db=db,
        person_id=person.id,
        slug="first-name",
        value="John",  # This should trigger condition to hide block2
        actor_type="system",
    )
    
    # Get next step - block2 should be hidden now
    result = get_next_step(db=db, person_id=person.id, jurisdiction="FR", purpose="KYC")
    assert result["step"] is not None  # Step still incomplete (block1 needs last-name)
    visible_blocks = result["step"]["blocks"]
    block_ids = [b["block_id"] for b in visible_blocks]
    assert "block1" in block_ids
    assert "block2" not in block_ids  # Hidden because first-name == "John"


def test_submit_step_atomic_rollback_on_validation_error(db: Session, person: Person, jurisdiction_config: JurisdictionConfig):
    """Test that submit_step rolls back all field writes atomically on validation error"""
    from database import AuditEvent
    
    # Capture initial state
    initial_profile_json = dict(person.profile_json) if person.profile_json else {}
    initial_audit_count = db.query(AuditEvent).filter(AuditEvent.person_id == person.id).count()
    
    # Attempt to submit step with one valid and one invalid field value
    # first-name is valid (string), but date-of-birth should be a string (ISO date) not a number
    with pytest.raises(ValueError, match="Value must be string"):
        submit_step(
            db=db,
            person_id=person.id,
            step_id="step1",
            values={
                "first-name": "John",  # Valid
                "last-name": 123,  # Invalid: should be string, not number
            },
            jurisdiction="FR",
            purpose="KYC",
        )
    
    # Verify rollback: no audit events committed
    db.refresh(person)
    final_audit_count = db.query(AuditEvent).filter(AuditEvent.person_id == person.id).count()
    assert final_audit_count == initial_audit_count, "No audit events should be committed on rollback"
    
    # Verify rollback: profile_json unchanged
    final_profile_json = person.profile_json or {}
    assert final_profile_json == initial_profile_json, "profile_json should be unchanged after rollback"
    
    # Verify first-name was not written
    assert "first-name" not in final_profile_json, "first-name should not be in profile_json after rollback"
