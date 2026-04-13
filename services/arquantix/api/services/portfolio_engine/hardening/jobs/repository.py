"""Repository for pe_job_runs."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from .models import JobRun


class JobRunRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> JobRun:
        row = JobRun(**data)
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def mark_completed(db: Session, run: JobRun, *, metadata: Optional[dict] = None) -> JobRun:
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        if metadata:
            run.metadata_ = {**(run.metadata_ or {}), **metadata}
        db.flush()
        return run

    @staticmethod
    def mark_failed(db: Session, run: JobRun, *, error_message: str) -> JobRun:
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        run.error_message = error_message
        db.flush()
        return run

    @staticmethod
    def get_by_id(db: Session, run_id: UUID) -> Optional[JobRun]:
        return db.query(JobRun).filter(JobRun.id == run_id).first()

    @staticmethod
    def list_runs(
        db: Session,
        *,
        job_type: Optional[str] = None,
        scope_type: Optional[str] = None,
        scope_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[JobRun], int]:
        query = db.query(JobRun)
        if job_type:
            query = query.filter(JobRun.job_type == job_type)
        if scope_type:
            query = query.filter(JobRun.scope_type == scope_type)
        if scope_id:
            query = query.filter(JobRun.scope_id == scope_id)
        if status:
            query = query.filter(JobRun.status == status)
        total = query.count()
        items = query.order_by(JobRun.started_at.desc()).offset(skip).limit(limit).all()
        return items, total
