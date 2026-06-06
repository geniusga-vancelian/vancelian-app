"""Constantes Settlement Layer — markers metadata (lecture P5, pas d'écriture S2.5)."""
from __future__ import annotations

SETTLEMENT_RECEIPT_METADATA_KEY = "settlement_receipt_hash"

# Phases orchestrateur autorisées pour settlement skeleton (P2 — post worker S2b).
SETTLEMENT_READY_PHASES = frozenset({"QUEUED", "PROCESSING", "ONCHAIN_CONFIRMED"})
