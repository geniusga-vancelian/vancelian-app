"""Phase 4A — journal bundle append-only (shadow mode, écriture miroir)."""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.bundle_ledger.enums import (
    BundleLedgerDirection,
    BundleLedgerEventType,
    BundleLedgerSourceSystem,
    BundleLedgerStatus,
)
from services.portfolio_engine.bundle_ledger.models import BundleLedgerEntry
from services.portfolio_engine.instruments.models import Instrument
from services.portfolio_engine.assets.models import Asset

logger = logging.getLogger(__name__)

CASH_EVENT_TYPES = frozenset({
    BundleLedgerEventType.BUNDLE_DEPOSIT.value,
    BundleLedgerEventType.BUNDLE_WITHDRAWAL.value,
    BundleLedgerEventType.BUNDLE_CASH_RESERVED.value,
    BundleLedgerEventType.BUNDLE_CASH_RELEASED.value,
})

ALLOCATION_EVENT_TYPES = frozenset({
    BundleLedgerEventType.BUNDLE_ALLOCATION_BUY.value,
    BundleLedgerEventType.BUNDLE_ALLOCATION_SELL.value,
    BundleLedgerEventType.BUNDLE_REBALANCE_BUY.value,
    BundleLedgerEventType.BUNDLE_REBALANCE_SELL.value,
})

RECOVERY_EVENT_TYPES = frozenset({
    BundleLedgerEventType.BUNDLE_RECOVERY_ADJUSTMENT.value,
})


def build_idempotency_key(
    *,
    source_system: str,
    source_id: str | None,
    event_type: str,
    direction: str,
) -> str:
    sid = (source_id or "").strip() or "_"
    return f"{source_system}:{sid}:{event_type}:{direction}"


def _asset_symbol_for_instrument(db: Session, instrument_id: UUID | None) -> str | None:
    if instrument_id is None:
        return None
    row = (
        db.query(Asset.symbol)
        .join(Instrument, Instrument.asset_id == Asset.id)
        .filter(Instrument.id == instrument_id)
        .first()
    )
    return str(row[0]).upper() if row else None


def append_bundle_ledger_entry(
    db: Session,
    *,
    person_id: UUID,
    bundle_portfolio_id: UUID,
    event_type: str,
    asset_symbol: str,
    quantity: Decimal,
    direction: str,
    source_system: str,
    source_id: str | None = None,
    asset_instrument_id: UUID | None = None,
    amount_usd: Decimal | None = None,
    batch_id: str | None = None,
    leg_id: str | None = None,
    transaction_intent_id: UUID | None = None,
    status: str = BundleLedgerStatus.CONFIRMED.value,
    metadata: dict[str, Any] | None = None,
) -> BundleLedgerEntry:
    """Append-only — idempotent sur ``idempotency_key``."""
    idempotency_key = build_idempotency_key(
        source_system=source_system,
        source_id=source_id,
        event_type=event_type,
        direction=direction,
    )
    existing = (
        db.query(BundleLedgerEntry)
        .filter(BundleLedgerEntry.idempotency_key == idempotency_key)
        .first()
    )
    if existing is not None:
        logger.debug("bundle_ledger.idempotent_skip key=%s", idempotency_key)
        return existing

    entry = BundleLedgerEntry(
        person_id=person_id,
        bundle_portfolio_id=bundle_portfolio_id,
        event_type=event_type,
        asset_symbol=asset_symbol.upper(),
        asset_instrument_id=asset_instrument_id,
        quantity=quantity,
        amount_usd=amount_usd,
        direction=direction,
        source_system=source_system,
        source_id=source_id,
        batch_id=batch_id,
        leg_id=leg_id,
        transaction_intent_id=transaction_intent_id,
        status=status,
        idempotency_key=idempotency_key,
        metadata_=metadata or {},
    )
    db.add(entry)
    db.flush()
    logger.info(
        "bundle_ledger.append event=%s portfolio=%s batch=%s qty=%s %s",
        event_type,
        bundle_portfolio_id,
        batch_id,
        quantity,
        asset_symbol,
    )
    return entry


