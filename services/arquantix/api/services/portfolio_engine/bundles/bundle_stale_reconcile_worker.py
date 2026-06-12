"""Cron background — reconcile-stale bundle portfolios (locks, intents, V3 zombies)."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from services.onchain_indexer.models import TransactionIntent
from services.portfolio_engine.bundles.bundle_invest_lock import BUNDLE_INVEST_LOCK_KEY
from services.portfolio_engine.bundles.bundle_transaction_intent import (
    _BUNDLE_TRANSACTION_PRODUCTS,
)
from services.portfolio_engine.bundles.rebalance_executor import (
    ACTION_V3_PROGRESS,
    ACTION_V3_RUNNING,
    ENTITY_TYPE_V3_REBALANCE,
)
from services.portfolio_engine.hardening.audit_models import AuditEvent
from services.transaction_intents.enums import IntentProductType, IntentStatus

logger = logging.getLogger(__name__)

_DEFAULT_INTERVAL_SECONDS = 300
_DEFAULT_PORTFOLIO_LIMIT = 50

_OPEN_INTENT_STATUSES = frozenset({
    IntentStatus.AWAITING_SIGNATURE.value,
    IntentStatus.SUBMITTED.value,
    IntentStatus.CREATED.value,
    IntentStatus.PARTIAL.value,
    IntentStatus.CONFIRMING.value,
    IntentStatus.RECONCILIATION_REQUIRED.value,
    "running",
    "created",
    "queued",
    "pending",
})


def bundle_stale_reconcile_cron_enabled() -> bool:
    raw = (os.environ.get("BUNDLE_STALE_RECONCILE_CRON_ENABLED") or "true").strip().lower()
    return raw in ("1", "true", "yes", "on")


def bundle_stale_reconcile_interval_seconds() -> int:
    raw = (os.environ.get("BUNDLE_STALE_RECONCILE_INTERVAL_SECONDS") or "").strip()
    try:
        return max(60, int(raw)) if raw else _DEFAULT_INTERVAL_SECONDS
    except ValueError:
        return _DEFAULT_INTERVAL_SECONDS


def bundle_stale_reconcile_portfolio_limit() -> int:
    raw = (os.environ.get("BUNDLE_STALE_RECONCILE_PORTFOLIO_LIMIT") or "").strip()
    try:
        return max(1, int(raw)) if raw else _DEFAULT_PORTFOLIO_LIMIT
    except ValueError:
        return _DEFAULT_PORTFOLIO_LIMIT


def discover_bundle_portfolios_for_stale_reconcile(
    db: Session,
    *,
    limit: int | None = None,
) -> list[tuple[UUID, UUID]]:
    """Retourne (client_id, portfolio_id) nécessitant un reconcile-stale."""
    cap = limit if limit is not None else bundle_stale_reconcile_portfolio_limit()
    seen: set[str] = set()
    out: list[tuple[UUID, UUID]] = []

    def _add(client_id: UUID | str | None, portfolio_id: UUID | str | None) -> None:
        if client_id is None or portfolio_id is None:
            return
        key = f"{client_id}:{portfolio_id}"
        if key in seen:
            return
        seen.add(key)
        out.append((UUID(str(client_id)), UUID(str(portfolio_id))))

    lock_rows = db.execute(
        text(
            f"""
            SELECT id::text AS portfolio_id, client_id::text AS client_id
            FROM pe_portfolios
            WHERE portfolio_type = 'bundle_portfolio'
              AND metadata ? '{BUNDLE_INVEST_LOCK_KEY}'
              AND metadata->'{BUNDLE_INVEST_LOCK_KEY}' IS NOT NULL
            ORDER BY updated_at DESC NULLS LAST
            LIMIT :lim
            """
        ),
        {"lim": cap},
    ).mappings().all()
    for row in lock_rows:
        _add(row.get("client_id"), row.get("portfolio_id"))

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    audit_rows = (
        db.query(AuditEvent)
        .filter(
            AuditEvent.entity_type == ENTITY_TYPE_V3_REBALANCE,
            AuditEvent.action.in_([ACTION_V3_RUNNING, ACTION_V3_PROGRESS]),
            AuditEvent.created_at >= cutoff,
        )
        .order_by(AuditEvent.created_at.desc())
        .limit(cap * 3)
        .all()
    )
    for row in audit_rows:
        meta = row.metadata_ or {}
        pid = meta.get("portfolio_id")
        if not pid:
            continue
        portfolio = db.execute(
            text(
                """
                SELECT client_id::text
                FROM pe_portfolios
                WHERE id = :pid AND portfolio_type = 'bundle_portfolio'
                """
            ),
            {"pid": str(pid)},
        ).mappings().first()
        if portfolio:
            _add(portfolio.get("client_id"), pid)

    intent_rows = (
        db.query(TransactionIntent)
        .filter(
            TransactionIntent.product_type.in_(
                list(_BUNDLE_TRANSACTION_PRODUCTS)
                + [IntentProductType.BUNDLE_INVEST.value],
            ),
            TransactionIntent.created_at >= cutoff,
        )
        .order_by(TransactionIntent.created_at.desc())
        .limit(cap * 3)
        .all()
    )
    for row in intent_rows:
        status = str(row.status or "").lower()
        if status in {
            IntentStatus.FAILED.value,
            IntentStatus.CONFIRMED.value,
            IntentStatus.FAILED_FINAL.value,
            "completed",
            "failed",
            "no_action",
        }:
            continue
        meta = row.metadata_json or {}
        pid = meta.get("portfolio_id") or meta.get("bundle_id")
        if not pid:
            continue
        portfolio = db.execute(
            text(
                """
                SELECT client_id::text
                FROM pe_portfolios
                WHERE id = :pid AND portfolio_type = 'bundle_portfolio'
                """
            ),
            {"pid": str(pid)},
        ).mappings().first()
        if portfolio:
            _add(portfolio.get("client_id"), pid)

    return out[:cap]


def reconcile_dead_letter_v3_deposit_outboxes(
    db: Session,
    *,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Filet — finalise les outbox DEAD_LETTER non encore clôturées côté intent/lock."""
    from services.portfolio_engine.bundles.bundle_v3_deposit_flow.deposit_service import (
        finalize_v3_deposit_outbox_dead_letter,
    )
    from services.transaction_outbox.enums import OutboxEventStatus, OutboxEventType
    from services.transaction_outbox.models import TransactionOutbox

    rows = (
        db.query(TransactionOutbox)
        .filter(
            TransactionOutbox.event_type == OutboxEventType.BUNDLE_V3_REBALANCE_REQUESTED.value,
            TransactionOutbox.status == OutboxEventStatus.DEAD_LETTER.value,
        )
        .order_by(TransactionOutbox.created_at.desc())
        .limit(limit)
        .all()
    )
    actions: list[dict[str, Any]] = []
    for row in rows:
        try:
            result = finalize_v3_deposit_outbox_dead_letter(
                db,
                outbox=row,
                reason="cron_dead_letter_sweep",
            )
            actions.append({"outbox_id": str(row.id), **result})
        except Exception as exc:
            logger.warning(
                "bundle_stale_reconcile.dead_letter_sweep_failed outbox=%s",
                row.id,
                exc_info=True,
            )
            actions.append({"outbox_id": str(row.id), "error": str(exc)[:500]})
    return actions


