"""Constantes Controller S3 v1 — LI.FI standalone."""
from __future__ import annotations

CONTROLLER_ACTOR = "controller_lifi_swap_v1"
CONTROLLER_VERSION = "s3-lifi-swap-v1.2"
RECONCILIATION_REPORT_METADATA_KEY = "reconciliation_report_hash"

# Snapshot Product Lock S4 = projection PE trading_available (pas wallet Privy).
PE_SNAPSHOT_WALLET_CHECK_SKIPPED = "balance_snapshot_pe_scope_wallet_check_skipped"

# Tolérance montants (alignée settlement S3b).
_AMOUNT_RELATIVE_TOLERANCE = 0.02
_AMOUNT_ABSOLUTE_TOLERANCE = 1e-12
