"""Allowlist pilot prod — Product Locks limités à des personnes explicites.

Règle fail-closed : ``TRANSACTION_PRODUCT_LOCKS_ENABLED=true`` sans allowlist
configurée → personne n'est pas éligible (no-op runtime).
"""
from __future__ import annotations

import os
from uuid import UUID

from sqlalchemy.orm import Session

from services.persons.contact_emails import person_contact_emails
from services.product_locks.config import transaction_product_locks_enabled


def product_locks_allowed_person_emails() -> frozenset[str]:
    raw = (os.getenv("TRANSACTION_PRODUCT_LOCKS_ALLOWED_PERSON_EMAILS") or "").strip()
    if not raw:
        return frozenset()
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


def product_locks_allowlist_configured() -> bool:
    return bool(product_locks_allowed_person_emails())


def is_person_product_locks_allowlisted(db: Session, person_id: UUID | None) -> bool:
    if person_id is None:
        return False
    allowed = product_locks_allowed_person_emails()
    if not allowed:
        return False
    return bool(person_contact_emails(db, person_id) & allowed)


def product_locks_enabled_for_person(db: Session, person_id: UUID | None) -> bool:
    """Product Locks actifs pour ``person_id`` uniquement si flag ON + allowlist + match email."""
    if not transaction_product_locks_enabled():
        return False
    if not product_locks_allowlist_configured():
        return False
    return is_person_product_locks_allowlisted(db, person_id)
