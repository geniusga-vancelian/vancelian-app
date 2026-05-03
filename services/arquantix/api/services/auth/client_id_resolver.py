"""Helper global de résolution `auth.client_id` (clôture audit identité).

Cf. `docs/arquantix/AUDIT_AUTH_IDENTITIES.md` § 5 (BUG B — cache identité
`jwt_only`) et § 7 (décisions actées, règle 4 : promotion globale).

Problème ciblé
──────────────
Le pipeline `resolve_identity_for_auth_context_fast` peut retourner un
`AuthContext` avec `client_id=None` alors que le client existe en base.
Reproduction : cache identité en miss + JWT contient un `person_id` →
mode `jwt_only` → pas de lookup DB → `client_id` à None.

Conséquences observées :
  - 403 `client_required` sur des endpoints `/api/app/*` qui devraient
    accepter le client (constaté `/conversations` poll en boucle, 02 mai).
  - Requêtes nécessitant `client_id` qui rendent un faux 403.

Stratégie
─────────
Ce helper expose une fonction **idempotente** que tout endpoint peut
appeler avant de gate sur `auth.client_id`. Il :
  1. No-op si `auth.client_id` est déjà résolu.
  2. Sinon, si `auth.person_id` est présent : un SELECT ciblé
     `pe_clients.id WHERE person_id=?` → mute `auth.client_id` en place.
  3. Aucune mutation de cache global (scoped par appel pour rester
     prévisible et minimiser les side-effects).

Phase 2a livre uniquement le helper. La migration progressive des
endpoints (chat assistance, portfolio, transactions, etc.) se fait
endpoint par endpoint dans une PR dédiée. Le scope reste réversible.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from services.auth.models import AuthContext

logger = logging.getLogger(__name__)


def patch_auth_client_id_from_person(
    auth: AuthContext, db: Session
) -> bool:
    """Si `auth.client_id` manque, tente de le résoudre via `auth.person_id`.

    Args:
        auth: contexte d'auth (mutable côté Pydantic v2).
        db:   session SQLAlchemy ouverte.

    Returns:
        ``True`` si `auth.client_id` a été (ou est) résolu après l'appel,
        ``False`` si on n'a rien pu faire (le caller décide alors quoi
        renvoyer — typiquement 403 `client_required`).

    Notes:
        - Pas d'exception : tous les fail-cases (DB error, person sans
          pe_client lié, etc.) retournent ``False``.
        - Pas de mutation de cache identité : volontairement scoped à
          ce seul appel pour éviter les side-effects globaux.
    """
    if auth.client_id is not None:
        return True
    if auth.person_id is None:
        return False

    # Lazy import : éviter le cycle `auth -> portfolio_engine -> auth`.
    try:
        from services.portfolio_engine.clients.models import (
            Client as PeClients,
        )
    except ImportError:
        logger.warning(
            "patch_auth_client_id: pe_clients module unavailable"
        )
        return False

    try:
        row = (
            db.query(PeClients.id)
            .filter(PeClients.person_id == auth.person_id)
            .one_or_none()
        )
    except Exception:  # noqa: BLE001 — best-effort, on log et on échoue
        logger.exception(
            "patch_auth_client_id: pe_clients lookup failed person_id=%s",
            auth.person_id,
        )
        return False

    if row is None:
        return False

    auth.client_id = row[0]
    return True
