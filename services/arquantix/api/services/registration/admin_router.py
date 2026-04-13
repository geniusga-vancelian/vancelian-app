"""Admin API for Registration Flow Engine — flow builder.

Provides CRUD endpoints for:
  - Jurisdictions
  - Flows (create, publish, archive)
  - Steps (CRUD + reorder)
  - Screens (CRUD + reorder)
  - Components (CRUD + reorder)
"""
from __future__ import annotations

import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from database import (
    get_db,
    RegistrationJurisdiction,
    RegistrationFlow,
    RegistrationFlowStep,
    RegistrationStepScreen,
    RegistrationScreenComponent,
    RegistrationRuntimeSetting,
    RegistrationSession,
    RegistrationSessionStep,
)

from .interaction_templates import (
    infer_interaction_template_display_name,
    infer_interaction_template_key,
    list_interaction_templates_for_api,
)
from .permission_prompt import list_permission_prompt_templates_for_api, validate_screen_for_admin

router = APIRouter(prefix="/api/admin/registration", tags=["Registration Admin"])


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class JurisdictionCreate(BaseModel):
    code: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1)
    entity_name: Optional[str] = None
    default_language: str = "en"
    is_active: bool = True


class JurisdictionUpdate(BaseModel):
    name: Optional[str] = None
    entity_name: Optional[str] = None
    default_language: Optional[str] = None
    is_active: Optional[bool] = None


class FlowCreate(BaseModel):
    jurisdiction_id: UUID
    name: str = Field(..., min_length=1)
    entrypoint_type: str = "individual"


class FlowUpdate(BaseModel):
    name: Optional[str] = None
    entrypoint_type: Optional[str] = None


class FlowPublish(BaseModel):
    published_by: str = Field(..., min_length=1)


class StepCreate(BaseModel):
    step_key: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    title_i18n: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    description_i18n: Optional[Dict[str, str]] = None
    position: int = 0
    is_optional: bool = False
    is_blocking: bool = True
    visibility_rule_json: Optional[Dict[str, Any]] = None
    completion_rule_json: Optional[Dict[str, Any]] = None


class StepUpdate(BaseModel):
    title: Optional[str] = None
    title_i18n: Optional[Dict[str, str]] = None
    description: Optional[str] = None
    description_i18n: Optional[Dict[str, str]] = None
    position: Optional[int] = None
    is_optional: Optional[bool] = None
    is_blocking: Optional[bool] = None
    visibility_rule_json: Optional[Dict[str, Any]] = None
    completion_rule_json: Optional[Dict[str, Any]] = None


class ScreenCreate(BaseModel):
    screen_key: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    title_i18n: Optional[Dict[str, str]] = None
    subtitle: Optional[str] = None
    subtitle_i18n: Optional[Dict[str, str]] = None
    button_label: Optional[str] = None
    button_label_i18n: Optional[Dict[str, str]] = None
    position: int = 0
    layout_type: str = "form"
    config_json: Optional[Dict[str, Any]] = None
    screen_type: str = "form"
    interaction_type: Optional[str] = None
    interaction_config_json: Optional[Dict[str, Any]] = None
    visibility_rule_json: Optional[Dict[str, Any]] = None


class ScreenUpdate(BaseModel):
    title: Optional[str] = None
    title_i18n: Optional[Dict[str, str]] = None
    subtitle: Optional[str] = None
    subtitle_i18n: Optional[Dict[str, str]] = None
    button_label: Optional[str] = None
    button_label_i18n: Optional[Dict[str, str]] = None
    position: Optional[int] = None
    layout_type: Optional[str] = None
    config_json: Optional[Dict[str, Any]] = None
    screen_type: Optional[str] = None
    interaction_type: Optional[str] = None
    interaction_config_json: Optional[Dict[str, Any]] = None
    visibility_rule_json: Optional[Dict[str, Any]] = None


class ComponentCreate(BaseModel):
    component_type: str = Field(..., min_length=1)
    component_key: str = Field(..., min_length=1)
    position: int = 0
    props_json: Optional[Dict[str, Any]] = None
    binding_slug: Optional[str] = None
    field_definition_id: Optional[UUID] = None
    visibility_rule_json: Optional[Dict[str, Any]] = None
    validation_rule_json: Optional[Dict[str, Any]] = None


class ComponentUpdate(BaseModel):
    component_type: Optional[str] = None
    position: Optional[int] = None
    props_json: Optional[Dict[str, Any]] = None
    binding_slug: Optional[str] = None
    field_definition_id: Optional[UUID] = None
    visibility_rule_json: Optional[Dict[str, Any]] = None
    validation_rule_json: Optional[Dict[str, Any]] = None


class ReorderItem(BaseModel):
    id: UUID
    position: int


class ReorderRequest(BaseModel):
    items: List[ReorderItem]


