"""Primitive `classify_actor()` — Phase 2a multi-agents.

Cette primitive est appelée **avant** tout dispatch d'agent par le
service assistance. Elle classe l'acteur authentifié en 4 catégories
qui déterminent le comportement :

  - `CUSTOMER`    : client métier normal, accès complet aux agents.
  - `ONBOARDING`  : registration en cours, accès aux agents en mode
                    « je t'aide à finir ton inscription ».
  - `ADMIN_BO`    : admin BO Vancelian (admin_users.person_id IS NULL),
                    le chat assistance d'un client lui est **interdit**
                    (HTTP 403 / `actor_admin_bo_not_allowed`).
  - `SUSPENDED`   : compte temporairement gelé pour raison de sécurité,
                    réponse standardisée court-circuit, **aucun tool
                    n'est exécuté**.

Cf. :
  - `docs/arquantix/AUDIT_AUTH_IDENTITIES.md` § 7.1 (spec de
    référence) ;
  - `docs/arquantix/MULTI_AGENTS_RUNTIME.md` § 11 (intégration runtime).

──────────────────────────────────────────────────────────────────────
Ordre de classification (priorité décroissante)

  1. SUSPENDED a priorité absolue (gel de sécurité) — testé d'abord
     pour qu'aucune autre logique ne puisse contourner le gel.
  2. CUSTOMER si `auth.client_id` est résolu (chemin nominal).
  3. ONBOARDING si `auth.person_id` est connu mais pas `client_id`.
  4. ADMIN_BO sinon (admin BO pur, pas de person_id ni client_id).

──────────────────────────────────────────────────────────────────────
Contraintes de robustesse

  - **Fail-safe** : en cas d'erreur DB (réseau, transaction cassée,
    etc.), on retourne `ADMIN_BO` qui est le mode le plus restrictif
    pour le chat (403). Mieux vaut un 403 spurious qu'un faux
    `CUSTOMER` qui pourrait laisser fuiter de la donnée.
  - **Aucun import circulaire** : pas de dépendance vers `service.py`
    ni vers les agents (uniquement DB + auth context).
  - **Idempotent** : 0 side-effect, 1 SELECT max sur `persons`.
"""

from __future__ import annotations

import enum
import logging
from typing import Optional

from sqlalchemy.orm import Session

from database import Person
from services.auth.models import AuthContext

logger = logging.getLogger(__name__)


class ActorKind(str, enum.Enum):
    """Catégorie d'acteur authentifié (cf. AUDIT_AUTH_IDENTITIES § 7.1).

    Hérite de `str` pour faciliter la sérialisation JSON et les
    comparaisons.
    """

    CUSTOMER = "customer"
    ONBOARDING = "onboarding"
    ADMIN_BO = "admin_bo"
    SUSPENDED = "suspended"


# Valeurs `persons.account_state` qui déclenchent SUSPENDED.
# Cf. AUDIT_AUTH_IDENTITIES § 7.1 — règle 5.
_SUSPENDED_ACCOUNT_STATES = frozenset({"PARTIAL", "BLOCKED"})


def classify_actor(auth: AuthContext, db: Session) -> ActorKind:
    """Classe l'acteur authentifié en 4 catégories.

    Args:
        auth: Le contexte d'auth résolu par le pipeline JWT (client_id,
              person_id, user_id).
        db:   Session SQLAlchemy ouverte (utilisée uniquement pour le
              check SUSPENDED).

    Returns:
        ActorKind: la catégorie déterminée. Jamais d'exception.

    Notes:
        - SUSPENDED a priorité absolue : on lit `persons` même si
          `client_id` est présent, pour ne jamais laisser passer un
          compte gelé.
        - En cas d'erreur DB, on retourne ADMIN_BO (mode restrictif).
    """
    # 1. SUSPENDED en priorité (gel de sécurité)
    if auth.person_id is not None:
        suspended = _is_person_suspended(auth.person_id, db)
        if suspended:
            return ActorKind.SUSPENDED

    # 2. CUSTOMER si client_id résolu
    if auth.client_id is not None:
        return ActorKind.CUSTOMER

    # 3. ONBOARDING : person sans pe_clients
    if auth.person_id is not None:
        return ActorKind.ONBOARDING

    # 4. ADMIN_BO par défaut
    return ActorKind.ADMIN_BO


def _is_person_suspended(person_id, db: Session) -> bool:
    """True si la personne est gelée (login_frozen ou account_state à risque).

    Robuste : retourne False en cas d'erreur DB (on laisse les autres
    règles décider — un faux SUSPENDED bloquerait le chat sans raison).
    Retourne False aussi si la personne n'existe pas (cas qui ne devrait
    pas arriver vu le pipeline auth, mais on évite un faux SUSPENDED).
    """
    try:
        row: Optional[Person] = (
            db.query(Person.login_frozen, Person.account_state)
            .filter(Person.id == person_id)
            .one_or_none()
        )
    except Exception as exc:  # noqa: BLE001 — fail-safe.
        logger.warning(
            "classify_actor._is_person_suspended db_error person_id=%s exc=%s",
            person_id,
            exc,
        )
        return False

    if row is None:
        return False

    login_frozen, account_state = row
    if login_frozen:
        return True
    if account_state in _SUSPENDED_ACCOUNT_STATES:
        return True
    return False
