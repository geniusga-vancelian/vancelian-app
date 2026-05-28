"""Feature flag for bundle execution backend."""
from __future__ import annotations

import os

VALID_PROVIDERS = frozenset({"exchange", "lifi_base", "lifi"})

_DEFAULT = "exchange"


def get_bundle_execution_provider_name() -> str:
    """Resolve bundle execution backend.

    Explicit ``BUNDLE_EXECUTION_PROVIDER`` wins. Otherwise, when Li.FI swaps are
    enabled and configured (or mock mode), default to ``lifi_base`` so preview and
    invest align with the portal swap engine without requiring a separate ECS env var.
    """
    raw = (os.environ.get("BUNDLE_EXECUTION_PROVIDER") or "").strip().lower()
    if raw:
        if raw in VALID_PROVIDERS:
            return raw
        return _DEFAULT

    try:
        from services.lifi.config import lifi_api_configured, swaps_enabled, swaps_mock_mode

        if swaps_enabled() and (lifi_api_configured() or swaps_mock_mode()):
            return "lifi_base"
    except ImportError:
        pass

    return _DEFAULT
