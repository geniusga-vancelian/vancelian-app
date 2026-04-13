"""Ensure OTP target matches verified identity when profile data exists (prod)."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database import Person
from services.security.two_factor_exceptions import TwoFactorException


def assert_target_allowed_for_person(
    db: Session,
    person: Person,
    *,
    channel: str,
    target: Optional[str],
    purpose: str,
    relaxed: bool,
) -> None:
    if relaxed or not target:
        return
    if purpose not in ("verify_email", "login"):
        return
    client = getattr(person, "trading_client", None)
    if client is None:
        from services.portfolio_engine.clients.models import Client

        client = db.query(Client).filter(Client.person_id == person.id).first()
    if client is None or not getattr(client, "email", None):
        return
    if target.strip().lower() != str(client.email).strip().lower():
        raise TwoFactorException(
            "target_mismatch",
            "Email does not match the account on file",
        )
