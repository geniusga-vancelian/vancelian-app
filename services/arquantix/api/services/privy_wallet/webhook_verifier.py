"""Privy webhook signature verification (Svix infrastructure)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import os
import time

from core.env import is_dev_mode

logger = logging.getLogger(__name__)

MODE_STUB = "stub"
MODE_SVIX = "svix"


class PrivyWebhookVerifyError(Exception):
    def __init__(self, code: str, message: str | None = None):
        self.code = code
        super().__init__(message or code)


def _webhook_mode() -> str:
    return (os.getenv("PRIVY_WEBHOOK_VERIFICATION_MODE") or MODE_SVIX).strip().lower()


def _webhook_secret() -> str | None:
    secret = (os.getenv("PRIVY_WEBHOOK_SECRET") or os.getenv("SVIX_WEBHOOK_SECRET") or "").strip()
    return secret or None


def _decode_svix_secret(secret: str) -> bytes:
    if secret.startswith("whsec_"):
        return base64.b64decode(secret.split("_", 1)[1])
    return secret.encode("utf-8")


def verify_svix_webhook(
    payload: bytes,
    *,
    svix_id: str | None,
    svix_timestamp: str | None,
    svix_signature: str | None,
) -> None:
    """Vérifie la signature Svix. Mode ``stub`` autorisé en dev/test uniquement."""
    mode = _webhook_mode()

    if mode == MODE_STUB:
        if not is_dev_mode() and os.getenv("ENV", "").strip().lower() == "production":
            raise PrivyWebhookVerifyError(
                "privy.webhook_stub_forbidden_in_production",
                "Mode stub interdit en production.",
            )
        return

    secret = _webhook_secret()
    if not secret:
        raise PrivyWebhookVerifyError(
            "privy.webhook_verification_not_configured",
            "PRIVY_WEBHOOK_SECRET manquant.",
        )

    if not svix_id or not svix_timestamp or not svix_signature:
        raise PrivyWebhookVerifyError(
            "privy.webhook_signature_missing",
            "En-têtes Svix manquants (svix-id, svix-timestamp, svix-signature).",
        )

    try:
        ts = int(svix_timestamp)
    except ValueError as exc:
        raise PrivyWebhookVerifyError(
            "privy.webhook_timestamp_invalid",
            "svix-timestamp invalide.",
        ) from exc

    now = int(time.time())
    if abs(now - ts) > 300:
        raise PrivyWebhookVerifyError(
            "privy.webhook_timestamp_stale",
            "Horodatage Svix trop ancien.",
        )

    secret_bytes = _decode_svix_secret(secret)
    body_text = payload.decode("utf-8")
    signed_content = f"{svix_id}.{svix_timestamp}.{body_text}"
    expected = hmac.new(
        secret_bytes,
        signed_content.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    expected_sig = base64.b64encode(expected).decode("utf-8")

    valid = False
    for part in svix_signature.split(" "):
        if part.startswith("v1,") and hmac.compare_digest(part[3:], expected_sig):
            valid = True
            break

    if not valid:
        raise PrivyWebhookVerifyError(
            "privy.webhook_signature_invalid",
            "Signature Svix invalide.",
        )
