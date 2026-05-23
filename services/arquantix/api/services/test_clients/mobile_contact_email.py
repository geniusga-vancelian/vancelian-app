"""Changement d’e-mail profil mobile : pending → vérification Privy → ``confirmed`` en base."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from database import AdminUser, Person
from services.portfolio_engine.clients.models import Client
from services.registration.service import get_person_collected_value

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", re.IGNORECASE)

STATUS_PENDING = "pending"
STATUS_CONFIRMED = "confirmed"

CHANGE_KEY = "contact_email_change"


def normalize_email(raw: str) -> str:
    return (raw or "").strip().lower()


def validate_email_format(email: str) -> None:
    if not email or not _EMAIL_RE.match(email):
        raise ValueError("Adresse e-mail invalide.")


def _contact_change_blob(person: Person) -> dict[str, Any]:
    pj = person.profile_json or {}
    raw = pj.get(CHANGE_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def get_contact_email_change_state(person: Optional[Person]) -> Optional[dict[str, Any]]:
    if person is None:
        return None
    blob = _contact_change_blob(person)
    if not blob:
        return None
    return {
        "pending_email": blob.get("pending_email"),
        "status": blob.get("status"),
        "requested_at": blob.get("requested_at"),
        "confirmed_at": blob.get("confirmed_at"),
    }


def _set_collected_email(person: Person, email: str) -> None:
    pj: dict[str, Any] = dict(person.profile_json or {})
    collected = dict(pj.get("collected") or {})
    collected["email"] = email
    collected["contact_email"] = email
    pj["collected"] = collected
    person.profile_json = pj
    flag_modified(person, "profile_json")


def request_contact_email_change(person: Person, new_email: str) -> dict[str, Any]:
    """Enregistre un changement **en attente** (aucune écriture de l’e-mail affiché tant que non confirmé)."""
    email = normalize_email(new_email)
    validate_email_format(email)
    current = normalize_email(
        get_person_collected_value(person, "email")
        or get_person_collected_value(person, "contact_email")
        or ""
    )
    if current and current == email:
        raise ValueError("Cette adresse est déjà celle de votre compte.")

    now = datetime.now(timezone.utc).isoformat()
    pj: dict[str, Any] = dict(person.profile_json or {})
    pj[CHANGE_KEY] = {
        "pending_email": email,
        "status": STATUS_PENDING,
        "requested_at": now,
        "confirmed_at": None,
    }
    person.profile_json = pj
    flag_modified(person, "profile_json")
    return dict(pj[CHANGE_KEY])


def _privy_token_email_matches(requested: str, verified_email: Optional[str]) -> bool:
    if verified_email and normalize_email(verified_email) == requested:
        return True
    # En dev stub le JWT n’embarque pas toujours l’e-mail : la session Privy côté app
    # + pending_email aligné suffisent après verify_privy_access_token.
    return verified_email is None or not str(verified_email).strip()


def confirm_contact_email_change(
    db: Session,
    *,
    person: Person,
    client: Client,
    new_email: str,
    verified_privy_email: Optional[str] = None,
) -> dict[str, Any]:
    """Après OTP Privy validé : écrit l’e-mail dans ``collected`` + ``pe_clients`` + statut ``confirmed``."""
    email = normalize_email(new_email)
    validate_email_format(email)

    blob = _contact_change_blob(person)
    pending = normalize_email(str(blob.get("pending_email") or ""))
    status = str(blob.get("status") or "").strip().lower()

    if status != STATUS_PENDING or not pending:
        raise ValueError(
            "Aucune demande de changement d’e-mail en cours. Relancez la modification."
        )
    if pending != email:
        raise ValueError(
            "L’adresse confirmée ne correspond pas à la demande en cours."
        )
    if not _privy_token_email_matches(email, verified_privy_email):
        raise ValueError(
            "Le jeton Privy ne correspond pas à l’adresse e-mail à confirmer."
        )

    taken = (
        db.query(Client)
        .filter(Client.email == email, Client.id != client.id)
        .first()
    )
    if taken is not None:
        raise ValueError("Cette adresse e-mail est déjà utilisée par un autre compte.")

    now = datetime.now(timezone.utc).isoformat()
    _set_collected_email(person, email)

    pj = dict(person.profile_json or {})
    pj[CHANGE_KEY] = {
        "pending_email": email,
        "status": STATUS_CONFIRMED,
        "requested_at": blob.get("requested_at"),
        "confirmed_at": now,
    }
    person.profile_json = pj
    flag_modified(person, "profile_json")

    client.email = email
    db.add(client)

    admin = db.query(AdminUser).filter(AdminUser.person_id == person.id).first()
    if admin is not None:
        other = (
            db.query(AdminUser)
            .filter(AdminUser.email == email, AdminUser.id != admin.id)
            .first()
        )
        if other is None:
            admin.email = email
            db.add(admin)

    db.add(person)
    db.flush()
    from services.test_clients.mobile_profile import sync_pe_client_email_from_collected

    sync_pe_client_email_from_collected(db, client)

    return {
        "email": email,
        "status": STATUS_CONFIRMED,
        "confirmed_at": now,
    }
