"""Parse et normalisation du header ``X-Device-Fingerprint`` (Phase 3.1)."""
from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any, Dict, Optional, Tuple

from services.security.security_env import is_auth_device_fingerprint_enabled

logger = logging.getLogger("arquantix.auth.security")

_ALLOWED_PLATFORM = frozenset({"ios", "android"})


def is_device_fingerprint_enabled() -> bool:
    return is_auth_device_fingerprint_enabled()


def parse_device_fingerprint_header(raw: Optional[str]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Retourne ``(metadata_normalisé, sha256_hex)`` ou ``(None, None)`` si absent / invalide / désactivé.
    Ne lève pas : les erreurs de parsing sont ignorées (rétrocompat).
    """
    if not is_device_fingerprint_enabled() or raw is None or not str(raw).strip():
        return None, None
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.debug("device_fingerprint: invalid JSON header")
        return None, None
    if not isinstance(data, dict):
        return None, None

    device_id = data.get("device_id")
    install_id = data.get("install_id")
    platform = data.get("platform")
    os_version = data.get("os_version")
    app_version = data.get("app_version")
    device_model = data.get("device_model")

    norm: Dict[str, Any] = {}
    if device_id is not None and str(device_id).strip():
        norm["device_id"] = str(device_id).strip()[:128]
    if install_id is not None and str(install_id).strip():
        norm["install_id"] = str(install_id).strip()[:64]
    if platform is not None and str(platform).strip():
        p = str(platform).strip().lower()
        if p in _ALLOWED_PLATFORM:
            norm["platform"] = p
        else:
            norm["platform"] = re.sub(r"[^a-z0-9_]", "_", p)[:32]
    if os_version is not None and str(os_version).strip():
        norm["os_version"] = str(os_version).strip()[:64]
    if app_version is not None and str(app_version).strip():
        norm["app_version"] = str(app_version).strip()[:64]
    if device_model is not None and str(device_model).strip():
        norm["device_model"] = str(device_model).strip()[:128]

    if not norm:
        return None, None

    canonical = json.dumps(norm, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    fp_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return norm, fp_hash
