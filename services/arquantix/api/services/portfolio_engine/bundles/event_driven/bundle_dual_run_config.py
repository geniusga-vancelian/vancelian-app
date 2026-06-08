"""Configuration B2b — dual-run lock legacy metadata + S4 parent (flag OFF par défaut)."""
from __future__ import annotations

import os


def bundle_s4_parent_lock_dual_run_enabled() -> bool:
    raw = (os.environ.get("BUNDLE_S4_PARENT_LOCK_DUAL_RUN_ENABLED") or "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}
