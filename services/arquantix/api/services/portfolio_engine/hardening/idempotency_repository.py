"""Repository for pe_idempotency_keys."""
from __future__ import annotations

from sqlalchemy import and_
from sqlalchemy.orm import Session

from .idempotency_models import IdempotencyKey


class IdempotencyRepository:

    @staticmethod
    def get_by_key_and_scope(
        db: Session, *, idempotency_key: str, scope: str
    ) -> IdempotencyKey | None:
        return (
            db.query(IdempotencyKey)
            .filter(
                and_(
                    IdempotencyKey.idempotency_key == idempotency_key,
                    IdempotencyKey.scope == scope,
                )
            )
            .first()
        )

    @staticmethod
    def reserve(db: Session, *, data: dict) -> IdempotencyKey:
        row = IdempotencyKey(**data)
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def store_response(
        db: Session,
        row: IdempotencyKey,
        *,
        response_status: int,
        response_body: dict | None,
    ) -> IdempotencyKey:
        row.response_status = response_status
        row.response_body = response_body
        db.flush()
        return row
