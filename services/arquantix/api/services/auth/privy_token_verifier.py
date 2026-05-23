"""Vérification des access tokens Privy (JWT ES256) — ne jamais logger le jeton complet.

Variables d’environnement lues :

- ``PRIVY_APP_ID`` : audience JWT (obligatoire en mode ``jwt``).
- ``PRIVY_APP_SECRET`` : réservé aux appels API Privy côté serveur / futurs SDK ; **non utilisé**
  pour la vérification JWT locale (clé publique).
- ``PRIVY_JWT_VERIFICATION_KEY`` : clé publique PEM **ES256** (dashboard Privy) — prioritaire si définie.
- ``PRIVY_JWKS_URL`` : endpoint JWKS (ex. ``.../jwks.json``) si pas de PEM : la clé est choisie via le ``kid`` du JWT.
- ``PRIVY_EXCHANGE_VERIFICATION_MODE`` : ``stub`` | ``jwt``.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from jose import JWTError, jwt

from core.env import is_dev_mode

logger = logging.getLogger(__name__)

MODE_STUB = "stub"
MODE_JWT = "jwt"


class PrivyVerifyError(Exception):
    """Erreur de vérification (code stable côté API)."""

    def __init__(self, code: str, message: Optional[str] = None):
        self.code = code
        super().__init__(message or code)


@dataclass(frozen=True)
class VerifiedPrivyAccess:
    """Claims vérifiées côté serveur (token Privy)."""

    privy_user_id: str
    app_id: str
    session_id: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    linked_wallets: Optional[List[Dict[str, Any]]] = None


def _exchange_mode() -> str:
    return (os.getenv("PRIVY_EXCHANGE_VERIFICATION_MODE") or "").strip().lower()


def _normalize_pem(raw: str) -> str:
    return (raw or "").replace("\\n", "\n").strip()


def _b64url_to_int(segment: str) -> int:
    pad = "=" * (-len(segment) % 4)
    return int.from_bytes(base64.urlsafe_b64decode(segment + pad), "big")


def _ec_p256_jwk_to_pem(jwk: Dict[str, Any]) -> str:
    if jwk.get("kty") != "EC" or jwk.get("crv") != "P-256":
        raise ValueError("clé JWKS attendue EC + P-256")
    nums = ec.EllipticCurvePublicNumbers(
        _b64url_to_int(jwk["x"]),
        _b64url_to_int(jwk["y"]),
        ec.SECP256R1(),
    )
    pub = nums.public_key(default_backend())
    return pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


@lru_cache(maxsize=8)
def _cached_jwks_kid_pem_pairs(jwks_url: str) -> Tuple[Tuple[str, str], ...]:
    req = urllib.request.Request(
        jwks_url,
        headers={"User-Agent": "arquantix-privy-jwks/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            payload = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        logger.info("privy.jwks_fetch_failed", extra={"reason": type(exc).__name__})
        raise PrivyVerifyError(
            "privy.verification_not_configured",
            "Impossible de récupérer le JWKS Privy.",
        ) from exc

    keys = payload.get("keys") or []
    pairs: Dict[str, str] = {}
    for k in keys:
        if not isinstance(k, dict):
            continue
        kid_raw = k.get("kid")
        if not kid_raw:
            continue
        kid_s = str(kid_raw).strip()
        try:
            pairs[kid_s] = _ec_p256_jwk_to_pem(k)
        except (KeyError, TypeError, ValueError):
            logger.info("privy.jwks_skip_key", extra={"kid": kid_s})

    if not pairs:
        raise PrivyVerifyError(
            "privy.verification_not_configured",
            "JWKS : aucune clé EC P-256 exploitable.",
        )
    return tuple(sorted(pairs.items()))


def _pem_from_jwks_url(token: str, jwks_url: str) -> str:
    try:
        header = jwt.get_unverified_header(token)
    except Exception as exc:
        raise PrivyVerifyError(
            "privy.token_invalid",
            "En-tête JWT Privy illisible.",
        ) from exc

    kid = header.get("kid") if isinstance(header, dict) else None
    if not kid or not str(kid).strip():
        raise PrivyVerifyError(
            "privy.token_invalid",
            "JWT sans kid ; impossible de sélectionner la clé JWKS.",
        )
    kid_s = str(kid).strip()
    mapping = dict(_cached_jwks_kid_pem_pairs(jwks_url.strip()))
    pem = mapping.get(kid_s)
    if not pem:
        # Nouvelle clé côté Privy après rotation : purge cache et retry une fois.
        _cached_jwks_kid_pem_pairs.cache_clear()
        mapping = dict(_cached_jwks_kid_pem_pairs(jwks_url.strip()))
        pem = mapping.get(kid_s)
    if not pem:
        logger.info(
            "privy.jwks_unknown_kid",
            extra={"kid": kid_s, "known": list(mapping.keys())},
        )
        raise PrivyVerifyError(
            "privy.token_invalid",
            "Kid JWKS inconnu pour ce jeton.",
        )
    return pem


def _is_production_like() -> bool:
    env = (os.getenv("ENV") or "").strip().lower()
    if env == "production":
        return True
    return not is_dev_mode()


def _parse_linked_accounts_raw(raw: Any) -> List[Dict[str, Any]]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    return []


def _primary_email_from_linked_accounts(accounts: List[Dict[str, Any]]) -> Optional[str]:
    candidates: List[tuple[int, str]] = []
    for account in accounts:
        if account.get("type") != "email":
            continue
        addr = account.get("address") or account.get("email")
        if not addr:
            continue
        normalized = str(addr).strip().lower()
        if not normalized or "@" not in normalized:
            continue
        lv_raw = account.get("latest_verified_at") or account.get("lv") or account.get("verified_at")
        try:
            lv = int(lv_raw) if lv_raw is not None else 0
        except (TypeError, ValueError):
            lv = 0
        candidates.append((lv, normalized))
    if not candidates:
        return None
    candidates.sort(key=lambda row: row[0], reverse=True)
    return candidates[0][1]


def _primary_phone_from_linked_accounts(accounts: List[Dict[str, Any]]) -> Optional[str]:
    for account in accounts:
        if account.get("type") != "phone":
            continue
        number = account.get("phoneNumber") or account.get("phone_number") or account.get("number")
        if number and str(number).strip():
            return str(number).strip()
    return None


def _extract_email_phone_wallets(claims: Dict[str, Any]) -> tuple[Optional[str], Optional[str], Optional[List[Dict[str, Any]]]]:
    email = claims.get("email")
    if email is not None:
        email = str(email).strip() or None
    phone = claims.get("phone_number") or claims.get("phone")
    if phone is not None:
        phone = str(phone).strip() or None

    linked_accounts = _parse_linked_accounts_raw(claims.get("linked_accounts"))
    if not email and linked_accounts:
        email = _primary_email_from_linked_accounts(linked_accounts)
    if not phone and linked_accounts:
        phone = _primary_phone_from_linked_accounts(linked_accounts)

    wallets_raw = claims.get("linked_accounts") or claims.get("wallets")
    wallets: Optional[List[Dict[str, Any]]] = None
    if isinstance(wallets_raw, list):
        wallets = [w for w in wallets_raw if isinstance(w, dict)]
    return email, phone, wallets


def _decode_privy_jwt_claims(token: str, *, app_id: str, pem: str) -> Dict[str, Any]:
    try:
        claims = jwt.decode(
            token,
            pem,
            algorithms=["ES256"],
            audience=app_id,
            issuer="privy.io",
            options={"verify_aud": True},
        )
    except JWTError as exc:
        logger.info(
            "privy.jwt_verify_failed",
            extra={"error_type": type(exc).__name__},
        )
        raise PrivyVerifyError("privy.token_invalid", "Jeton Privy invalide ou expiré.") from exc
    if not isinstance(claims, dict):
        raise PrivyVerifyError("privy.token_invalid", "Claims JWT Privy invalides.")
    return claims


def _resolve_privy_jwt_verification_pem(token: str) -> tuple[str, str]:
    app_id = (os.getenv("PRIVY_APP_ID") or "").strip()
    pem_static = _normalize_pem(os.getenv("PRIVY_JWT_VERIFICATION_KEY") or "")
    jwks_url = (os.getenv("PRIVY_JWKS_URL") or "").strip()
    if not app_id:
        raise PrivyVerifyError(
            "privy.verification_not_configured",
            "PRIVY_APP_ID requis en mode jwt.",
        )
    if not pem_static and not jwks_url:
        raise PrivyVerifyError(
            "privy.verification_not_configured",
            "PRIVY_JWT_VERIFICATION_KEY ou PRIVY_JWKS_URL requis en mode jwt.",
        )
    pem = pem_static if pem_static else _pem_from_jwks_url(token, jwks_url)
    return app_id, pem


def merge_privy_identity_token(
    verified: VerifiedPrivyAccess,
    identity_token: Optional[str],
) -> VerifiedPrivyAccess:
    """Complète l’e-mail manquant depuis le identity token Privy (``linked_accounts``)."""
    if verified.email:
        return verified
    token = (identity_token or "").strip()
    if not token or _exchange_mode() != MODE_JWT:
        return verified

    app_id, pem = _resolve_privy_jwt_verification_pem(token)
    claims = _decode_privy_jwt_claims(token, app_id=app_id, pem=pem)
    sub = claims.get("sub")
    if not sub or str(sub).strip() != verified.privy_user_id:
        # Identity token périmé (ex. localStorage web) : ignorer, l’access token fait foi.
        logger.info(
            "privy.identity_token_subject_mismatch_ignored",
            extra={"access_sub": verified.privy_user_id[:32]},
        )
        return verified

    email, phone, linked_wallets = _extract_email_phone_wallets(claims)
    if not email and not phone and not linked_wallets:
        return verified
    return VerifiedPrivyAccess(
        privy_user_id=verified.privy_user_id,
        app_id=verified.app_id,
        session_id=verified.session_id,
        email=email or verified.email,
        phone=phone or verified.phone,
        linked_wallets=linked_wallets or verified.linked_wallets,
    )


def fetch_privy_user_verified_email(privy_user_id: str) -> Optional[str]:
    """Dernier recours : API Privy (requiert ``PRIVY_APP_SECRET`` côté serveur)."""
    uid = (privy_user_id or "").strip()
    if not uid:
        return None
    app_id = (os.getenv("PRIVY_APP_ID") or "").strip()
    app_secret = (os.getenv("PRIVY_APP_SECRET") or "").strip()
    if not app_id or not app_secret:
        return None

    auth = base64.b64encode(f"{app_id}:{app_secret}".encode()).decode()
    url = f"https://api.privy.io/v1/users/{uid}"
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
        with urllib.request.urlopen(req, timeout=12) as resp:
            payload = json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        logger.info(
            "privy.users_fetch_failed",
            extra={"reason": type(exc).__name__},
        )
        return None

    if not isinstance(payload, dict):
        return None
    linked = _parse_linked_accounts_raw(payload.get("linked_accounts"))
    return _primary_email_from_linked_accounts(linked)


def enrich_verified_privy_access(
    verified: VerifiedPrivyAccess,
    *,
    identity_token: Optional[str] = None,
) -> VerifiedPrivyAccess:
    """Complète l’e-mail depuis identity token puis, si besoin, l’API Privy."""
    merged = merge_privy_identity_token(verified, identity_token)
    if merged.email:
        return merged
    api_email = fetch_privy_user_verified_email(merged.privy_user_id)
    if not api_email:
        return merged
    return VerifiedPrivyAccess(
        privy_user_id=merged.privy_user_id,
        app_id=merged.app_id,
        session_id=merged.session_id,
        email=api_email,
        phone=merged.phone,
        linked_wallets=merged.linked_wallets,
    )


def verify_stub_privy_token(access_token: str) -> str:
    """Mode dev/test : ``stub:{external_subject}``."""
    if _is_production_like():
        raise PrivyVerifyError(
            "privy.stub_forbidden_in_production",
            "Le mode stub Privy est interdit en production.",
        )

    if _exchange_mode() != MODE_STUB:
        raise PrivyVerifyError(
            "privy.verification_not_configured",
            "Mode stub non actif.",
        )

    t = (access_token or "").strip()
    if not t:
        raise PrivyVerifyError("privy.token_missing", "Jeton Privy manquant.")
    if not t.startswith("stub:"):
        raise PrivyVerifyError("privy.token_invalid", "Jeton stub invalide.")
    subj = t[5:].strip()
    if not subj:
        raise PrivyVerifyError("privy.token_invalid", "Sujet stub vide.")
    return subj


def verify_privy_access_token(access_token: str) -> VerifiedPrivyAccess:
    """
    Point d’entrée unique : stub (dev) ou JWT ES256 avec clé PEM ou JWKS Privy.

    Variables :
    - ``PRIVY_EXCHANGE_VERIFICATION_MODE`` : ``stub`` | ``jwt``
    - ``PRIVY_APP_ID`` : audience JWT (obligatoire en mode jwt)
    - ``PRIVY_JWT_VERIFICATION_KEY`` : clé publique PEM ES256 (prioritaire si définie)
    - ``PRIVY_JWKS_URL`` : URL JWKS (`.../jwks.json`) si PEM absent (sélection par ``kid``)
    - ``PRIVY_APP_SECRET`` : documenté pour l’API / SDK client serveur (non utilisé ici pour le JWT)
    """
    token = (access_token or "").strip()
    if not token:
        raise PrivyVerifyError("privy.token_missing", "Jeton Privy manquant.")

    mode = _exchange_mode()
    if mode == MODE_STUB:
        sub = verify_stub_privy_token(token)
        app_id = (os.getenv("PRIVY_APP_ID") or "").strip() or "stub"
        return VerifiedPrivyAccess(privy_user_id=sub, app_id=app_id)

    if mode != MODE_JWT:
        raise PrivyVerifyError(
            "privy.verification_not_configured",
            "Configurer PRIVY_EXCHANGE_VERIFICATION_MODE=stub ou jwt.",
        )

    # Secret application (API admin Privy) : périmètre Phase 2 = vérif JWT par clé publique uniquement.
    _ = (os.getenv("PRIVY_APP_SECRET") or "").strip()
    app_id, pem = _resolve_privy_jwt_verification_pem(token)
    claims = _decode_privy_jwt_claims(token, app_id=app_id, pem=pem)

    sub = claims.get("sub")
    if not sub or not str(sub).strip():
        raise PrivyVerifyError("privy.token_invalid", "Claim sub manquant.")

    email, phone, linked_wallets = _extract_email_phone_wallets(claims)
    session_id = claims.get("sid")
    sid = str(session_id).strip() if session_id is not None else None

    return VerifiedPrivyAccess(
        privy_user_id=str(sub).strip(),
        app_id=app_id,
        session_id=sid,
        email=email,
        phone=phone,
        linked_wallets=linked_wallets,
    )
