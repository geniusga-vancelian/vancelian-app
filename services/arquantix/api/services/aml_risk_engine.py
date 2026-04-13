"""
AML Risk Scoring Engine
Reuses condition evaluator from onboarding_engine
"""
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime

from database import Person, AuditEvent
from services.jurisdiction_configs import get_active_config
from services.onboarding_engine import evaluate_condition
from services.person_fields import set_person_field_value
from schemas_aml_risk import AMLRiskConfig


def compute_aml_risk(
    db: Session,
    person_id: uuid.UUID,
    jurisdiction: str,
    correlation_id: Optional[uuid.UUID] = None,
    actor_type: str = "system",
    actor_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute AML risk score for a person.
    Returns computed risk data and writes audit event + projects to profile_json.
    """
    person = db.query(Person).filter(Person.id == person_id).with_for_update().first()
    if not person:
        raise ValueError(f"Person not found: {person_id}")
    
    config = get_active_config(db=db, jurisdiction=jurisdiction, purpose="AML_RISK")
    if not config:
        raise ValueError(f"No active AML_RISK config found for jurisdiction={jurisdiction}")
    
    config_schema = AMLRiskConfig(**config.config_json)
    profile_json = person.profile_json or {}
    
    # Initialize scoring state
    score = 0
    flags = []
    required_actions = []
    reasons = []
    stopped = False
    
    # Evaluate rules in order
    for rule in config_schema.rules:
        if stopped:
            break
        
        # Evaluate condition using existing evaluator
        condition_dict = rule.when.model_dump()
        matches = evaluate_condition(condition_dict, profile_json)
        
        if matches:
            # Apply effect
            effect = rule.effect
            score_delta = int(effect.add_score * rule.weight)
            score += score_delta
            
            if effect.set_flag:
                flags.append(effect.set_flag)
            
            if effect.require_action:
                required_actions.append(effect.require_action)
            
            if effect.stop:
                stopped = True
            
            # Capture reason
            field_slug = rule.when.field_slug
            field_data = profile_json.get(field_slug)
            value_snapshot = field_data.get("value") if isinstance(field_data, dict) else field_data
            
            reasons.append({
                "rule_id": rule.rule_id,
                "description_en": rule.description_en,
                "slug": field_slug,
                "value_snapshot": value_snapshot,
                "score_delta": score_delta,
                "flags_added": [effect.set_flag] if effect.set_flag else [],
                "actions_added": [effect.require_action] if effect.require_action else [],
            })
    
    # Bound score
    min_score = config_schema.outputs.min_score
    max_score = config_schema.outputs.max_score
    score = max(min_score, min(max_score, score))
    
    # Resolve tier
    tier = "low"
    for tier_def in config_schema.outputs.tiers:
        if tier_def.min <= score <= tier_def.max:
            tier = tier_def.tier
            break
    
    # Deduplicate flags and actions
    flags = list(set(flags))
    required_actions = list(set(required_actions))
    
    # Create audit event
    audit_event = AuditEvent(
        id=uuid.uuid4(),
        person_id=person_id,
        event_type="AML_RISK_COMPUTED",
        actor_type=actor_type,
        actor_id=actor_id,
        correlation_id=correlation_id or uuid.uuid4(),
        payload={
            "jurisdiction": jurisdiction,
            "config_id": str(config.id),
            "version": config.version,
            "score": score,
            "tier": tier,
            "flags": flags,
            "required_actions": required_actions,
            "reasons": reasons,
        },
        schema_version=1,
        created_at=datetime.utcnow(),
    )
    db.add(audit_event)
    db.flush()
    
    # Project derived fields into profile_json using same envelope as FIELD_SET
    # Get field definitions for derived fields
    from database import FieldDefinition
    
    derived_fields = {
        "risk-score-current": float(score),
        "risk-tier-current": tier,
        "aml-flags": flags,
        "aml-required-actions": required_actions,
    }
    
    new_profile_json = dict(person.profile_json) if person.profile_json else {}
    
    for slug, value in derived_fields.items():
        field_def = db.query(FieldDefinition).filter(FieldDefinition.slug == slug).first()
        if field_def:
            new_profile_json[slug] = {
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
    
    person.profile_json = new_profile_json
    person.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(audit_event)
    
    return {
        "person_id": str(person_id),
        "jurisdiction": jurisdiction,
        "config_id": str(config.id),
        "version": config.version,
        "score": score,
        "tier": tier,
        "flags": flags,
        "required_actions": required_actions,
        "reasons": reasons,
        "audit_event_id": str(audit_event.id),
    }


def get_latest_risk(
    db: Session,
    person_id: uuid.UUID,
) -> Dict[str, Any]:
    """
    Get latest risk data from profile_json derived fields and last audit event.
    """
    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise ValueError(f"Person not found: {person_id}")
    
    profile_json = person.profile_json or {}
    
    # Extract derived fields
    risk_score_data = profile_json.get("risk-score-current")
    risk_score = risk_score_data.get("value") if isinstance(risk_score_data, dict) else risk_score_data
    
    risk_tier_data = profile_json.get("risk-tier-current")
    risk_tier = risk_tier_data.get("value") if isinstance(risk_tier_data, dict) else risk_tier_data
    
    aml_flags_data = profile_json.get("aml-flags")
    aml_flags = aml_flags_data.get("value") if isinstance(aml_flags_data, dict) else (aml_flags_data if isinstance(aml_flags_data, list) else [])
    
    aml_actions_data = profile_json.get("aml-required-actions")
    aml_actions = aml_actions_data.get("value") if isinstance(aml_actions_data, dict) else (aml_actions_data if isinstance(aml_actions_data, list) else [])
    
    # Get last AML_RISK_COMPUTED event
    last_event = db.query(AuditEvent).filter(
        AuditEvent.person_id == person_id,
        AuditEvent.event_type == "AML_RISK_COMPUTED",
    ).order_by(AuditEvent.created_at.desc()).first()
    
    last_computed_at = last_event.created_at.isoformat() if last_event else None
    last_config_version = last_event.payload.get("version") if last_event and last_event.payload else None
    
    return {
        "person_id": str(person_id),
        "risk_score_current": float(risk_score) if risk_score is not None else None,
        "risk_tier_current": risk_tier,
        "aml_flags": aml_flags if isinstance(aml_flags, list) else [],
        "aml_required_actions": aml_actions if isinstance(aml_actions, list) else [],
        "last_computed_at": last_computed_at,
        "last_config_version": last_config_version,
    }
