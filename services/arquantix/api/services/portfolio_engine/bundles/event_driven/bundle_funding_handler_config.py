"""Configuration B3a — bundle funding handler (flag OFF par défaut)."""
from __future__ import annotations

import os


def bundle_funding_handler_enabled() -> bool:
    raw = (os.environ.get("BUNDLE_FUNDING_HANDLER_ENABLED") or "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}
