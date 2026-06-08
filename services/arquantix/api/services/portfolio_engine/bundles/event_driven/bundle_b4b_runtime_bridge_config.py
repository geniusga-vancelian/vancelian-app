"""Configuration B4b — bundle minimal runtime bridge (flag OFF par défaut)."""
from __future__ import annotations

import os


def bundle_b4b_runtime_bridge_enabled() -> bool:
    raw = (os.environ.get("BUNDLE_B4B_RUNTIME_BRIDGE_ENABLED") or "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}
