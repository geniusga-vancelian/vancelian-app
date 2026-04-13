"""Registration execution event taxonomy + safe emit path (production).

Append-only audit trail. All emissions MUST use ``safe_log_registration_event`` (or the
alias ``emit_registration_execution_event``). Inserts run inside a SAVEPOINT so failures
never poison the parent transaction used by the registration runtime.

Payload contracts (minimal keys; optional keys allowed):

- registration.flow.version_locked: flow_id, flow_version, flow_name, jurisdiction
- registration.session.started: jurisdiction, flow_name, flow_version, entrypoint_type
- registration.session.resumed: (reserved — emit when resume API exists)
- registration.session.completed: person_id, projected_fields (list), status
- registration.session.abandoned: (reserved)
- registration.screen.entered: step_key, step_title, screen_key, screen_title
- registration.screen.submitted: screen_key, field_slugs_count
- registration.fields.submitted: field_slugs, masked_values, screen_key
- registration.validation.failed: screen_key, reason, errors
- registration.phone.validated: phone_validation_event, field_slug, result, error_code, risk_signal (masked)
- registration.navigation.next / prev: from/to keys and ids
- registration.step.completed: step_key, step_title
- registration.step.skipped: (reserved)
- registration.step.blocked: step_key, reason, blocking_step_key
- registration.projection.completed: person_id, projected_fields (list)
- registration.rule.evaluated: batch_source, evaluations (list)
- registration.runtime.error: message, where (optional)

Address step / Places (product observability — optional future emissions):

- registration.address.autocomplete_used: screen_key, session_id (hashed), source hint
- registration.address.manual_fallback: screen_key
- registration.address.hybrid_or_override: screen_key (see FIELDS_SUBMITTED address_sources_summary)
- registration.address.details_failed: screen_key, error_class (no place_id)
- registration.address.rate_limited: route (autocomplete|details), screen_key optional

Server-side HTTP 429 for /api/address/* is already observable via access logs and metrics;
client-side abandon on address screen is not emitted today — define with product analytics.
"""
from __future__ import annotations

import logging
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database import RegistrationExecutionEvent, RegistrationSession

logger = logging.getLogger(__name__)

# --- Taxonomy (stable string IDs) --------------------------------------------


class RegistrationEventType:
    FLOW_VERSION_LOCKED = "registration.flow.version_locked"
    SESSION_STARTED = "registration.session.started"
    SESSION_RESUMED = "registration.session.resumed"
    SESSION_COMPLETED = "registration.session.completed"
    SESSION_ABANDONED = "registration.session.abandoned"

    SCREEN_ENTERED = "registration.screen.entered"
    SCREEN_SUBMITTED = "registration.screen.submitted"
    FIELDS_SUBMITTED = "registration.fields.submitted"
    VALIDATION_FAILED = "registration.validation.failed"
    PHONE_VALIDATED = "registration.phone.validated"

    INTERACTION_PREPARED = "registration.interaction.prepared"
    INTERACTION_RESEND_REQUESTED = "registration.interaction.resend_requested"
    INTERACTION_COMPLETED = "registration.interaction.completed"

    NAVIGATION_NEXT = "registration.navigation.next"
    NAVIGATION_PREV = "registration.navigation.prev"
    STEP_COMPLETED = "registration.step.completed"
    STEP_SKIPPED = "registration.step.skipped"
    STEP_BLOCKED = "registration.step.blocked"
    # Legacy type still found in older rows — do not emit; kept for replay parsers
    NAVIGATION_BLOCKED_LEGACY = "registration.navigation.blocked"

    PROJECTION_COMPLETED = "registration.projection.completed"
    RULE_EVALUATED = "registration.rule.evaluated"
    RUNTIME_ERROR = "registration.runtime.error"


class RegistrationEventSource:
    RUNTIME = "runtime"
    SYSTEM = "system"
    ADMIN = "admin"
    FLUTTER = "flutter"


class RegistrationEventStatus:
    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"
    SKIPPED = "skipped"
    INFO = "info"


# Human-readable labels for admin UI / support (French-friendly short labels)
EVENT_TYPE_LABELS: Dict[str, str] = {
    RegistrationEventType.FLOW_VERSION_LOCKED: "Version de flow verrouillée",
    RegistrationEventType.SESSION_STARTED: "Session démarrée",
    RegistrationEventType.SESSION_RESUMED: "Session reprise",
    RegistrationEventType.SESSION_COMPLETED: "Session terminée",
    RegistrationEventType.SESSION_ABANDONED: "Session abandonnée",
    RegistrationEventType.SCREEN_ENTERED: "Écran affiché",
    RegistrationEventType.SCREEN_SUBMITTED: "Écran soumis",
    RegistrationEventType.FIELDS_SUBMITTED: "Champs enregistrés",
    RegistrationEventType.VALIDATION_FAILED: "Validation échouée",
    RegistrationEventType.PHONE_VALIDATED: "Validation téléphone (audit)",
    RegistrationEventType.INTERACTION_PREPARED: "Interaction préparée (2FA / SMS)",
    RegistrationEventType.INTERACTION_RESEND_REQUESTED: "Renvoi SMS interaction",
    RegistrationEventType.INTERACTION_COMPLETED: "Interaction terminée",
    RegistrationEventType.NAVIGATION_NEXT: "Navigation suivant",
    RegistrationEventType.NAVIGATION_PREV: "Navigation précédent",
    RegistrationEventType.STEP_COMPLETED: "Étape complétée",
    RegistrationEventType.STEP_SKIPPED: "Étape ignorée",
    RegistrationEventType.STEP_BLOCKED: "Étape bloquée",
    RegistrationEventType.NAVIGATION_BLOCKED_LEGACY: "Navigation bloquée (ancien)",
    RegistrationEventType.PROJECTION_COMPLETED: "Projection Person terminée",
    RegistrationEventType.RULE_EVALUATED: "Règles évaluées",
    RegistrationEventType.RUNTIME_ERROR: "Erreur runtime",
}


