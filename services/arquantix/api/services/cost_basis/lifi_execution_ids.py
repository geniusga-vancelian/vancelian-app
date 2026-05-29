"""Identifiants provider cost basis attendus pour un swap Li.FI."""
from __future__ import annotations

from services.cost_basis.valuation import classify_native_quote


def expected_lifi_provider_execution_ids(swap) -> list[str]:
    """Liste des ``provider_execution_id`` qu'un swap self-trading devrait produire."""
    swap_id = str(swap.id)
    from_asset = str(swap.from_asset).upper()
    to_asset = str(swap.to_asset).upper()
    ids = [f"lifi:{swap_id}:acquisition:{to_asset}"]
    if classify_native_quote(from_asset) == "crypto":
        ids.append(f"lifi:{swap_id}:disposal:{from_asset}")
    return ids


def swap_fully_ingested(db, swap, *, repo) -> bool:
    """True si toutes les lignes cost basis attendues existent déjà."""
    for provider_id in expected_lifi_provider_execution_ids(swap):
        if repo.find_by_provider(
            db,
            provider_source="lifi",
            provider_execution_id=provider_id,
        ) is None:
            return False
    return True
