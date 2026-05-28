"""Détection écarts intents ↔ ledger / raw events (Phase 7)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import PersonCryptoWallet
from services.lifi.enums import SwapSessionStatus
from services.lifi.lifi_swap_settlement import swap_settlement_already_applied
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import RawOnChainEvent, TransactionIntent

from .enums import IntentStatus
from .lifi_intent_sync import LINKED_TABLE
from .bundle_intent_sync import (
    BUNDLE_PRODUCT,
    LEG_CONFIRMED,
    LEG_FAILED,
    bundle_context_from_swap_audit,
)
from .lombard_intent_sync import (
    LOMBARD_PRODUCT,
    STEP_CONFIRMED,
    STEP_FAILED,
)
from .morpho_intent_sync import MORPHO_LINKED_TABLE, MORPHO_PRODUCT
from .repository import TransactionIntentRepository


def scan_intent_gaps_for_person(
    db: Session,
    person_id: UUID,
    *,
    stale_hours: int = 24,
) -> list[dict[str, Any]]:
    """Retourne des anomalies intent (sans persistance)."""
    anomalies: list[dict[str, Any]] = []
    stale_cutoff = datetime.now(timezone.utc) - timedelta(hours=stale_hours)

    swaps = (
        db.query(PersonWalletSwap)
        .filter(PersonWalletSwap.person_id == person_id)
        .order_by(PersonWalletSwap.created_at.desc())
        .limit(200)
        .all()
    )
    for swap in swaps:
        intent = TransactionIntentRepository.find_by_linked(
            db,
            linked_table=LINKED_TABLE,
            linked_id=swap.id,
        )
        if intent is None and swap.status not in {
            SwapSessionStatus.PENDING.value,
            SwapSessionStatus.FAILED.value,
        }:
            anomalies.append(
                _anomaly(
                    "swap_without_intent",
                    person_id=person_id,
                    reference_id=str(swap.id),
                    metadata={"swap_status": swap.status, "tx_hash": swap.tx_hash},
                )
            )
            continue

        if intent is None:
            continue

        if intent.status == IntentStatus.SUBMITTED.value and not intent.tx_hash:
            anomalies.append(
                _anomaly(
                    "intent_submitted_without_tx_hash",
                    person_id=person_id,
                    reference_id=str(intent.id),
                    wallet_address=intent.wallet_address,
                    metadata={"linked_swap_id": str(swap.id)},
                )
            )

        if intent.tx_hash and not intent.raw_onchain_event_id:
            has_raw = (
                db.query(RawOnChainEvent.id)
                .filter(RawOnChainEvent.tx_hash == intent.tx_hash.lower())
                .first()
            )
            if has_raw:
                anomalies.append(
                    _anomaly(
                        "intent_tx_without_raw_link",
                        person_id=person_id,
                        reference_id=str(intent.id),
                        metadata={"tx_hash": intent.tx_hash},
                    )
                )

        if intent.status == IntentStatus.CONFIRMED.value and not swap_settlement_already_applied(
            swap
        ):
            anomalies.append(
                _anomaly(
                    "intent_confirmed_without_ledger",
                    person_id=person_id,
                    reference_id=str(intent.id),
                    metadata={"swap_id": str(swap.id)},
                )
            )

        if intent.status == IntentStatus.FAILED.value and swap_settlement_already_applied(swap):
            anomalies.append(
                _anomaly(
                    "intent_failed_with_ledger",
                    person_id=person_id,
                    reference_id=str(intent.id),
                    metadata={"swap_id": str(swap.id)},
                )
            )

        if intent.status in {
            IntentStatus.PARTIAL.value,
            IntentStatus.RECONCILIATION_REQUIRED.value,
        }:
            updated = intent.updated_at or intent.created_at
            if updated and updated.replace(tzinfo=timezone.utc) < stale_cutoff:
                anomalies.append(
                    _anomaly(
                        "intent_partial_stale",
                        person_id=person_id,
                        reference_id=str(intent.id),
                        metadata={"intent_status": intent.status},
                    )
                )

    wallet_addrs = {
        str(w.address).lower()
        for w in db.query(PersonCryptoWallet)
        .filter(
            PersonCryptoWallet.person_id == person_id,
            PersonCryptoWallet.revoked_at.is_(None),
        )
        .all()
        if w.address
    }
    if wallet_addrs:
        raw_rows = (
            db.query(RawOnChainEvent)
            .filter(RawOnChainEvent.wallet_address.in_(wallet_addrs))
            .order_by(RawOnChainEvent.parsed_at.desc())
            .limit(50)
            .all()
        )
        for raw in raw_rows:
            has_intent = (
                db.query(TransactionIntent.id)
                .filter(
                    TransactionIntent.person_id == person_id,
                    or_(
                        TransactionIntent.raw_onchain_event_id == raw.id,
                        TransactionIntent.tx_hash == raw.tx_hash,
                    ),
                )
                .first()
            )
            if not has_intent:
                anomalies.append(
                    _anomaly(
                        "raw_event_without_intent",
                        person_id=person_id,
                        reference_id=str(raw.id),
                        wallet_address=raw.wallet_address,
                        metadata={
                            "tx_hash": raw.tx_hash,
                            "asset": raw.asset,
                            "chain_id": raw.chain_id,
                        },
                    )
                )

    anomalies.extend(_scan_morpho_vault_gaps(db, person_id, stale_cutoff=stale_cutoff))
    anomalies.extend(_scan_lombard_borrow_gaps(db, person_id, stale_cutoff=stale_cutoff))
    anomalies.extend(_scan_bundle_invest_gaps(db, person_id, stale_cutoff=stale_cutoff))

    return anomalies


def _scan_morpho_vault_gaps(
    db: Session,
    person_id: UUID,
    *,
    stale_cutoff: datetime,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    rows = db.execute(
        sa.text(
            """
            SELECT id, person_id, wallet_address, vault_address, chain_id, operation,
                   status, tx_hash, idempotency_key, tx_index, created_at, updated_at
            FROM onchain_vault_transactions
            WHERE person_id = :person_id
              AND integration_mode = 'direct_morpho'
              AND operation IN ('deposit', 'withdraw')
            ORDER BY created_at DESC
            LIMIT 200
            """
        ),
        {"person_id": str(person_id)},
    ).mappings().all()

    for row in rows:
        vault_tx_id = str(row["id"])
        vault_status = str(row["status"] or "").lower()
        intent = TransactionIntentRepository.find_by_vault_transaction(
            db,
            vault_transaction_id=vault_tx_id,
            person_id=person_id,
        )

        if vault_status == "success" and intent is None:
            out.append(
                _anomaly(
                    "vault_tx_success_without_intent",
                    person_id=person_id,
                    reference_id=vault_tx_id,
                    wallet_address=row.get("wallet_address"),
                    metadata={"operation": row.get("operation"), "tx_hash": row.get("tx_hash")},
                )
            )
            continue

        if intent is None:
            continue

        if intent.status == IntentStatus.CONFIRMED.value and vault_status != "success":
            out.append(
                _anomaly(
                    "intent_confirmed_vault_tx_not_success",
                    person_id=person_id,
                    reference_id=str(intent.id),
                    wallet_address=intent.wallet_address,
                    metadata={
                        "vault_transaction_id": vault_tx_id,
                        "vault_status": vault_status,
                    },
                )
            )

        if vault_status in ("reverted", "failed") and intent.status not in (
            IntentStatus.FAILED.value,
            IntentStatus.RECONCILIATION_REQUIRED.value,
        ):
            out.append(
                _anomaly(
                    "vault_tx_reverted_intent_not_failed",
                    person_id=person_id,
                    reference_id=str(intent.id),
                    metadata={"vault_status": vault_status, "intent_status": intent.status},
                )
            )

        if intent.tx_hash and not intent.raw_onchain_event_id:
            has_raw = (
                db.query(RawOnChainEvent.id)
                .filter(RawOnChainEvent.tx_hash == intent.tx_hash.lower())
                .first()
            )
            if has_raw:
                out.append(
                    _anomaly(
                        "intent_tx_without_raw_link",
                        person_id=person_id,
                        reference_id=str(intent.id),
                        metadata={"tx_hash": intent.tx_hash, "product": MORPHO_PRODUCT},
                    )
                )

        updated = row.get("updated_at") or row.get("created_at")
        if vault_status == "pending" and updated and updated.replace(tzinfo=timezone.utc) < stale_cutoff:
            out.append(
                _anomaly(
                    "vault_tx_pending_stale",
                    person_id=person_id,
                    reference_id=vault_tx_id,
                    metadata={"intent_id": str(intent.id) if intent else None},
                )
            )
            if intent and intent.status in (
                IntentStatus.SUBMITTED.value,
                IntentStatus.AWAITING_SIGNATURE.value,
            ):
                out.append(
                    _anomaly(
                        "intent_submitted_stale",
                        person_id=person_id,
                        reference_id=str(intent.id),
                        metadata={"vault_transaction_id": vault_tx_id},
                    )
                )

    return out


def _scan_lombard_borrow_gaps(
    db: Session,
    person_id: UUID,
    *,
    stale_cutoff: datetime,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    groups = db.execute(
        sa.text(
            """
            SELECT idempotency_key AS group_key, vault_address, MAX(updated_at) AS updated_at
            FROM onchain_vault_transactions
            WHERE person_id = :person_id
              AND integration_mode = 'lombard_v1'
            GROUP BY idempotency_key, vault_address
            ORDER BY MAX(created_at) DESC
            LIMIT 100
            """
        ),
        {"person_id": str(person_id)},
    ).mappings().all()

    for group in groups:
        group_key = str(group["group_key"])
        vault_address = str(group["vault_address"])
        rows = db.execute(
            sa.text(
                """
                SELECT id, status, tx_hash, operation, tx_index, updated_at
                FROM onchain_vault_transactions
                WHERE person_id = :person_id
                  AND idempotency_key = :group_key
                  AND integration_mode = 'lombard_v1'
                ORDER BY tx_index ASC, operation ASC
                """
            ),
            {"person_id": str(person_id), "group_key": group_key},
        ).mappings().all()

        if not rows:
            continue

        intent = TransactionIntentRepository.find_by_lombard_group(
            db,
            person_id=person_id,
            group_key=group_key,
            market_or_vault=vault_address,
        )

        if intent is None:
            out.append(
                _anomaly(
                    "lombard_group_without_parent_intent",
                    person_id=person_id,
                    reference_id=group_key,
                    metadata={
                        "product_type": LOMBARD_PRODUCT,
                        "vault_address": vault_address,
                        "ledger_count": len(rows),
                    },
                )
            )
            continue

        meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
        steps = meta.get("steps") if isinstance(meta.get("steps"), list) else []
        steps_by_ledger = {
            str(s.get("ledger_entry_id")): s
            for s in steps
            if isinstance(s, dict) and s.get("ledger_entry_id")
        }

        for row in rows:
            ledger_id = str(row["id"])
            ledger_status = str(row["status"] or "").lower()
            step = steps_by_ledger.get(ledger_id)
            if step is None:
                continue
            step_status = str(step.get("status") or "")

            if ledger_status == "success" and step_status != STEP_CONFIRMED:
                out.append(
                    _anomaly(
                        "lombard_step_success_intent_step_not_confirmed",
                        person_id=person_id,
                        reference_id=str(intent.id),
                        metadata={
                            "group_key": group_key,
                            "ledger_entry_id": ledger_id,
                            "ledger_status": ledger_status,
                            "step_status": step_status,
                        },
                    )
                )

            if ledger_status in ("reverted", "failed") and step_status != STEP_FAILED:
                out.append(
                    _anomaly(
                        "lombard_step_failed_intent_step_not_failed",
                        person_id=person_id,
                        reference_id=str(intent.id),
                        metadata={
                            "group_key": group_key,
                            "ledger_entry_id": ledger_id,
                            "ledger_status": ledger_status,
                            "step_status": step_status,
                        },
                    )
                )

        if intent.status == IntentStatus.CONFIRMED.value:
            if not all(
                str(steps_by_ledger.get(str(r["id"]), {}).get("status")) == STEP_CONFIRMED
                for r in rows
                if str(r["id"]) in steps_by_ledger
            ):
                out.append(
                    _anomaly(
                        "lombard_parent_confirmed_step_not_confirmed",
                        person_id=person_id,
                        reference_id=str(intent.id),
                        metadata={"group_key": group_key},
                    )
                )

        if intent.status == IntentStatus.PARTIAL.value:
            updated = group.get("updated_at")
            if updated and updated.replace(tzinfo=timezone.utc) < stale_cutoff:
                out.append(
                    _anomaly(
                        "lombard_parent_partial_stale",
                        person_id=person_id,
                        reference_id=str(intent.id),
                        metadata={"group_key": group_key, "intent_status": intent.status},
                    )
                )

        if intent.tx_hash and not intent.raw_onchain_event_id:
            has_raw = (
                db.query(RawOnChainEvent.id)
                .filter(RawOnChainEvent.tx_hash == intent.tx_hash.lower())
                .first()
            )
            if has_raw:
                out.append(
                    _anomaly(
                        "intent_tx_without_raw_link",
                        person_id=person_id,
                        reference_id=str(intent.id),
                        metadata={"tx_hash": intent.tx_hash, "product": LOMBARD_PRODUCT},
                    )
                )

    return out


def _scan_bundle_invest_gaps(
    db: Session,
    person_id: UUID,
    *,
    stale_cutoff: datetime,
) -> list[dict[str, Any]]:
    from services.lifi.enums import SwapSessionStatus
    from services.lifi.lifi_swap_settlement import swap_settlement_already_applied
    from services.lifi.models import PersonWalletSwap

    out: list[dict[str, Any]] = []
    parents = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.person_id == person_id,
            TransactionIntent.product_type == BUNDLE_PRODUCT,
        )
        .order_by(TransactionIntent.created_at.desc())
        .limit(100)
        .all()
    )

    for intent in parents:
        meta = intent.metadata_json if isinstance(intent.metadata_json, dict) else {}
        legs = meta.get("legs") if isinstance(meta.get("legs"), list) else []
        batch_id = meta.get("batch_id") or intent.linked_reference_id

        if intent.status == IntentStatus.CONFIRMED.value:
            if not all(
                isinstance(leg, dict) and leg.get("status") == LEG_CONFIRMED for leg in legs
            ):
                out.append(
                    _anomaly(
                        "bundle_parent_confirmed_leg_not_confirmed",
                        person_id=person_id,
                        reference_id=str(intent.id),
                        metadata={"batch_id": batch_id, "product_type": BUNDLE_PRODUCT},
                    )
                )

        if intent.status == IntentStatus.PARTIAL.value:
            updated = intent.updated_at or intent.created_at
            if updated and updated.replace(tzinfo=timezone.utc) < stale_cutoff:
                out.append(
                    _anomaly(
                        "bundle_parent_partial_stale",
                        person_id=person_id,
                        reference_id=str(intent.id),
                        metadata={"batch_id": batch_id},
                    )
                )

        if intent.status == IntentStatus.FAILED.value:
            for leg in legs:
                if not isinstance(leg, dict):
                    continue
                swap_id = leg.get("swap_id")
                if not swap_id:
                    continue
                swap = (
                    db.query(PersonWalletSwap)
                    .filter(
                        PersonWalletSwap.id == UUID(str(swap_id)),
                        PersonWalletSwap.person_id == person_id,
                    )
                    .first()
                )
                if swap and _swap_has_pe_atoms(swap):
                    out.append(
                        _anomaly(
                            "bundle_parent_failed_with_pe_atoms",
                            person_id=person_id,
                            reference_id=str(intent.id),
                            metadata={"swap_id": str(swap_id), "batch_id": batch_id},
                        )
                    )
                    break

        for leg in legs:
            if not isinstance(leg, dict):
                continue
            swap_id = leg.get("swap_id")
            if not swap_id:
                continue
            swap = (
                db.query(PersonWalletSwap)
                .filter(
                    PersonWalletSwap.id == UUID(str(swap_id)),
                    PersonWalletSwap.person_id == person_id,
                )
                .first()
            )
            if swap is None:
                continue
            leg_status = str(leg.get("status") or "")
            if swap.status == SwapSessionStatus.CONFIRMED.value and leg_status != LEG_CONFIRMED:
                out.append(
                    _anomaly(
                        "bundle_leg_swap_confirmed_intent_leg_not_confirmed",
                        person_id=person_id,
                        reference_id=str(intent.id),
                        metadata={"swap_id": str(swap_id), "leg_status": leg_status},
                    )
                )
            if leg_status == LEG_FAILED and _swap_has_pe_atoms(swap):
                out.append(
                    _anomaly(
                        "bundle_leg_failed_with_pe_atoms",
                        person_id=person_id,
                        reference_id=str(intent.id),
                        metadata={"swap_id": str(swap_id)},
                    )
                )

        if intent.tx_hash and not intent.raw_onchain_event_id:
            has_raw = (
                db.query(RawOnChainEvent.id)
                .filter(RawOnChainEvent.tx_hash == intent.tx_hash.lower())
                .first()
            )
            if has_raw:
                out.append(
                    _anomaly(
                        "intent_tx_without_raw_link",
                        person_id=person_id,
                        reference_id=str(intent.id),
                        metadata={"tx_hash": intent.tx_hash, "product": BUNDLE_PRODUCT},
                    )
                )

    seen_batch_keys: set[tuple[str, str]] = set()
    swaps = (
        db.query(PersonWalletSwap)
        .filter(PersonWalletSwap.person_id == person_id)
        .order_by(PersonWalletSwap.created_at.desc())
        .limit(200)
        .all()
    )
    for swap in swaps:
        ctx = bundle_context_from_swap_audit(swap)
        if not ctx or not ctx.get("batch_id"):
            continue
        batch_id = str(ctx["batch_id"])
        bundle_id = str(ctx.get("portfolio_id") or "")
        key = (batch_id, bundle_id)
        if key in seen_batch_keys:
            continue
        seen_batch_keys.add(key)

        parent = TransactionIntentRepository.find_by_bundle_batch(
            db,
            person_id=person_id,
            bundle_id=bundle_id,
            batch_id=batch_id,
        )
        if parent is None:
            out.append(
                _anomaly(
                    "bundle_batch_without_parent_intent",
                    person_id=person_id,
                    reference_id=batch_id,
                    metadata={
                        "product_type": BUNDLE_PRODUCT,
                        "bundle_id": bundle_id,
                        "sample_swap_id": str(swap.id),
                    },
                )
            )
            continue

        if swap.status == SwapSessionStatus.CONFIRMED.value and swap_settlement_already_applied(
            swap
        ):
            meta = parent.metadata_json if isinstance(parent.metadata_json, dict) else {}
            legs = meta.get("legs") if isinstance(meta.get("legs"), list) else []
            leg_id = str(ctx.get("leg_id") or "")
            matched = next(
                (leg for leg in legs if isinstance(leg, dict) and str(leg.get("leg_id")) == leg_id),
                None,
            )
            if matched is None or matched.get("status") != LEG_CONFIRMED:
                out.append(
                    _anomaly(
                        "bundle_leg_swap_confirmed_intent_leg_not_confirmed",
                        person_id=person_id,
                        reference_id=str(parent.id),
                        metadata={"swap_id": str(swap.id), "batch_id": batch_id},
                    )
                )

    return out


def _swap_has_pe_atoms(swap: Any) -> bool:
    audit = getattr(swap, "audit_log", None)
    if not isinstance(audit, list):
        return False
    return any(
        isinstance(e, dict) and e.get("event") == "bundle_pe_atoms_applied" for e in audit
    )


def _anomaly(
    discrepancy_type: str,
    *,
    person_id: UUID,
    reference_id: str,
    wallet_address: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "layer": "intent",
        "discrepancy_type": discrepancy_type,
        "person_id": str(person_id),
        "reference_type": "transaction_intent",
        "reference_id": reference_id,
        "wallet_address": wallet_address,
        "metadata_json": metadata or {},
        "severity": "P2",
    }


def persist_intent_discrepancies(
    db: Session,
    person_id: UUID,
    *,
    stale_hours: int = 24,
) -> int:
    from services.onchain_reconciliation.discrepancy_repository import DiscrepancyRepository

    anomalies = scan_intent_gaps_for_person(db, person_id, stale_hours=stale_hours)
    written = 0
    for row in anomalies:
        DiscrepancyRepository.upsert_open(
            db,
            person_id=person_id,
            layer=row["layer"],
            discrepancy_type=row["discrepancy_type"],
            severity=row.get("severity", "P2"),
            wallet_address=row.get("wallet_address"),
            reference_type=row.get("reference_type"),
            reference_id=row.get("reference_id"),
            metadata_json=row.get("metadata_json"),
        )
        written += 1
    return written
