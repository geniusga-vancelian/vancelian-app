"""Repository for pe_reconciliation_reports. Append-only."""
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from .models import ReconciliationReport


class ReconciliationReportRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> ReconciliationReport:
        row = ReconciliationReport(**data)
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def get_by_id(db: Session, report_id: UUID) -> Optional[ReconciliationReport]:
        return db.query(ReconciliationReport).filter(ReconciliationReport.id == report_id).first()

    @staticmethod
    def list_reports(
        db: Session,
        *,
        reconciliation_type: Optional[str] = None,
        scope_type: Optional[str] = None,
        scope_id: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ReconciliationReport], int]:
        query = db.query(ReconciliationReport)
        if reconciliation_type:
            query = query.filter(ReconciliationReport.reconciliation_type == reconciliation_type)
        if scope_type:
            query = query.filter(ReconciliationReport.scope_type == scope_type)
        if scope_id:
            query = query.filter(ReconciliationReport.scope_id == scope_id)
        if status:
            query = query.filter(ReconciliationReport.status == status)
        total = query.count()
        items = query.order_by(ReconciliationReport.created_at.desc()).offset(skip).limit(limit).all()
        return items, total
