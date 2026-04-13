"""Read-only session replay reconstruction from execution events + ORM state."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from uuid import UUID

from sqlalchemy.orm import Session, joinedload

from database import (
    RegistrationFlow,
    RegistrationSession,
    RegistrationSessionData,
    RegistrationSessionStep,
)

from .execution_events import (
    RegistrationEventType,
    list_events_for_session,
    serialize_event,
)


def _parse_ts(iso: Optional[str]) -> Optional[datetime]:
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None


def build_session_replay(
    db: Session,
    session_id: UUID,
    *,
    include_timeline: bool = True,
) -> Dict[str, Any]:
    """Deterministic read-only replay: metadata + timeline + derived sections + stats.

    Tolerates missing event types (partial tracking).
    """
    session = (
        db.query(RegistrationSession)
        .options(
            joinedload(RegistrationSession.jurisdiction),
            joinedload(RegistrationSession.flow),
            joinedload(RegistrationSession.current_step),
            joinedload(RegistrationSession.current_screen),
        )
        .filter(RegistrationSession.id == session_id)
        .first()
    )
    if session is None:
        return {"error": "session_not_found", "session_id": str(session_id)}

    events_orm = list_events_for_session(db, session_id)
    events = [serialize_event(e, include_ui_hints=True) for e in events_orm]

    screens_viewed: List[str] = []
    screens_seen: Set[str] = set()
    submits_count = 0
    validation_failures_count = 0
    blocked_steps_count = 0
    rule_batches: List[Dict[str, Any]] = []
    validation_failures: List[Dict[str, Any]] = []
    block_events: List[Dict[str, Any]] = []
    projection_final: Optional[Dict[str, Any]] = None

    for ev in events:
        t = ev["event_type"]
        payload = ev.get("payload_json") or {}
        if t == RegistrationEventType.SCREEN_ENTERED:
            sk = payload.get("screen_key")
            if sk and sk not in screens_seen:
                screens_seen.add(sk)
                screens_viewed.append(sk)
        elif t == RegistrationEventType.FIELDS_SUBMITTED:
            submits_count += 1
        elif t == RegistrationEventType.VALIDATION_FAILED:
            validation_failures_count += 1
            validation_failures.append(
                {
                    "at": ev.get("created_at"),
                    "screen_key": payload.get("screen_key"),
                    "reason": payload.get("reason"),
                    "errors": payload.get("errors") or payload.get("fields"),
                }
            )
        elif t in (RegistrationEventType.STEP_BLOCKED, RegistrationEventType.NAVIGATION_BLOCKED_LEGACY):
            blocked_steps_count += 1
            block_events.append(
                {
                    "at": ev.get("created_at"),
                    "blocking_step_key": payload.get("blocking_step_key"),
                    "reason": payload.get("reason"),
                }
            )
        elif t == RegistrationEventType.RULE_EVALUATED:
            rule_batches.append(
                {
                    "at": ev.get("created_at"),
                    "batch_source": payload.get("batch_source"),
                    "count": payload.get("count"),
                    "evaluations": payload.get("evaluations") or [],
                }
            )
        elif t == RegistrationEventType.PROJECTION_COMPLETED:
            projection_final = {
                "at": ev.get("created_at"),
                "person_id": payload.get("person_id"),
                "projected_fields": payload.get("projected_fields"),
            }

    duration_seconds: Optional[float] = None
    if events:
        t0 = _parse_ts(events[0].get("created_at"))
        t1 = _parse_ts(events[-1].get("created_at"))
        if t0 and t1:
            duration_seconds = max(0.0, (t1 - t0).total_seconds())
    if duration_seconds is None and session.created_at and session.updated_at:
        duration_seconds = max(
            0.0, (session.updated_at - session.created_at).total_seconds()
        )

    data_rows = (
        db.query(RegistrationSessionData)
        .filter(RegistrationSessionData.session_id == session_id)
        .all()
    )
    # Flat collected slugs (no per-screen attribution in DB)
    collected_snapshot = {r.field_slug: r.value_json for r in data_rows}

    step_state_rows = (
        db.query(RegistrationSessionStep)
        .filter(RegistrationSessionStep.session_id == session_id)
        .all()
    )
    step_states = [
        {
            "step_id": str(r.step_id),
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "skipped_at": r.skipped_at.isoformat() if r.skipped_at else None,
        }
        for r in step_state_rows
    ]

    flow = session.flow
    summary = {
        "screens_viewed_count": len(screens_viewed),
        "submits_count": submits_count,
        "validation_failures_count": validation_failures_count,
        "blocked_steps_count": blocked_steps_count,
        "rule_evaluation_batches_count": len(rule_batches),
        "duration_seconds": duration_seconds,
        "events_total": len(events),
    }

    jurisdiction_code = session.jurisdiction.code if session.jurisdiction else None

    return {
        "session_id": str(session.id),
        "session_status": session.status,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "jurisdiction": jurisdiction_code,
        "flow": {
            "id": str(flow.id) if flow else None,
            "name": flow.name if flow else None,
            "version": session.flow_version,
        },
        "person_id": str(session.person_id) if session.person_id else None,
        "client_id": str(session.client_id) if session.client_id else None,
        "current_step": {
            "id": str(session.current_step.id) if session.current_step else None,
            "step_key": session.current_step.step_key if session.current_step else None,
        }
        if session.current_step
        else None,
        "current_screen": {
            "id": str(session.current_screen.id) if session.current_screen else None,
            "screen_key": session.current_screen.screen_key if session.current_screen else None,
        }
        if session.current_screen
        else None,
        "summary": summary,
        "screens_viewed": screens_viewed,
        "validation_failures": validation_failures,
        "blocked_events": block_events,
        "rule_evaluation_batches": rule_batches,
        "projection": projection_final,
        "step_states": step_states,
        "collected_data_snapshot": collected_snapshot,
        "timeline": events if include_timeline else [],
    }


def list_registration_sessions_for_admin(
    db: Session,
    *,
    status: Optional[str] = None,
    jurisdiction_id: Optional[UUID] = None,
    flow_id: Optional[UUID] = None,
    person_id: Optional[UUID] = None,
    client_id: Optional[UUID] = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[List[Dict[str, Any]], int]:
    """Paginated session list for admin (read-only)."""
    q = db.query(RegistrationSession).options(
        joinedload(RegistrationSession.jurisdiction),
        joinedload(RegistrationSession.flow),
        joinedload(RegistrationSession.current_step),
        joinedload(RegistrationSession.current_screen),
    )
    if status:
        q = q.filter(RegistrationSession.status == status)
    if jurisdiction_id:
        q = q.filter(RegistrationSession.jurisdiction_id == jurisdiction_id)
    if flow_id:
        q = q.filter(RegistrationSession.flow_id == flow_id)
    if person_id:
        q = q.filter(RegistrationSession.person_id == person_id)
    if client_id:
        q = q.filter(RegistrationSession.client_id == client_id)

    total = q.count()
    rows = (
        q.order_by(RegistrationSession.created_at.desc())
        .offset(offset)
        .limit(min(limit, 200))
        .all()
    )
    items = [_serialize_session_row(s) for s in rows]
    return items, total


def _serialize_session_row(session: RegistrationSession) -> Dict[str, Any]:
    j = session.jurisdiction
    f = session.flow
    return {
        "id": str(session.id),
        "short_id": str(session.id)[:8],
        "status": session.status,
        "flow_id": str(session.flow_id),
        "flow_name": f.name if f else None,
        "flow_version": session.flow_version,
        "jurisdiction_id": str(session.jurisdiction_id),
        "jurisdiction_code": j.code if j else None,
        "person_id": str(session.person_id) if session.person_id else None,
        "client_id": str(session.client_id) if session.client_id else None,
        "current_step_key": session.current_step.step_key if session.current_step else None,
        "current_screen_key": session.current_screen.screen_key if session.current_screen else None,
        "progress_percent": session.progress_percent,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
    }


def get_session_admin_detail(db: Session, session_id: UUID) -> Optional[Dict[str, Any]]:
    """Full session read model without execution timeline (use /replay or /execution-events)."""
    replay = build_session_replay(db, session_id, include_timeline=False)
    if replay.get("error"):
        return None
    return {k: v for k, v in replay.items() if k != "timeline"}


def registration_sessions_observability_summary(db: Session) -> Dict[str, Any]:
    """Lightweight aggregates for admin / future KPIs (read-only)."""
    from database import RegistrationExecutionEvent
    from sqlalchemy import func

    total = db.query(func.count(RegistrationSession.id)).scalar() or 0
    by_status = (
        db.query(RegistrationSession.status, func.count(RegistrationSession.id))
        .group_by(RegistrationSession.status)
        .all()
    )
    completed = sum(c for s, c in by_status if s == "completed")
    in_prog = sum(c for s, c in by_status if s == "in_progress")

    blocked_events = (
        db.query(func.count(RegistrationExecutionEvent.id))
        .filter(
            RegistrationExecutionEvent.event_type.in_(
                [
                    RegistrationEventType.STEP_BLOCKED,
                    RegistrationEventType.NAVIGATION_BLOCKED_LEGACY,
                ]
            )
        )
        .scalar()
        or 0
    )
    val_fail = (
        db.query(func.count(RegistrationExecutionEvent.id))
        .filter(RegistrationExecutionEvent.event_type == RegistrationEventType.VALIDATION_FAILED)
        .scalar()
        or 0
    )

    return {
        "sessions_total": int(total),
        "sessions_by_status": {s: int(c) for s, c in by_status},
        "completed_count": int(completed),
        "in_progress_count": int(in_prog),
        "execution_events_validation_failed_total": int(val_fail),
        "execution_events_blocked_total": int(blocked_events),
    }
