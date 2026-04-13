"""Anonymisation partielle des champs sensibles pour export SIEM (pas la DB interne)."""
from __future__ import annotations

import copy
import re
from typing import Any, Dict


def _mask_email(value: str) -> str:
    s = value.strip()
    if "@" not in s:
        return "***"
    local, _, domain = s.partition("@")
    if len(local) <= 2:
        return f"*@{domain}"
    return f"{local[0]}***{local[-1]}@{domain}"


def _mask_ip(value: str) -> str:
    s = value.strip()
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", s):
        parts = s.split(".")
        return f"{parts[0]}.{parts[1]}.{parts[2]}.*"
    if ":" in s and len(s) > 8:
        return s[:8] + "…"
    return "***"


def _mask_device_id(value: str) -> str:
    s = (value or "").strip()
    if len(s) <= 8:
        return "***"
    return f"{s[:4]}…{s[-4:]}"


def anonymize_metadata_for_sink(metadata: Dict[str, Any] | None) -> Dict[str, Any]:
    """Copie profonde avec masquage des clés ressemblant à e-mail / token."""
    if not metadata:
        return {}
    out: Dict[str, Any] = copy.deepcopy(metadata)
    key_hints = (
        "email",
        "mail",
        "token",
        "secret",
        "password",
        "authorization",
        "credential",
        "refresh",
        "access_token",
    )
    for k, v in list(out.items()):
        kl = k.lower()
        if isinstance(v, str):
            if any(h in kl for h in key_hints):
                if "@" in v:
                    out[k] = _mask_email(v)
                elif len(v) > 12:
                    out[k] = v[:4] + "…"
                else:
                    out[k] = "***"
            elif kl.endswith("_email") or kl == "identifier_domain":
                if "@" in v:
                    out[k] = _mask_email(v)
    return out


def anonymize_security_payload_for_sink(
    *,
    user_id: int | None,
    device_id: str,
    ip_address: str | None,
    user_agent: str | None,
    metadata: Dict[str, Any] | None,
) -> Dict[str, Any]:
    return {
        "user_id": user_id,
        "device_id": _mask_device_id(device_id),
        "ip_address": _mask_ip(ip_address) if ip_address else None,
        "user_agent": (user_agent or "")[:80] + ("…" if user_agent and len(user_agent) > 80 else ""),
        "metadata": anonymize_metadata_for_sink(metadata or {}),
    }