# ------------------------------------------------------------------
# Jurisdictions
# ------------------------------------------------------------------

@router.get("/jurisdictions")
def list_jurisdictions(db: Session = Depends(get_db)):
    rows = db.query(RegistrationJurisdiction).order_by(RegistrationJurisdiction.code).all()
    return [_ser_jurisdiction(j) for j in rows]


@router.post("/jurisdictions", status_code=status.HTTP_201_CREATED)
def create_jurisdiction(payload: JurisdictionCreate, db: Session = Depends(get_db)):
    j = RegistrationJurisdiction(
        code=payload.code.upper(),
        name=payload.name,
        entity_name=payload.entity_name,
        default_language=payload.default_language,
        is_active=payload.is_active,
    )
    db.add(j)
    db.commit()
    db.refresh(j)
    return _ser_jurisdiction(j)


@router.patch("/jurisdictions/{jurisdiction_id}")
def update_jurisdiction(jurisdiction_id: UUID, payload: JurisdictionUpdate, db: Session = Depends(get_db)):
    j = db.query(RegistrationJurisdiction).filter(RegistrationJurisdiction.id == jurisdiction_id).first()
    if not j:
        raise HTTPException(status_code=404, detail="Jurisdiction not found")
    for k, v in payload.dict(exclude_unset=True).items():
        setattr(j, k, v)
    db.commit()
    db.refresh(j)
    return _ser_jurisdiction(j)


def _ser_jurisdiction(j: RegistrationJurisdiction) -> dict:
    return {
        "id": str(j.id), "code": j.code, "name": j.name,
        "entity_name": j.entity_name, "default_language": j.default_language,
        "supported_languages": j.supported_languages,
        "is_active": j.is_active,
    }


# ------------------------------------------------------------------
# Flows
# ------------------------------------------------------------------

@router.get("/flows")
def list_flows(
    jurisdiction_id: Optional[UUID] = Query(None),
    include_health: bool = Query(False, description="Attach can_publish and health counts per flow"),
    include_policy_summary: bool = Query(
        True,
        description="Attach jurisdiction policy counts/defaults for admin cards",
    ),
    db: Session = Depends(get_db),
):
    q = db.query(RegistrationFlow).options(joinedload(RegistrationFlow.jurisdiction))
    if jurisdiction_id:
        q = q.filter(RegistrationFlow.jurisdiction_id == jurisdiction_id)
    rows = q.order_by(RegistrationFlow.created_at.desc()).all()
    from . import jurisdiction_policy_admin_service as _jps

    policy_by_code: Dict[str, Dict[str, Any]] = {}
    if include_policy_summary:
        codes = [f.jurisdiction.code for f in rows if f.jurisdiction and f.jurisdiction.code]
        policy_by_code = _jps.policy_summaries_for_codes(db, codes)

    if not include_health:
        out = [_ser_flow(f) for f in rows]
        if include_policy_summary:
            for d, f in zip(out, rows):
                if f.jurisdiction:
                    d["jurisdiction_policy_summary"] = policy_by_code.get(
                        f.jurisdiction.code.upper()
                    )
        return out
    from .governance import check_flow_health

    out: List[Dict[str, Any]] = []
    for f in rows:
        d = _ser_flow(f)
        h = check_flow_health(f.id, db)
        d["can_publish"] = h.can_publish
        d["health_error_count"] = len(h.errors)
        d["health_warning_count"] = len(h.warnings)
        if include_policy_summary and f.jurisdiction:
            d["jurisdiction_policy_summary"] = policy_by_code.get(f.jurisdiction.code.upper())
        out.append(d)
    return out


@router.get("/flows/health-summary")
def flows_health_summary(db: Session = Depends(get_db)):
    """Diagnostic view: every flow with publish gate outcome and blocking errors."""
    from .governance import check_flow_health

    rows = db.query(RegistrationFlow).order_by(RegistrationFlow.name).all()
    summaries: List[Dict[str, Any]] = []
    publishable = 0
    for f in rows:
        h = check_flow_health(f.id, db)
        if h.can_publish:
            publishable += 1
        summaries.append({
            "flow_id": str(f.id),
            "name": f.name,
            "status": f.status,
            "version": f.version,
            "can_publish": h.can_publish,
            "error_count": len(h.errors),
            "warning_count": len(h.warnings),
            "errors": [e.to_dict() for e in h.errors],
        })
    return {
        "flows_total": len(rows),
        "publishable_count": publishable,
        "blocked_count": len(rows) - publishable,
        "flows": summaries,
    }


