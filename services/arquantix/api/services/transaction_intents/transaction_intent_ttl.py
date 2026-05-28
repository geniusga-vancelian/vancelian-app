"""Politique TTL transaction_intents (Phase 8 — observabilité)."""
from __future__ import annotations

import os
from typing import Optional

from .enums import IntentProductType, IntentStatus

# Minutes avant qu’un intent soit considéré stale (surcharge via env INTENT_TTL_*_MINUTES).
DEFAULT_TTL_MINUTES: dict[str, int] = {
    IntentStatus.AWAITING_SIGNATURE.value: 60,
    IntentStatus.SUBMITTED.value: 45,
    IntentStatus.PARTIAL.value: 120,
    IntentStatus.RECONCILIATION_REQUIRED.value: 360,
    IntentStatus.CONFIRMING.value: 45,
    IntentStatus.CREATED.value: 60,
}

# P1 = flux multi-step / bundle ; P2 = swap / vault simple.
PRODUCT_STALE_SEVERITY: dict[str, str] = {
    IntentProductType.LIFI_SWAP.value: "P2",
    IntentProductType.MORPHO_EARN.value: "P2",
    IntentProductType.LOMBARD_BORROW.value: "P1",
    IntentProductType.BUNDLE_INVEST.value: "P1",
}


def ttl_minutes_for_status(status: str) -> Optional[int]:
    norm = (status or "").strip().lower()
    env_key = f"INTENT_TTL_{norm.upper()}_MINUTES"
    raw = os.getenv(env_key, "").strip()
    if raw.isdigit():
        return int(raw)
    return DEFAULT_TTL_MINUTES.get(norm)


def stale_discrepancy_type_for_status(status: str) -> str:
    norm = (status or "").strip().lower()
    return f"intent_{norm}_stale"


def severity_for_product(product_type: str) -> str:
    return PRODUCT_STALE_SEVERITY.get((product_type or "").strip().lower(), "P2")
