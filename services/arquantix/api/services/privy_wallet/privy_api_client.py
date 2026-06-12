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


def extract_delegated_wallet_addresses(user_payload: dict[str, Any]) -> set[str]:
    """Adresses (lowercase) des wallets délégués (signer app ajouté) — flag Privy ``delegated``.

    Privy marque ``delegated: true`` sur le linked_account ``type=wallet`` dès qu'un signer
    (key-quorum de l'app) est attaché au wallet embedded de l'utilisateur.
    """
    out: set[str] = set()
    for item in extract_wallet_linked_accounts(user_payload):
        if item.get("delegated") is not True:
            continue
        address = str(item.get("address") or "").strip().lower()
        if address:
            out.add(address)
    return out


def is_wallet_delegated(user_payload: dict[str, Any], wallet_address: str) -> bool:
    """True si ``wallet_address`` est délégué (signer serveur de l'app présent)."""
    target = (wallet_address or "").strip().lower()
    if not target:
        return False
    return target in extract_delegated_wallet_addresses(user_payload)


def extract_solana_wallet_linked_accounts(user_payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Comptes wallet Solana depuis ``linked_accounts`` Privy."""
    out: list[dict[str, Any]] = []
    for item in extract_wallet_linked_accounts(user_payload):
        chain_raw = item.get("chain_type") or item.get("chainType") or ""
        chain = str(chain_raw).strip().lower()
        if chain not in ("solana", "sol"):
            continue
        out.append(item)
    return out


def create_privy_wallet(
    *,
    privy_user_id: str,
    chain_type: str = "solana",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """``POST /v1/wallets`` — wallet user-owned (ex. Solana)."""
    uid = (privy_user_id or "").strip()
    if not uid:
        raise PrivyApiError("privy.api.missing_user_id", "privy_user_id requis")

    app_id = (os.getenv("PRIVY_APP_ID") or "").strip()
    app_secret = (os.getenv("PRIVY_APP_SECRET") or "").strip()
    if not app_id or not app_secret:
        raise PrivyApiError(
            "privy.api.not_configured",
            "PRIVY_APP_ID et PRIVY_APP_SECRET requis pour créer un wallet.",
        )

    body = {
        "chain_type": chain_type,
        "owner": {"user_id": uid},
    }
    payload_bytes = json.dumps(body).encode("utf-8")
    auth = base64.b64encode(f"{app_id}:{app_secret}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "privy-app-id": app_id,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "arquantix-privy-wallets/1.0",
    }
    if idempotency_key:
        headers["privy-idempotency-key"] = idempotency_key.strip()

    req = urllib.request.Request(
        "https://api.privy.io/v1/wallets",
        data=payload_bytes,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode()[:500]
        except Exception:
            detail = ""
        logger.info(
            "privy.api.wallet_create_http_error",
            extra={"status": exc.code, "privy_user_id_prefix": uid[:24], "detail": detail[:200]},
        )
        raise PrivyApiError(
            "privy.api.wallet_create_failed",
            f"Création wallet Privy impossible (HTTP {exc.code}){': ' + detail if detail else ''}.",
            http_status=exc.code,
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        logger.info("privy.api.wallet_create_failed", extra={"reason": type(exc).__name__})
        raise PrivyApiError(
            "privy.api.wallet_create_failed",
            "Impossible de contacter l’API Privy.",
        ) from exc

    if not isinstance(payload, dict):
        raise PrivyApiError("privy.api.invalid_response", "Réponse Privy invalide.")
    return payload
