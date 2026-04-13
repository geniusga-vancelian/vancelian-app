"""Idempotency service (Hardening Subphase 1).

Reusable service that protects critical write endpoints from duplicate
processing. Callers interact through `check_or_reserve` and
`store_response`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from .hashing import compute_request_hash
from .idempotency_repository import IdempotencyRepository

DEFAULT_TTL_HOURS = 24


class IdempotencyConflictError(Exception):
    """Same idempotency key submitted with a different request payload."""

    def __init__(self, key: str, scope: str):
        super().__init__(
            f"Idempotency key '{key}' in scope '{scope}' already used "
            "with a different request payload"
        )


class IdempotencyInProgressError(Exception):
    """Same idempotency key is already being processed."""

    def __init__(self, key: str, scope: str):
        super().__init__(
            f"Idempotency key '{key}' in scope '{scope}' is being processed"
        )


class IdempotencyResult:
    """Return value from `check_or_reserve`.

    If `replayed` is True, `stored_status` and `stored_body` contain the
    previously stored response and the caller should return it immediately.
    """

    def __init__(
        self,
        replayed: bool,
        stored_status: Optional[int] = None,
        stored_body: Optional[dict] = None,
    ):
        self.replayed = replayed
        self.stored_status = stored_status
        self.stored_body = stored_body


_repo = IdempotencyRepository()


class IdempotencyService:

    @staticmethod
    def check_or_reserve(
        db: Session,
        *,
        idempotency_key: str,
        scope: str,
        request_data: Any,
        ttl_hours: int = DEFAULT_TTL_HOURS,
    ) -> IdempotencyResult:
        """Check existing key or reserve a new one.

        Returns an `IdempotencyResult`:
        - replayed=True  → caller should return stored response
        - replayed=False → caller should proceed, then call `store_response`

        Raises IdempotencyConflictError or IdempotencyInProgressError.
        """
        req_hash = compute_request_hash(request_data)
        existing = _repo.get_by_key_and_scope(
            db, idempotency_key=idempotency_key, scope=scope
        )

        if existing is not None:
            if existing.request_hash != req_hash:
                raise IdempotencyConflictError(idempotency_key, scope)

            if existing.response_status is not None:
                return IdempotencyResult(
                    replayed=True,
                    stored_status=existing.response_status,
                    stored_body=existing.response_body,
                )

            raise IdempotencyInProgressError(idempotency_key, scope)

        now = datetime.now(timezone.utc)
        _repo.reserve(
            db,
            data={
                "idempotency_key": idempotency_key,
                "scope": scope,
                "request_hash": req_hash,
                "created_at": now,
                "expires_at": now + timedelta(hours=ttl_hours),
            },
        )
        return IdempotencyResult(replayed=False)

    @staticmethod
    def store_response(
        db: Session,
        *,
        idempotency_key: str,
        scope: str,
        response_status: int,
        response_body: dict | None,
    ) -> None:
        """Persist the response for a previously reserved key."""
        row = _repo.get_by_key_and_scope(
            db, idempotency_key=idempotency_key, scope=scope
        )
        if row is None:
            return
        _repo.store_response(
            db, row, response_status=response_status, response_body=response_body,
        )
