"""Export d’événements sécurité vers Datadog Logs (HTTP intake v2)."""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict

logger = logging.getLogger("arquantix.auth.siem")


def _site_host() -> str:
    site = (os.getenv("DD_SITE") or os.getenv("DATADOG_SITE") or "datadoghq.com").strip()
    if site in ("datadoghq.eu", "eu"):
        return "http-intake.logs.datadoghq.eu"
    if site in ("us3.datadoghq.com", "us3"):
        return "http-intake.logs.us3.datadoghq.com"
    if site in ("us5.datadoghq.com", "us5"):
        return "http-intake.logs.us5.datadoghq.com"
    return "http-intake.logs.datadoghq.com"


def push_datadog_log(payload: Dict[str, Any]) -> bool:
    """
    Envoie un log structuré. ``payload`` doit contenir au minimum ``event_type``, ``@timestamp`` ISO.
    Retourne True si accepté (2xx).
    """
    api_key = (os.getenv("DATADOG_API_KEY") or os.getenv("DD_API_KEY") or "").strip()
    if not api_key:
        logger.debug("datadog_sink skipped: no DATADOG_API_KEY")
        return False

    service = (os.getenv("SECURITY_EVENTS_DATADOG_SERVICE") or "arquantix-auth-security").strip()
    source = (os.getenv("SECURITY_EVENTS_DATADOG_SOURCE") or "python").strip()

    body_obj = {
        "ddsource": source,
        "ddtags": f"env:{os.getenv('ENVIRONMENT', os.getenv('ENV', 'dev'))},service:{service}",
        "service": service,
        "message": json.dumps(payload, default=str),
        "event_type": payload.get("event_type"),
        "severity": payload.get("severity", "info"),
    }
    url = f"https://{_site_host()}/api/v2/logs"
    data = json.dumps([body_obj]).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "DD-API-KEY": api_key,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310
            return 200 <= resp.getcode() < 300
    except urllib.error.HTTPError as e:
        logger.warning("datadog_sink http_error %s %s", e.code, e.reason)
    except Exception as exc:  # noqa: BLE001
        logger.warning("datadog_sink failed: %s", exc)
    return False
