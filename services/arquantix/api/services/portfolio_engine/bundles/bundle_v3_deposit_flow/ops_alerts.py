"""Alertes ops Bundle V3 deposit — outbox pending / guard ACTIVE (read-only audit)."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

OUTBOX_EVENT_TYPE = "bundle.v3_rebalance_requested"
DEFAULT_PENDING_MINUTES = 10


def _pending_threshold_minutes() -> int:
    raw = (os.environ.get("BUNDLE_V3_OUTBOX_PENDING_ALERT_MINUTES") or "").strip()
    return int(raw) if raw.isdigit() else DEFAULT_PENDING_MINUTES


def audit_bundle_v3_deposit_ops(db: Session) -> dict[str, Any]:
    """Détecte outbox PENDING > seuil et guard ACTIVE couplé à outbox pending."""
    threshold = _pending_threshold_minutes()
    now = datetime.now(timezone.utc)

    pending_outbox = db.execute(
        text(
            """
            SELECT o.id::text, o.status, o.created_at, o.attempt_count,
                   o.payload_json->>'portfolio_id' AS portfolio_id,
                   o.payload_json->>'batch_id' AS batch_id,
                   EXTRACT(EPOCH FROM (:now - o.created_at)) / 60.0 AS age_minutes
            FROM transaction_outbox o
            WHERE o.event_type = :event_type
              AND o.status IN ('pending', 'processing')
              AND o.created_at < :now - make_interval(mins => :threshold)
            ORDER BY o.created_at ASC
            """
        ),
        {
            "event_type": OUTBOX_EVENT_TYPE,
            "now": now,
            "threshold": threshold,
        },
    ).mappings().all()

    active_guards = db.execute(
        text(
            """
            SELECT pfo.id::text, pfo.portfolio_id::text, pfo.status,
                   pfo.execution_id::text, pfo.started_at, pfo.expires_at,
                   EXTRACT(EPOCH FROM (:now - pfo.started_at)) / 60.0 AS age_minutes
            FROM portfolio_financial_operations pfo
            WHERE pfo.status = 'ACTIVE'
              AND pfo.operation_type = 'BUNDLE_INVEST'
              AND pfo.started_at < :now - make_interval(mins => :threshold)
            ORDER BY pfo.started_at ASC
            """
        ),
        {"now": now, "threshold": threshold},
    ).mappings().all()

    guard_with_pending_outbox = db.execute(
        text(
            """
            SELECT pfo.id::text AS guard_id, pfo.portfolio_id::text,
                   pfo.execution_id::text AS batch_id,
                   o.id::text AS outbox_id, o.status AS outbox_status,
                   o.created_at AS outbox_created_at
            FROM portfolio_financial_operations pfo
            JOIN transaction_outbox o
              ON o.event_type = :event_type
             AND o.status IN ('pending', 'processing')
             AND (
               o.payload_json->>'portfolio_id' = pfo.portfolio_id::text
               OR o.payload_json->>'batch_id' = pfo.execution_id::text
               OR o.payload_json->>'deposit_execution_id' = pfo.execution_id::text
             )
            WHERE pfo.status = 'ACTIVE'
              AND pfo.operation_type = 'BUNDLE_INVEST'
            ORDER BY o.created_at ASC
            """
        ),
        {"event_type": OUTBOX_EVENT_TYPE},
    ).mappings().all()

    alerts: list[dict[str, Any]] = []
    for row in pending_outbox:
        alerts.append({
            "level": "critical",
            "code": "bundle_v3_outbox_pending_stale",
            "message": (
                f"Outbox {row['id']} PENDING {float(row['age_minutes']):.1f}min "
                f"(portfolio={row['portfolio_id']}, batch={row['batch_id']})"
            ),
            "outbox_id": row["id"],
            "portfolio_id": row["portfolio_id"],
            "batch_id": row["batch_id"],
            "age_minutes": float(row["age_minutes"]),
        })

    for row in guard_with_pending_outbox:
        alerts.append({
            "level": "critical",
            "code": "bundle_v3_guard_active_with_pending_outbox",
            "message": (
                f"Guard ACTIVE {row['guard_id']} with outbox {row['outbox_id']} "
                f"({row['outbox_status']}) portfolio={row['portfolio_id']}"
            ),
            "guard_id": row["guard_id"],
            "outbox_id": row["outbox_id"],
            "portfolio_id": row["portfolio_id"],
            "batch_id": row["batch_id"],
        })

    for row in active_guards:
        guard_id = row["id"]
        if any(a.get("guard_id") == guard_id for a in alerts):
            continue
        alerts.append({
            "level": "critical",
            "code": "bundle_v3_guard_active_stale",
            "message": (
                f"Guard ACTIVE {guard_id} {float(row['age_minutes']):.1f}min "
                f"portfolio={row['portfolio_id']} batch={row['execution_id']}"
            ),
            "guard_id": guard_id,
            "portfolio_id": row["portfolio_id"],
            "batch_id": row["execution_id"],
            "age_minutes": float(row["age_minutes"]),
        })

    return {
        "threshold_minutes": threshold,
        "pending_outbox_count": len(pending_outbox),
        "active_guard_stale_count": len(active_guards),
        "guard_with_pending_outbox_count": len(guard_with_pending_outbox),
        "alerts": alerts,
        "pending_outbox": [dict(r) for r in pending_outbox],
        "active_guards_stale": [dict(r) for r in active_guards],
        "guard_with_pending_outbox": [dict(r) for r in guard_with_pending_outbox],
    }


def audit_bundle_rebalancing_stale_state(db: Session) -> dict[str, Any]:
    """Détecte invest_lock legacy + cash leg matériel sans rééquilibrage récent."""
    legacy_lock_rows = db.execute(
        text(
            """
            SELECT p.id::text AS portfolio_id,
                   p.client_id::text,
                   p.metadata_->'bundle_invest_lock'->>'batch_id' AS batch_id,
                   p.metadata_->'bundle_invest_lock'->>'status' AS lock_status
            FROM pe_portfolios p
            WHERE p.metadata_ ? 'bundle_invest_lock'
              AND (p.metadata_->'bundle_invest_lock') IS NOT NULL
            ORDER BY p.updated_at DESC
            LIMIT 50
            """
        ),
    ).mappings().all()

    alerts: list[dict[str, Any]] = []
    for row in legacy_lock_rows:
        alerts.append({
            "level": "warning",
            "code": "bundle_legacy_invest_lock_with_rebalancing_available",
            "message": (
                f"Portfolio {row['portfolio_id']} legacy invest_lock "
                f"(batch={row['batch_id']}) — utiliser /rebalancing"
            ),
            "portfolio_id": row["portfolio_id"],
            "batch_id": row["batch_id"],
            "lock_status": row["lock_status"],
        })

    return {
        "legacy_lock_count": len(legacy_lock_rows),
        "alerts": alerts,
        "legacy_locks": [dict(r) for r in legacy_lock_rows],
    }


def bundle_v3_ops_alerts_for_tick(db: Session) -> list[dict[str, Any]]:
    """Interface tick — retourne uniquement les alertes CRITICAL/WARNING."""
    audit = audit_bundle_v3_deposit_ops(db)
    rebalancing_audit = audit_bundle_rebalancing_stale_state(db)
    alerts = list(audit.get("alerts") or [])
    alerts.extend(rebalancing_audit.get("alerts") or [])
    return alerts
