"""Passcode serveur (ACK), JWT partiel (``sec_inc``), état compte app (``acct_st``)."""
from __future__ import annotations

from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database import AdminUser, Person
from services.auth.account_policy import has_portfolio_customer_for_person, is_web_only_mobile_app_user

# Contrat produit / clients (JWT claim ``acct_st``, réponses SMS)
ACCOUNT_STATE_ACTIVE = "ACTIVE"
ACCOUNT_STATE_PARTIAL = "PARTIAL"
ACCOUNT_STATE_INCOMPLETE = "INCOMPLETE"
ACCOUNT_STATE_ADMIN_WEB = "ADMIN_WEB"


def person_has_local_passcode_ack(db: Session, person_id: Any) -> bool:
    """True si ``profile_json.security.local_passcode_registered_at`` est défini."""
    if person_id is None:
        return False
    try:
        pid = person_id if isinstance(person_id, UUID) else UUID(str(person_id))
    except (ValueError, TypeError):
        return False
    p = db.get(Person, pid)
    if p is None:
        return False
    pj: dict[str, Any] = dict(p.profile_json or {})
    sec = pj.get("security") if isinstance(pj.get("security"), dict) else {}
    ts = sec.get("local_passcode_registered_at")
    return bool(ts and str(ts).strip())


def ensure_pe_client_if_passcode_ack(db: Session, user: AdminUser) -> None:
    """Best-effort : si passcode serveur OK, provisionne ``pe_clients`` avant dérivation ACTIVE / bootstrap."""
    if getattr(user, "person_id", None) is None:
        return
    if not person_has_local_passcode_ack(db, user.person_id):
        return
    try:
        from services.client_identity.service import ClientIdentityService

        _raw = getattr(user, "email", None)
        _ce = str(_raw).strip() if _raw else None
        ClientIdentityService.ensure_pe_client_for_login_user(
            db,
            person_id=user.person_id,
            client_email=_ce,
            actor_type="mobile_identity.ensure_pe_if_ack",
            actor_id=str(user.id),
        )
        db.flush()
    except Exception:
        pass


def persist_person_account_state_column(db: Session, user: AdminUser, derived_state: str) -> None:
    """Persiste ``persons.account_state`` sur l’état dérivé (facts) — requêtes / audits / migration."""
    if getattr(user, "person_id", None) is None:
        return
    if derived_state not in (ACCOUNT_STATE_ACTIVE, ACCOUNT_STATE_PARTIAL):
        return
    p = db.get(Person, user.person_id)
    if p is None:
        return
    if getattr(p, "account_state", None) == derived_state:
        return
    p.account_state = derived_state
    db.add(p)


def derive_account_state(db: Session, user: AdminUser) -> str:
    """
    - **ACTIVE** : passcode serveur + ``PeClient`` pour la Person.
    - **PARTIAL** : Person liée mais setup incomplet (OTP OK côté mobile, sans accès app complet).
    - **INCOMPLETE** : mobile en base sans Person (orphelin) ou hors app mobile.
    - **ADMIN_WEB** : compte réservé back-office.
    """
    if is_web_only_mobile_app_user(user):
        return ACCOUNT_STATE_ADMIN_WEB
    if getattr(user, "person_id", None) is None:
        return ACCOUNT_STATE_INCOMPLETE
    if not getattr(user, "mobile_app_allowed", True):
        return ACCOUNT_STATE_INCOMPLETE
    if person_has_local_passcode_ack(db, user.person_id) and has_portfolio_customer_for_person(
        db, user
    ):
        return ACCOUNT_STATE_ACTIVE
    return ACCOUNT_STATE_PARTIAL


def should_issue_partial_session_for_mobile_app(db: Session, user: AdminUser) -> bool:
    """
    True → JWT avec ``sec_inc`` (OTP validé, compte pas encore ACTIVE).

    Les comptes web-only ou sans Person ne passent pas par cette voie.
    """
    if is_web_only_mobile_app_user(user):
        return False
    if getattr(user, "person_id", None) is None:
        return False
    if not getattr(user, "mobile_app_allowed", True):
        return False
    return derive_account_state(db, user) != ACCOUNT_STATE_ACTIVE


NEEDS_SECURITY_SETUP_DETAIL: dict[str, Any] = {
    "code": "needs_security_setup",
    "message": (
        "Configuration du code d’accès requise. Finalisez la sécurisation du compte "
        "(passcode enregistré côté serveur)."
    ),
}
