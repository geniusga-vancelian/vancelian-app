"""PR E — flags environnement pour attestation obligatoire (rétrocompat : tout désactivé par défaut)."""
from __future__ import annotations

import os

from services.auth.device_security_pr_d2 import device_security_level


def _truthy(name: str, default: str = "false") -> bool:
    return (os.getenv(name, default) or "").strip().lower() in ("1", "true", "yes", "on")


def device_attestation_required_login() -> bool:
    """Si true : login mobile (hors legacy-unknown) exige attestation valide."""
    return _truthy("DEVICE_ATTESTATION_REQUIRED_LOGIN", "false")


def device_attestation_required_refresh() -> bool:
    """Si true : refresh exige en-tête d’attestation valide (complète ``DEVICE_ATTESTATION_REQUIRED`` niveau D3)."""
    return _truthy("DEVICE_ATTESTATION_REQUIRED_REFRESH", "false")


def device_attestation_required_sensitive() -> bool:
    """Si true : routes sensibles (Depends dédié) exigent niveau ``DEVICE_TRUST_REQUIRED_LEVEL``."""
    return _truthy("DEVICE_ATTESTATION_REQUIRED_SENSITIVE", "false")


def device_trust_required_level() -> str:
    raw = (os.getenv("DEVICE_TRUST_REQUIRED_LEVEL") or "HIGH").strip().upper()
    if raw in ("HIGH", "MEDIUM", "LOW"):
        return raw
    return "HIGH"


def refresh_attestation_max_age_sec() -> int:
    """Fenêtre max sans nouvelle attestation sur refresh (PR E + ``DEVICE_SECURITY_LEVEL>=3``)."""
    try:
        return max(300, min(86400 * 7, int(os.getenv("DEVICE_ATTESTATION_REFRESH_MAX_AGE_SEC", "86400"))))
    except ValueError:
        return 86400


def refresh_requires_attestation_when_d3() -> bool:
    """Si true et ``DEVICE_SECURITY_LEVEL>=3`` : refresh refuse attestation stale même sans ``DEVICE_ATTESTATION_REQUIRED_REFRESH``."""
    return _truthy("DEVICE_ATTESTATION_REFRESH_STRICT_ON_D3", "true")


def enforce_refresh_attestation_on_level_3() -> bool:
    return device_security_level() >= 3 and refresh_requires_attestation_when_d3()
