"""
Person field update service with audit trail
Event → State projection for client profile fields
"""
from sqlalchemy.orm import Session
from typing import Optional, Any
import uuid
from datetime import datetime

from database import Person, AuditEvent, FieldDefinition


def set_person_field_value(
    db: Session,
    person_id: uuid.UUID,
    slug: Optional[str] = None,
    field_definition_id: Optional[uuid.UUID] = None,
    value: Any = None,
    actor_type: str = "system",
    actor_id: Optional[str] = None,
    correlation_id: Optional[uuid.UUID] = None,
    auto_commit: bool = True,
) -> tuple[Person, AuditEvent]:
    """
    Set a field value for a person with mandatory audit trail.
    Event → State projection: writes audit_event then updates profile_json.
    
    Args:
        db: Database session
        person_id: UUID of person
        slug: Field slug (preferred) OR field_definition_id must be provided
        field_definition_id: UUID of field_definition (alternative to slug)
        value: Field value (JSON-serializable)
        actor_type: user|admin|system|provider
        actor_id: Optional actor identifier
        correlation_id: Optional correlation ID
        auto_commit: If True, commit immediately. If False, only flush (for batch operations)
    
    Returns:
        Tuple of (Person, AuditEvent)
    
    Raises:
        ValueError: If person/field not found, invalid actor_type, or type mismatch
    """
    # Validate actor_type
    valid_actor_types = {'user', 'admin', 'system', 'provider'}
    if actor_type not in valid_actor_types:
        raise ValueError(f"Invalid actor_type: {actor_type}. Must be one of {valid_actor_types}")
    
    # Load person (with lock to prevent concurrent updates)
    person = db.query(Person).filter(Person.id == person_id).with_for_update().first()
    if not person:
        raise ValueError(f"Person not found: {person_id}")
    
    # Load field definition
    if slug:
        field_def = db.query(FieldDefinition).filter(FieldDefinition.slug == slug).first()
        if not field_def:
            raise ValueError(f"Field definition not found for slug: {slug}")
    elif field_definition_id:
        field_def = db.query(FieldDefinition).filter(FieldDefinition.id == field_definition_id).first()
        if not field_def:
            raise ValueError(f"Field definition not found: {field_definition_id}")
    else:
        raise ValueError("Either slug or field_definition_id must be provided")
    
    if not field_def.is_active:
        raise ValueError(f"Field definition is not active: {field_def.slug}")
    
    # Basic type validation
    _validate_value_type(value, field_def.field_type)
    
    # Get current value from profile_json
    current_field_data = person.profile_json.get(field_def.slug) if person.profile_json else None
    old_value = current_field_data.get('value') if isinstance(current_field_data, dict) else current_field_data
    
    # Prepare new field data structure
    new_field_data = {
        "value": value,
        "field_definition_id": str(field_def.id),
        "field_type": field_def.field_type,
        "category": field_def.category,
        "source": {
            "actor_type": actor_type,
            "actor_id": actor_id,
        },
        "collected_at": datetime.utcnow().isoformat(),
    }
    
    # Create audit_event FIRST (before updating profile_json)
    audit_event = AuditEvent(
        id=uuid.uuid4(),
        person_id=person_id,
        event_type='FIELD_SET',
        actor_type=actor_type,
        actor_id=actor_id,
        correlation_id=correlation_id or uuid.uuid4(),
        payload={
            'slug': field_def.slug,
            'field_definition_id': str(field_def.id),
            'new_value': value,
            'old_value': old_value,
            'field_type': field_def.field_type,
            'category': field_def.category,
        },
        schema_version=1,
        created_at=datetime.utcnow()
    )
    db.add(audit_event)
    db.flush()
    
    # Update profile_json (state cache, not source of truth)
    new_profile_json = dict(person.profile_json) if person.profile_json else {}
    new_profile_json[field_def.slug] = new_field_data
    person.profile_json = new_profile_json
    
    # Update updated_at (application-level)
    person.updated_at = datetime.utcnow()
    
    if auto_commit:
        db.commit()
        db.refresh(person)
        db.refresh(audit_event)
    else:
        db.flush()
    
    return person, audit_event


def _validate_value_type(value: Any, field_type: str) -> None:
    """Basic type validation"""
    if field_type == 'string' and not isinstance(value, str):
        raise ValueError(f"Value must be string for field_type 'string', got {type(value).__name__}")
    elif field_type == 'date' and not isinstance(value, str):
        raise ValueError(f"Value must be string (ISO date) for field_type 'date', got {type(value).__name__}")
    elif field_type == 'datetime' and not isinstance(value, str):
        raise ValueError(f"Value must be string (ISO datetime) for field_type 'datetime', got {type(value).__name__}")
    elif field_type == 'boolean' and not isinstance(value, bool):
        raise ValueError(f"Value must be bool for field_type 'boolean', got {type(value).__name__}")
    elif field_type == 'number' and not isinstance(value, (int, float)):
        raise ValueError(f"Value must be number for field_type 'number', got {type(value).__name__}")
    elif field_type == 'enum' and not isinstance(value, str):
        raise ValueError(f"Value must be string for field_type 'enum', got {type(value).__name__}")
    elif field_type == 'array' and not isinstance(value, list):
        raise ValueError(f"Value must be list for field_type 'array', got {type(value).__name__}")
    elif field_type == 'json' and not isinstance(value, (dict, list)):
        raise ValueError(f"Value must be dict or list for field_type 'json', got {type(value).__name__}")
    elif field_type == 'file' and not isinstance(value, str):
        raise ValueError(f"Value must be string (file path/URL) for field_type 'file', got {type(value).__name__}")
