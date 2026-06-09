"""Configuration — Portfolio Financial Operation Guard (PR-4)."""
from __future__ import annotations

import os


def portfolio_financial_operation_guard_enabled() -> bool:
    raw = (os.environ.get("PORTFOLIO_FINANCIAL_OPERATION_GUARD_ENABLED") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def default_portfolio_financial_operation_ttl_seconds(
    operation_type: str | None = None,
) -> int:
    """TTL par défaut — aligné bundle invest lock (120 min) sauf override env."""
    _ = operation_type
    raw = (os.environ.get("PORTFOLIO_FINANCIAL_OPERATION_TTL_SECONDS") or "7200").strip()
    try:
        return max(60, int(raw))
    except ValueError:
        return 7200
