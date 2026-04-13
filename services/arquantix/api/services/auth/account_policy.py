"""Politique compte : distinguer back-office web et application mobile Flutter."""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from database import AdminUser

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def admin_email_protected() -> str:
    """E-mail du compte administrateur système (même convention que seed / purge)."""
    return (os.getenv("ADMIN_EMAIL") or "admin@arquantix.com").strip().lower()


def is_web_only_mobile_app_user(user: AdminUser) -> bool:
    """
    True si ce compte ne doit jamais recevoir de session JWT « app mobile ».

    - ``mobile_app_allowed=False`` en base, ou
    - e-mail identique à ``ADMIN_EMAIL`` (filet de sécurité si la colonne est mal synchronisée).
    """
    if not getattr(user, "mobile_app_allowed", True):
        return True
    em = (user.email or "").strip().lower()
    if em and em == admin_email_protected():
        return True
    return False


def app_signup_phone_blocked_by_existing_user(user: AdminUser) -> bool:
    """
    True si une ligne ``admin_users`` avec ce ``mobile_e164`` doit bloquer l’inscription app.

    - **Bloque** si une **Person** est déjà liée (compte client / reprise à traiter côté login).
    - **Ne bloque pas** si **web-only** (sans Person) : libération du mobile à la vérif signup.
    - **Ne bloque pas** si **orphelin** (``person_id`` NULL, pas web-only) : ligne résiduelle sans
      identité Person — l’inscription libère le numéro à la vérif (évite « mobile fantôme »).
    """
    if getattr(user, "person_id", None) is not None:
        return True
    if is_web_only_mobile_app_user(user):
        return False
    return False


def has_portfolio_customer_for_person(db: "Session", user: AdminUser) -> bool:
    """
    True si l’utilisateur est lié à une Personne qui possède une ligne ``pe_clients``
    (client « Customer » portfolio).
    """
    from services.portfolio_engine.clients.models import Client as PeClient

    pid = getattr(user, "person_id", None)
    if pid is None:
        return False
    return db.query(PeClient).filter(PeClient.person_id == pid).first() is not None
