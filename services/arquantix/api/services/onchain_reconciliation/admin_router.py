"""Router admin — pilotage des écarts de réconciliation (Phase 5A)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from database import get_db
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.hardening.security.dependencies import require_admin_or_ops

from . import admin_service
from . import intent_admin_service
from .admin_export import export_audit_csv
from .correction_apply import CorrectionApplyError
from .correction_policy import CorrectionPolicyError
from .correction_workflow import CorrectionWorkflowError
from . import correction_workflow
from .raw_event_consumption import RawEventConsumptionError
from services.defi_observability.admin_service import get_job_run_admin, list_job_runs_admin
from services.transaction_intents.transaction_intent_health import (
    build_admin_health_payload,
    reconcile_stale_intents,
)

from .schemas import (
    CorrectionApplyResponse,
    CorrectionAuditRead,
    CorrectionPreviewResponse,
    DiscrepancyDetailResponse,
    DiscrepancyListItem,
    DiscrepancyListResponse,
    DiscrepancyRead,
    DefiJobRunListResponse,
    DefiJobRunSummary,
    IntentHealthResponse,
    IntentListResponse,
    IntentStaleReconcileResponse,
    TransactionIntentSummary,
    PreviewCorrectionRequest,
    RejectCorrectionRequest,
    RequestCorrectionRequest,
    ResolveManuallyRequest,
    StatusChangeRequest,
)

onchain_reconciliation_admin_router = APIRouter(
    prefix="/api/admin/onchain-reconciliation",
    tags=["onchain-reconciliation-admin"],
)
_guard = require_admin_or_ops()


def _parse_dt(value: Optional[str], field: str) -> Optional[datetime]:
    if not value:
        return None
    try:
        text = value.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"invalid_{field}",
        ) from exc


def _actor_id(actor: ActorContext) -> str:
    return str(actor.actor_id or actor.actor_type or "admin")


@onchain_reconciliation_admin_router.get("/export.csv")
def export_csv(
    export_type: str = Query("audit", description="discrepancies | corrections | audit"),
    person_id: Optional[UUID] = Query(None),
    wallet_address: Optional[str] = Query(None),
    layer: Optional[str] = Query(None),
    asset: Optional[str] = Query(None),
    discrepancy_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(5000, ge=1, le=10000),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    _ = actor
    try:
        filename, content = export_audit_csv(
            db,
            export_type=export_type,
            filters={
                "person_id": person_id,
                "wallet_address": wallet_address,
                "layer": layer,
                "asset": asset,
                "discrepancy_type": discrepancy_type,
                "severity": severity,
                "status": status,
            },
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@onchain_reconciliation_admin_router.get(
    "/jobs",
    response_model=DefiJobRunListResponse,
)
def list_defi_observability_jobs(
    job_name: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    _ = actor
    items, total = list_job_runs_admin(db, job_name=job_name, skip=skip, limit=limit)
    return DefiJobRunListResponse(
        items=[DefiJobRunSummary.model_validate(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@onchain_reconciliation_admin_router.get(
    "/jobs/{run_id}",
    response_model=DefiJobRunSummary,
)
def get_defi_observability_job(
    run_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    _ = actor
    row = get_job_run_admin(db, run_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job_run_not_found")
    return DefiJobRunSummary.model_validate(row)


@onchain_reconciliation_admin_router.get(
    "/health",
    response_model=IntentHealthResponse,
)
def get_transaction_intent_health(
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    _ = actor
    payload = build_admin_health_payload(db)
    return IntentHealthResponse.model_validate(payload)


@onchain_reconciliation_admin_router.post(
    "/health/reconcile-stale",
    response_model=IntentStaleReconcileResponse,
)
def post_reconcile_stale_intents(
    dry_run: bool = Query(True, description="Si true, aucune écriture"),
    person_id: Optional[UUID] = Query(None),
    limit: int = Query(500, ge=1, le=2000),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    _ = actor
    report = reconcile_stale_intents(
        db,
        dry_run=dry_run,
        person_id=person_id,
        limit=limit,
    )
    if not dry_run:
        db.commit()
    else:
        db.rollback()
    return IntentStaleReconcileResponse.model_validate(report)


@onchain_reconciliation_admin_router.get("/orphaned-intents")
def list_orphaned_intents(
    older_than_minutes: int = Query(10, ge=0, le=10080),
    person_id: Optional[UUID] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    """Visibilité — intents orchestrateur non terminaux dont le swap lié est terminal."""
    _ = actor
    from services.transaction_intents.orphan_intent_reconciliation import (
        find_orphaned_lifi_intents,
    )

    items = find_orphaned_lifi_intents(
        db,
        older_than_minutes=older_than_minutes,
        limit=limit,
        person_id=person_id,
    )
    return {"count": len(items), "items": items}


@onchain_reconciliation_admin_router.post("/orphaned-intents/reconcile")
def post_reconcile_orphaned_intents(
    dry_run: bool = Query(True, description="Si true, aucune écriture"),
    older_than_minutes: int = Query(10, ge=0, le=10080),
    person_id: Optional[UUID] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    """Repair read/repair-only — propage l'état terminal du swap à l'intent orphelin."""
    _ = actor
    from services.transaction_intents.orphan_intent_reconciliation import (
        reconcile_orphaned_lifi_intents,
    )

    report = reconcile_orphaned_lifi_intents(
        db,
        dry_run=dry_run,
        older_than_minutes=older_than_minutes,
        limit=limit,
        person_id=person_id,
    )
    if dry_run:
        db.rollback()
    return report


@onchain_reconciliation_admin_router.get(
    "/intents",
    response_model=IntentListResponse,
)
def list_transaction_intents(
    person_id: Optional[UUID] = Query(None),
    wallet_address: Optional[str] = Query(None),
    product_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    tx_hash: Optional[str] = Query(None),
    created_from: Optional[str] = Query(None),
    created_to: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    _ = actor
    items, total = intent_admin_service.list_intents_admin(
        db,
        filters={
            "person_id": person_id,
            "wallet_address": wallet_address,
            "product_type": product_type,
            "status": status,
            "tx_hash": tx_hash,
            "created_from": _parse_dt(created_from, "created_from"),
            "created_to": _parse_dt(created_to, "created_to"),
        },
        skip=skip,
        limit=limit,
    )
    return IntentListResponse(
        items=[TransactionIntentSummary.model_validate(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@onchain_reconciliation_admin_router.get(
    "/discrepancies",
    response_model=DiscrepancyListResponse,
)
def list_discrepancies(
    person_id: Optional[UUID] = Query(None),
    wallet_address: Optional[str] = Query(None),
    layer: Optional[str] = Query(None),
    asset: Optional[str] = Query(None),
    discrepancy_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    created_from: Optional[str] = Query(None),
    created_to: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    _ = actor
    items, total = admin_service.list_discrepancies_admin(
        db,
        filters={
            "person_id": person_id,
            "wallet_address": wallet_address,
            "layer": layer,
            "asset": asset,
            "discrepancy_type": discrepancy_type,
            "severity": severity,
            "status": status,
            "created_from": _parse_dt(created_from, "created_from"),
            "created_to": _parse_dt(created_to, "created_to"),
        },
        skip=skip,
        limit=limit,
    )
    return DiscrepancyListResponse(
        items=[DiscrepancyListItem.model_validate(i) for i in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@onchain_reconciliation_admin_router.get(
    "/discrepancies/{discrepancy_id}",
    response_model=DiscrepancyDetailResponse,
)
def get_discrepancy(
    discrepancy_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    _ = actor
    detail = admin_service.get_discrepancy_detail(db, discrepancy_id)
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="discrepancy_not_found")
    return DiscrepancyDetailResponse.model_validate(detail)


@onchain_reconciliation_admin_router.post(
    "/discrepancies/{discrepancy_id}/acknowledge",
    response_model=DiscrepancyRead,
)
def acknowledge_discrepancy(
    discrepancy_id: UUID,
    body: StatusChangeRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        row = admin_service.acknowledge_discrepancy(
            db,
            discrepancy_id=discrepancy_id,
            actor_id=_actor_id(actor),
            note=body.note,
        )
        db.commit()
        return DiscrepancyRead.model_validate(row)
    except LookupError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="discrepancy_not_found")


@onchain_reconciliation_admin_router.post(
    "/discrepancies/{discrepancy_id}/ignore",
    response_model=DiscrepancyRead,
)
def ignore_discrepancy(
    discrepancy_id: UUID,
    body: StatusChangeRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        row = admin_service.ignore_discrepancy(
            db,
            discrepancy_id=discrepancy_id,
            actor_id=_actor_id(actor),
            note=body.note,
        )
        db.commit()
        return DiscrepancyRead.model_validate(row)
    except LookupError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="discrepancy_not_found")


@onchain_reconciliation_admin_router.post(
    "/discrepancies/{discrepancy_id}/resolve-manually",
    response_model=DiscrepancyRead,
)
def resolve_manually(
    discrepancy_id: UUID,
    body: ResolveManuallyRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        row = admin_service.resolve_manually(
            db,
            discrepancy_id=discrepancy_id,
            actor_id=_actor_id(actor),
            note=body.note,
            resolution_code=body.resolution_code,
            extra_metadata=body.metadata_json,
        )
        db.commit()
        return DiscrepancyRead.model_validate(row)
    except LookupError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="discrepancy_not_found")


@onchain_reconciliation_admin_router.post(
    "/discrepancies/{discrepancy_id}/preview-correction",
    response_model=CorrectionPreviewResponse,
)
def preview_correction(
    discrepancy_id: UUID,
    body: PreviewCorrectionRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        preview = admin_service.preview_correction(
            db,
            discrepancy_id=discrepancy_id,
            actor_id=_actor_id(actor),
            explicit_action=body.action,
        )
        db.commit()
        return CorrectionPreviewResponse.model_validate(preview)
    except LookupError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="discrepancy_not_found")
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _workflow_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, LookupError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@onchain_reconciliation_admin_router.post(
    "/discrepancies/{discrepancy_id}/request-correction",
    response_model=CorrectionAuditRead,
)
def request_correction(
    discrepancy_id: UUID,
    body: RequestCorrectionRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        row = correction_workflow.request_correction(
            db,
            discrepancy_id=discrepancy_id,
            action=body.action,
            requested_by=_actor_id(actor),
            raw_onchain_event_id=body.raw_onchain_event_id,
            deposit_id=body.deposit_id,
        )
        db.commit()
        return CorrectionAuditRead.model_validate(row)
    except CorrectionPolicyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except CorrectionWorkflowError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RawEventConsumptionError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise _workflow_http_error(exc) from exc


@onchain_reconciliation_admin_router.post(
    "/corrections/{correction_id}/approve",
    response_model=CorrectionAuditRead,
)
def approve_correction(
    correction_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        row = correction_workflow.approve_correction(
            db,
            correction_id=correction_id,
            approved_by=_actor_id(actor),
        )
        db.commit()
        return CorrectionAuditRead.model_validate(row)
    except CorrectionPolicyError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise _workflow_http_error(exc) from exc


@onchain_reconciliation_admin_router.post(
    "/corrections/{correction_id}/reject",
    response_model=CorrectionAuditRead,
)
def reject_correction(
    correction_id: UUID,
    body: RejectCorrectionRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        row = correction_workflow.reject_correction(
            db,
            correction_id=correction_id,
            rejected_by=_actor_id(actor),
            reason=body.reason,
        )
        db.commit()
        return CorrectionAuditRead.model_validate(row)
    except Exception as exc:
        db.rollback()
        raise _workflow_http_error(exc) from exc


@onchain_reconciliation_admin_router.post(
    "/corrections/{correction_id}/apply",
    response_model=CorrectionApplyResponse,
)
def apply_correction(
    correction_id: UUID,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        result = correction_workflow.apply_approved_correction(
            db,
            correction_id=correction_id,
            actor_id=_actor_id(actor),
        )
        db.commit()
        return CorrectionApplyResponse.model_validate(result)
    except (CorrectionApplyError, CorrectionPolicyError, RawEventConsumptionError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        raise _workflow_http_error(exc) from exc
