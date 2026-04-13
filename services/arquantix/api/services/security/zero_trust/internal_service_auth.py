"""
Authentification service-à-service (S2S) — base JWT + scopes internes.

## Pattern recommandé (production)

1. **JWT dédié** : émettre des jetons avec ``iss`` / ``aud`` fixes, durée courte (5–15 min),
   et claims ``scopes`` (liste de strings) alignés sur les capacités métier
   (ex. ``internal:market_data:read``). Vérifier signature avec une clé **distincte** de
   celle des utilisateurs finaux (``INTERNAL_JWT_SECRET`` ou JWKS interne).

2. **mTLS** : en complément ou à la place du JWT entre services, terminer TLS mutuel
   au load balancer (ex. ALB + certificat client) ou en mesh (Istio/Linkerd). Le service
   appelant est identifié par le **CN/SAN** du certificat ; le JWT peut alors ne porter
   que des autorisations fines (scopes) alors que mTLS garantit l’origine réseau.

3. **Zero Trust** : chaque appel interne doit passer par la même logique de décision si
   l’action est sensible (policy engine + journalisation), pas seulement « confiance
   réseau VPC ».

## Implémentation actuelle

- ``verify_internal_service_jwt`` : validation HS256 optionnelle (hors chemin critique
  tant que ``INTERNAL_JWT_SECRET`` n’est pas configuré).
- mTLS : **non implémenté dans ce module** — à configurer au niveau infra (voir ci-dessus).
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from jose import JWTError, jwt

INTERNAL_JWT_SECRET = os.getenv("INTERNAL_JWT_SECRET", "").strip()
INTERNAL_JWT_AUDIENCE = os.getenv("INTERNAL_JWT_AUDIENCE", "arquantix-internal")
INTERNAL_JWT_ISSUER = os.getenv("INTERNAL_JWT_ISSUER", "arquantix-services")
INTERNAL_JWT_ALG = os.getenv("INTERNAL_JWT_ALG", "HS256")


def internal_jwt_configured() -> bool:
    return bool(INTERNAL_JWT_SECRET) and len(INTERNAL_JWT_SECRET) >= 16


def issue_internal_service_token(
    *,
    subject: str,
    scopes: List[str],
    expires_seconds: int = 600,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """Émet un JWT S2S (tests / bootstrap). Ne pas exposer publiquement."""
    if not internal_jwt_configured():
        raise RuntimeError("INTERNAL_JWT_SECRET not configured")
    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "sub": subject,
        "iss": INTERNAL_JWT_ISSUER,
        "aud": INTERNAL_JWT_AUDIENCE,
        "scopes": list(scopes),
        "iat": int(now.timestamp()),
        "exp": int(now.timestamp()) + int(expires_seconds),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, INTERNAL_JWT_SECRET, algorithm=INTERNAL_JWT_ALG)


def verify_internal_service_jwt(token: str) -> Optional[Dict[str, Any]]:
    """
    Décode et vérifie un JWT S2S. Retourne le payload ou ``None`` si invalide / désactivé.
    """
    if not internal_jwt_configured():
        return None
    try:
        return jwt.decode(
            token,
            INTERNAL_JWT_SECRET,
            algorithms=[INTERNAL_JWT_ALG],
            audience=INTERNAL_JWT_AUDIENCE,
            issuer=INTERNAL_JWT_ISSUER,
        )
    except JWTError:
        return None


def token_has_scope(payload: Dict[str, Any], required: str) -> bool:
    scopes = payload.get("scopes") or []
    if not isinstance(scopes, list):
        return False
    return required in scopes or "*" in scopes
