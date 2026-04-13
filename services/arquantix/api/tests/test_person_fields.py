"""
Tests for person field update service
"""
import pytest
import uuid
from datetime import datetime
from sqlalchemy.orm import Session

from database import Person, AuditEvent, FieldDefinition
from services.person_fields import set_person_field_value


@pytest.fixture
def field_definition(db: Session):
    """Create or get a test field definition"""
    # Check if field exists in current transaction scope
    field = db.query(FieldDefinition).filter(FieldDefinition.slug == "first-name").first()
    if not field:
        field = FieldDefinition(
            id=uuid.uuid4(),
            slug="first-name",
            field_name_en="First Name",
            field_type="string",
            category="identity",
            is_active=True,
        )
        db.add(field)
        db.flush()
    return field


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


def test_set_field_creates_audit_event(db: Session, person: Person, field_definition: FieldDefinition):
    """Test that setting a field creates an audit event"""
    person, audit_event = set_person_field_value(
        db=db,
        person_id=person.id,
        slug="first-name",
        value="John",
        actor_type="admin",
        actor_id="admin@test.com",
    )
    
    assert audit_event is not None
    assert audit_event.event_type == "FIELD_SET"
    assert audit_event.person_id == person.id
    assert audit_event.actor_type == "admin"
    assert audit_event.actor_id == "admin@test.com"
    assert audit_event.payload["slug"] == "first-name"
    assert audit_event.payload["new_value"] == "John"
    assert audit_event.payload["field_definition_id"] == str(field_definition.id)
    assert audit_event.payload["field_type"] == "string"
    assert audit_event.payload["category"] == "identity"


def test_set_field_updates_profile_json(db: Session, person: Person, field_definition: FieldDefinition):
    """Test that setting a field updates profile_json correctly"""
    person, _ = set_person_field_value(
        db=db,
        person_id=person.id,
        slug="first-name",
        value="John",
        actor_type="admin",
    )
    
    db.refresh(person)
    assert "first-name" in person.profile_json
    
    field_data = person.profile_json["first-name"]
    assert field_data["value"] == "John"
    assert field_data["field_definition_id"] == str(field_definition.id)
    assert field_data["field_type"] == "string"
    assert field_data["category"] == "identity"
    assert field_data["source"]["actor_type"] == "admin"
    assert "collected_at" in field_data


def test_set_field_with_field_definition_id(db: Session, person: Person, field_definition: FieldDefinition):
    """Test that setting a field works with field_definition_id instead of slug"""
    person, audit_event = set_person_field_value(
        db=db,
        person_id=person.id,
        field_definition_id=field_definition.id,
        value="Jane",
        actor_type="user",
    )
    
    assert audit_event.payload["slug"] == "first-name"
    assert person.profile_json["first-name"]["value"] == "Jane"


def test_set_field_allows_multiple_events(db: Session, person: Person, field_definition: FieldDefinition):
    """Test that multiple FIELD_SET events are allowed (no idempotency enforcement)"""
    # Set field first time
    person, event1 = set_person_field_value(
        db=db,
        person_id=person.id,
        slug="first-name",
        value="John",
        actor_type="admin",
    )
    
    # Set field second time (should create new event)
    person, event2 = set_person_field_value(
        db=db,
        person_id=person.id,
        slug="first-name",
        value="Jane",
        actor_type="admin",
    )
    
    assert event1.id != event2.id
    assert event2.payload["old_value"] == "John"
    assert event2.payload["new_value"] == "Jane"
    assert person.profile_json["first-name"]["value"] == "Jane"


def test_set_field_validates_type(db: Session, person: Person, field_definition: FieldDefinition):
    """Test that type validation works"""
    with pytest.raises(ValueError, match="Value must be string"):
        set_person_field_value(
            db=db,
            person_id=person.id,
            slug="first-name",
            value=123,  # Wrong type
            actor_type="admin",
        )


def test_set_field_validates_person_exists(db: Session, field_definition: FieldDefinition):
    """Test that setting field on non-existent person raises error"""
    fake_id = uuid.uuid4()
    with pytest.raises(ValueError, match="Person not found"):
        set_person_field_value(
            db=db,
            person_id=fake_id,
            slug="first-name",
            value="John",
            actor_type="admin",
        )


def test_set_field_validates_field_exists(db: Session, person: Person):
    """Test that setting non-existent field raises error"""
    with pytest.raises(ValueError, match="Field definition not found"):
        set_person_field_value(
            db=db,
            person_id=person.id,
            slug="non-existent-field",
            value="test",
            actor_type="admin",
        )


def test_set_field_validates_actor_type(db: Session, person: Person, field_definition: FieldDefinition):
    """Test that invalid actor_type raises error"""
    with pytest.raises(ValueError, match="Invalid actor_type"):
        set_person_field_value(
            db=db,
            person_id=person.id,
            slug="first-name",
            value="John",
            actor_type="invalid",
        )
