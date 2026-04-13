"""Dashboard produit — métriques agrégées risque (Phase 5) ; données = store en mémoire du processus."""
from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, Depends, Query

from auth import get_current_user
from database import AdminUser
from services.security.risk_calibration import compute_calibration_suggestions
from services.security.risk_dashboard_store import (
    aggregate_experiments,
    aggregate_factors,
    aggregate_segments,
    aggregate_summary,
    compute_alerts,
    get_feedback_snapshots_copy,
    recent_decisions,
)
from services.security.risk_feedback import RiskFeedback

router = APIRouter(prefix="/admin/security", tags=["admin-risk-dashboard"])


@router.get("/risk-dashboard/summary")
def risk_dashboard_summary(
    current_user: AdminUser = Depends(get_current_user),
    window_hours: float = Query(default=24.0, ge=1.0, le=168.0),
) -> dict[str, Any]:
    _ = current_user
    return aggregate_summary(window_hours=window_hours)


@router.get("/risk-dashboard/factors")
def risk_dashboard_factors(
    current_user: AdminUser = Depends(get_current_user),
    window_hours: float = Query(default=24.0, ge=1.0, le=168.0),
) -> dict[str, Any]:
    _ = current_user
    return aggregate_factors(window_hours=window_hours)


@router.get("/risk-dashboard/segments")
def risk_dashboard_segments(
    current_user: AdminUser = Depends(get_current_user),
    window_hours: float = Query(default=24.0, ge=1.0, le=168.0),
) -> dict[str, Any]:
    _ = current_user
    return aggregate_segments(window_hours=window_hours)


@router.get("/risk-dashboard/experiments")
def risk_dashboard_experiments(
    current_user: AdminUser = Depends(get_current_user),
    window_hours: float = Query(default=24.0, ge=1.0, le=168.0),
) -> dict[str, Any]:
    _ = current_user
    return aggregate_experiments(window_hours=window_hours)


@router.get("/risk-dashboard/alerts")
def risk_dashboard_alerts(
    current_user: AdminUser = Depends(get_current_user),
    window_hours: float = Query(default=24.0, ge=1.0, le=168.0),
) -> dict[str, Any]:
    _ = current_user
    return compute_alerts(window_hours=window_hours)


@router.get("/risk-dashboard/recent")
def risk_dashboard_recent(
    current_user: AdminUser = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
) -> dict[str, Any]:
    _ = current_user
    return {"decisions": recent_decisions(limit=limit)}


@router.get("/risk-dashboard/calibration-suggestions")
def risk_dashboard_calibration_suggestions(
    current_user: AdminUser = Depends(get_current_user),
) -> dict[str, Any]:
    _ = current_user
    fbs = get_feedback_snapshots_copy()
    models: List[RiskFeedback] = []
    for f in fbs:
        models.append(
            RiskFeedback(
                action_key=f.action_key,
                user_id="dashboard",
                risk_score=0.0,
                risk_level="unknown",
                decision="",
                outcome="",
                feedback_type=f.feedback_type,
                factor_codes=list(f.factor_codes),
            )
        )
    suggestions = compute_calibration_suggestions(models)
    return {
        "suggestions": [s.model_dump() for s in suggestions],
        "feedback_events_used": len(models),
    }
