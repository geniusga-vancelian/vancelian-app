"""Audit service (Hardening Subphase 1).

Append-only audit trail for business events across the Portfolio Engine.
Best-effort: audit failures are logged but do not crash business logic.
"""
import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from .audit_repository import AuditRepository

logger = logging.getLogger(__name__)
_repo = AuditRepository()


class AuditService:

    @staticmethod
    def log_event(
        db: Session,
        *,
        entity_type: str,
        entity_id: Optional[str] = None,
        action: str,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        try:
            _repo.create(
                db,
                data={
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "action": action,
                    "actor_type": actor_type,
                    "actor_id": actor_id,
                    "request_id": request_id,
                    "metadata_": metadata or {},
                },
            )
        except Exception:
            logger.exception("Failed to persist audit event: %s/%s", action, entity_id)

    @staticmethod
    def log_success(
        db: Session,
        *,
        entity_type: str,
        entity_id: Optional[str] = None,
        action: str,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        meta = dict(metadata or {})
        meta["outcome"] = "success"
        AuditService.log_event(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            request_id=request_id,
            metadata=meta,
        )

    @staticmethod
    def log_failure(
        db: Session,
        *,
        entity_type: str,
        entity_id: Optional[str] = None,
        action: str,
        error: str,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
        request_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        meta = dict(metadata or {})
        meta["outcome"] = "failure"
        meta["error"] = error
        AuditService.log_event(
            db,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_type=actor_type,
            actor_id=actor_id,
            request_id=request_id,
            metadata=meta,
        )