def record_reversal_event(
    db: Session,
    *,
    original: BundleLedgerEntry,
    reason: str,
    metadata: dict[str, Any] | None = None,
) -> BundleLedgerEntry:
    """Correction comptable — nouvelle entrée inverse, jamais d'update destructif."""
    reverse_direction = {
        BundleLedgerDirection.CREDIT.value: BundleLedgerDirection.DEBIT.value,
        BundleLedgerDirection.DEBIT.value: BundleLedgerDirection.CREDIT.value,
        BundleLedgerDirection.INFO.value: BundleLedgerDirection.INFO.value,
    }.get(original.direction, BundleLedgerDirection.INFO.value)

    reversal_meta = {
        "reversal_of_entry_id": str(original.id),
        "reason": reason,
        **(metadata or {}),
    }
    source_id = f"reversal:{original.id}"
    return append_bundle_ledger_entry(
        db,
        person_id=original.person_id,
        bundle_portfolio_id=original.bundle_portfolio_id,
        event_type=BundleLedgerEventType.BUNDLE_RECOVERY_ADJUSTMENT.value,
        asset_symbol=original.asset_symbol,
        quantity=original.quantity,
        direction=reverse_direction,
        source_system=BundleLedgerSourceSystem.MANUAL_RECOVERY.value,
        source_id=source_id,
        asset_instrument_id=original.asset_instrument_id,
        amount_usd=original.amount_usd,
        batch_id=original.batch_id,
        leg_id=original.leg_id,
        transaction_intent_id=original.transaction_intent_id,
        status=BundleLedgerStatus.REVERSED.value,
        metadata=reversal_meta,
    )


def _resolve_person_id(db: Session, *, person_id: UUID | None, client_id: UUID) -> UUID | None:
    if person_id is not None:
        return person_id
    from services.portfolio_engine.clients.models import Client

    row = db.query(Client.person_id).filter(Client.id == client_id).first()
    return row[0] if row and row[0] is not None else None


def record_bundle_deposit(
    db: Session,
    *,
    person_id: UUID | None,
    client_id: UUID,
    bundle_portfolio_id: UUID,
    entry_asset: str,
    entry_instrument_id: UUID,
    amount: Decimal,
    batch_id: str,
    cost_basis_eur: Decimal | None = None,
    cash_leg_atom_id: str | None = None,
) -> BundleLedgerEntry | None:
    pid = _resolve_person_id(db, person_id=person_id, client_id=client_id)
    if pid is None:
        return None
    return append_bundle_ledger_entry(
        db,
        person_id=pid,
        bundle_portfolio_id=bundle_portfolio_id,
        event_type=BundleLedgerEventType.BUNDLE_DEPOSIT.value,
        asset_symbol=entry_asset,
        asset_instrument_id=entry_instrument_id,
        quantity=amount,
        direction=BundleLedgerDirection.CREDIT.value,
        source_system=BundleLedgerSourceSystem.PE_TRANSFER.value,
        source_id=f"{batch_id}:fund",
        batch_id=batch_id,
        metadata={
            "client_id": str(client_id),
            "cost_basis_eur": float(cost_basis_eur) if cost_basis_eur is not None else None,
            "cash_leg_atom_id": cash_leg_atom_id,
            "shadow_mode": True,
        },
    )


def record_bundle_withdrawal(
    db: Session,
    *,
    person_id: UUID | None,
    client_id: UUID,
    bundle_portfolio_id: UUID,
    entry_asset: str,
    entry_instrument_id: UUID,
    amount: Decimal,
    batch_id: str,
    cost_basis_eur: Decimal | None = None,
    partial: bool = False,
) -> BundleLedgerEntry | None:
    pid = _resolve_person_id(db, person_id=person_id, client_id=client_id)
    if pid is None:
        return None
    return append_bundle_ledger_entry(
        db,
        person_id=pid,
        bundle_portfolio_id=bundle_portfolio_id,
        event_type=BundleLedgerEventType.BUNDLE_WITHDRAWAL.value,
        asset_symbol=entry_asset,
        asset_instrument_id=entry_instrument_id,
        quantity=amount,
        direction=BundleLedgerDirection.DEBIT.value,
        source_system=BundleLedgerSourceSystem.PE_TRANSFER.value,
        source_id=f"{batch_id}:release",
        batch_id=batch_id,
        metadata={
            "client_id": str(client_id),
            "cost_basis_eur": float(cost_basis_eur) if cost_basis_eur is not None else None,
            "partial_release": partial,
            "shadow_mode": True,
        },
    )


