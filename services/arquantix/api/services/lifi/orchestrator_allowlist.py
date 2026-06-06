"""Allowlist pilot prod — orchestrateur LI.FI limité à des personnes explicites.

Règle fail-closed : flags globaux ON sans allowlist configurée → personne n'est pas éligible
(legacy pour tous). Voir CONTROLLED_PROD_PILOT_LIFI_ORCHESTRATOR.md.
"""
from __future__ import annotations

import os
from uuid import UUID

from sqlalchemy.orm import Session

from database import Person, PersonExternalIdentity
from services.portfolio_engine.clients.models import Client


def lifi_orchestrator_allowed_person_emails() -> frozenset[str]:
    raw = (os.getenv("LIFI_ORCHESTRATOR_ALLOWED_PERSON_EMAILS") or "").strip()
    if not raw:
        return frozenset()
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


def lifi_orchestrator_allowlist_configured() -> bool:
    return bool(lifi_orchestrator_allowed_person_emails())


def _person_contact_emails(db: Session, person_id: UUID) -> frozenset[str]:
    emails: set[str] = set()
    for row in db.query(Client).filter(Client.person_id == person_id).all():
        if row.email:
            emails.add(row.email.strip().lower())
    for row in (
        db.query(PersonExternalIdentity).filter(PersonExternalIdentity.person_id == person_id).all()
    ):
        if row.external_email:
            emails.add(row.external_email.strip().lower())
    person = db.query(Person).filter(Person.id == person_id).first()
    if person and isinstance(person.profile_json, dict):
        contact = person.profile_json.get("contact")
        if isinstance(contact, dict):
            collected = contact.get("collected_email")
            if collected:
                emails.add(str(collected).strip().lower())
    return frozenset(emails)


def is_person_lifi_orchestrator_allowlisted(db: Session, person_id: UUID | None) -> bool:
    if person_id is None:
        return False
    allowed = lifi_orchestrator_allowed_person_emails()
    if not allowed:
        return False
    return bool(_person_contact_emails(db, person_id) & allowed)


def lifi_intent_orchestrator_enabled_for_person(db: Session, person_id: UUID | None) -> bool:
    from services.lifi.config import lifi_intent_orchestrator_enabled

    if not lifi_intent_orchestrator_enabled():
        return False
    if not lifi_orchestrator_allowlist_configured():
        return False
    return is_person_lifi_orchestrator_allowlisted(db, person_id)


def lifi_outbox_worker_enabled_for_person(db: Session, person_id: UUID | None) -> bool:
    from services.lifi.config import lifi_outbox_worker_enabled

    if not lifi_outbox_worker_enabled():
        return False
    if not lifi_orchestrator_allowlist_configured():
        return False
    return is_person_lifi_orchestrator_allowlisted(db, person_id)


def lifi_settlement_layer_ledger_enabled_for_person(db: Session, person_id: UUID | None) -> bool:
    from services.lifi.config import lifi_settlement_layer_ledger_enabled

    if not lifi_settlement_layer_ledger_enabled():
        return False
    if not lifi_orchestrator_allowlist_configured():
        return False
    return is_person_lifi_orchestrator_allowlisted(db, person_id)
