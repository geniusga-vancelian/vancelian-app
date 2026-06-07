"""Résolution des emails de contact d'une person (allowlists pilot)."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from database import Person, PersonExternalIdentity
from services.portfolio_engine.clients.models import Client


def person_contact_emails(db: Session, person_id: UUID) -> frozenset[str]:
    """Emails connus pour ``person_id`` (lowercase, trim).

    Sources : ``clients.email`` · ``person_external_identities.external_email``
    · ``profile_json.contact.collected_email``.
    """
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
