"""Configuration — Bundle V3 Deposit Flow."""
from __future__ import annotations

import os


def bundle_v3_deposit_flow_enabled() -> bool:
    raw = (os.environ.get("BUNDLE_V3_DEPOSIT_FLOW_ENABLED") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def bundle_v3_deposit_worker_enabled() -> bool:
    raw = (os.environ.get("BUNDLE_V3_DEPOSIT_WORKER_ENABLED") or "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def bundle_v3_deposit_immediate_kick_enabled() -> bool:
    """Traite l'outbox rebalance juste après le dépôt HTTP (sans attendre le cron)."""
    raw = (os.environ.get("BUNDLE_V3_DEPOSIT_IMMEDIATE_KICK_ENABLED") or "").strip().lower()
    if raw in ("0", "false", "no", "off"):
        return False
    return bundle_v3_deposit_worker_enabled()
