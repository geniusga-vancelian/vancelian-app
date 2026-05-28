"""Persistence reconciliation_discrepancies — insert idempotent par fingerprint."""
from __future__ import annotations

import hashlib
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from .discrepancy_models import ReconciliationDiscrepancy


def build_discrepancy_fingerprint(
    *,
    person_id: UUID,
    layer: str,
    discrepancy_type: str,
    reference_id: str | None,
    wallet_address: str | None = None,
) -> str:
    payload = "|".join(
        [
            str(person_id),
            layer.strip().lower(),
            discrepancy_type.strip().lower(),
            (reference_id or "").strip().lower(),
            (wallet_address or "").strip().lower(),
        ]
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def _iso_dt(value: Any) -> str | None:
    if value is None:
        return None
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def discrepancy_to_dict(row: ReconciliationDiscrepancy) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "person_id": str(row.person_id),
        "wallet_address": row.wallet_address,
        "layer": row.layer,
        "asset": row.asset,
        "discrepancy_type": row.discrepancy_type,
        "db_amount": str(row.db_amount) if row.db_amount is not None else None,
        "onchain_amount": str(row.onchain_amount) if row.onchain_amount is not None else None,
        "delta": str(row.delta) if row.delta is not None else None,
        "severity": row.severity,
        "status": row.status,
        "reference_type": row.reference_type,
        "reference_id": row.reference_id,
        "fingerprint": row.fingerprint,
        "metadata_json": row.metadata_json,
        "created_at": _iso_dt(row.created_at),
        "resolved_at": _iso_dt(row.resolved_at),
    }


class DiscrepancyRepository:

    @staticmethod
    def find_by_fingerprint(db: Session, fingerprint: str) -> ReconciliationDiscrepancy | None:
        return (
            db.query(ReconciliationDiscrepancy)
            .filter(ReconciliationDiscrepancy.fingerprint == fingerprint)
            .first()
        )

    @staticmethod
    def upsert_open(
        db: Session,
        *,
        person_id: UUID,
        layer: str,
        discrepancy_type: str,
        severity: str = "P2",
        wallet_address: str | None = None,
        asset: str | None = None,
        db_amount: Decimal | None = None,
        onchain_amount: Decimal | None = None,
        delta: Decimal | None = None,
        reference_type: str | None = None,
        reference_id: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> tuple[ReconciliationDiscrepancy, bool]:
        fingerprint = build_discrepancy_fingerprint(
            person_id=person_id,
            layer=layer,
            discrepancy_type=discrepancy_type,
            reference_id=reference_id,
            wallet_address=wallet_address,
        )
        existing = DiscrepancyRepository.find_by_fingerprint(db, fingerprint)
        if existing is not None:
            if existing.status != "open":
                existing.status = "open"
                existing.resolved_at = None
                existing.metadata_json = metadata_json or existing.metadata_json
                db.add(existing)
                db.flush()
            return existing, False

        row = ReconciliationDiscrepancy(
            person_id=person_id,
            wallet_address=(wallet_address or "").strip().lower() or None,
            layer=layer,
            asset=asset.upper() if asset else None,
            discrepancy_type=discrepancy_type,
            db_amount=db_amount,
            onchain_amount=onchain_amount,
            delta=delta,
            severity=severity,
            status="open",
            reference_type=reference_type,
            reference_id=reference_id,
            fingerprint=fingerprint,
            metadata_json=metadata_json,
        )
        db.add(row)
        db.flush()
        return row, True

    @staticmethod
    def list_open_for_person(db: Session, person_id: UUID) -> list[ReconciliationDiscrepancy]:
        return (
            db.query(ReconciliationDiscrepancy)
            .filter(
                ReconciliationDiscrepancy.person_id == person_id,
                ReconciliationDiscrepancy.status == "open",
            )
            .order_by(ReconciliationDiscrepancy.created_at.desc())
            .all()
        )

    @staticmethod
    def find_by_id(db: Session, discrepancy_id: UUID) -> ReconciliationDiscrepancy | None:
        return (
            db.query(ReconciliationDiscrepancy)
            .filter(ReconciliationDiscrepancy.id == discrepancy_id)
            .first()
        )

    @staticmethod
    def list_filtered(
        db: Session,
        *,
        person_id: UUID | None = None,
        wallet_address: str | None = None,
        layer: str | None = None,
        asset: str | None = None,
        discrepancy_type: str | None = None,
        severity: str | None = None,
        status: str | None = None,
        created_from: Any | None = None,
        created_to: Any | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[ReconciliationDiscrepancy], int]:
        q = db.query(ReconciliationDiscrepancy)
        if person_id is not None:
            q = q.filter(ReconciliationDiscrepancy.person_id == person_id)
        if wallet_address:
            q = q.filter(
                ReconciliationDiscrepancy.wallet_address == wallet_address.strip().lower(),
            )
        if layer:
            q = q.filter(ReconciliationDiscrepancy.layer == layer.strip().lower())
        if asset:
            q = q.filter(ReconciliationDiscrepancy.asset == asset.strip().upper())
        if discrepancy_type:
            q = q.filter(ReconciliationDiscrepancy.discrepancy_type == discrepancy_type.strip().lower())
        if severity:
            q = q.filter(ReconciliationDiscrepancy.severity == severity.strip().upper())
        if status:
            q = q.filter(ReconciliationDiscrepancy.status == status.strip().lower())
        if created_from is not None:
            q = q.filter(ReconciliationDiscrepancy.created_at >= created_from)
        if created_to is not None:
            q = q.filter(ReconciliationDiscrepancy.created_at <= created_to)

        total = q.count()
        rows = (
            q.order_by(ReconciliationDiscrepancy.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return rows, total

    @staticmethod
    def update_status(
        db: Session,
        row: ReconciliationDiscrepancy,
        *,
        status: str,
        resolved: bool,
        metadata_patch: dict[str, Any] | None = None,
    ) -> ReconciliationDiscrepancy:
        from datetime import datetime, timezone

        row.status = status
        if resolved:
            row.resolved_at = datetime.now(timezone.utc)
        if metadata_patch:
            base = row.metadata_json if isinstance(row.metadata_json, dict) else {}
            row.metadata_json = {**base, **metadata_patch}
        db.add(row)
        db.flush()
        return row