@router.post("/flows", status_code=status.HTTP_201_CREATED)
def create_flow(payload: FlowCreate, db: Session = Depends(get_db)):
    max_version = (
        db.query(RegistrationFlow.version)
        .filter(
            RegistrationFlow.jurisdiction_id == payload.jurisdiction_id,
            RegistrationFlow.entrypoint_type == payload.entrypoint_type,
        )
        .order_by(RegistrationFlow.version.desc())
        .first()
    )
    next_version = (max_version[0] + 1) if max_version else 1

    f = RegistrationFlow(
        jurisdiction_id=payload.jurisdiction_id,
        name=payload.name,
        version=next_version,
        status="draft",
        entrypoint_type=payload.entrypoint_type,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return _ser_flow(f)


@router.post("/flows/{flow_id}/publish")
def publish_flow(flow_id: UUID, payload: FlowPublish, db: Session = Depends(get_db)):
    flow = db.query(RegistrationFlow).filter(RegistrationFlow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    if flow.status == "active":
        raise HTTPException(status_code=409, detail="Already active")

    from .governance import check_flow_health
    health = check_flow_health(flow_id, db)
    if not health.can_publish:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Flow has blocking errors — fix them before publishing",
                "errors": [e.to_dict() for e in health.errors],
            },
        )

    db.query(RegistrationFlow).filter(
        RegistrationFlow.jurisdiction_id == flow.jurisdiction_id,
        RegistrationFlow.entrypoint_type == flow.entrypoint_type,
        RegistrationFlow.status == "active",
    ).update({"status": "archived"})

    flow.status = "active"
    flow.published_at = datetime.now(timezone.utc)
    flow.published_by = payload.published_by
    db.commit()
    db.refresh(flow)
    return _ser_flow(flow)