def record_allocation_buy(
    db: Session,
    *,
    person_id: UUID,
    bundle_portfolio_id: UUID,
    target_instrument_id: UUID,
    target_asset_symbol: str,
    crypto_received: Decimal,
    entry_asset_consumed: Decimal,
    entry_instrument_id: UUID,
    entry_asset_symbol: str,
    batch_id: str | None = None,
    leg_id: str | None = None,
    swap_id: UUID | None = None,
    cost_basis_eur: Decimal | None = None,
    planned_entry_consumed: Decimal | None = None,
    planned_crypto_received: Decimal | None = None,
) -> list[BundleLedgerEntry]:
    source_id = str(swap_id) if swap_id else (leg_id or batch_id or "allocation")
    entries: list[BundleLedgerEntry] = []

    buy_metadata = {
        "entry_asset": entry_asset_symbol,
        "entry_instrument_id": str(entry_instrument_id),
        "entry_consumed": float(entry_asset_consumed),
        "cost_basis_eur": float(cost_basis_eur) if cost_basis_eur is not None else None,
        "swap_id": str(swap_id) if swap_id else None,
        "shadow_mode": True,
    }
    if planned_entry_consumed is not None:
        buy_metadata["planned_entry_consumed"] = float(planned_entry_consumed)
    if planned_crypto_received is not None:
        buy_metadata["planned_crypto_received"] = float(planned_crypto_received)

    entries.append(
        append_bundle_ledger_entry(
            db,
            person_id=person_id,
            bundle_portfolio_id=bundle_portfolio_id,
            event_type=BundleLedgerEventType.BUNDLE_ALLOCATION_BUY.value,
            asset_symbol=target_asset_symbol,
            asset_instrument_id=target_instrument_id,
            quantity=crypto_received,
            direction=BundleLedgerDirection.CREDIT.value,
            source_system=BundleLedgerSourceSystem.LIFI.value,
            source_id=source_id,
            batch_id=batch_id,
            leg_id=leg_id,
            metadata=buy_metadata,
        )
    )
    entries.append(
        append_bundle_ledger_entry(
            db,
            person_id=person_id,
            bundle_portfolio_id=bundle_portfolio_id,
            event_type=BundleLedgerEventType.BUNDLE_CASH_RELEASED.value,
            asset_symbol=entry_asset_symbol,
            asset_instrument_id=entry_instrument_id,
            quantity=entry_asset_consumed,
            direction=BundleLedgerDirection.DEBIT.value,
            source_system=BundleLedgerSourceSystem.LIFI.value,
            source_id=f"{source_id}:cash",
            batch_id=batch_id,
            leg_id=leg_id,
            metadata={
                "linked_event": BundleLedgerEventType.BUNDLE_ALLOCATION_BUY.value,
                "swap_id": str(swap_id) if swap_id else None,
                "shadow_mode": True,
            },
        )
    )
    return entries


def record_allocation_sell(
    db: Session,
    *,
    person_id: UUID,
    bundle_portfolio_id: UUID,
    instrument_id: UUID,
    asset_symbol: str,
    sell_qty: Decimal,
    entry_received: Decimal,
    entry_instrument_id: UUID,
    entry_asset_symbol: str,
    batch_id: str | None = None,
    leg_id: str | None = None,
    swap_id: UUID | None = None,
    withdraw_sell: bool = False,
    cost_basis_eur: Decimal | None = None,
) -> list[BundleLedgerEntry]:
    source_id = str(swap_id) if swap_id else (leg_id or batch_id or "sell")
    entries: list[BundleLedgerEntry] = []

    entries.append(
        append_bundle_ledger_entry(
            db,
            person_id=person_id,
            bundle_portfolio_id=bundle_portfolio_id,
            event_type=BundleLedgerEventType.BUNDLE_ALLOCATION_SELL.value,
            asset_symbol=asset_symbol,
            asset_instrument_id=instrument_id,
            quantity=sell_qty,
            direction=BundleLedgerDirection.DEBIT.value,
            source_system=BundleLedgerSourceSystem.LIFI.value,
            source_id=source_id,
            batch_id=batch_id,
            leg_id=leg_id,
            metadata={
                "entry_asset": entry_asset_symbol,
                "entry_received": float(entry_received),
                "withdraw_sell": withdraw_sell,
                "cost_basis_eur": float(cost_basis_eur) if cost_basis_eur is not None else None,
                "swap_id": str(swap_id) if swap_id else None,
                "shadow_mode": True,
            },
        )
    )
    entries.append(
        append_bundle_ledger_entry(
            db,
            person_id=person_id,
            bundle_portfolio_id=bundle_portfolio_id,
            event_type=BundleLedgerEventType.BUNDLE_DEPOSIT.value,
            asset_symbol=entry_asset_symbol,
            asset_instrument_id=entry_instrument_id,
            quantity=entry_received,
            direction=BundleLedgerDirection.CREDIT.value,
            source_system=BundleLedgerSourceSystem.LIFI.value,
            source_id=f"{source_id}:cash_credit",
            batch_id=batch_id,
            leg_id=leg_id,
            metadata={
                "linked_event": BundleLedgerEventType.BUNDLE_ALLOCATION_SELL.value,
                "internal_cash_leg": True,
                "withdraw_sell": withdraw_sell,
                "swap_id": str(swap_id) if swap_id else None,
                "shadow_mode": True,
            },
        )
    )
    return entries


