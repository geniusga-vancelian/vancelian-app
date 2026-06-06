"""Checksum settlement skeleton — déterministe (Contract v1 Q4, sans persistance S2.5)."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from services.onchain_indexer.models import TransactionIntent


def compute_settlement_receipt_hash(intent: TransactionIntent, *, linked_snapshot: dict[str, Any]) -> str:
    """Hash déterministe — deux projections identiques → même hash."""
    payload = {
        "intent_id": str(intent.id),
        "idempotency_key": intent.idempotency_key,
        "product_type": intent.product_type,
        "linked_table": intent.linked_table,
        "linked_id": str(intent.linked_id) if intent.linked_id else None,
        "assets_json": intent.assets_json,
        "linked_snapshot": linked_snapshot,
        "skeleton": "s2.5-noop",
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def linked_entity_snapshot(linked: Any) -> dict[str, Any]:
    if linked is None:
        return {}
    return {
        "id": str(getattr(linked, "id", "")),
        "status": getattr(linked, "status", None),
        "amount_in": str(getattr(linked, "amount_in", "")),
        "from_asset": getattr(linked, "from_asset", None),
        "to_asset": getattr(linked, "to_asset", None),
    }
