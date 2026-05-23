"""Client HTTP minimal pour l’API Privy (serveur) — wallets utilisateur."""
from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)


class PrivyApiError(Exception):
    def __init__(self, code: str, message: str, *, http_status: int | None = None):
        self.code = code
        self.http_status = http_status
        super().__init__(message)


def privy_server_api_configured() -> bool:
    app_id = (os.getenv("PRIVY_APP_ID") or "").strip()
    app_secret = (os.getenv("PRIVY_APP_SECRET") or "").strip()
    return bool(app_id and app_secret)


def fetch_privy_user(privy_user_id: str) -> dict[str, Any]:
    """``GET /v1/users/{id}`` — nécessite ``PRIVY_APP_ID`` + ``PRIVY_APP_SECRET``."""
    uid = (privy_user_id or "").strip()
    if not uid:
        raise PrivyApiError("privy.api.missing_user_id", "privy_user_id requis")

    app_id = (os.getenv("PRIVY_APP_ID") or "").strip()
    app_secret = (os.getenv("PRIVY_APP_SECRET") or "").strip()
    if not app_id or not app_secret:
        raise PrivyApiError(
            "privy.api.not_configured",
            "PRIVY_APP_ID et PRIVY_APP_SECRET requis pour la réconciliation API.",
        )

    encoded = urllib.parse.quote(uid, safe="")
    auth = base64.b64encode(f"{app_id}:{app_secret}".encode()).decode()
    url = f"https://api.privy.io/v1/users/{encoded}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Basic {auth}",
            "privy-app-id": app_id,
            "Accept": "application/json",
            "User-Agent": "arquantix-privy-users/1.0",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        logger.info(
            "privy.api.users_fetch_http_error",
            extra={"status": exc.code, "privy_user_id_prefix": uid[:24]},
        )
        raise PrivyApiError(
            "privy.api.users_fetch_failed",
            f"API Privy indisponible (HTTP {exc.code}).",
            http_status=exc.code,
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        logger.info("privy.api.users_fetch_failed", extra={"reason": type(exc).__name__})
        raise PrivyApiError(
            "privy.api.users_fetch_failed",
            "Impossible de contacter l’API Privy.",
        ) from exc

    if not isinstance(payload, dict):
        raise PrivyApiError("privy.api.invalid_response", "Réponse Privy invalide.")
    return payload


def extract_wallet_linked_accounts(user_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Extrait les comptes ``type=wallet`` depuis ``linked_accounts`` Privy."""
    raw = user_payload.get("linked_accounts")
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "").strip().lower() != "wallet":
            continue
        address = item.get("address")
        if address and str(address).strip():
            out.append(item)
    return out
