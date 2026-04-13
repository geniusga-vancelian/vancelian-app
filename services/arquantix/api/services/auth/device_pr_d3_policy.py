"""PR D3 — feature flags (compat PR D2)."""
from __future__ import annotations

import os

from services.auth.device_security_pr_d2 import device_security_level


def register_key_pk_attestation_binding_required() -> bool:
    """Si true : ``register-key`` exige attestation valide + ``pk_sha256`` cohérent avec la clé."""
    return (os.getenv("REGISTER_KEY_PK_ATTESTATION_BINDING", "false").strip().lower() in ("1", "true", "yes"))


def sensitive_routes_device_signature_enabled() -> bool:
    """Routes sensibles : signature device + nonce si ``DEVICE_SECURITY_LEVEL`` >= 2."""
    return device_security_level() >= 2


def device_signature_failure_rate_limit_max() -> int:
    try:
        return max(5, min(1000, int(os.getenv("DEVICE_SIGNATURE_FAILURE_RL_MAX", "30"))))
    except ValueError:
        return 30


def device_signature_nonce_ttl_sec() -> int:
    try:
        return max(60, min(900, int(os.getenv("DEVICE_SIGNATURE_NONCE_TTL_SEC", "300"))))
    except ValueError:
        return 300
