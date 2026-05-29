"""Identifiants provider cost basis attendus pour un swap Li.FI bundle."""
from __future__ import annotations

from services.cost_basis.lifi_execution_ids import expected_lifi_provider_execution_ids


def expected_bundle_lifi_provider_execution_ids(swap) -> list[str]:
    """Préfixe ``bundle-lifi`` pour distinguer du self-trading."""
    return [
        pid.replace("lifi:", "bundle-lifi:", 1)
        for pid in expected_lifi_provider_execution_ids(swap)
    ]


def bundle_swap_fully_ingested(db, swap, *, repo) -> bool:
    for provider_id in expected_bundle_lifi_provider_execution_ids(swap):
        if repo.find_by_provider(
            db,
            provider_source="bundle_lifi",
            provider_execution_id=provider_id,
        ) is None:
            return False
    return True
