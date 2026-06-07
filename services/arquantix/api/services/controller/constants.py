"""Constantes Controller S3 v1 — LI.FI standalone."""
from __future__ import annotations

CONTROLLER_ACTOR = "controller_lifi_swap_v1"
RECONCILIATION_REPORT_METADATA_KEY = "reconciliation_report_hash"

# Tolérance montants (alignée settlement S3b).
_AMOUNT_RELATIVE_TOLERANCE = 0.02
_AMOUNT_ABSOLUTE_TOLERANCE = 1e-12