@router.post("/flows/{flow_id}/archive")
def archive_flow(flow_id: UUID, db: Session = Depends(get_db)):
    flow = db.query(RegistrationFlow).filter(RegistrationFlow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    flow.status = "archived"
    db.commit()
    return _ser_flow(flow)


@router.patch("/flows/{flow_id}")
def update_flow(flow_id: UUID, body: FlowUpdate, db: Session = Depends(get_db)):
    flow = db.query(RegistrationFlow).filter(RegistrationFlow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    if body.name is not None:
        flow.name = body.name
    if body.entrypoint_type is not None:
        flow.entrypoint_type = body.entrypoint_type
    flow.updated_at = datetime.now(timezone.utc)
    db.commit()
    return _ser_flow(flow)


@router.delete("/flows/{flow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_flow(flow_id: UUID, db: Session = Depends(get_db)):
    flow = db.query(RegistrationFlow).filter(RegistrationFlow.id == flow_id).first()
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    if flow.status == "active":
        raise HTTPException(status_code=409, detail="Cannot delete an active flow. Archive it first.")
    db.delete(flow)
    db.commit()


@router.get("/flows/{flow_id}")
def get_flow_detail(flow_id: UUID, db: Session = Depends(get_db)):
    from .service import RegistrationFlowService
    flow = (
        db.query(RegistrationFlow)
        .options(
            joinedload(RegistrationFlow.jurisdiction),
            joinedload(RegistrationFlow.steps)
            .joinedload(RegistrationFlowStep.screens)
            .joinedload(RegistrationStepScreen.components),
        )
        .filter(RegistrationFlow.id == flow_id)
        .first()
    )
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")
    return RegistrationFlowService.serialize_flow(flow)


@router.get("/sessions/summary-stats")
def registration_sessions_summary_stats(db: Session = Depends(get_db)):
    """Lightweight aggregates for KPIs / monitoring (read-only)."""
    from .replay import registration_sessions_observability_summary

    return registration_sessions_observability_summary(db)


@router.get("/sessions")
def list_registration_sessions(
    status: Optional[str] = Query(None),
    jurisdiction_id: Optional[UUID] = Query(None),
    flow_id: Optional[UUID] = Query(None),
    person_id: Optional[UUID] = Query(None),
    client_id: Optional[UUID] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """Paginated list of registration sessions (support / compliance)."""
    from .replay import list_registration_sessions_for_admin

    items, total = list_registration_sessions_for_admin(
        db,
        status=status,
        jurisdiction_id=jurisdiction_id,
        flow_id=flow_id,
        person_id=person_id,
        client_id=client_id,
        limit=limit,
        offset=offset,
    )
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/sessions/{session_id}")
def get_registration_session_admin(session_id: UUID, db: Session = Depends(get_db)):
    """Session detail + derived replay sections (no raw event list)."""
    from .replay import get_session_admin_detail

    row = get_session_admin_detail(db, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


@router.get("/sessions/{session_id}/replay")
def get_registration_session_replay(session_id: UUID, db: Session = Depends(get_db)):
    """Full read-only replay including chronological timeline."""
    from .replay import build_session_replay

    s = db.query(RegistrationSession).filter(RegistrationSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return build_session_replay(db, session_id, include_timeline=True)


@router.get("/sessions/{session_id}/execution-events")
def list_registration_session_execution_events(session_id: UUID, db: Session = Depends(get_db)):
    """Ordered execution timeline for admin replay / support."""
    from .execution_events import list_events_for_session, serialize_event

    s = db.query(RegistrationSession).filter(RegistrationSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    rows = list_events_for_session(db, session_id)
    return {
        "session_id": str(session_id),
        "flow_id": str(s.flow_id),
        "flow_version": s.flow_version,
        "session_status": s.status,
        "person_id": str(s.person_id) if s.person_id else None,
        "client_id": str(s.client_id) if s.client_id else None,
        "events": [serialize_event(e, include_ui_hints=True) for e in rows],
        "event_count": len(rows),
    }


@router.get("/flows/{flow_id}/preview")
def preview_flow(
    flow_id: UUID,
    simulate_session: bool = Query(False),
    db: Session = Depends(get_db),
):
    """Full flow preview for the admin UI, optionally simulating a first screen."""
    from .service import RegistrationFlowService, RegistrationSessionService

    flow = (
        db.query(RegistrationFlow)
        .options(
            joinedload(RegistrationFlow.jurisdiction),
            joinedload(RegistrationFlow.steps)
            .joinedload(RegistrationFlowStep.screens)
            .joinedload(RegistrationStepScreen.components),
        )
        .filter(RegistrationFlow.id == flow_id)
        .first()
    )
    if not flow:
        raise HTTPException(status_code=404, detail="Flow not found")

    serialized = RegistrationFlowService.serialize_flow(flow)

    result = {
        "flow": serialized,
        "steps": serialized.get("steps", []),
        "screens": [],
        "components": [],
        "statistics": {
            "total_steps": len(serialized.get("steps", [])),
            "total_screens": 0,
            "total_components": 0,
            "blocking_steps": 0,
        },
    }

    for step in serialized.get("steps", []):
        is_blocking = step.get("is_blocking", True)
        if is_blocking:
            result["statistics"]["blocking_steps"] += 1
        for screen in step.get("screens", []):
            screen_with_step = {**screen, "step_key": step["step_key"], "step_title": step["title"]}
            result["screens"].append(screen_with_step)
            result["statistics"]["total_screens"] += 1
            for comp in screen.get("components", []):
                comp_with_context = {
                    **comp, "screen_key": screen["screen_key"], "step_key": step["step_key"],
                }
                result["components"].append(comp_with_context)
                result["statistics"]["total_components"] += 1

    if simulate_session and flow.jurisdiction:
        try:
            svc = RegistrationSessionService()
            first_screen = svc.start_session(db, flow.jurisdiction.code)
            result["first_screen"] = first_screen
            db.rollback()
        except Exception as exc:
            result["first_screen"] = {"error": str(exc)}

    return result


def _ser_flow(f: RegistrationFlow) -> dict:
    return {
        "id": str(f.id),
        "jurisdiction_id": str(f.jurisdiction_id),
        "name": f.name, "version": f.version, "status": f.status,
        "entrypoint_type": f.entrypoint_type,
        "published_at": f.published_at.isoformat() if f.published_at else None,
        "published_by": f.published_by,
    }


# ------------------------------------------------------------------
# Steps
# ------------------------------------------------------------------

@router.get("/flows/{flow_id}/steps")
def list_steps(flow_id: UUID, db: Session = Depends(get_db)):
    rows = (
        db.query(RegistrationFlowStep)
        .filter(RegistrationFlowStep.flow_id == flow_id)
        .order_by(RegistrationFlowStep.position)
        .all()
    )
    return [_ser_step(s) for s in rows]


@router.post("/flows/{flow_id}/steps", status_code=status.HTTP_201_CREATED)
def create_step(flow_id: UUID, payload: StepCreate, db: Session = Depends(get_db)):
    s = RegistrationFlowStep(
        flow_id=flow_id,
        step_key=payload.step_key,
        title=payload.title,
        description=payload.description,
        position=payload.position,
        is_optional=payload.is_optional,
        is_blocking=payload.is_blocking,
        visibility_rule_json=payload.visibility_rule_json,
        completion_rule_json=payload.completion_rule_json,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _ser_step(s)


@router.patch("/steps/{step_id}")
def update_step(step_id: UUID, payload: StepUpdate, db: Session = Depends(get_db)):
    s = db.query(RegistrationFlowStep).filter(RegistrationFlowStep.id == step_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Step not found")
    for k, v in payload.dict(exclude_unset=True).items():
        setattr(s, k, v)
    db.commit()
    db.refresh(s)
    return _ser_step(s)


def _detach_sessions_before_step_delete(db: Session, step_id: UUID) -> None:
    """Les FK session → step/screen n'ont pas ON DELETE : il faut libérer avant DELETE du step."""
    screen_ids = [
        row[0]
        for row in db.query(RegistrationStepScreen.id)
        .filter(RegistrationStepScreen.step_id == step_id)
        .all()
    ]
    if screen_ids:
        db.query(RegistrationSession).filter(
            RegistrationSession.current_screen_id.in_(screen_ids)
        ).update({RegistrationSession.current_screen_id: None}, synchronize_session=False)
        db.query(RegistrationSessionStep).filter(
            RegistrationSessionStep.last_screen_id.in_(screen_ids)
        ).update({RegistrationSessionStep.last_screen_id: None}, synchronize_session=False)
    db.query(RegistrationSession).filter(
        RegistrationSession.current_step_id == step_id
    ).update({RegistrationSession.current_step_id: None}, synchronize_session=False)
    db.query(RegistrationSessionStep).filter(
        RegistrationSessionStep.step_id == step_id
    ).delete(synchronize_session=False)


@router.delete("/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_step(step_id: UUID, db: Session = Depends(get_db)):
    s = db.query(RegistrationFlowStep).filter(RegistrationFlowStep.id == step_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Step not found")
    _detach_sessions_before_step_delete(db, step_id)
    db.delete(s)
    db.commit()


@router.post("/flows/{flow_id}/steps/reorder")
def reorder_steps(flow_id: UUID, payload: ReorderRequest, db: Session = Depends(get_db)):
    for item in payload.items:
        db.query(RegistrationFlowStep).filter(
            RegistrationFlowStep.id == item.id,
            RegistrationFlowStep.flow_id == flow_id,
        ).update({"position": item.position})
    db.commit()
    return {"status": "ok"}


def _ser_step(s: RegistrationFlowStep) -> dict:
    return {
        "id": str(s.id), "flow_id": str(s.flow_id),
        "step_key": s.step_key, "title": s.title, "description": s.description,
        "title_i18n": s.title_i18n, "description_i18n": s.description_i18n,
        "position": s.position, "is_optional": s.is_optional,
        "is_blocking": s.is_blocking,
        "visibility_rule_json": s.visibility_rule_json,
        "completion_rule_json": s.completion_rule_json,
    }


# ------------------------------------------------------------------
# Interaction templates (admin builder)
# ------------------------------------------------------------------


@router.get("/interaction-templates")
def list_interaction_templates():
    """Business presets for interaction screens; runtime contract unchanged."""
    return list_interaction_templates_for_api()


@router.get("/permission-prompt-templates")
def list_permission_prompt_templates():
    """Presets for Face ID / notifications permission screens (screen_type=permission_prompt)."""
    return list_permission_prompt_templates_for_api()


# ------------------------------------------------------------------
# Screens
# ------------------------------------------------------------------


@router.get("/steps/{step_id}/screens")
def list_screens(step_id: UUID, db: Session = Depends(get_db)):
    rows = (
        db.query(RegistrationStepScreen)
        .filter(RegistrationStepScreen.step_id == step_id)
        .order_by(RegistrationStepScreen.position)
        .all()
    )
    return [_ser_screen(s) for s in rows]


@router.post("/steps/{step_id}/screens", status_code=status.HTTP_201_CREATED)
def create_screen(step_id: UUID, payload: ScreenCreate, db: Session = Depends(get_db)):
    st = payload.screen_type or "form"
    try:
        validate_screen_for_admin(
            screen_type=st,
            interaction_type=payload.interaction_type,
            interaction_config_json=payload.interaction_config_json,
            config_json=payload.config_json,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    it = payload.interaction_type if st == "interaction" else None
    icfg = payload.interaction_config_json if st == "interaction" else None

    s = RegistrationStepScreen(
        step_id=step_id,
        screen_key=payload.screen_key,
        title=payload.title,
        title_i18n=payload.title_i18n,
        subtitle=payload.subtitle,
        subtitle_i18n=payload.subtitle_i18n,
        button_label=payload.button_label,
        button_label_i18n=payload.button_label_i18n,
        position=payload.position,
        layout_type=payload.layout_type,
        config_json=payload.config_json,
        screen_type=st,
        interaction_type=it,
        interaction_config_json=icfg,
        visibility_rule_json=payload.visibility_rule_json,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return _ser_screen(s)


@router.patch("/screens/{screen_id}")
def update_screen(screen_id: UUID, payload: ScreenUpdate, db: Session = Depends(get_db)):
    s = db.query(RegistrationStepScreen).filter(RegistrationStepScreen.id == screen_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Screen not found")
    m = payload.dict(exclude_unset=True)
    new_st = m.get("screen_type", getattr(s, "screen_type", None) or "form")
    new_it = m["interaction_type"] if "interaction_type" in m else s.interaction_type
    new_icfg = (
        m["interaction_config_json"] if "interaction_config_json" in m else s.interaction_config_json
    )
    new_cfg = m["config_json"] if "config_json" in m else s.config_json
    if new_st == "form":
        new_it = None
        new_icfg = None
    elif new_st == "permission_prompt":
        new_it = None
        new_icfg = None
    try:
        validate_screen_for_admin(
            screen_type=new_st,
            interaction_type=new_it,
            interaction_config_json=new_icfg,
            config_json=new_cfg,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    for k, v in m.items():
        setattr(s, k, v)
    st_final = getattr(s, "screen_type", "form")
    if st_final == "form" or st_final == "permission_prompt":
        s.interaction_type = None
        s.interaction_config_json = None

    db.commit()
    db.refresh(s)
    return _ser_screen(s)


@router.delete("/screens/{screen_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_screen(screen_id: UUID, db: Session = Depends(get_db)):
    s = db.query(RegistrationStepScreen).filter(RegistrationStepScreen.id == screen_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Screen not found")
    db.query(RegistrationSessionStep).filter(
        RegistrationSessionStep.last_screen_id == screen_id,
    ).update({"last_screen_id": None}, synchronize_session="fetch")
    db.query(RegistrationSession).filter(
        RegistrationSession.current_screen_id == screen_id,
    ).update({"current_screen_id": None}, synchronize_session="fetch")
    db.delete(s)
    db.commit()


@router.post("/steps/{step_id}/screens/reorder")
def reorder_screens(step_id: UUID, payload: ReorderRequest, db: Session = Depends(get_db)):
    for item in payload.items:
        db.query(RegistrationStepScreen).filter(
            RegistrationStepScreen.id == item.id,
            RegistrationStepScreen.step_id == step_id,
        ).update({"position": item.position})
    db.commit()
    return {"status": "ok"}


def _ser_screen(s: RegistrationStepScreen) -> dict:
    st = getattr(s, "screen_type", None) or "form"
    it = getattr(s, "interaction_type", None)
    icfg = getattr(s, "interaction_config_json", None)
    itk = infer_interaction_template_key(
        screen_type=st, interaction_type=it, interaction_config_json=icfg if isinstance(icfg, dict) else None,
    )
    itd = infer_interaction_template_display_name(
        screen_type=st, interaction_type=it, interaction_config_json=icfg if isinstance(icfg, dict) else None,
    )
    return {
        "id": str(s.id), "step_id": str(s.step_id),
        "screen_key": s.screen_key, "title": s.title, "subtitle": s.subtitle,
        "title_i18n": s.title_i18n, "subtitle_i18n": s.subtitle_i18n,
        "button_label": s.button_label, "button_label_i18n": s.button_label_i18n,
        "position": s.position, "layout_type": s.layout_type,
        "config": s.config_json,
        "screen_type": st,
        "interaction_type": it,
        "interaction_config_json": icfg,
        "interaction_template_key": itk,
        "interaction_template_display_name": itd,
        "visibility_rule_json": getattr(s, "visibility_rule_json", None),
    }


# ------------------------------------------------------------------
# Components
# ------------------------------------------------------------------

@router.get("/screens/{screen_id}/components")
def list_components(screen_id: UUID, db: Session = Depends(get_db)):
    rows = (
        db.query(RegistrationScreenComponent)
        .filter(RegistrationScreenComponent.screen_id == screen_id)
        .order_by(RegistrationScreenComponent.position)
        .all()
    )
    return [_ser_component(c) for c in rows]


@router.post("/screens/{screen_id}/components", status_code=status.HTTP_201_CREATED)
def create_component(screen_id: UUID, payload: ComponentCreate, db: Session = Depends(get_db)):
    from .governance import validate_component_family
    validate_component_family(
        payload.component_type,
        payload.field_definition_id,
        payload.binding_slug,
        db,
        props_json=payload.props_json,
    )

    c = RegistrationScreenComponent(
        screen_id=screen_id,
        component_type=payload.component_type,
        component_key=payload.component_key,
        position=payload.position,
        props_json=payload.props_json,
        binding_slug=payload.binding_slug,
        field_definition_id=payload.field_definition_id,
        visibility_rule_json=payload.visibility_rule_json,
        validation_rule_json=payload.validation_rule_json,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _ser_component(c)


@router.patch("/components/{component_id}")
def update_component(component_id: UUID, payload: ComponentUpdate, db: Session = Depends(get_db)):
    c = db.query(RegistrationScreenComponent).filter(RegistrationScreenComponent.id == component_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Component not found")

    data = payload.dict(exclude_unset=True)
    ct = data.get("component_type", c.component_type)
    fd_id = data.get("field_definition_id", c.field_definition_id)
    bs = data.get("binding_slug", c.binding_slug)
    next_props = c.props_json if isinstance(c.props_json, dict) else {}
    if "props_json" in data:
        pj = data.get("props_json")
        next_props = pj if isinstance(pj, dict) else {}

    from .governance import validate_component_family
    validate_component_family(ct, fd_id, bs, db, props_json=next_props)

    for k, v in data.items():
        setattr(c, k, v)
    db.commit()
    db.refresh(c)
    return _ser_component(c)


@router.delete("/components/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_component(component_id: UUID, db: Session = Depends(get_db)):
    c = db.query(RegistrationScreenComponent).filter(RegistrationScreenComponent.id == component_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Component not found")
    db.delete(c)
    db.commit()


@router.post("/screens/{screen_id}/components/reorder")
def reorder_components(screen_id: UUID, payload: ReorderRequest, db: Session = Depends(get_db)):
    for item in payload.items:
        db.query(RegistrationScreenComponent).filter(
            RegistrationScreenComponent.id == item.id,
            RegistrationScreenComponent.screen_id == screen_id,
        ).update({"position": item.position})
    db.commit()
    return {"status": "ok"}


def _ser_component(c: RegistrationScreenComponent) -> dict:
    return {
        "id": str(c.id), "screen_id": str(c.screen_id),
        "component_type": c.component_type, "component_key": c.component_key,
        "position": c.position, "props": c.props_json or {},
        "binding_slug": c.binding_slug,
        "field_definition_id": str(c.field_definition_id) if c.field_definition_id else None,
        "visibility_rule_json": c.visibility_rule_json,
        "validation_rule_json": c.validation_rule_json,
    }


# ------------------------------------------------------------------
# Field Definitions
# ------------------------------------------------------------------

@router.get("/field-definitions")
def list_field_definitions(
    category: Optional[str] = None,
    field_type: Optional[str] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
):
    """List all field definitions with optional filters and usage counts."""
    from database import FieldDefinition
    from .governance import get_field_usage_count

    q = db.query(FieldDefinition)
    if is_active is not None:
        q = q.filter(FieldDefinition.is_active == is_active)
    if category:
        q = q.filter(FieldDefinition.category == category)
    if field_type:
        q = q.filter(FieldDefinition.field_type == field_type)
    if search:
        like = f"%{search}%"
        q = q.filter(
            FieldDefinition.slug.ilike(like)
            | FieldDefinition.field_name_en.ilike(like)
            | FieldDefinition.ui_label.ilike(like)
        )
    fields = q.order_by(FieldDefinition.category, FieldDefinition.slug).all()
    usage_counts = get_field_usage_count(db)

    return [
        {
            "id": str(f.id),
            "slug": f.slug,
            "slug_snake": f.slug.replace("-", "_"),
            "field_name_en": f.field_name_en,
            "label": f.ui_label or f.field_name_en,
            "field_type": f.field_type,
            "category": f.category,
            "is_active": f.is_active,
            "component_type_default": f.component_type_default,
            "required_default": f.required_default,
            "options": f.options_json,
            "usage_count": usage_counts.get(str(f.id), 0),
        }
        for f in fields
    ]


@router.get("/field-definitions/catalog")
def get_field_catalog(db: Session = Depends(get_db)):
    """Return active field definitions for the component builder."""
    from database import FieldDefinition

    fields = (
        db.query(FieldDefinition)
        .filter(FieldDefinition.is_active == True)
        .order_by(FieldDefinition.category, FieldDefinition.slug)
        .all()
    )
    return [
        {
            "id": str(f.id),
            "slug": f.slug,
            "slug_snake": f.slug.replace("-", "_"),
            "label": f.ui_label or f.field_name_en,
            "field_type": f.field_type,
            "category": f.category,
            "component_type_default": f.component_type_default,
            "required_default": f.required_default,
            "options": f.options_json,
        }
        for f in fields
    ]


@router.get("/field-definitions/{field_id}")
def get_field_definition(field_id: UUID, db: Session = Depends(get_db)):
    """Return a single field definition with its usage across flows."""
    from database import FieldDefinition
    from .governance import get_field_usage

    f = db.query(FieldDefinition).filter(FieldDefinition.id == field_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Field definition not found")

    usages = get_field_usage(field_id, db)
    return {
        "id": str(f.id),
        "slug": f.slug,
        "slug_snake": f.slug.replace("-", "_"),
        "field_name_en": f.field_name_en,
        "label": f.ui_label or f.field_name_en,
        "field_type": f.field_type,
        "category": f.category,
        "is_active": f.is_active,
        "ui_label": f.ui_label,
        "component_type_default": f.component_type_default,
        "required_default": f.required_default,
        "options": f.options_json,
        "created_at": f.created_at.isoformat() if f.created_at else None,
        "updated_at": f.updated_at.isoformat() if f.updated_at else None,
        "usages": usages,
        "usage_count": len(usages),
    }


@router.patch("/field-definitions/{field_id}")
def update_field_definition(field_id: UUID, payload: Dict[str, Any], db: Session = Depends(get_db)):
    """Update metadata of a field definition."""
    from database import FieldDefinition

    f = db.query(FieldDefinition).filter(FieldDefinition.id == field_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Field definition not found")

    allowed = {"ui_label", "component_type_default", "required_default", "options_json", "is_active", "category"}
    for k, v in payload.items():
        if k in allowed:
            setattr(f, k, v)
    db.commit()
    db.refresh(f)
    return {"status": "ok", "id": str(f.id)}


# ------------------------------------------------------------------
# Flow Health Check
# ------------------------------------------------------------------

@router.get("/flows/{flow_id}/health")
def flow_health(flow_id: UUID, db: Session = Depends(get_db)):
    """Run governance checks and return a publish-readiness report."""
    from .governance import check_flow_health
    report = check_flow_health(flow_id, db)
    return report.to_dict()


# ------------------------------------------------------------------
# Component Support Registry
# ------------------------------------------------------------------

@router.get("/component-support")
def component_support():
    """Return the registry of supported component types."""
    from .governance import get_component_support_registry
    return get_component_support_registry()


@router.get("/component-families")
def component_families():
    """Return content vs field-bound component type classification."""
    from .governance import get_content_component_types, get_field_bound_component_types
    return {
        "content": get_content_component_types(),
        "field_bound": get_field_bound_component_types(),
    }


# ---------------------------------------------------------------------------
# Legacy normalization (diagnostic + safe auto-fix)
# ---------------------------------------------------------------------------


class LegacyNormalizationApplyBody(BaseModel):
    """Require explicit confirmation before mutating legacy components."""

    confirm: bool = False


@router.get("/legacy-normalization/report")
def legacy_normalization_report(db: Session = Depends(get_db)):
    """Classify all registration screen components (OK / auto-fixable / ambiguous) + flow health snapshot."""
    from .legacy_normalization import diagnose_registration_components, result_to_dict

    return result_to_dict(diagnose_registration_components(db))


@router.post("/legacy-normalization/dry-run")
def legacy_normalization_dry_run(db: Session = Depends(get_db)):
    """Same classification as report, with totals aligned to apply (no writes)."""
    from .legacy_normalization import apply_auto_fixes, result_to_dict

    return result_to_dict(apply_auto_fixes(db, dry_run=True))


@router.post("/legacy-normalization/apply")
def legacy_normalization_apply(
    payload: LegacyNormalizationApplyBody,
    db: Session = Depends(get_db),
):
    """Apply only non-ambiguous auto-fixes. Rolls back all changes on error."""
    if not payload.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refused: send {\"confirm\": true} to apply legacy normalization fixes",
        )
    from .legacy_normalization import apply_auto_fixes, result_to_dict

    out = result_to_dict(apply_auto_fixes(db, dry_run=False))
    if out.get("errors"):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": "Legacy normalization failed; transaction rolled back", "errors": out["errors"]},
        )
    return out


# ---------------------------------------------------------------------------
# Runtime Settings — current jurisdiction
# ---------------------------------------------------------------------------

class PatchCurrentJurisdictionRequest(BaseModel):
    jurisdiction_code: str = Field(..., min_length=1, max_length=20)


@router.get("/runtime/current-jurisdiction")
def admin_get_current_jurisdiction(db: Session = Depends(get_db)):
    """Admin view of current jurisdiction setting."""
    setting = db.query(RegistrationRuntimeSetting).first()
    if not setting:
        return {"current_jurisdiction_code": None}
    return {"current_jurisdiction_code": setting.current_jurisdiction_code}


@router.patch("/runtime/current-jurisdiction")
def admin_patch_current_jurisdiction(
    payload: PatchCurrentJurisdictionRequest,
    db: Session = Depends(get_db),
):
    """Set the current jurisdiction for runtime testing."""
    jurisdiction = (
        db.query(RegistrationJurisdiction)
        .filter(
            RegistrationJurisdiction.code == payload.jurisdiction_code,
            RegistrationJurisdiction.is_active.is_(True),
        )
        .first()
    )
    if not jurisdiction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active jurisdiction '{payload.jurisdiction_code}' not found",
        )

    setting = db.query(RegistrationRuntimeSetting).first()
    if setting:
        setting.current_jurisdiction_code = payload.jurisdiction_code
    else:
        setting = RegistrationRuntimeSetting(
            current_jurisdiction_code=payload.jurisdiction_code,
        )
        db.add(setting)

    db.commit()
    return {
        "current_jurisdiction_code": payload.jurisdiction_code,
        "jurisdiction_name": jurisdiction.name,
    }
