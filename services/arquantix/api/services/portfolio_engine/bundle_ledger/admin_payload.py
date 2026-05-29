"""Enrichissement payload admin réconciliation bundle ledger."""
from __future__ import annotations

from typing import Any

from services.portfolio_engine.bundle_ledger.config import bundle_ledger_history_enabled
from services.portfolio_engine.bundle_ledger.history import resolve_history_source
from services.portfolio_engine.bundle_ledger.rollout import _read_last_backfill_summary
from services.portfolio_engine.portfolios.models import Portfolio


def enrich_admin_reconciliation_payload(
    payload: dict[str, Any],
    *,
    portfolio: Portfolio | None,
) -> dict[str, Any]:
    source, fallback_reason = resolve_history_source(payload)
    enriched = dict(payload)
    enriched["current_history_source"] = source
    enriched["flag_enabled"] = bundle_ledger_history_enabled()
    enriched["fallback_reason"] = fallback_reason
    enriched["last_backfill_summary"] = _read_last_backfill_summary(portfolio)
    return enriched
