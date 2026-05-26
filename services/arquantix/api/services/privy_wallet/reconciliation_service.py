"""Réconciliation ledger Privy ↔ soldes on-chain (batch + auto-heal)."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.exchange.assets import ASSET_PRECISION

from .asset_mapping import normalize_evm_address
from .deposit_backfill import (
    discover_missing_transfers_for_wallet,
    fetch_aggregated_on_chain_balances,
    ingest_transfer_as_deposit,
)
from .enums import PrivyReconciliationItemStatus, PrivyReconciliationRunStatus, PrivyWebhookEventStatus
from .evm_chain_config import CHAIN_LABELS, PRIVY_EVM_PILOT_CHAIN_IDS, resolve_chain_rpc_url
from .models import PersonWalletReconciliationItem, PersonWalletReconciliationRun, PrivyWebhookEvent
from .repository import PersonCryptoWalletRepository, PersonWalletBalanceRepository
from .webhook_service import FUNDS_DEPOSITED_EVENT, PrivyWebhookProcessor

logger = logging.getLogger(__name__)

RECONCILIATION_ASSETS: tuple[str, ...] = ("USDC", "USDT", "ETH", "EURC")
DUST_TOLERANCE_BY_ASSET: dict[str, Decimal] = {
    "USDC": Decimal("0.01"),
    "USDT": Decimal("0.01"),
    "EURC": Decimal("0.01"),
    "ETH": Decimal("0.00001"),
}


@dataclass(frozen=True)
class ReconciliationRunSummary:
    run_id: UUID
    scope: str
    person_id: UUID | None
    status: str
    items_checked: int
    matched_count: int
    healed_count: int
    chain_ahead_count: int
    ledger_ahead_count: int
    mismatch_count: int
    unresolved_count: int
    replayed_webhooks: int
    message: str


def dust_tolerance(asset: str) -> Decimal:
    return DUST_TOLERANCE_BY_ASSET.get(asset.upper(), Decimal("0.01"))


def _ledger_balance_for_asset(
    db: Session,
    *,
    person_id: UUID,
    asset: str,
) -> Decimal:
    repo = PersonWalletBalanceRepository()
    total = Decimal("0")
    for row in repo.list_for_person(db, person_id):
        if row.asset.upper() == asset.upper():
            total += Decimal(str(row.balance or 0))
    return total


def _on_chain_total_for_asset(
    *,
    wallet_address: str,
    asset: str,
    chain_ids: list[int],
) -> tuple[Decimal, dict[int, Decimal]]:
    per_chain = fetch_aggregated_on_chain_balances(
        wallet_address=wallet_address,
        chain_ids=chain_ids,
        assets=[asset],
    )
    by_chain: dict[int, Decimal] = {}
    total = Decimal("0")
    for chain_id in chain_ids:
        amount = per_chain.get((chain_id, asset.upper()), Decimal("0"))
        by_chain[chain_id] = amount
        total += amount
    return total, by_chain


def replay_failed_webhooks_for_person(db: Session, person_id: UUID) -> list[dict[str, Any]]:
    wallet_repo = PersonCryptoWalletRepository()
    wallets = wallet_repo.list_active_for_person(db, person_id)
    addresses = {normalize_evm_address(w.address) for w in wallets if w.address}
    addresses.discard(None)

    processor = PrivyWebhookProcessor()
    results: list[dict[str, Any]] = []

    events = (
        db.query(PrivyWebhookEvent)
        .filter(
            PrivyWebhookEvent.event_type == FUNDS_DEPOSITED_EVENT,
            PrivyWebhookEvent.processing_status == PrivyWebhookEventStatus.FAILED.value,
        )
        .order_by(PrivyWebhookEvent.received_at.desc())
        .limit(500)
        .all()
    )

    for event in events:
        try:
            normalized = processor._normalize_deposit_payload(event.payload_raw)
        except Exception:
            continue
        if normalized.to_address not in addresses:
            continue

        processor._event_repo.update_status(
            db,
            event,
            status=PrivyWebhookEventStatus.RECEIVED.value,
            error_message=None,
        )
        status = processor.process_event(db, event)
        db.refresh(event)
        results.append(
            {
                "event_id": str(event.id),
                "tx_hash": normalized.tx_hash,
                "asset": normalized.asset,
                "amount": str(normalized.amount),
                "processing_status": status,
                "deposit_id": str(event.linked_deposit_id) if event.linked_deposit_id else None,
                "error": event.error_message,
            }
        )
    return results


def run_person_wallet_reconciliation(
    db: Session,
    *,
    person_id: UUID,
    auto_heal: bool = True,
    scope: str = "person",
) -> ReconciliationRunSummary:
    wallet_repo = PersonCryptoWalletRepository()
    wallets = wallet_repo.list_active_for_person(db, person_id)
    if not wallets:
        raise ValueError("Aucun wallet Privy actif pour cette personne")

    primary = wallets[0]
    wallet_address = primary.address
    chain_ids = [cid for cid in PRIVY_EVM_PILOT_CHAIN_IDS if resolve_chain_rpc_url(cid)]

    run = PersonWalletReconciliationRun(
        id=uuid.uuid4(),
        scope=scope,
        person_id=person_id,
        status=PrivyReconciliationRunStatus.RUNNING.value,
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.flush()

    replayed = replay_failed_webhooks_for_person(db, person_id) if auto_heal else []
    healed_count = sum(1 for r in replayed if r.get("processing_status") == PrivyWebhookEventStatus.PROCESSED.value)

    matched_count = 0
    chain_ahead_count = 0
    ledger_ahead_count = 0
    mismatch_count = 0
    unresolved_count = 0
    items_checked = 0

    for asset in RECONCILIATION_ASSETS:
        ledger_total = _ledger_balance_for_asset(db, person_id=person_id, asset=asset)
        on_chain_total, per_chain = _on_chain_total_for_asset(
            wallet_address=wallet_address,
            asset=asset,
            chain_ids=chain_ids,
        )
        delta = on_chain_total - ledger_total
        tolerance = dust_tolerance(asset)

        status = PrivyReconciliationItemStatus.MATCHED.value
        action_taken = "none"
        notes: list[str] = []

        if abs(delta) <= tolerance:
            matched_count += 1
        elif delta > tolerance:
            status = PrivyReconciliationItemStatus.CHAIN_AHEAD.value
            chain_ahead_count += 1
            if auto_heal:
                discovered = []
                for chain_id in chain_ids:
                    if per_chain.get(chain_id, Decimal("0")) <= Decimal("0"):
                        continue
                    discovered.extend(
                        discover_missing_transfers_for_wallet(
                            db,
                            chain_id=chain_id,
                            wallet_address=wallet_address,
                        )
                    )
                ingested = 0
                for transfer in discovered:
                    if transfer["asset"].upper() != asset.upper():
                        continue
                    result = ingest_transfer_as_deposit(
                        db,
                        transfer=transfer,
                        source="reconciliation_scan",
                    )
                    if result.get("status") in (
                        PrivyWebhookEventStatus.PROCESSED.value,
                        "already_ingested",
                    ):
                        ingested += 1
                if ingested:
                    action_taken = "backfill_deposit"
                    healed_count += 1
                    status = PrivyReconciliationItemStatus.HEALED.value
                    notes.append(f"{ingested} dépôt(s) backfillé(s)")
                    ledger_total = _ledger_balance_for_asset(db, person_id=person_id, asset=asset)
                    delta = on_chain_total - ledger_total
                    if abs(delta) <= tolerance:
                        matched_count += 1
                        chain_ahead_count -= 1
                        status = PrivyReconciliationItemStatus.MATCHED.value
                else:
                    unresolved_count += 1
                    status = PrivyReconciliationItemStatus.UNRESOLVED.value
                    notes.append("Écart positif — backfill auto impossible (tx non trouvée)")
        elif delta < -tolerance:
            status = PrivyReconciliationItemStatus.LEDGER_AHEAD.value
            ledger_ahead_count += 1
            mismatch_count += 1
            notes.append("Ledger > on-chain — investigation manuelle requise")

        items_checked += 1
        db.add(
            PersonWalletReconciliationItem(
                id=uuid.uuid4(),
                run_id=run.id,
                person_id=person_id,
                wallet_address=wallet_address,
                chain_id=None,
                chain_label=",".join(CHAIN_LABELS.get(c, str(c)) for c in chain_ids),
                asset=asset,
                ledger_balance=ledger_total,
                on_chain_balance=on_chain_total,
                delta=delta,
                status=status,
                action_taken=action_taken,
                notes="; ".join(notes) if notes else None,
                metadata_json={"per_chain": {str(k): str(v) for k, v in per_chain.items()}},
            )
        )

    run.status = (
        PrivyReconciliationRunStatus.COMPLETED.value
        if mismatch_count == 0 and unresolved_count == 0
        else PrivyReconciliationRunStatus.COMPLETED_WITH_ISSUES.value
    )
    run.finished_at = datetime.now(timezone.utc)
    run.items_checked = items_checked
    run.matched_count = matched_count
    run.healed_count = healed_count
    run.chain_ahead_count = chain_ahead_count
    run.ledger_ahead_count = ledger_ahead_count
    run.mismatch_count = mismatch_count
    run.unresolved_count = unresolved_count
    run.replayed_webhooks = len(replayed)
    run.summary_json = {
        "wallet_address": wallet_address,
        "chain_ids": chain_ids,
        "replayed_webhooks": replayed,
    }
    db.add(run)

    message = (
        f"Réconciliation terminée — {matched_count} OK, {healed_count} corrigé(s), "
        f"{unresolved_count} non résolu(s), {mismatch_count} alerte(s)."
    )
    return ReconciliationRunSummary(
        run_id=run.id,
        scope=scope,
        person_id=person_id,
        status=run.status,
        items_checked=items_checked,
        matched_count=matched_count,
        healed_count=healed_count,
        chain_ahead_count=chain_ahead_count,
        ledger_ahead_count=ledger_ahead_count,
        mismatch_count=mismatch_count,
        unresolved_count=unresolved_count,
        replayed_webhooks=len(replayed),
        message=message,
    )
