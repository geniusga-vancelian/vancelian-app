"""Repository for pe_scheduled_jobs."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import ScheduledJob


class ScheduledJobRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> ScheduledJob:
        row = ScheduledJob(**data)
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def get_by_id(db: Session, job_id: UUID) -> Optional[ScheduledJob]:
        return db.query(ScheduledJob).filter(ScheduledJob.id == job_id).first()

    @staticmethod
    def list_jobs(
        db: Session,
        *,
        job_type: Optional[str] = None,
        is_enabled: Optional[bool] = None,
        scope_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ScheduledJob], int]:
        query = db.query(ScheduledJob)
        if job_type:
            query = query.filter(ScheduledJob.job_type == job_type)
        if is_enabled is not None:
            query = query.filter(ScheduledJob.is_enabled == is_enabled)
        if scope_type:
            query = query.filter(ScheduledJob.scope_type == scope_type)
        total = query.count()
        items = query.order_by(ScheduledJob.created_at.desc()).offset(skip).limit(limit).all()
        return items, total

    @staticmethod
    def list_due(db: Session, *, now: datetime) -> list[ScheduledJob]:
        return (
            db.query(ScheduledJob)
            .filter(
                ScheduledJob.is_enabled.is_(True),
                ScheduledJob.schedule_type != "manual_only",
                ScheduledJob.next_run_at <= now,
            )
            .order_by(ScheduledJob.next_run_at.asc())
            .all()
        )

    @staticmethod
    def update(db: Session, job: ScheduledJob, **kwargs) -> ScheduledJob:
        for k, v in kwargs.items():
            setattr(job, k, v)
        db.flush()
        return job