def record_rebalance(
    db: Session,
    *,
    person_id: UUID,
    bundle_portfolio_id: UUID,
    side: str,
    instrument_id: UUID,
    asset_symbol: str,
    quantity: Decimal,
    entry_instrument_id: UUID,
    entry_asset_symbol: str,
    entry_amount: Decimal,
    batch_id: str | None = None,
    leg_id: str | None = None,
    swap_id: UUID | None = None,
    cost_basis_eur: Decimal | None = None,
) -> list[BundleLedgerEntry]:
    source_id = str(swap_id) if swap_id else (leg_id or batch_id or f"rebalance_{side}")
    if side == "buy":
        event_type = BundleLedgerEventType.BUNDLE_REBALANCE_BUY.value
        direction = BundleLedgerDirection.CREDIT.value
    else:
        event_type = BundleLedgerEventType.BUNDLE_REBALANCE_SELL.value
        direction = BundleLedgerDirection.DEBIT.value

    entries: list[BundleLedgerEntry] = [
        append_bundle_ledger_entry(
            db,
            person_id=person_id,
            bundle_portfolio_id=bundle_portfolio_id,
            event_type=event_type,
            asset_symbol=asset_symbol,
            asset_instrument_id=instrument_id,
            quantity=quantity,
            direction=direction,
            source_system=BundleLedgerSourceSystem.LIFI.value,
            source_id=source_id,
            batch_id=batch_id,
            leg_id=leg_id,
            metadata={
                "entry_asset": entry_asset_symbol,
                "entry_amount": float(entry_amount),
                "cost_basis_eur": float(cost_basis_eur) if cost_basis_eur is not None else None,
                "swap_id": str(swap_id) if swap_id else None,
                "shadow_mode": True,
            },
        )
    ]
    cash_event = (
        BundleLedgerEventType.BUNDLE_CASH_RELEASED.value
        if side == "buy"
        else BundleLedgerEventType.BUNDLE_DEPOSIT.value
    )
    cash_direction = (
        BundleLedgerDirection.DEBIT.value if side == "buy" else BundleLedgerDirection.CREDIT.value
    )
    entries.append(
        append_bundle_ledger_entry(
            db,
            person_id=person_id,
            bundle_portfolio_id=bundle_portfolio_id,
            event_type=cash_event,
            asset_symbol=entry_asset_symbol,
            asset_instrument_id=entry_instrument_id,
            quantity=entry_amount,
            direction=cash_direction,
            source_system=BundleLedgerSourceSystem.LIFI.value,
            source_id=f"{source_id}:cash",
            batch_id=batch_id,
            leg_id=leg_id,
            metadata={
                "linked_event": event_type,
                "internal_cash_leg": True,
                "swap_id": str(swap_id) if swap_id else None,
                "shadow_mode": True,
            },
        )
    )
    return entries


