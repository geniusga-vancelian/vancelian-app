"""Admin — historique defi_observability_job_runs."""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .job_run_repository import DefiJobRunRepository, job_run_to_dict


def list_job_runs_admin(
    db: Session,
    *,
    job_name: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    rows, total = DefiJobRunRepository.list_recent(
        db, job_name=job_name, skip=skip, limit=limit
    )
    return [job_run_to_dict(r) for r in rows], total


def get_job_run_admin(db: Session, run_id: UUID) -> Optional[dict[str, Any]]:
    row = DefiJobRunRepository.find_by_id(db, run_id)
    if row is None:
        return None
    return job_run_to_dict(row)
