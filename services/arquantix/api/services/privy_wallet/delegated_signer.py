"""Signature serveur déléguée Privy (Session Signers / authorization key).

Permet à un worker d'envoyer une transaction sponsorisée depuis le wallet embedded
d'un utilisateur **sans navigateur**, une fois que l'utilisateur a délégué son wallet
au key-quorum de l'app.

Mécanisme (cf. docs Privy « user-and-server-signers ») :
1. L'app détient une clé d'autorisation P-256 (``PRIVY_AUTHORIZATION_KEY``), enregistrée
   en key-quorum dans le dashboard Privy et ajoutée comme signer du wallet user.
2. Pour chaque appel ``POST /v1/wallets/{id}/rpc`` (eth_sendTransaction sponsorisé), le
   serveur signe le payload canonicalisé (ECDSA P-256 / SHA-256) et place la signature
   base64 dans l'en-tête ``privy-authorization-signature``.

Le format du corps RPC et de l'input de signature reproduit **à l'identique** le chemin
navigateur prod (web/src/lib/portal/privySponsoredRpcRequest.ts) pour garantir la parité.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from services.privy_wallet.privy_api_client import PrivyApiError

logger = logging.getLogger(__name__)

PRIVY_API_BASE = "https://api.privy.io"
_AUTH_KEY_PREFIX = "wallet-auth:"


# --------------------------------------------------------------------------- config


def _app_id() -> str:
    return (os.getenv("PRIVY_APP_ID") or "").strip()


def _app_secret() -> str:
    return (os.getenv("PRIVY_APP_SECRET") or "").strip()


def _authorization_key_raw() -> str:
    return (os.getenv("PRIVY_AUTHORIZATION_KEY") or "").strip()


def privy_delegated_signing_configured() -> bool:
    """True si app id/secret + clé d'autorisation présents (sinon module inerte)."""
    return bool(_app_id() and _app_secret() and _authorization_key_raw())


# ------------------------------------------------------------------- hex helpers


def _normalize_hex(value: Any, *, default: str = "0x0") -> str:
    """Normalise une valeur EVM en hex minuscule ``0x…`` (mirroir normalizePrivyTxValueHex)."""
    if value is None:
        return default
    if isinstance(value, bool):  # garde-fou: bool est un int en Python
        raise ValueError("valeur hex booléenne invalide")
    if isinstance(value, int):
        return "0x" + format(value, "x")
    text = str(value).strip().lower()
    if not text:
        return default
    if text.startswith("0x"):
        return text
    if text.isdigit():
        return "0x" + format(int(text), "x")
    return text


# --------------------------------------------------------- payload construction


def build_eth_send_transaction_rpc_body(
    *,
    chain_id: int,
    to: str,
    data: str,
    value: Any = None,
    gas_limit: Any = None,
) -> dict[str, Any]:
    """Corps RPC Privy identique au chemin navigateur (eth_sendTransaction sponsorisé)."""
    transaction: dict[str, str] = {
        "to": to.strip().lower(),
        "data": data.strip().lower(),
        "value": _normalize_hex(value),
    }
    if gas_limit is not None and str(gas_limit).strip():
        transaction["gas_limit"] = _normalize_hex(gas_limit)

    return {
        "method": "eth_sendTransaction",
        "caip2": f"eip155:{int(chain_id)}",
        "chain_type": "ethereum",
        "sponsor": True,
        "params": {"transaction": transaction},
    }


def build_wallet_rpc_url(privy_wallet_id: str) -> str:
    wallet_id = (privy_wallet_id or "").strip()
    if not wallet_id:
        raise PrivyApiError("privy.wallet_id_required", "Wallet Privy introuvable.")
    return f"{PRIVY_API_BASE}/v1/wallets/{urllib.parse.quote(wallet_id, safe='')}/rpc"


def build_authorization_signature_input(
    *,
    app_id: str,
    rpc_url: str,
    rpc_body: dict[str, Any],
) -> dict[str, Any]:
    aid = (app_id or "").strip()
    if not aid:
        raise PrivyApiError("privy.app_id_required", "Privy App ID manquant pour signer.")
    return {
        "version": 1,
        "method": "POST",
        "url": rpc_url,
        "body": rpc_body,
        "headers": {"privy-app-id": aid},
    }


