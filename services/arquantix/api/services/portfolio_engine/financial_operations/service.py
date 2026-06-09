"""Service — Portfolio Financial Operation Guard (PR-4)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from services.portfolio_engine.financial_operations.config import (
    default_portfolio_financial_operation_ttl_seconds,
    portfolio_financial_operation_guard_enabled,
)
from services.portfolio_engine.financial_operations.enums import (
    PortfolioFinancialOperationStatus,
    PortfolioFinancialOperationType,
)
from services.portfolio_engine.financial_operations.exceptions import (
    PortfolioFinancialOperationInProgress409,
)
from services.portfolio_engine.financial_operations.models import PortfolioFinancialOperation


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_uuid(value: UUID | str) -> UUID:
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


def _operation_type_value(
    operation_type: PortfolioFinancialOperationType | str,
) -> str:
    if isinstance(operation_type, PortfolioFinancialOperationType):
        return operation_type.value
    return str(operation_type)


@dataclass(frozen=True)
class AcquirePortfolioFinancialOperationResult:
    acquired: bool
    skipped: bool
    idempotent: bool
    operation: PortfolioFinancialOperation | None


def expire_stale_portfolio_financial_operations(
    db: Session,
    *,
    portfolio_id: UUID | str | None = None,
    now: datetime | None = None,
) -> int:
    """Marque EXPIRED les opérations ACTIVE dont expires_at est dépassé."""
    ts = now or _utcnow()
    q = db.query(PortfolioFinancialOperation).filter(
        PortfolioFinancialOperation.status == PortfolioFinancialOperationStatus.ACTIVE.value,
        PortfolioFinancialOperation.released_at.is_(None),
        PortfolioFinancialOperation.expires_at < ts,
    )
    if portfolio_id is not None:
        q = q.filter(PortfolioFinancialOperation.portfolio_id == _as_uuid(portfolio_id))
    rows = q.with_for_update(skip_locked=True).all()
    for row in rows:
        row.status = PortfolioFinancialOperationStatus.EXPIRED.value
        row.released_at = ts
    if rows:
        db.flush()
    return len(rows)


def find_active_portfolio_financial_operation(
    db: Session,
    *,
    portfolio_id: UUID | str,
    for_update: bool = False,
) -> PortfolioFinancialOperation | None:
    expire_stale_portfolio_financial_operations(db, portfolio_id=portfolio_id)
    q = db.query(PortfolioFinancialOperation).filter(
        PortfolioFinancialOperation.portfolio_id == _as_uuid(portfolio_id),
        PortfolioFinancialOperation.status == PortfolioFinancialOperationStatus.ACTIVE.value,
        PortfolioFinancialOperation.released_at.is_(None),
    )
    if for_update:
        q = q.with_for_update()
    return q.order_by(PortfolioFinancialOperation.started_at.desc()).first()


def acquire_portfolio_financial_operation(
    db: Session,
    *,
    portfolio_id: UUID | str,
    operation_type: PortfolioFinancialOperationType | str,
    execution_id: UUID | str,
    ttl_seconds: int | None = None,
) -> AcquirePortfolioFinancialOperationResult:
    """Acquiert le slot portefeuille — flag OFF → no-op strict."""
    if not portfolio_financial_operation_guard_enabled():
        return AcquirePortfolioFinancialOperationResult(
            acquired=False,
            skipped=True,
            idempotent=False,
            operation=None,
        )

    pid = _as_uuid(portfolio_id)
    eid = _as_uuid(execution_id)
    op_type = _operation_type_value(operation_type)
    ttl = ttl_seconds or default_portfolio_financial_operation_ttl_seconds(op_type)
    now = _utcnow()
    expires_at = now + timedelta(seconds=ttl)

    expire_stale_portfolio_financial_operations(db, portfolio_id=pid, now=now)

    active = find_active_portfolio_financial_operation(db, portfolio_id=pid, for_update=True)
    if active is not None:
        if active.execution_id == eid and active.operation_type == op_type:
            return AcquirePortfolioFinancialOperationResult(
                acquired=True,
                skipped=False,
                idempotent=True,
                operation=active,
            )
        raise PortfolioFinancialOperationInProgress409(
            portfolio_id=pid,
            existing_operation_type=str(active.operation_type),
            existing_execution_id=active.execution_id,
            requested_operation_type=op_type,
            requested_execution_id=eid,
        )

    row = PortfolioFinancialOperation(
        portfolio_id=pid,
        operation_type=op_type,
        execution_id=eid,
        status=PortfolioFinancialOperationStatus.ACTIVE.value,
        started_at=now,
        expires_at=expires_at,
    )
    savepoint = db.begin_nested()
    try:
        db.add(row)
        db.flush()
    except IntegrityError as exc:
        savepoint.rollback()
        raced = find_active_portfolio_financial_operation(db, portfolio_id=pid, for_update=True)
        if raced is not None and raced.execution_id == eid and raced.operation_type == op_type:
            return AcquirePortfolioFinancialOperationResult(
                acquired=True,
                skipped=False,
                idempotent=True,
                operation=raced,
            )
        if raced is not None:
            raise PortfolioFinancialOperationInProgress409(
                portfolio_id=pid,
                existing_operation_type=str(raced.operation_type),
                existing_execution_id=raced.execution_id,
                requested_operation_type=op_type,
                requested_execution_id=eid,
            ) from exc
        raise

    return AcquirePortfolioFinancialOperationResult(
        acquired=True,
        skipped=False,
        idempotent=False,
        operation=row,
    )


def release_portfolio_financial_operation(
    db: Session,
    *,
    portfolio_id: UUID | str,
    execution_id: UUID | str,
    terminal_status: str = PortfolioFinancialOperationStatus.RELEASED.value,
) -> bool:
    """Libère une opération active — flag OFF → no-op."""
    if not portfolio_financial_operation_guard_enabled():
        return False

    pid = _as_uuid(portfolio_id)
    eid = _as_uuid(execution_id)
    now = _utcnow()
    row = (
        db.query(PortfolioFinancialOperation)
        .filter(
            PortfolioFinancialOperation.portfolio_id == pid,
            PortfolioFinancialOperation.execution_id == eid,
            PortfolioFinancialOperation.status == PortfolioFinancialOperationStatus.ACTIVE.value,
            PortfolioFinancialOperation.released_at.is_(None),
        )
        .with_for_update()
        .first()
    )
    if row is None:
        return False

    status = terminal_status
    if status not in {
        PortfolioFinancialOperationStatus.RELEASED.value,
        PortfolioFinancialOperationStatus.FAILED.value,
        PortfolioFinancialOperationStatus.EXPIRED.value,
    }:
        status = PortfolioFinancialOperationStatus.RELEASED.value

    row.status = status
    row.released_at = now
    db.flush()
    return True


def audit_portfolio_financial_operations(
    db: Session,
    *,
    portfolio_id: UUID | str,
    limit: int = 10,
) -> dict[str, Any]:
    """Audit read-only — opération active + historique récent."""
    pid = _as_uuid(portfolio_id)
    expire_stale_portfolio_financial_operations(db, portfolio_id=pid)
    active = find_active_portfolio_financial_operation(db, portfolio_id=pid)
    recent = (
        db.query(PortfolioFinancialOperation)
        .filter(PortfolioFinancialOperation.portfolio_id == pid)
        .order_by(PortfolioFinancialOperation.started_at.desc())
        .limit(limit)
        .all()
    )

    def _serialize(row: PortfolioFinancialOperation | None) -> dict[str, Any] | None:
        if row is None:
            return None
        return {
            "id": str(row.id),
            "portfolio_id": str(row.portfolio_id),
            "operation_type": row.operation_type,
            "execution_id": str(row.execution_id),
            "status": row.status,
            "started_at": row.started_at.isoformat() if row.started_at else None,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "released_at": row.released_at.isoformat() if row.released_at else None,
        }

    return {
        "portfolio_id": str(pid),
        "guard_enabled": portfolio_financial_operation_guard_enabled(),
        "active_operation": _serialize(active),
        "recent_operations": [_serialize(r) for r in recent],
    }
