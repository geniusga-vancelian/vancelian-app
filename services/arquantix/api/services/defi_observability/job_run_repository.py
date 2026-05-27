"""Repository defi_observability_job_runs."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import DefiObservabilityJobRun

JOB_NAME_TICK = "defi_observability_tick"


def job_run_to_dict(row: DefiObservabilityJobRun) -> dict[str, Any]:
    started = row.started_at
    finished = row.finished_at
    duration_s = None
    if started and finished:
        s = started.replace(tzinfo=timezone.utc) if started.tzinfo is None else started
        f = finished.replace(tzinfo=timezone.utc) if finished.tzinfo is None else finished
        duration_s = round((f - s).total_seconds(), 2)
    return {
        "id": str(row.id),
        "job_name": row.job_name,
        "status": row.status,
        "started_at": started.isoformat() if started else None,
        "finished_at": finished.isoformat() if finished else None,
        "duration_seconds": duration_s,
        "summary_json": row.summary_json,
        "error_json": row.error_json,
    }


class DefiJobRunRepository:

    @staticmethod
    def create(db: Session, *, job_name: str) -> DefiObservabilityJobRun:
        row = DefiObservabilityJobRun(
            job_name=job_name,
            status="running",
            summary_json={"dry_run": None},
        )
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def finish(
        db: Session,
        row: DefiObservabilityJobRun,
        *,
        status: str,
        summary_json: dict[str, Any],
        error_json: Optional[dict[str, Any]] = None,
    ) -> DefiObservabilityJobRun:
        row.status = status
        row.summary_json = summary_json
        row.error_json = error_json
        row.finished_at = datetime.now(timezone.utc)
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def list_recent(
        db: Session,
        *,
        job_name: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[DefiObservabilityJobRun], int]:
        q = db.query(DefiObservabilityJobRun)
        if job_name:
            q = q.filter(DefiObservabilityJobRun.job_name == job_name)
        total = q.count()
        rows = (
            q.order_by(DefiObservabilityJobRun.started_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    @staticmethod
    def find_by_id(db: Session, run_id: UUID) -> Optional[DefiObservabilityJobRun]:
        return db.query(DefiObservabilityJobRun).filter(DefiObservabilityJobRun.id == run_id).first()
