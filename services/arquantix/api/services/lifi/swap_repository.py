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

    # Événement audit posé juste avant la diffusion on-chain (signature serveur, D1).
    BROADCAST_INITIATED_EVENT = "swap_broadcast_initiated"

    @classmethod
    def mark_broadcasting(
        cls,
        row: PersonWalletSwap,
        *,
        idempotency_key: str,
        privy_wallet_id: str,
        chain_id: int,
        to: str,
        data: str,
        value: Any,
        gas_limit: Any,
        signing_wallet_address: str | None = None,
    ) -> None:
        """Passe le swap en ``BROADCASTING`` et persiste de quoi rejouer la diffusion.

        Les champs de transaction sont stockés en clair pour permettre un rejeu **à
        l'identique** (même corps RPC) avec la même clé d'idempotence Privy au retry —
        condition de la garantie exactly-once.
        """
        row.status = SwapSessionStatus.BROADCASTING.value
        cls.append_audit(
            row,
            {
                "event": cls.BROADCAST_INITIATED_EVENT,
                "idempotency_key": idempotency_key,
                "privy_wallet_id": privy_wallet_id,
                "chain_id": int(chain_id),
                "to": to,
                "data": data,
                "value": value,
                "gas_limit": gas_limit,
                "signing_wallet_address": signing_wallet_address,
            },
        )

    @classmethod
    def read_broadcast_intent(cls, row: PersonWalletSwap) -> dict[str, Any] | None:
        """Dernier ``swap_broadcast_initiated`` persisté (rejeu retry), ou ``None``."""
        for event in reversed(list(row.audit_log or [])):
            if isinstance(event, dict) and event.get("event") == cls.BROADCAST_INITIATED_EVENT:
                return event
        return None

    @staticmethod
    def mark_expired_if_needed(row: PersonWalletSwap) -> bool:
        if row.status in {
            SwapSessionStatus.CONFIRMED.value,
            SwapSessionStatus.FAILED.value,
            SwapSessionStatus.EXPIRED.value,
            SwapSessionStatus.SUBMITTED.value,
            # In-flight on-chain : ne jamais expirer un swap déjà en cours de diffusion (D1).
            SwapSessionStatus.BROADCASTING.value,
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
