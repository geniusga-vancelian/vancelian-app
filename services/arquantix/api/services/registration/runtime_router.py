"""Runtime API for Registration Flow Engine — consumed by Flutter.

Endpoints:
  GET  /api/registration/flows/active  — resolve active flow for a jurisdiction
  POST /api/registration/sessions/start — start a new session
  GET  /api/registration/sessions/{id}/screen — get current screen
  POST /api/registration/sessions/{id}/submit — submit answers + advance
  POST /api/registration/sessions/{id}/next — go to next screen
  POST /api/registration/sessions/{id}/prev — go to previous screen
  POST /api/registration/sessions/{id}/interaction/prepare — SMS OTP (reuse ou création) + JWT court
  POST /api/registration/sessions/{id}/interaction/resend — nouveau SMS (supersede pending + create)
  POST /api/registration/sessions/{id}/interaction/complete — figer la vérif sur la session
  POST /api/registration/sessions/{id}/complete — finalise session + project
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import get_optional_user_for_registration
from database import (
    AdminUser,
    get_db,
    RegistrationRuntimeSetting,
    RegistrationJurisdiction,
    RegistrationFlow,
)
from .interaction_helpers import RegistrationInteractionError
from .service import (
    RegistrationFlowService,
    RegistrationSessionService,
    FlowNotFoundError,
    SessionNotFoundError,
    SessionCompletedError,
    RegistrationAlreadyCompletedError,
    NoNextScreenError,
    NoPreviousScreenError,
    StepBlockedError,
    ValidationError,
    RegistrationError,
)

router = APIRouter(prefix="/api/registration", tags=["Registration"])

_log = logging.getLogger(__name__)

_flow_svc = RegistrationFlowService()
_session_svc = RegistrationSessionService()


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class StartSessionRequest(BaseModel):
    jurisdiction: str = Field(..., min_length=1, max_length=10)
    entrypoint_type: str = Field("individual", max_length=50)
    person_id: Optional[UUID] = None


class SubmitScreenRequest(BaseModel):
    answers: Dict[str, Any] = Field(default_factory=dict)


class InteractionResendRequest(BaseModel):
    screen_id: UUID = Field(..., description="Current registration screen id")
    interaction_type: str = Field(..., min_length=1, max_length=64)


class InteractionCompleteRequest(BaseModel):
    screen_id: UUID = Field(..., description="Current registration screen id")
    interaction_type: str = Field(..., min_length=1, max_length=64)
    challenge_id: UUID
    verified: bool = Field(..., description="Must be true after OTP verified via /api/2fa/verify")


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.get("/runtime/current-jurisdiction")
def get_current_jurisdiction(db: Session = Depends(get_db)):
    """Return the current jurisdiction setting with its active flow."""
    try:
        setting = db.query(RegistrationRuntimeSetting).first()
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No current jurisdiction configured",
            )

        jurisdiction = (
            db.query(RegistrationJurisdiction)
            .filter(RegistrationJurisdiction.code == setting.current_jurisdiction_code)
            .first()
        )

        flow = None
        if jurisdiction:
            flow = (
                db.query(RegistrationFlow)
                .filter(
                    RegistrationFlow.jurisdiction_id == jurisdiction.id,
                    RegistrationFlow.status == "active",
                    RegistrationFlow.entrypoint_type == "individual",
                )
                .order_by(RegistrationFlow.version.desc())
                .first()
            )

        return {
            "jurisdiction_code": setting.current_jurisdiction_code,
            "jurisdiction_name": jurisdiction.name if jurisdiction else None,
            "active_flow_id": str(flow.id) if flow else None,
            "active_flow_name": flow.name if flow else None,
            "active_flow_version": flow.version if flow else None,
        }
    except HTTPException:
        raise
    except Exception:
        _log.exception("GET /api/registration/runtime/current-jurisdiction failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "code": "registration_runtime_error",
                "message": (
                    "Registration runtime failed (database or configuration). "
                    "See server logs for the exception."
                ),
            },
        ) from None


@router.get("/flows/active")
def get_active_flow(
    jurisdiction: str = Query(..., min_length=1),
    entrypoint_type: str = Query("individual"),
    lang: Optional[str] = Query(None, max_length=10),
    db: Session = Depends(get_db),
):
    """Return the active flow definition for a jurisdiction (full tree).

    Pass ``?lang=fr`` to resolve all localizable text to French.
    Falls back to jurisdiction default_language, then ``en``.
    """
    try:
        flow = _flow_svc.get_active_flow(db, jurisdiction, entrypoint_type)
        return _flow_svc.serialize_flow(flow, lang=lang)
    except FlowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/sessions/start", status_code=status.HTTP_201_CREATED)
def start_session(
    payload: StartSessionRequest,
    db: Session = Depends(get_db),
    current_user: Optional[AdminUser] = Depends(get_optional_user_for_registration),
):
    """Crée une session d'inscription ou **reprend** la session ``in_progress`` existante.

    Si un JWT Bearer est fourni (compte déjà connecté), ``person_id`` est pris depuis
    ``admin_users.person_id`` (inscription mobile) et le corps ``person_id`` est ignoré.

    Reprise : même personne + même juridiction + session non terminée → écran courant
    (pas de nouvelle ligne ``registration_sessions``).
    """
    person_id = payload.person_id
    if current_user is not None:
        person_id = getattr(current_user, "person_id", None)
        if person_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "person_required",
                    "message": "Le compte n’est pas lié à un profil personne.",
                },
            )
    try:
        result = _session_svc.start_session(
            db,
            jurisdiction_code=payload.jurisdiction,
            entrypoint_type=payload.entrypoint_type,
            person_id=person_id,
        )
        db.commit()
        return result
    except FlowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except RegistrationAlreadyCompletedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "registration_already_completed",
                "message": str(exc),
            },
        )
    except RegistrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/sessions/{session_id}/screen")
def get_current_screen(
    session_id: UUID,
    db: Session = Depends(get_db),
):
    """Return the current screen for a session (with components and collected data)."""
    try:
        return _session_svc.get_current_screen(db, session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.post("/sessions/{session_id}/submit")
def submit_screen(
    session_id: UUID,
    payload: SubmitScreenRequest,
    db: Session = Depends(get_db),
):
    """Save answers for current screen and advance to next."""
    try:
        result = _session_svc.submit_screen(db, session_id, payload.answers)
        db.commit()
        return result
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SessionCompletedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValidationError as exc:
        if getattr(exc, "code", None):
            detail_submit: Dict[str, Any] = {"code": exc.code, "message": str(exc)}
            if getattr(exc, "field_slug", None):
                detail_submit["field"] = exc.field_slug
            if getattr(exc, "message_hint", None):
                detail_submit["message_hint"] = exc.message_hint
            if getattr(exc, "debug_extra", None):
                detail_submit["debug"] = exc.debug_extra
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail_submit
            )
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        )
    except StepBlockedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except RegistrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/sessions/{session_id}/next")
def next_screen(
    session_id: UUID,
    db: Session = Depends(get_db),
):
    """Advance to the next visible screen."""
    try:
        result = _session_svc.next_screen(db, session_id)
        db.commit()
        return result
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except StepBlockedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except (SessionCompletedError, NoNextScreenError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/sessions/{session_id}/prev")
def prev_screen(
    session_id: UUID,
    db: Session = Depends(get_db),
):
    """Go back to the previous visible screen."""
    try:
        result = _session_svc.prev_screen(db, session_id)
        db.commit()
        return result
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except NoPreviousScreenError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/sessions/{session_id}/complete")
def complete_session(
    session_id: UUID,
    db: Session = Depends(get_db),
):
    """Mark session as completed and project data to Person."""
    try:
        result = _session_svc.complete_session(db, session_id)
        db.commit()
        return result
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SessionCompletedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except RegistrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/sessions/{session_id}/interaction/prepare")
def prepare_registration_interaction(
    session_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    """Start or reuse SMS OTP for the current interaction screen; returns a JWT for /api/2fa/verify."""
    try:
        result = _session_svc.prepare_interaction(
            db,
            session_id,
            app_testing=getattr(request.app.state, "testing", False),
            client_ip=(request.client.host if request.client else None),
        )
        db.commit()
        return result
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SessionCompletedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except RegistrationInteractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message},
        )
    except ValidationError as exc:
        msg = str(exc)
        if "Wait " in msg and "before requesting" in msg:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg)
    except RegistrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/sessions/{session_id}/interaction/resend")
def resend_registration_interaction(
    session_id: UUID,
    payload: InteractionResendRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """Supersede pending SMS challenges and send a new OTP (explicit user intent)."""
    try:
        result = _session_svc.resend_interaction(
            db,
            session_id,
            screen_id=payload.screen_id,
            interaction_type=payload.interaction_type,
            app_testing=getattr(request.app.state, "testing", False),
            client_ip=(request.client.host if request.client else None),
        )
        db.commit()
        return result
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SessionCompletedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except RegistrationInteractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message},
        )
    except ValidationError as exc:
        msg = str(exc)
        if "Wait " in msg and "before requesting" in msg:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=msg)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg)
    except RegistrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/sessions/{session_id}/interaction/complete")
def complete_registration_interaction(
    session_id: UUID,
    payload: InteractionCompleteRequest,
    db: Session = Depends(get_db),
):
    """Persist SMS verification outcome on the session after a successful /api/2fa/verify."""
    try:
        result = _session_svc.complete_interaction(
            db,
            session_id,
            screen_id=payload.screen_id,
            interaction_type=payload.interaction_type,
            challenge_id=payload.challenge_id,
            verified=payload.verified,
        )
        db.commit()
        return result
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SessionCompletedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except RegistrationInteractionError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": exc.code, "message": exc.message},
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except RegistrationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/flows/{flow_id}/flutter-contract")
def get_flutter_contract(
    flow_id: UUID,
    db: Session = Depends(get_db),
):
    """Return the flow structure in the exact format expected by the Flutter renderer.

    This endpoint validates that the backend output is directly consumable
    by the Flutter dynamic registration widget without any transformation.
    """
    try:
        flow = _flow_svc.get_flow_by_id(db, flow_id)
    except FlowNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    serialized = _flow_svc.serialize_flow(flow)

    component_types = set()
    binding_slugs = []
    for step in serialized.get("steps", []):
        for screen in step.get("screens", []):
            for comp in screen.get("components", []):
                component_types.add(comp["component_type"])
                if comp.get("binding_slug"):
                    binding_slugs.append(comp["binding_slug"])

    return {
        "contract_version": "1.0",
        "flow": serialized,
        "flutter_metadata": {
            "component_types_used": sorted(component_types),
            "binding_slugs": binding_slugs,
            "total_screens": sum(
                len(step.get("screens", [])) for step in serialized.get("steps", [])
            ),
            "total_components": sum(
                len(screen.get("components", []))
                for step in serialized.get("steps", [])
                for screen in step.get("screens", [])
            ),
        },
    }
