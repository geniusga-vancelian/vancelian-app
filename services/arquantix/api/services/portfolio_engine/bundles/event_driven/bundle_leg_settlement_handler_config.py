"""Configuration B3c — bundle leg settlement handler (flag OFF par défaut)."""
from __future__ import annotations

import os


def bundle_leg_settlement_handler_enabled() -> bool:
    raw = (os.environ.get("BUNDLE_LEG_SETTLEMENT_HANDLER_ENABLED") or "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}
