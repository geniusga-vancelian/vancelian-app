"""Phase 4C — validation panel rollout bundle ledger."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from services.portfolio_engine.bundle_ledger.backfill import plan_backfill, run_backfill
from services.portfolio_engine.bundle_ledger.config import bundle_ledger_history_enabled
from services.portfolio_engine.bundle_ledger.history import (
    maybe_list_bundle_transactions_from_ledger,
    resolve_history_source,
)
from services.portfolio_engine.bundle_ledger.observability import log_bundle_ledger_event
from services.portfolio_engine.bundle_ledger.reconciliation import reconcile_bundle_ledger_shadow
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.portfolios.models import Portfolio

LAST_BACKFILL_META_KEY = "bundle_ledger_last_backfill"


def _read_last_backfill_summary(portfolio: Portfolio | None) -> dict[str, Any] | None:
    if portfolio is None:
        return None
    meta = portfolio.metadata_ if isinstance(portfolio.metadata_, dict) else {}
    raw = meta.get(LAST_BACKFILL_META_KEY)
    return dict(raw) if isinstance(raw, dict) else None


def store_last_backfill_summary(
    db: Session,
    *,
    portfolio_id: UUID,
    summary: dict[str, Any],
) -> None:
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if portfolio is None:
        return
    meta = deepcopy(portfolio.metadata_) if isinstance(portfolio.metadata_, dict) else {}
    meta[LAST_BACKFILL_META_KEY] = {
        **summary,
        "stored_at": datetime.now(timezone.utc).isoformat(),
    }
    portfolio.metadata_ = meta
    db.flush()


def _resolve_person_id(db: Session, portfolio: Portfolio) -> UUID:
    client = db.query(Client).filter(Client.id == portfolio.client_id).first()
    if client is None or client.person_id is None:
        raise ValueError(f"person_id_missing_for_portfolio:{portfolio.id}")
    return client.person_id


def validate_portfolio_rollout(
    db: Session,
    *,
    portfolio_id: UUID,
    apply_backfill: bool = False,
) -> dict[str, Any]:
    """Dry-run backfill → apply optionnel → reconcile → history source."""
    portfolio = (
        db.query(Portfolio)
        .filter(
            Portfolio.id == portfolio_id,
            Portfolio.portfolio_type == "bundle_portfolio",
        )
        .first()
    )
    if portfolio is None:
        raise ValueError(f"bundle_portfolio_not_found:{portfolio_id}")

    person_id = _resolve_person_id(db, portfolio)
    client = db.query(Client).filter(Client.id == portfolio.client_id).first()

    backfill_dry = plan_backfill(
        db,
        person_id=person_id,
        portfolio_id=portfolio_id,
    )
    for warning in backfill_dry.warnings:
        log_bundle_ledger_event(
            "bundle_backfill_warning",
            person_id=str(person_id),
            portfolio_id=str(portfolio_id),
            warning=warning,
            verdict="dry_run",
        )
    backfill_apply_result: dict[str, Any] | None = None

    if apply_backfill:
        applied = run_backfill(
            db,
            person_id=person_id,
            portfolio_id=portfolio_id,
            dry_run=False,
        )
        backfill_apply_result = applied.to_dict()
        if applied.applied:
            log_bundle_ledger_event(
                "bundle_backfill_applied",
                person_id=str(person_id),
                portfolio_id=str(portfolio_id),
                applied_count=len(applied.applied),
                entries_count=len(applied.applied),
                verdict="applied",
            )
            store_last_backfill_summary(
                db,
                portfolio_id=portfolio_id,
                summary={
                    "applied_count": len(applied.applied),
                    "warnings": applied.warnings,
                    "applied_keys": applied.applied,
                },
            )
        for warning in applied.warnings:
            log_bundle_ledger_event(
                "bundle_backfill_warning",
                person_id=str(person_id),
                portfolio_id=str(portfolio_id),
                warning=warning,
                verdict="warning",
            )
        db.refresh(portfolio)

    reconciliation = reconcile_bundle_ledger_shadow(
        db,
        person_id=person_id,
        portfolio_id=portfolio_id,
    )
    verdict = str(reconciliation.get("verdict") or "UNKNOWN")

    if verdict == "DIFF":
        log_bundle_ledger_event(
            "ledger_reconciliation_diff",
            person_id=str(person_id),
            portfolio_id=str(portfolio_id),
            verdict=verdict,
            fallback_reason="ledger_diff",
            entries_count=int(reconciliation.get("ledger_entry_count") or 0),
            differences=reconciliation.get("differences"),
        )

    history_source, fallback_reason = resolve_history_source(reconciliation)
    entries_count = int(reconciliation.get("ledger_entry_count") or 0)

    history_txs: list[dict[str, Any]] | None = None
    history_meta: dict[str, Any] | None = None
    if client is not None:
        history_txs, history_meta = maybe_list_bundle_transactions_from_ledger(
            db,
            client_id=client.id,
            person_id=person_id,
            portfolio_id=portfolio_id,
            limit=20,
        )

    effective_source = "legacy"
    if history_meta and history_meta.get("source") == "bundle_ledger":
        effective_source = "ledger"
    elif history_source == "ledger":
        effective_source = "ledger"

    rollout_ready = verdict == "MATCH"

    return {
        "portfolio_id": str(portfolio_id),
        "person_id": str(person_id),
        "verdict": verdict,
        "rollout_ready": rollout_ready,
        "history_source_expected": history_source,
        "history_source_effective": effective_source,
        "fallback_reason": fallback_reason,
        "entries_count": entries_count,
        "flag_enabled": bundle_ledger_history_enabled(),
        "backfill_dry_run": backfill_dry.to_dict(),
        "backfill_apply": backfill_apply_result,
        "reconciliation": {
            "verdict": verdict,
            "ledger_entry_count": entries_count,
            "missing_ledger_entries": reconciliation.get("missing_ledger_entries"),
            "differences": reconciliation.get("differences"),
        },
        "history_sample_count": len(history_txs or []),
        "last_backfill_summary": _read_last_backfill_summary(portfolio),
    }


def validate_rollout_panel(
    db: Session,
    *,
    portfolio_ids: list[UUID],
    apply_backfill: bool = False,
) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    counts = {"MATCH": 0, "INCOMPLETE": 0, "DIFF": 0, "OTHER": 0}

    for pid in portfolio_ids:
        try:
            row = validate_portfolio_rollout(
                db,
                portfolio_id=pid,
                apply_backfill=apply_backfill,
            )
            results.append(row)
            v = row.get("verdict", "OTHER")
            if v in counts:
                counts[v] += 1
            else:
                counts["OTHER"] += 1
        except Exception as exc:
            errors.append({"portfolio_id": str(pid), "error": str(exc)})

    match_count = counts["MATCH"]
    total_ok = len(results)
    panel_ready = match_count == total_ok and total_ok > 0 and not errors

    return {
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "portfolio_count": len(portfolio_ids),
        "results": results,
        "errors": errors,
        "summary": {
            **counts,
            "match_count": match_count,
            "error_count": len(errors),
        },
        "rollout_ready": panel_ready,
        "rollout_status": "ready" if panel_ready else "not_ready",
        "flag_enabled": bundle_ledger_history_enabled(),
        "recommendation": (
            "Panel MATCH — candidat activation flag sur ces portfolios (prod limitée)."
            if panel_ready
            else "Panel not ready — ne pas activer le flag globalement ; corriger DIFF/INCOMPLETE."
        ),
    }
