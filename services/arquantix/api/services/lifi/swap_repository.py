"""Repository sessions swap."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.lifi.enums import SwapSessionStatus
from services.lifi.models import PersonWalletSwap


class PersonWalletSwapRepository:

    @staticmethod
    def create(
        db: Session,
        *,
        person_id: UUID,
        from_asset: str,
        to_asset: str,
        from_chain: str,
        to_chain: str,
        amount_in: Decimal,
        slippage_bps: int,
        expires_at: datetime,
    ) -> PersonWalletSwap:
        row = PersonWalletSwap(
            person_id=person_id,
            status=SwapSessionStatus.PENDING.value,
            from_asset=from_asset,
            to_asset=to_asset,
            from_chain=from_chain,
            to_chain=to_chain,
            amount_in=amount_in,
            slippage_bps=slippage_bps,
            expires_at=expires_at,
            audit_log=[],
        )
        db.add(row)
        db.flush()
        return row

    @staticmethod
    def get_for_person(db: Session, *, swap_id: UUID, person_id: UUID) -> PersonWalletSwap | None:
        return (
            db.query(PersonWalletSwap)
            .filter(
                PersonWalletSwap.id == swap_id,
                PersonWalletSwap.person_id == person_id,
            )
            .first()
        )

    @staticmethod
    def append_audit(row: PersonWalletSwap, event: dict[str, Any]) -> None:
        log = list(row.audit_log or [])
        log.append({**event, "at": datetime.now(timezone.utc).isoformat()})
        row.audit_log = log

    @staticmethod
    def mark_expired_if_needed(row: PersonWalletSwap) -> bool:
        if row.status in {
            SwapSessionStatus.CONFIRMED.value,
            SwapSessionStatus.FAILED.value,
            SwapSessionStatus.EXPIRED.value,
            SwapSessionStatus.SUBMITTED.value,
        }:
            return False
        if row.expires_at and row.expires_at <= datetime.now(timezone.utc):
            row.status = SwapSessionStatus.EXPIRED.value
            return True
        return False

    @staticmethod
    def list_confirmed_for_person_asset(
        db: Session,
        *,
        person_id: UUID,
        asset: str,
        limit: int = 200,
    ) -> list[PersonWalletSwap]:
        asset_u = asset.strip().upper()
        return (
            db.query(PersonWalletSwap)
            .filter(
                PersonWalletSwap.person_id == person_id,
                PersonWalletSwap.status == SwapSessionStatus.CONFIRMED.value,
                (
                    (PersonWalletSwap.from_asset == asset_u)
                    | (PersonWalletSwap.to_asset == asset_u)
                ),
            )
            .order_by(PersonWalletSwap.confirmed_at.desc(), PersonWalletSwap.created_at.desc())
            .limit(limit)
            .all()
        )
