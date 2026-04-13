"""Repository for pe_audit_events. Append-only: no update, no delete."""
from sqlalchemy.orm import Session

from .audit_models import AuditEvent


class AuditRepository:

    @staticmethod
    def create(db: Session, *, data: dict) -> AuditEvent:
        row = AuditEvent(**data)
        db.add(row)
        db.flush()
        return row
