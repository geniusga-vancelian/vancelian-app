"""Bloque le démarrage API en production si des mocks DeFi (LI.FI / bundles) sont actifs."""
from __future__ import annotations

import os

from services.security.security_env import is_production_env

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _env_flag_enabled(name: str) -> bool:
    raw = (os.getenv(name) or "").strip().lower()
    return raw in _TRUTHY


def collect_production_mock_violations() -> list[str]:
    """Liste les variables mock interdites en production (vide si OK)."""
    violations: list[str] = []
    if _env_flag_enabled("LIFI_SWAPS_MOCK"):
        violations.append("LIFI_SWAPS_MOCK")
    if _env_flag_enabled("BUNDLE_LIFI_SYNC_MOCK"):
        violations.append("BUNDLE_LIFI_SYNC_MOCK")
    return violations


def enforce_production_mock_guard(*, testing: bool = False) -> None:
    """
    Fail fast au boot si mocks LI.FI actifs en production.

    Ignoré sous pytest (``testing=True`` sur l'app) ou hors ``APP_ENV``/``ENV`` production.
    """
    if testing:
        return
    if not is_production_env():
        return

    violations = collect_production_mock_violations()
    if not violations:
        return

    raise RuntimeError(
        "Production DeFi mock guard: forbidden env in production — "
        f"{', '.join(violations)}. "
        "Set all mock flags to false before deploy.",
    )