def canonicalize_payload(payload: dict[str, Any]) -> bytes:
    """JSON canonique (clés triées, sans espaces) — RFC 8785 pour nos payloads ASCII."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


# ------------------------------------------------------------------- signing


def _load_authorization_private_key() -> ec.EllipticCurvePrivateKey:
    raw = _authorization_key_raw()
    if not raw:
        raise PrivyApiError(
            "privy.authorization_key_missing",
            "PRIVY_AUTHORIZATION_KEY absent — signature serveur impossible.",
        )
    pem_b64 = raw[len(_AUTH_KEY_PREFIX):] if raw.startswith(_AUTH_KEY_PREFIX) else raw
    pem = f"-----BEGIN PRIVATE KEY-----\n{pem_b64}\n-----END PRIVATE KEY-----\n"
    try:
        key = serialization.load_pem_private_key(pem.encode("utf-8"), password=None)
    except Exception as exc:  # pragma: no cover - format clé invalide
        raise PrivyApiError(
            "privy.authorization_key_invalid",
            "PRIVY_AUTHORIZATION_KEY invalide (P-256 PKCS8 base64 attendu).",
        ) from exc
    if not isinstance(key, ec.EllipticCurvePrivateKey):
        raise PrivyApiError(
            "privy.authorization_key_invalid",
            "Clé d'autorisation Privy non elliptique (P-256 attendue).",
        )
    return key


def generate_authorization_signature(signature_input: dict[str, Any]) -> str:
    """Signe le payload canonicalisé en ECDSA P-256 / SHA-256, retourne base64 (DER)."""
    key = _load_authorization_private_key()
    serialized = canonicalize_payload(signature_input)
    signature = key.sign(serialized, ec.ECDSA(hashes.SHA256()))
    return base64.b64encode(signature).decode("ascii")


# --------------------------------------------------------------- transport


def _basic_auth_headers() -> dict[str, str]:
    app_id = _app_id()
    app_secret = _app_secret()
    if not app_id or not app_secret:
        raise PrivyApiError(
            "privy.api.not_configured",
            "PRIVY_APP_ID et PRIVY_APP_SECRET requis pour la signature serveur.",
        )
    auth = base64.b64encode(f"{app_id}:{app_secret}".encode()).decode()
    return {
        "Authorization": f"Basic {auth}",
        "privy-app-id": app_id,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "arquantix-privy-delegated-signer/1.0",
    }


def _read_tx_hash(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("hash", "transaction_hash", "tx_hash"):
            value = data.get(key)
            if isinstance(value, str) and value.strip() and value.strip() != "0x":
                return value.strip().lower()
    return None


def _read_transaction_id(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if isinstance(data, dict):
        tx_id = data.get("transaction_id")
        if isinstance(tx_id, str) and tx_id.strip():
            return tx_id.strip()
    return None


def _http_post_json(url: str, headers: dict[str, str], body: bytes, *, timeout: int) -> Any:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode()[:400]
        except Exception:  # pragma: no cover
            detail = ""
        raise PrivyApiError(
            "privy.rpc_failed",
            f"Appel RPC Privy échoué (HTTP {exc.code}){': ' + detail if detail else ''}.",
            http_status=exc.code,
        ) from exc
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise PrivyApiError(
            "privy.rpc_unreachable", "Impossible de contacter l'API Privy."
        ) from exc


def _fetch_transaction_hash(transaction_id: str, *, timeout: int = 15) -> str | None:
    url = f"{PRIVY_API_BASE}/v1/transactions/{urllib.parse.quote(transaction_id, safe='')}"
    req = urllib.request.Request(url, headers=_basic_auth_headers(), method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode())
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    for key in ("transaction_hash", "hash", "tx_hash"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip() and value.strip() != "0x":
            return value.strip().lower()
    return None


def send_delegated_sponsored_transaction(
    *,
    privy_wallet_id: str,
    chain_id: int,
    to: str,
    data: str,
    value: Any = None,
    gas_limit: Any = None,
    rpc_timeout: int = 60,
    hash_wait_timeout: int = 120,
    idempotency_key: str | None = None,
) -> dict[str, str | None]:
    """Envoie une tx sponsorisée depuis le wallet user via la clé d'autorisation app.

    Retourne ``{"hash": ..., "transaction_id": ...}``. Lève ``PrivyApiError`` sinon.

    ``idempotency_key`` : si fourni, ajoute l'en-tête ``privy-idempotency-key``. Privy
    garantit alors qu'une requête rejouée avec la **même clé et le même corps** ne diffuse
    pas une seconde transaction (fenêtre 24 h) — garde-fou exactly-once du retry (D1).
    La clé d'idempotence n'entre **pas** dans le payload signé d'autorisation, donc elle ne
    modifie pas la signature.
    """
    if not privy_delegated_signing_configured():
        raise PrivyApiError(
            "privy.delegated_signing_not_configured",
            "Signature serveur Privy non configurée (clé d'autorisation manquante).",
        )

    rpc_url = build_wallet_rpc_url(privy_wallet_id)
    rpc_body = build_eth_send_transaction_rpc_body(
        chain_id=chain_id, to=to, data=data, value=value, gas_limit=gas_limit
    )
    signature_input = build_authorization_signature_input(
        app_id=_app_id(), rpc_url=rpc_url, rpc_body=rpc_body
    )
    authorization_signature = generate_authorization_signature(signature_input)

    headers = {**_basic_auth_headers(), "privy-authorization-signature": authorization_signature}
    if idempotency_key and idempotency_key.strip():
        headers["privy-idempotency-key"] = idempotency_key.strip()
    payload = _http_post_json(
        rpc_url, headers, json.dumps(rpc_body).encode("utf-8"), timeout=rpc_timeout
    )

    tx_hash = _read_tx_hash(payload)
    transaction_id = _read_transaction_id(payload)
    if not tx_hash and transaction_id:
        deadline = time.time() + hash_wait_timeout
        while time.time() < deadline:
            tx_hash = _fetch_transaction_hash(transaction_id)
            if tx_hash:
                break
            time.sleep(2)

    if not tx_hash:
        raise PrivyApiError(
            "privy.missing_tx_hash",
            "Transaction Privy envoyée mais hash indisponible — réessayez.",
        )
    return {"hash": tx_hash, "transaction_id": transaction_id}
