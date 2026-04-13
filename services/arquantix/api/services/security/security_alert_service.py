"""
Alertes SIEM production : HIGH (log + persistance événement) ; CRITICAL (+ webhook + email).

Slack : utiliser une URL Incoming Webhook dans ``SECURITY_ALERT_WEBHOOK_URL`` (JSON ``text``).
"""
from __future__ import annotations

import json
import logging
import os
import urllib.error
import urllib.request
from typing import Any, Dict

logger = logging.getLogger("arquantix.security.siem.alert")


def severity_normalize(s: str) -> str:
    u = (s or "").strip().upper()
    return u if u in ("LOW", "MEDIUM", "HIGH", "CRITICAL") else "LOW"


def _summarize_body(body: Dict[str, Any]) -> Dict[str, Any]:
    """Évite de stocker des payloads énormes en DB."""
    out: Dict[str, Any] = {}
    for k, v in list(body.items())[:40]:
        if isinstance(v, (str, int, float, bool)) or v is None:
            out[str(k)[:64]] = v
        else:
            out[str(k)[:64]] = str(type(v).__name__)
    return out


def _persist_alert_event(*, severity: str, title: str, summary: Dict[str, Any]) -> None:
    try:
        from services.auth.security_events_service import is_security_events_enabled
        from services.security.security_event_pipeline import emit_security_event
    except Exception:  # noqa: BLE001
        return
    if not is_security_events_enabled():
        return
    emit_security_event(
        "security.siem.alert",
        user_id=None,
        device_id="siem",
        ip=None,
        metadata={
            "alert_severity": severity,
            "alert_title": title[:500],
            "summary": summary,
        },
        risk_level=severity,
    )


def _webhook_post(url: str, payload: Dict[str, Any]) -> None:
    data = json.dumps(payload, default=str).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=12):  # noqa: S310
        pass


def _send_critical_email(subject: str, text: str) -> None:
    to_addr = (os.getenv("SECURITY_ALERT_EMAIL_TO") or "").strip()
    if not to_addr:
        return
    sender = (os.getenv("SES_FROM_EMAIL") or os.getenv("AWS_SES_FROM") or "").strip()
    region = (os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "eu-west-1").strip()
    if not sender:
        logger.warning("security.alert email skipped: SES_FROM_EMAIL not set")
        return
    try:
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client("ses", region_name=region)
        client.send_email(
            Source=sender,
            Destination={"ToAddresses": [to_addr]},
            Message={
                "Subject": {"Data": subject[:200], "Charset": "UTF-8"},
                "Body": {"Text": {"Data": text[:50000], "Charset": "UTF-8"}},
            },
        )
    except ClientError as e:
        logger.warning("security.alert ses failed: %s", e)
    except Exception as exc:  # noqa: BLE001
        logger.warning("security.alert email failed: %s", exc)


def emit_siem_alert(
    *,
    severity: str,
    title: str,
    body: Dict[str, Any],
) -> None:
    """
    HIGH : log + événement ``security.siem.alert`` en base.
    CRITICAL : idem + webhook (Slack-compatible) + email SES si configuré.
    """
    sev = severity_normalize(severity)
    summary = _summarize_body(body)
    logger.warning("security.siem.alert %s %s keys=%s", sev, title, list(summary.keys()))

    if sev in ("HIGH", "CRITICAL"):
        _persist_alert_event(severity=sev, title=title, summary=summary)

    url = (os.getenv("SECURITY_ALERT_WEBHOOK_URL") or "").strip()
    if sev == "CRITICAL" and url:
        try:
            _webhook_post(
                url,
                {
                    "text": f":rotating_light: `[{sev}]` *{title}*",
                    "severity": sev,
                    "title": title,
                    "details": summary,
                },
            )
        except urllib.error.HTTPError as e:
            logger.warning("security.alert webhook http %s", e.code)
        except Exception as exc:  # noqa: BLE001
            logger.warning("security.alert webhook failed: %s", exc)

    if sev == "CRITICAL":
        _send_critical_email(
            subject=f"[{sev}] {title}",
            text=json.dumps({"title": title, "details": summary}, indent=2, default=str),
        )