def tick_bundle_stale_reconcile(
    db: Session,
    *,
    dry_run: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """Point d'entrée cron — reconcile-stale sur portfolios bundle actifs/suspects."""
    from services.portfolio_engine.bundles.rebalancing_portfolio import (
        reconcile_stale_bundle_portfolio_state,
    )

    if not bundle_stale_reconcile_cron_enabled():
        return {"enabled": False, "skipped": True}

    dead_letter_actions: list[dict[str, Any]] = []
    if not dry_run:
        dead_letter_actions = reconcile_dead_letter_v3_deposit_outboxes(db)

    targets = discover_bundle_portfolios_for_stale_reconcile(db, limit=limit)
    reconciled: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for client_id, portfolio_id in targets:
        if dry_run:
            reconciled.append({
                "portfolio_id": str(portfolio_id),
                "client_id": str(client_id),
                "dry_run": True,
            })
            continue
        try:
            result = reconcile_stale_bundle_portfolio_state(
                db,
                client_id=client_id,
                portfolio_id=portfolio_id,
            )
            reconciled.append({
                "portfolio_id": str(portfolio_id),
                "actions_count": len(result.get("actions") or []),
                "active_status": (result.get("active_operation") or {}).get("status"),
            })
        except Exception as exc:
            logger.warning(
                "bundle_stale_reconcile.portfolio_failed portfolio=%s",
                portfolio_id,
                exc_info=True,
            )
            errors.append({
                "portfolio_id": str(portfolio_id),
                "error": str(exc)[:500],
            })

    if not dry_run and (reconciled or dead_letter_actions):
        db.commit()

    return {
        "enabled": True,
        "skipped": False,
        "dry_run": dry_run,
        "targets": len(targets),
        "reconciled": len(reconciled),
        "dead_letter_swept": len(dead_letter_actions),
        "errors": len(errors),
        "details": reconciled[:20],
        "dead_letter_details": dead_letter_actions[:20],
        "error_details": errors[:10],
    }