def record_recovery_event(
    db: Session,
    *,
    person_id: UUID,
    bundle_portfolio_id: UUID,
    batch_id: str,
    reason: str,
    lock_type: str,
    previous_status: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> BundleLedgerEntry:
    return append_bundle_ledger_entry(
        db,
        person_id=person_id,
        bundle_portfolio_id=bundle_portfolio_id,
        event_type=BundleLedgerEventType.BUNDLE_RECOVERY_ADJUSTMENT.value,
        asset_symbol="USDC",
        quantity=Decimal("0"),
        direction=BundleLedgerDirection.INFO.value,
        source_system=BundleLedgerSourceSystem.MANUAL_RECOVERY.value,
        source_id=f"{batch_id}:{lock_type}:expired",
        batch_id=batch_id,
        status=BundleLedgerStatus.CONFIRMED.value,
        metadata={
            "lock_type": lock_type,
            "previous_status": previous_status,
            "reason": reason,
            "cash_leg_preserved": True,
            **(metadata or {}),
            "shadow_mode": True,
        },
    )


def record_withdraw_finalize_info(
    db: Session,
    *,
    person_id: UUID,
    bundle_portfolio_id: UUID,
    batch_id: str,
    released: bool,
    reason: str | None = None,
    cash_available: float | None = None,
    requested: float | None = None,
    released_amount: float | None = None,
) -> BundleLedgerEntry:
    return append_bundle_ledger_entry(
        db,
        person_id=person_id,
        bundle_portfolio_id=bundle_portfolio_id,
        event_type=BundleLedgerEventType.BUNDLE_RECOVERY_ADJUSTMENT.value,
        asset_symbol="USDC",
        quantity=Decimal(str(released_amount or 0)),
        direction=BundleLedgerDirection.INFO.value,
        source_system=BundleLedgerSourceSystem.PE_TRANSFER.value,
        source_id=f"{batch_id}:withdraw_finalize",
        batch_id=batch_id,
        metadata={
            "finalize_released": released,
            "reason": reason,
            "cash_available": cash_available,
            "requested": requested,
            "released_amount": released_amount,
            "shadow_mode": True,
        },
    )


def _serialize_entry(entry: BundleLedgerEntry) -> dict[str, Any]:
    return {
        "id": str(entry.id),
        "person_id": str(entry.person_id),
        "bundle_portfolio_id": str(entry.bundle_portfolio_id),
        "event_type": entry.event_type,
        "asset_symbol": entry.asset_symbol,
        "asset_instrument_id": str(entry.asset_instrument_id) if entry.asset_instrument_id else None,
        "quantity": float(entry.quantity),
        "amount_usd": float(entry.amount_usd) if entry.amount_usd is not None else None,
        "direction": entry.direction,
        "source_system": entry.source_system,
        "source_id": entry.source_id,
        "batch_id": entry.batch_id,
        "leg_id": entry.leg_id,
        "transaction_intent_id": (
            str(entry.transaction_intent_id) if entry.transaction_intent_id else None
        ),
        "status": entry.status,
        "metadata": entry.metadata_ or {},
        "created_at": entry.created_at.isoformat() if entry.created_at else None,
    }


def list_bundle_ledger_entries(
    db: Session,
    *,
    bundle_portfolio_id: UUID,
    person_id: UUID | None = None,
    batch_id: str | None = None,
    limit: int = 200,
) -> dict[str, Any]:
    q = db.query(BundleLedgerEntry).filter(
        BundleLedgerEntry.bundle_portfolio_id == bundle_portfolio_id,
    )
    if person_id is not None:
        q = q.filter(BundleLedgerEntry.person_id == person_id)
    if batch_id:
        q = q.filter(BundleLedgerEntry.batch_id == batch_id)

    rows = q.order_by(BundleLedgerEntry.created_at.desc()).limit(limit).all()
    serialized = [_serialize_entry(r) for r in rows]

    cash_movements = [e for e in serialized if e["event_type"] in CASH_EVENT_TYPES]
    allocation_movements = [e for e in serialized if e["event_type"] in ALLOCATION_EVENT_TYPES]
    recovery_events = [e for e in serialized if e["event_type"] in RECOVERY_EVENT_TYPES]

    return {
        "bundle_portfolio_id": str(bundle_portfolio_id),
        "entries": serialized,
        "cash_movements": cash_movements,
        "allocation_movements": allocation_movements,
        "recovery_events": recovery_events,
        "source_links": [
            {
                "source_system": e["source_system"],
                "source_id": e["source_id"],
                "batch_id": e["batch_id"],
                "leg_id": e["leg_id"],
                "event_type": e["event_type"],
            }
            for e in serialized
            if e.get("source_id")
        ],
        "shadow_mode": True,
        "count": len(serialized),
    }
