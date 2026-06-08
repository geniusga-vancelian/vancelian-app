"""Configuration B5 — bundle parent controller (flag OFF par défaut)."""
from __future__ import annotations

import os


def bundle_parent_controller_enabled() -> bool:
    raw = (os.environ.get("BUNDLE_PARENT_CONTROLLER_ENABLED") or "false").strip().lower()
    return raw in {"1", "true", "yes", "on"}
