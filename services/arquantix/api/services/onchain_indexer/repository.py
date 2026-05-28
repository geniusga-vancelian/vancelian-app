"""Repository raw_onchain_events — insert idempotent."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from .models import RawOnChainEvent


class RawOnChainEventRepository:

    @staticmethod
    def find_by_chain_tx_log(
        db: Session,
        *,
        chain_id: int,
        tx_hash: str,
        log_index: int,
    ) -> RawOnChainEvent | None:
        normalized = str(tx_hash or "").strip().lower()
        return (
            db.query(RawOnChainEvent)
            .filter(
                RawOnChainEvent.chain_id == chain_id,
                RawOnChainEvent.tx_hash == normalized,
                RawOnChainEvent.log_index == log_index,
            )
            .first()
        )

    @staticmethod
    def insert_if_absent(db: Session, *, data: dict[str, Any]) -> tuple[RawOnChainEvent, bool]:
        """
        Insère un événement si absent.

        Returns:
            (row, created) — ``created=False`` si déjà présent (idempotent).
        """
        chain_id = int(data["chain_id"])
        tx_hash = str(data["tx_hash"]).strip().lower()
        log_index = int(data.get("log_index") or 0)

        existing = RawOnChainEventRepository.find_by_chain_tx_log(
            db,
            chain_id=chain_id,
            tx_hash=tx_hash,
            log_index=log_index,
        )
        if existing is not None:
            return existing, False

        row = RawOnChainEvent(
            chain_id=chain_id,
            block_number=data.get("block_number"),
            tx_hash=tx_hash,
            log_index=log_index,
            contract_address=data.get("contract_address"),
            event_type=str(data.get("event_type") or "erc20_transfer"),
            wallet_address=str(data["wallet_address"]).strip().lower(),
            asset=str(data["asset"]).upper(),
            amount_raw=Decimal(str(data["amount_raw"])),
            payload_json=data.get("payload_json"),
        )
        db.add(row)
        db.flush()
        return row, True
