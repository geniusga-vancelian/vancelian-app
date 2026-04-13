"""Hooks d’attestation appareil (Apple / Google) — Phase 3.2, non implémenté ici."""
from __future__ import annotations

from typing import Any, Dict


def verify_device_attestation(fingerprint: Dict[str, Any], payload: bytes) -> bool:
    """
    Vérifie une attestation matérielle (App Attest / Play Integrity).

    Phase 3.1 : stub toujours False ; Phase 3.2 branchera la vérif réelle sans changer la signature.
    """
    _ = fingerprint, payload
    return False
