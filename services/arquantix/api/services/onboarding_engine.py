"""
Onboarding step engine
Evaluates conditions and determines next step
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
import uuid

from database import Person, FieldDefinition
from services.jurisdiction_configs import get_active_config
from services.person_fields import set_person_field_value
from schemas_jurisdiction import JurisdictionConfigSchema, ConditionExpression, ConditionAction


def evaluate_condition(expression: Dict[str, Any], profile_json: Dict[str, Any]) -> bool:
    """
    Evaluate a condition expression against profile_json.
    """
    field_slug = expression["field_slug"]
    operator = expression["operator"]
    expected_value = expression["value"]
    
    # Get field value from profile_json
    field_data = profile_json.get(field_slug)
    actual_value = field_data.get("value") if isinstance(field_data, dict) else field_data
    
    if operator == "equals":
        return actual_value == expected_value
    elif operator == "not_equals":
        return actual_value != expected_value
    elif operator == "in":
        return actual_value in expected_value if isinstance(expected_value, list) else False
    elif operator == "not_in":
        return actual_value not in expected_value if isinstance(expected_value, list) else True
    elif operator == "exists":
        return actual_value is not None
    elif operator == "not_exists":
        return actual_value is None
    else:
        return False


def evaluate_block_visibility(block: Dict[str, Any], profile_json: Dict[str, Any]) -> bool:
    """
    Evaluate if a block should be visible based on conditions.
    Default: visible unless explicitly hidden.
    """
    if not block.get("conditions"):
        return True
    
    # Evaluate all conditions for this block
    for condition in block["conditions"]:
        when = condition["when"]
        if evaluate_condition(when, profile_json):
            # Condition is true, check actions
            for action in condition["then"]:
                if action["action"] == "hide_block" and action["target"] == block["block_id"]:
                    return False
                elif action["action"] == "show_block" and action["target"] == block["block_id"]:
                    return True
    
    # Default: visible if no conditions match or no explicit hide action
    return True


def is_field_completed(field_slug: str, profile_json: Dict[str, Any]) -> bool:
    """
    Check if a field has a non-null value.
    """
    field_data = profile_json.get(field_slug)
    if not field_data:
        return False
    value = field_data.get("value") if isinstance(field_data, dict) else field_data
    return value is not None


def get_next_step(
    db: Session,
    person_id: uuid.UUID,
    jurisdiction: str,
    purpose: str,
) -> Dict[str, Any]:
    """
    Get the next step for a person's onboarding.
    Returns step with only visible blocks and fields.
    """
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise ValueError(f"Person not found: {person_id}")
    
    config = get_active_config(db, jurisdiction, purpose)
    if not config:
        raise ValueError(f"No active config found for jurisdiction={jurisdiction}, purpose={purpose}")
    
    config_schema = JurisdictionConfigSchema(**config.config_json)
    profile_json = person.profile_json or {}
    
    # Find next incomplete step
    for step in config_schema.steps:
        visible_blocks = []
        step_completed = True
        
        for block in step.blocks:
            if not evaluate_block_visibility(block.model_dump(), profile_json):
                continue
            
            visible_blocks.append(block)
            
            # Check if all required fields in this block are completed
            for field_slug in block.fields:
                if block.required and not is_field_completed(field_slug, profile_json):
                    step_completed = False
        
        # If step has visible blocks and is not completed, return it
        if len(visible_blocks) > 0 and not step_completed:
            # Return this step with only visible blocks
            return {
                "config_id": str(config.id),
                "version": config.version,
                "step": {
                    "step_id": step.step_id,
                    "title_en": step.title_en,
                    "description_en": step.description_en,
                    "blocks": [
                        {
                            "block_id": b.block_id,
                            "fields": b.fields,
                            "layout": b.layout,
                            "required": b.required,
                        }
                        for b in visible_blocks
                    ],
                },
                "completion": {
                    "current_step": step.step_id,
                    "total_steps": len(config_schema.steps),
                    "completed": False,
                },
            }
    
    # All steps completed
    return {
        "config_id": str(config.id),
        "version": config.version,
        "step": None,
        "completion": {
            "total_steps": len(config_schema.steps),
            "completed": True,
        },
    }


def submit_step(
    db: Session,
    person_id: uuid.UUID,
    step_id: str,
    values: Dict[str, Any],
    jurisdiction: str,
    purpose: str,
    actor_type: str = "user",
    actor_id: Optional[str] = None,
    correlation_id: Optional[uuid.UUID] = None,
) -> Dict[str, Any]:
    """
    Submit step values and return next step.
    """
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise ValueError(f"Person not found: {person_id}")
    
    config = get_active_config(db, jurisdiction, purpose)
    if not config:
        raise ValueError(f"No active config found for jurisdiction={jurisdiction}, purpose={purpose}")
    
    config_schema = JurisdictionConfigSchema(**config.config_json)
    profile_json = person.profile_json or {}
    
    # Find the step
    step = next((s for s in config_schema.steps if s.step_id == step_id), None)
    if not step:
        raise ValueError(f"Step not found: {step_id}")
    
    # Get visible blocks for this step
    visible_blocks = []
    for block in step.blocks:
        if evaluate_block_visibility(block.model_dump(), profile_json):
            visible_blocks.append(block)
    
    # Validate submitted slugs exist in visible blocks
    valid_slugs = set()
    for block in visible_blocks:
        valid_slugs.update(block.fields)
    
    submitted_slugs = set(values.keys())
    invalid_slugs = submitted_slugs - valid_slugs
    if invalid_slugs:
        raise ValueError(f"Invalid field slugs: {invalid_slugs}. Valid slugs for this step: {valid_slugs}")
    
    # Validate slugs exist in field_definitions
    for slug in submitted_slugs:
        field_def = db.query(FieldDefinition).filter(FieldDefinition.slug == slug).first()
        if not field_def:
            raise ValueError(f"Field definition not found for slug: {slug}")
    
    # Submit each field value (creates audit event + updates profile_json)
    # All writes happen in a single transaction for atomicity
    audit_event_ids = []
    try:
        for slug, value in values.items():
            updated_person, audit_event = set_person_field_value(
                db=db,
                person_id=person_id,
                slug=slug,
                value=value,
                actor_type=actor_type,
                actor_id=actor_id,
                correlation_id=correlation_id,
                auto_commit=False,  # Defer commit until all fields processed
            )
            audit_event_ids.append(str(audit_event.id))
        
        # Commit all field writes atomically
        db.commit()
        
        # Refresh person to get latest state
        db.refresh(person)
        
        # Get next step
        next_step_result = get_next_step(db, person_id, jurisdiction, purpose)
        
        return {
            "person_id": str(person_id),
            "step_id": step_id,
            "audit_event_ids": audit_event_ids,
            "next_step": next_step_result.get("step"),
            "completion": next_step_result.get("completion"),
        }
    except Exception:
        # Rollback entire transaction on any error
        db.rollback()
        raise