# UI hint: neutral | success | warning | danger | info
EVENT_TYPE_BADGE_VARIANT: Dict[str, str] = {
    RegistrationEventType.VALIDATION_FAILED: "danger",
    RegistrationEventType.STEP_BLOCKED: "warning",
    RegistrationEventType.NAVIGATION_BLOCKED_LEGACY: "warning",
    RegistrationEventType.RUNTIME_ERROR: "danger",
    RegistrationEventType.SESSION_COMPLETED: "success",
    RegistrationEventType.PROJECTION_COMPLETED: "success",
    RegistrationEventType.SESSION_ABANDONED: "neutral",
}


def human_label_for_event_type(event_type: str) -> str:
    return EVENT_TYPE_LABELS.get(event_type, event_type)


def badge_variant_for_event_type(event_type: str) -> str:
    return EVENT_TYPE_BADGE_VARIANT.get(event_type, "info")


def safe_log_registration_event(
    db: Session,
    session: RegistrationSession,
    *,
    event_type: str,
    event_source: str = RegistrationEventSource.RUNTIME,
    event_status: Optional[str] = RegistrationEventStatus.SUCCESS,
    payload: Optional[Dict[str, Any]] = None,
    step_id: Optional[UUID] = None,
    screen_id: Optional[UUID] = None,
    component_id: Optional[UUID] = None,
) -> None:
    """Insert one execution event. Never raises; failures rollback only the savepoint.

    This is the single supported entry point for writing tracking rows.
    """
    try:
        with db.begin_nested():
            row = RegistrationExecutionEvent(
                id=uuid_mod.uuid4(),
                session_id=session.id,
                flow_id=session.flow_id,
                flow_version=session.flow_version,
                step_id=step_id,
                screen_id=screen_id,
                component_id=component_id,
                person_id=session.person_id,
                client_id=session.client_id,
                event_type=event_type,
                event_source=event_source,
                event_status=event_status,
                payload_json=payload or {},
                created_at=datetime.now(timezone.utc),
            )
            db.add(row)
            db.flush()
    except Exception:
        logger.warning(
            "registration_tracking_failed event_type=%s session_id=%s",
            event_type,
            getattr(session, "id", None),
            exc_info=True,
        )


def emit_registration_execution_event(
    db: Session,
    session: RegistrationSession,
    *,
    event_type: str,
    event_source: str = RegistrationEventSource.RUNTIME,
    event_status: Optional[str] = RegistrationEventStatus.SUCCESS,
    payload: Optional[Dict[str, Any]] = None,
    step_id: Optional[UUID] = None,
    screen_id: Optional[UUID] = None,
    component_id: Optional[UUID] = None,
) -> None:
    """Backward-compatible alias for ``safe_log_registration_event``."""
    safe_log_registration_event(
        db,
        session,
        event_type=event_type,
        event_source=event_source,
        event_status=event_status,
        payload=payload,
        step_id=step_id,
        screen_id=screen_id,
        component_id=component_id,
    )


def list_events_for_session(db: Session, session_id: UUID) -> List[RegistrationExecutionEvent]:
    return (
        db.query(RegistrationExecutionEvent)
        .filter(RegistrationExecutionEvent.session_id == session_id)
        .order_by(RegistrationExecutionEvent.created_at.asc())
        .all()
    )


def serialize_event(e: RegistrationExecutionEvent, *, include_ui_hints: bool = False) -> Dict[str, Any]:
    base = {
        "id": str(e.id),
        "session_id": str(e.session_id),
        "flow_id": str(e.flow_id) if e.flow_id else None,
        "flow_version": e.flow_version,
        "step_id": str(e.step_id) if e.step_id else None,
        "screen_id": str(e.screen_id) if e.screen_id else None,
        "component_id": str(e.component_id) if e.component_id else None,
        "person_id": str(e.person_id) if e.person_id else None,
        "client_id": str(e.client_id) if e.client_id else None,
        "event_type": e.event_type,
        "event_source": e.event_source,
        "event_status": e.event_status,
        "payload_json": e.payload_json or {},
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }
    if include_ui_hints:
        base["label_fr"] = human_label_for_event_type(e.event_type)
        base["badge_variant"] = badge_variant_for_event_type(e.event_type)
    return base
