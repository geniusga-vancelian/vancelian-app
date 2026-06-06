"""Chargement du périmètre legacy gelé — docs/accounting/legacy/FROZEN_SCOPE.json."""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_SCOPE: dict[str, Any] = {
    "legacy_frozen": True,
    "requires_protocol_proof": True,
    "do_not_auto_fix": True,
    "frozen_scopes": [
        {"id": "uvp_user_vault_positions", "assets_affected": ["USDC", "EURC"]},
        {"id": "ovt_vault_backfill_gaps", "assets_affected": ["USDC", "EURC"]},
        {"id": "ovt_lombard_backfill_gaps", "assets_affected": ["USDC", "CBBTC", "CBETH"]},
        {"id": "lombard_liability_historical_delta", "assets_affected": ["USDC"]},
    ],
}

_GAP_TYPE_TO_FROZEN_ID = {
    "vault_position_not_in_pe": "uvp_user_vault_positions",
    "scope_pe_missing_or_divergent": "ovt_lombard_backfill_gaps",
}


def _find_frozen_scope_path() -> Path | None:
    cur = Path(__file__).resolve()
    for root in cur.parents:
        candidate = root / "docs/accounting/legacy/FROZEN_SCOPE.json"
        if candidate.is_file():
            return candidate
    return None


@lru_cache(maxsize=1)
def load_frozen_scope() -> dict[str, Any]:
    path = _find_frozen_scope_path()
    if path is None:
        logger.warning("FROZEN_SCOPE.json introuvable — défaut embarqué")
        return dict(_DEFAULT_SCOPE)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Lecture FROZEN_SCOPE.json échouée: %s", exc)
        return dict(_DEFAULT_SCOPE)


def frozen_scope_ids() -> set[str]:
    return {str(s.get("id")) for s in load_frozen_scope().get("frozen_scopes", []) if s.get("id")}


def assets_in_frozen_scope(asset: str) -> list[str]:
    asset_u = (asset or "").upper()
    hits: list[str] = []
    for scope in load_frozen_scope().get("frozen_scopes", []):
        affected = {str(a).upper() for a in scope.get("assets_affected") or []}
        if asset_u in affected:
            hits.append(str(scope.get("id")))
    return hits


def map_scope_gap_to_frozen_id(gap_type: str, expected_scope: str | None = None) -> str:
    if gap_type == "vault_position_not_in_pe":
        return "uvp_user_vault_positions"
    if gap_type == "scope_pe_missing_or_divergent":
        if expected_scope == "vault_position":
            return "ovt_vault_backfill_gaps"
        if expected_scope == "liability":
            return "lombard_liability_historical_delta"
        if expected_scope == "trading_locked_collateral":
            return "ovt_lombard_backfill_gaps"
        return "ovt_lombard_backfill_gaps"
    return _GAP_TYPE_TO_FROZEN_ID.get(gap_type, "legacy_unknown")
