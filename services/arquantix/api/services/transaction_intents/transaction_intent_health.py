"""Santé transaction_intents — TTL stale + agrégats admin (Phase 8)."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from services.lifi.lifi_swap_settlement import swap_settlement_already_applied
from services.lifi.models import PersonWalletSwap
from services.onchain_indexer.models import TransactionIntent
from services.transaction_intents.enums import IntentProductType, IntentStatus

from .transaction_intent_ttl import (
    severity_for_product,
    stale_discrepancy_type_for_status,
    ttl_minutes_for_status,
)

STALE_TRACKED_STATUSES = frozenset(
    {
        IntentStatus.AWAITING_SIGNATURE.value,
        IntentStatus.SUBMITTED.value,
        IntentStatus.PARTIAL.value,
        IntentStatus.RETRYABLE_FAILED.value,
        IntentStatus.RECONCILIATION_REQUIRED.value,
        IntentStatus.CONFIRMING.value,
        IntentStatus.CREATED.value,
    }
)

KNOWN_PRODUCTS = (
    IntentProductType.LIFI_SWAP.value,
    IntentProductType.MORPHO_EARN.value,
    IntentProductType.LEDGITY_VAULT.value,
    IntentProductType.LOMBARD_BORROW.value,
    IntentProductType.BUNDLE_INVEST.value,
    IntentProductType.BUNDLE_WITHDRAW.value,
)
# PRIVY_DEPOSIT : enum dormant — réservé au futur parcours webapp deposit_started.
# Les dépôts Privy externes observés ne créent pas d'intent (voir privy_deposit_intent_sync.py).


@dataclass
class StaleIntentRow:
    intent_id: str
    person_id: str
    product_type: str
    status: str
    updated_at: str
    age_minutes: float
    ttl_minutes: int
    discrepancy_type: str
    severity: str
    wallet_address: Optional[str] = None
    tx_hash: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "person_id": self.person_id,
            "product_type": self.product_type,
            "status": self.status,
            "updated_at": self.updated_at,
            "age_minutes": round(self.age_minutes, 1),
            "ttl_minutes": self.ttl_minutes,
            "discrepancy_type": self.discrepancy_type,
            "severity": self.severity,
            "wallet_address": self.wallet_address,
            "tx_hash": self.tx_hash,
        }


@dataclass
class ProductHealthSummary:
    product_type: str
    total: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    stale: int = 0
    without_raw_link: int = 0
    submitted_old: int = 0
    confirmed_without_ledger: int = 0
    success_rate: Optional[float] = None
    partial_rate: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "product_type": self.product_type,
            "total": self.total,
            "by_status": dict(self.by_status),
            "stale": self.stale,
            "without_raw_onchain_event": self.without_raw_link,
            "submitted_too_old": self.submitted_old,
            "confirmed_without_ledger": self.confirmed_without_ledger,
            "success_rate": self.success_rate,
            "partial_rate": self.partial_rate,
        }


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def classify_stale_intent(
    intent: TransactionIntent,
    *,
    now: datetime | None = None,
) -> Optional[StaleIntentRow]:
    """Retourne un descriptor stale si l’intent dépasse le TTL de son statut."""
    status = (intent.status or "").strip().lower()
    if status not in STALE_TRACKED_STATUSES:
        return None

    ttl = ttl_minutes_for_status(status)
    if ttl is None:
        return None

    ref = _aware(intent.updated_at) or _aware(intent.created_at)
    if ref is None:
        return None

    now_utc = now or datetime.now(timezone.utc)
    age = now_utc - ref
    if age < timedelta(minutes=ttl):
        return None

    product = (intent.product_type or "unknown").strip().lower()
    return StaleIntentRow(
        intent_id=str(intent.id),
        person_id=str(intent.person_id) if intent.person_id else "",
        product_type=product,
        status=status,
        updated_at=ref.isoformat(),
        age_minutes=age.total_seconds() / 60.0,
        ttl_minutes=ttl,
        discrepancy_type=stale_discrepancy_type_for_status(status),
        severity=severity_for_product(product),
        wallet_address=intent.wallet_address,
        tx_hash=intent.tx_hash,
    )


def list_stale_intents(
    db: Session,
    *,
    person_id: UUID | None = None,
    limit: int = 500,
    now: datetime | None = None,
) -> list[StaleIntentRow]:
    q = db.query(TransactionIntent).filter(
        TransactionIntent.status.in_(list(STALE_TRACKED_STATUSES)),
    )
    if person_id is not None:
        q = q.filter(TransactionIntent.person_id == person_id)
    rows = q.order_by(TransactionIntent.updated_at.asc()).limit(limit).all()

    out: list[StaleIntentRow] = []
    for row in rows:
        stale = classify_stale_intent(row, now=now)
        if stale:
            out.append(stale)
    return out


def stale_to_discrepancy(stale: StaleIntentRow) -> dict[str, Any]:
    return {
        "layer": "intent",
        "discrepancy_type": stale.discrepancy_type,
        "person_id": stale.person_id,
        "reference_type": "transaction_intent",
        "reference_id": stale.intent_id,
        "wallet_address": stale.wallet_address,
        "severity": stale.severity,
        "metadata_json": {
            "product_type": stale.product_type,
            "intent_status": stale.status,
            "age_minutes": stale.age_minutes,
            "ttl_minutes": stale.ttl_minutes,
            "tx_hash": stale.tx_hash,
        },
    }


def reconcile_stale_intents(
    db: Session,
    *,
    dry_run: bool = True,
    person_id: UUID | None = None,
    limit: int = 500,
) -> dict[str, Any]:
    """
    Crée des discrepancies layer=intent pour intents stale.
    Ne modifie jamais les intents ni le ledger.
    """
    stale_rows = list_stale_intents(db, person_id=person_id, limit=limit)
    written = 0

    if not dry_run:
        from services.onchain_reconciliation.discrepancy_repository import DiscrepancyRepository

        for stale in stale_rows:
            if not stale.person_id:
                continue
            disc = stale_to_discrepancy(stale)
            DiscrepancyRepository.upsert_open(
                db,
                person_id=UUID(stale.person_id),
                layer=disc["layer"],
                discrepancy_type=disc["discrepancy_type"],
                severity=disc["severity"],
                wallet_address=disc.get("wallet_address"),
                reference_type=disc.get("reference_type"),
                reference_id=disc.get("reference_id"),
                metadata_json=disc.get("metadata_json"),
            )
            written += 1

    return {
        "dry_run": dry_run,
        "stale_detected": len(stale_rows),
        "discrepancies_written": written,
        "stale_items": [s.to_dict() for s in stale_rows[:50]],
    }


def _count_without_raw(db: Session, product_type: str) -> int:
    return (
        db.query(func.count(TransactionIntent.id))
        .filter(
            TransactionIntent.product_type == product_type,
            TransactionIntent.tx_hash.isnot(None),
            TransactionIntent.raw_onchain_event_id.is_(None),
        )
        .scalar()
        or 0
    )


def _count_submitted_old(db: Session, product_type: str, *, now: datetime) -> int:
    ttl = ttl_minutes_for_status(IntentStatus.SUBMITTED.value) or 45
    cutoff = now - timedelta(minutes=ttl)
    return (
        db.query(func.count(TransactionIntent.id))
        .filter(
            TransactionIntent.product_type == product_type,
            TransactionIntent.status == IntentStatus.SUBMITTED.value,
            TransactionIntent.updated_at < cutoff,
        )
        .scalar()
        or 0
    )


def _count_lifi_confirmed_without_ledger(db: Session, *, sample_limit: int = 300) -> int:
    rows = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.product_type == IntentProductType.LIFI_SWAP.value,
            TransactionIntent.status == IntentStatus.CONFIRMED.value,
            TransactionIntent.linked_id.isnot(None),
        )
        .order_by(TransactionIntent.updated_at.desc())
        .limit(sample_limit)
        .all()
    )
    count = 0
    for intent in rows:
        if intent.linked_id is None:
            continue
        swap = (
            db.query(PersonWalletSwap)
            .filter(
                PersonWalletSwap.id == intent.linked_id,
                PersonWalletSwap.person_id == intent.person_id,
            )
            .first()
        )
        if swap and not swap_settlement_already_applied(swap):
            count += 1
    return count


def compute_health_summary(
    db: Session,
    *,
    sample_limit: int = 5000,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Agrégats par product_type + stale global."""
    now_utc = now or datetime.now(timezone.utc)

    status_rows = (
        db.query(
            TransactionIntent.product_type,
            TransactionIntent.status,
            func.count(TransactionIntent.id),
        )
        .group_by(TransactionIntent.product_type, TransactionIntent.status)
        .all()
    )

    products: dict[str, ProductHealthSummary] = {
        p: ProductHealthSummary(product_type=p) for p in KNOWN_PRODUCTS
    }

    for product_type, status, cnt in status_rows:
        pt = (product_type or "unknown").strip().lower()
        if pt not in products:
            products[pt] = ProductHealthSummary(product_type=pt)
        products[pt].total += int(cnt)
        products[pt].by_status[status or "unknown"] = (
            products[pt].by_status.get(status or "unknown", 0) + int(cnt)
        )

    stale_all = list_stale_intents(db, limit=sample_limit, now=now_utc)
    stale_by_product: Counter[str] = Counter(s.product_type for s in stale_all)

    for pt, summary in products.items():
        summary.stale = stale_by_product.get(pt, 0)
        summary.without_raw_link = _count_without_raw(db, pt)
        summary.submitted_old = _count_submitted_old(db, pt, now=now_utc)
        if pt == IntentProductType.LIFI_SWAP.value:
            summary.confirmed_without_ledger = _count_lifi_confirmed_without_ledger(db)

        confirmed = summary.by_status.get(IntentStatus.CONFIRMED.value, 0)
        failed = summary.by_status.get(IntentStatus.FAILED.value, 0)
        partial = summary.by_status.get(IntentStatus.PARTIAL.value, 0)
        terminal = confirmed + failed
        if terminal > 0:
            summary.success_rate = round(confirmed / terminal, 4)
        if summary.total > 0:
            summary.partial_rate = round(partial / summary.total, 4)

    global_stale = len(stale_all)
    global_total = sum(p.total for p in products.values())

    return {
        "generated_at": now_utc.isoformat(),
        "global": {
            "total_intents": global_total,
            "stale_intents": global_stale,
            "ttl_policy_minutes": {
                IntentStatus.AWAITING_SIGNATURE.value: ttl_minutes_for_status(
                    IntentStatus.AWAITING_SIGNATURE.value
                ),
                IntentStatus.SUBMITTED.value: ttl_minutes_for_status(IntentStatus.SUBMITTED.value),
                IntentStatus.PARTIAL.value: ttl_minutes_for_status(IntentStatus.PARTIAL.value),
                IntentStatus.RECONCILIATION_REQUIRED.value: ttl_minutes_for_status(
                    IntentStatus.RECONCILIATION_REQUIRED.value
                ),
            },
        },
        "by_product": [products[p].to_dict() for p in KNOWN_PRODUCTS if p in products]
        + [
            products[k].to_dict()
            for k in sorted(products.keys())
            if k not in KNOWN_PRODUCTS
        ],
        "stale_preview": [s.to_dict() for s in stale_all[:30]],
    }


def top_intent_anomalies(
    db: Session,
    *,
    limit: int = 15,
) -> list[dict[str, Any]]:
    """Top discrepancy_type ouverts layer=intent."""
    from services.onchain_reconciliation.discrepancy_models import ReconciliationDiscrepancy

    rows = (
        db.query(
            ReconciliationDiscrepancy.discrepancy_type,
            func.count(ReconciliationDiscrepancy.id),
        )
        .filter(
            ReconciliationDiscrepancy.layer == "intent",
            ReconciliationDiscrepancy.status == "open",
        )
        .group_by(ReconciliationDiscrepancy.discrepancy_type)
        .order_by(func.count(ReconciliationDiscrepancy.id).desc())
        .limit(limit)
        .all()
    )
    return [
        {"discrepancy_type": dtype, "count": int(cnt)}
        for dtype, cnt in rows
    ]


def build_admin_health_payload(db: Session) -> dict[str, Any]:
    summary = compute_health_summary(db)
    summary["top_anomalies"] = top_intent_anomalies(db)
    return summary
