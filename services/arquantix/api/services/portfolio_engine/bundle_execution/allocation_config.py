"""Configuration Phase 5A — buffer d'exécution et quotes parallèles bundle."""
from __future__ import annotations

import os
from decimal import Decimal, ROUND_DOWN

BUNDLE_ALLOC_MAX_PARALLEL_LEGS = 5
_DEFAULT_BUFFER_USDC = Decimal("1.0")


def bundle_alloc_execution_buffer_usdc() -> Decimal:
    raw = (os.environ.get("BUNDLE_ALLOC_EXECUTION_BUFFER_USDC") or "1.0").strip()
    try:
        return max(Decimal("0"), Decimal(raw))
    except Exception:
        return _DEFAULT_BUFFER_USDC


def bundle_alloc_execution_buffer_bps() -> int | None:
    raw = (os.environ.get("BUNDLE_ALLOC_EXECUTION_BUFFER_BPS") or "").strip()
    if not raw:
        return None
    try:
        return max(0, int(raw))
    except ValueError:
        return None


def bundle_alloc_parallel_quotes_enabled() -> bool:
    raw = (os.environ.get("BUNDLE_ALLOC_PARALLEL_QUOTES_ENABLED") or "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def compute_execution_buffer(fund_amount: Decimal) -> Decimal:
    """Buffer conservé en cash leg — non alloué aux legs."""
    if fund_amount <= 0:
        return Decimal("0")

    buffer = bundle_alloc_execution_buffer_usdc()
    bps = bundle_alloc_execution_buffer_bps()
    if bps is not None:
        bps_amount = (fund_amount * Decimal(bps) / Decimal(10000)).quantize(
            Decimal("0.000001"), rounding=ROUND_DOWN,
        )
        buffer = max(buffer, bps_amount)

    if buffer >= fund_amount:
        return fund_amount.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
    return buffer.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)


def compute_allocatable_amount(fund_amount: Decimal) -> tuple[Decimal, Decimal]:
    """Retourne (allocatable, buffer) avec ``allocatable = fund − buffer``."""
    buffer = compute_execution_buffer(fund_amount)
    allocatable = (fund_amount - buffer).quantize(Decimal("0.000001"), rounding=ROUND_DOWN)
    if allocatable < 0:
        allocatable = Decimal("0")
    return allocatable, buffer
