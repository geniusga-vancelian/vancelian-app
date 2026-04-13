"""Endpoints admin read-only — observabilité des événements de sécurité auth."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth import get_current_user
from database import AdminUser, AuthGlobalRiskScore, AuthSecurityEvent, AuthSession, AuthSessionIntelligence, get_db
from schemas import (
    AdaptiveAuthDecisionPayload,
    AdminSecurityActionResponse,
    AdminSecurityUserIdBody,
    AuthSecurityEventItem,
    AuthSecurityEventsSummary,
    PasskeysSecurityConfigResponse,
    SecurityAnomaliesResponse,
    SecurityCorrelationFindingSchema,
    SecurityUserRiskResponse,
    SessionIntelligenceResponse,
)
from services.auth.security_correlation_service import (
    findings_to_dicts,
    run_all_detections,
    user_risk_profile,
)
from services.security.security_correlation_engine import (
    assess_global_peers,
    assess_user_risk,
    signals_to_dicts,
)
from services.auth.security_signal_service import SecuritySignalService
from services.auth.webauthn_config import build_passkeys_admin_config_dict
from services.security.sensitive_action_events import record_sensitive_action_completed, record_sensitive_action_failed
from services.security.session_intelligence_dependencies import require_continuous_auth_for_action

router = APIRouter(prefix="/admin/security", tags=["admin-security"])


@router.get("/events", response_model=List[AuthSecurityEventItem])
def list_auth_security_events(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
    user_id: Optional[int] = None,
    device_id: Optional[str] = None,
    ip: Optional[str] = None,
    event_type: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    _ = current_user
    q = select(AuthSecurityEvent).order_by(AuthSecurityEvent.created_at.desc())
    if user_id is not None:
        q = q.where(AuthSecurityEvent.user_id == user_id)
    if device_id:
        q = q.where(AuthSecurityEvent.device_id == device_id[:128])
    if ip:
        q = q.where(AuthSecurityEvent.ip_address == ip[:45])
    if event_type:
        q = q.where(AuthSecurityEvent.event_type == event_type[:128])
    if from_date is not None:
        q = q.where(AuthSecurityEvent.created_at >= from_date)
    if to_date is not None:
        q = q.where(AuthSecurityEvent.created_at <= to_date)
    rows = db.execute(q.limit(limit)).scalars().all()
    return list(rows)


@router.get("/events/summary", response_model=AuthSecurityEventsSummary)
def auth_security_events_summary(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
    window_hours: int = Query(default=24, ge=1, le=168),
):
    _ = current_user
    since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    stmt = (
        select(AuthSecurityEvent.event_type, func.count())
        .where(AuthSecurityEvent.created_at >= since)
        .group_by(AuthSecurityEvent.event_type)
    )
    rows = db.execute(stmt).all()
    counts = {str(et): int(n) for et, n in rows}
    total = sum(counts.values())
    flags = SecuritySignalService.detect_anomalies(db)
    return AuthSecurityEventsSummary(
        total_window=total,
        counts_by_type=counts,
        anomaly_flags=flags,
    )


@router.get("/legacy-persons/shutdown-readiness")
def legacy_persons_shutdown_readiness(
    successor_identity_hits: int = Query(default=0, ge=0, description="Hits observés sur GET .../identity (externe / métrique), 0 si inconnu"),
    current_user: AdminUser = Depends(get_current_user),
):
    """Phase 4C.4 — go/no-go pour couper ALLOW_LEGACY_UNAUTHENTICATED_KYC (lecture seule)."""
    _ = current_user
    from services.persons.legacy_persons_shutdown_readiness import (
        build_legacy_persons_shutdown_readiness_report,
    )

    return build_legacy_persons_shutdown_readiness_report(successor_identity_hits=successor_identity_hits)


@router.get("/legacy-persons/metrics-export")
def legacy_persons_metrics_export(
    current_user: AdminUser = Depends(get_current_user),
):
    """Phase 4C.8 — export JSON des métriques legacy persons (in-process), pour scraping / jobs."""
    _ = current_user
    from services.persons.legacy_persons_metrics import build_legacy_persons_metrics_export

    return build_legacy_persons_metrics_export()


@router.get("/anomalies", response_model=SecurityAnomaliesResponse)
def security_correlation_anomalies(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    """
    Moteur de corrélation (lecture seule). N’envoie pas de webhooks ;
    utiliser ``evaluate_and_alert`` depuis un job planifié si besoin.
    """
    _ = current_user
    findings = run_all_detections(db)
    legacy = SecuritySignalService.detect_anomalies(db)
    fd = findings_to_dicts(findings)
    geng = assess_global_peers(db)
    return SecurityAnomaliesResponse(
        generated_at=datetime.now(timezone.utc),
        findings=[SecurityCorrelationFindingSchema.model_validate(x) for x in fd],
        legacy_flags=legacy,
        global_risk_index=geng.risk_score,
        global_risk_level=geng.risk_level,
        engine_signals=signals_to_dicts(geng.signals),
    )


@router.get("/user-risk/{user_id}", response_model=SecurityUserRiskResponse)
def security_user_risk(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("view_sensitive_data")),
    window_hours: int = Query(default=168, ge=1, le=720),
):
    score, findings, n = user_risk_profile(db, user_id, window_hours=window_hours)
    fd = findings_to_dicts(findings)
    uass = assess_user_risk(db, user_id, window_hours=window_hours)
    out = SecurityUserRiskResponse(
        user_id=user_id,
        risk_score=uass.risk_level,
        risk_index=uass.risk_score,
        findings=[SecurityCorrelationFindingSchema.model_validate(x) for x in fd],
        recent_event_count=n,
        engine_signals=signals_to_dicts(uass.signals),
    )
    record_sensitive_action_completed(
        user_id=current_user.id,
        action_key="view_sensitive_data",
        request=request,
        db=db,
        extra={
            "endpoint": "GET /admin/security/user-risk/{user_id}",
            "data_scope": "security_risk",
            "target_user_id": user_id,
            "window_hours": window_hours,
        },
    )
    db.commit()
    return out


@router.get("/passkeys/config", response_model=PasskeysSecurityConfigResponse)
def passkeys_security_config(
    probe: bool = Query(
        False,
        description="Si true, tente un GET sur les URLs .well-known via WEBAUTHN_PUBLIC_BASE_URL",
    ),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    _ = db
    _ = current_user
    data = build_passkeys_admin_config_dict(probe=probe)
    return PasskeysSecurityConfigResponse(**data)


@router.post("/unblock-user", response_model=AdminSecurityActionResponse)
def admin_security_unblock_user(
    request: Request,
    body: AdminSecurityUserIdBody,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("security_settings_change")),
):
    """Lève verrouillage temporaire, blocage refresh et flag — réinitialise step-up sessions."""
    user = db.get(AdminUser, body.user_id)
    if user is None:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="security_settings_change",
            request=request,
            db=db,
            reason="admin_unblock_user_not_found",
            extra={"target_user_id": body.user_id},
        )
        db.commit()
        return AdminSecurityActionResponse(ok=False, detail="user_not_found")
    user.security_account_locked_until = None
    user.security_refresh_blocked = False
    user.security_flagged = False
    for s in (
        db.query(AuthSession)
        .filter(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .all()
    ):
        s.step_up_otp_required = False
    db.commit()
    record_sensitive_action_completed(
        user_id=current_user.id,
        action_key="security_settings_change",
        request=request,
        db=db,
        extra={"step": "admin_unblock_user", "target_user_id": user.id},
    )
    return AdminSecurityActionResponse(ok=True, detail="unblocked")


@router.post("/reset-risk", response_model=AdminSecurityActionResponse)
def admin_security_reset_risk(
    request: Request,
    body: AdminSecurityUserIdBody,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("security_settings_change")),
):
    """Score global à zéro + même effet qu’un déblocage opérationnel."""
    user = db.get(AdminUser, body.user_id)
    if user is None:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="security_settings_change",
            request=request,
            db=db,
            reason="admin_reset_risk_user_not_found",
            extra={"target_user_id": body.user_id},
        )
        db.commit()
        return AdminSecurityActionResponse(ok=False, detail="user_not_found")
    now = datetime.now(timezone.utc)
    row = db.query(AuthGlobalRiskScore).filter(AuthGlobalRiskScore.user_id == user.id).first()
    if row:
        row.score = 0
        row.level = "LOW"
        row.updated_at = now
    else:
        db.add(AuthGlobalRiskScore(user_id=user.id, score=0, level="LOW", updated_at=now))
    user.security_account_locked_until = None
    user.security_refresh_blocked = False
    user.security_flagged = False
    for s in (
        db.query(AuthSession)
        .filter(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .all()
    ):
        s.step_up_otp_required = False
    db.commit()
    record_sensitive_action_completed(
        user_id=current_user.id,
        action_key="security_settings_change",
        request=request,
        db=db,
        extra={"step": "admin_reset_risk", "target_user_id": user.id},
    )
    return AdminSecurityActionResponse(ok=True, detail="risk_reset")


def _fake_request_for_orchestrator_preview(device_id: Optional[str]) -> Any:
    return SimpleNamespace(
        headers={"x-device-id": device_id or "admin-preview-device"},
        client=SimpleNamespace(host="127.0.0.1"),
    )


@router.get("/auth-orchestrator/preview", response_model=AdaptiveAuthDecisionPayload)
def auth_orchestrator_preview(
    request: Request,
    user_id: int = Query(..., ge=1),
    device_id: Optional[str] = Query(None, max_length=128),
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("view_sensitive_data")),
):
    """Simulation de décision pour un utilisateur (support / QA / sécurité)."""
    from services.auth.adaptive_auth_orchestrator import (
        is_adaptive_auth_enabled,
        orchestrate_login_strategy_from_request,
    )

    if not is_adaptive_auth_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADAPTIVE_AUTH_ENABLED=false",
        )
    user = db.get(AdminUser, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    req = _fake_request_for_orchestrator_preview(device_id)
    ident = (
        {"kind": "email", "value": str(user.email).strip().lower()}
        if getattr(user, "email", None)
        else {"kind": "phone_e164", "value": str(getattr(user, "mobile_e164", "") or "+0000")}
    )
    decision, _ = orchestrate_login_strategy_from_request(
        db,
        req,
        user,
        device_header=device_id or "admin-preview-device",
        login_identifier=ident,
        login_channel="orchestrate",
        attestation_trusted=False,
    )
    payload = AdaptiveAuthDecisionPayload(**decision.to_dict())
    record_sensitive_action_completed(
        user_id=current_user.id,
        action_key="view_sensitive_data",
        request=request,
        db=db,
        extra={
            "endpoint": "GET /admin/security/auth-orchestrator/preview",
            "data_scope": "auth_orchestration_preview",
            "target_user_id": user_id,
        },
    )
    db.commit()
    return payload


@router.get("/auth-orchestrator/decision-log", response_model=List[AuthSecurityEventItem])
def auth_orchestrator_decision_log(
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("view_sensitive_data")),
    limit: int = Query(default=100, ge=1, le=500),
):
    """Dernières décisions persistées (``auth.login.orchestrated``)."""
    q = (
        select(AuthSecurityEvent)
        .where(AuthSecurityEvent.event_type == "auth.login.orchestrated")
        .order_by(AuthSecurityEvent.created_at.desc())
        .limit(limit)
    )
    rows = db.execute(q).scalars().all()
    record_sensitive_action_completed(
        user_id=current_user.id,
        action_key="view_sensitive_data",
        request=request,
        db=db,
        extra={
            "endpoint": "GET /admin/security/auth-orchestrator/decision-log",
            "data_scope": "auth_security_events",
            "record_count": len(rows),
            "export_type": "orchestrator_decisions",
        },
    )
    db.commit()
    return list(rows)


@router.get("/session-intelligence/logs", response_model=List[AuthSecurityEventItem])
def list_session_intelligence_logs(
    request: Request,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("view_sensitive_data")),
    limit: int = Query(default=100, ge=1, le=500),
):
    """Événements liés à la session intelligence / risque continu (préfixe ``auth.session.``)."""
    q = (
        select(AuthSecurityEvent)
        .where(AuthSecurityEvent.event_type.like("auth.session.%"))
        .order_by(AuthSecurityEvent.created_at.desc())
        .limit(limit)
    )
    rows = db.execute(q).scalars().all()
    record_sensitive_action_completed(
        user_id=current_user.id,
        action_key="view_sensitive_data",
        request=request,
        db=db,
        extra={
            "endpoint": "GET /admin/security/session-intelligence/logs",
            "data_scope": "session_intelligence",
            "record_count": len(rows),
        },
    )
    db.commit()
    return list(rows)


@router.get("/session-intelligence/{session_id}", response_model=SessionIntelligenceResponse)
def get_session_intelligence_row(
    request: Request,
    session_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("view_sensitive_data")),
):
    row = db.query(AuthSessionIntelligence).filter(AuthSessionIntelligence.session_id == session_id).first()
    if row is None:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="view_sensitive_data",
            request=request,
            db=db,
            reason="session_intelligence_not_found",
            extra={"session_id": str(session_id), "data_scope": "session_intelligence"},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_intelligence_not_found")
    out = SessionIntelligenceResponse.model_validate(row)
    record_sensitive_action_completed(
        user_id=current_user.id,
        action_key="view_sensitive_data",
        request=request,
        db=db,
        extra={
            "endpoint": "GET /admin/security/session-intelligence/{session_id}",
            "data_scope": "session_intelligence",
            "session_id": str(session_id),
        },
    )
    db.commit()
    return out


@router.get("/session-intelligence/probe-continuous-auth")
def probe_continuous_auth_dependency(
    current_user: AdminUser = Depends(require_continuous_auth_for_action("view_sensitive_data")),
):
    """Vérifie que la dépendance d’auth continue passe (exemple d’intégration)."""
    return {"ok": True, "user_id": current_user.id}
