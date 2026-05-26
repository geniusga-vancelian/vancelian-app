"""Feature flag for bundle execution backend (Phase 1: exchange only)."""
from __future__ import annotations

import os

VALID_PROVIDERS = frozenset({"exchange", "lifi_base", "lifi"})

_DEFAULT = "exchange"


def get_bundle_execution_provider_name() -> str:
    raw = (os.environ.get("BUNDLE_EXECUTION_PROVIDER") or _DEFAULT).strip().lower()
    if raw not in VALID_PROVIDERS:
        return _DEFAULT
    return raw
