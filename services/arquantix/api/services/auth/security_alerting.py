"""Alertes sécurité — délégué à ``services.security.security_alert_service``."""
from __future__ import annotations

from typing import Any, Dict

from services.security.security_alert_service import emit_siem_alert, severity_normalize


def severity_rank(sev: str) -> int:
    return {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}.get(severity_normalize(sev), 0)


def send_security_alert(
    *,
    severity: str,
    title: str,
    body: Dict[str, Any],
) -> None:
    emit_siem_alert(severity=severity, title=title, body=body)
