"""Résolution stricte Person → pe_client pour custody (flux canonique euro / IBAN).

Aucune création d’entité ici : uniquement chargement et validation.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session

from database import AdminUser, Person
from services.portfolio_engine.clients.models import Client
from services.registration.service import get_person_collected_value

logger = logging.getLogger(__name__)

class CustodyIdentityResolutionError(ValueError):
    """Erreur de résolution d’identité pour custody (message exploitable par l’API)."""


class PersonNotFoundForCustodyError(CustodyIdentityResolutionError):
    pass


class AmbiguousPhoneResolutionError(CustodyIdentityResolutionError):
    pass


class PeClientMissingForPersonError(CustodyIdentityResolutionError):
    pass


class OrphanPeClientError(CustodyIdentityResolutionError):
    pass


class MultipleResolutionInputsError(CustodyIdentityResolutionError):
    pass


class NoResolutionInputError(CustodyIdentityResolutionError):
    pass


ResolutionSource = Literal["person_id", "phone_e164", "pe_client_id"]


@dataclass(frozen=True)
class CustodyIdentityResolution:
    person_id: UUID
    pe_client_id: UUID
    person_email_collected: str | None
    pe_client_email: str | None
    phone_e164: str | None
    source: ResolutionSource


def normalize_phone_e164(raw: str) -> str:
    t = re.sub(r"\s+", "", (raw or "").strip())
    if not t:
        return ""
    if not t.startswith("+"):
        t = "+" + t.lstrip("+")
    return t


def _phones_from_person_profile(person: Person) -> set[str]:
    out: set[str] = set()
    pj = person.profile_json or {}
    coll = pj.get("collected") if isinstance(pj.get("collected"), dict) else {}
    for key in ("phone_e164", "phone"):
        raw = coll.get(key) if isinstance(coll, dict) else None
        if raw:
            n = normalize_phone_e164(str(raw))
            if n:
                out.add(n)
    return out


def find_person_ids_by_phone_e164(db: Session, phone: str) -> list[UUID]:
    """Retourne les person_id dont le numéro correspond (profil + admin_users.mobile_e164).

    Déduplique ; l’appelant doit refuser si len > 1.
    """
    want = normalize_phone_e164(phone)
    if not want:
        return []

    found: set[UUID] = set()

    au_rows = db.query(AdminUser).filter(AdminUser.mobile_e164 == want).all()
    for u in au_rows:
        if u.person_id is not None:
            found.add(u.person_id)

    for person in db.query(Person).all():
        if want in _phones_from_person_profile(person):
            found.add(person.id)

    return list(found)


def _collected_business_email(person: Person) -> str | None:
    for slug in ("email", "contact_email"):
        raw = get_person_collected_value(person, slug)
        if raw is None:
            continue
        s = str(raw).strip()
        if s and "@" in s:
            return s
    return None


def _phone_for_display(db: Session, person: Person) -> str | None:
    pj = person.profile_json or {}
    coll = pj.get("collected") if isinstance(pj.get("collected"), dict) else {}
    for key in ("phone_e164", "phone"):
        raw = coll.get(key) if isinstance(coll, dict) else None
        if raw:
            n = normalize_phone_e164(str(raw))
            if n:
                return n
    u = db.query(AdminUser).filter(AdminUser.person_id == person.id).first()
    if u and u.mobile_e164:
        return normalize_phone_e164(u.mobile_e164)
    return None


def get_pe_client_for_person_or_raise(db: Session, person_id: UUID) -> Client:
    c = db.query(Client).filter(Client.person_id == person_id).first()
    if c is None:
        raise PeClientMissingForPersonError(
            f"Aucune ligne pe_clients pour person_id={person_id}. "
            "Provisionner le client PE (app / ensure_pe_client) avant custody."
        )
    return c


def resolve_person_and_pe_client_for_custody(
    db: Session,
    *,
    person_id: UUID | None = None,
    phone_e164: str | None = None,
    pe_client_id: UUID | None = None,
) -> CustodyIdentityResolution:
    """Résout exactement une Person et un PeClient — aucun fallback silencieux.

    Exactement **un** des trois paramètres doit être non nul.
    """
    inputs = [x for x in (person_id, phone_e164, pe_client_id) if x is not None]
    if len(inputs) == 0:
        raise NoResolutionInputError(
            "Fournir exactement un critère : person_id, phone_e164 ou pe_client_id."
        )
    if len(inputs) > 1:
        raise MultipleResolutionInputsError(
            "Fournir un seul critère : person_id, phone_e164 ou pe_client_id (pas plusieurs)."
        )

    source: ResolutionSource
    person: Person
    client: Client

    if person_id is not None:
        source = "person_id"
        person = db.query(Person).filter(Person.id == person_id).first()
        if person is None:
            raise PersonNotFoundForCustodyError(f"Person introuvable : {person_id}")
        client = get_pe_client_for_person_or_raise(db, person.id)

    elif phone_e164 is not None:
        source = "phone_e164"
        pids = find_person_ids_by_phone_e164(db, phone_e164)
        if len(pids) == 0:
            raise PersonNotFoundForCustodyError(
                f"Aucune personne pour le téléphone {normalize_phone_e164(phone_e164)!r}."
            )
        if len(pids) > 1:
            raise AmbiguousPhoneResolutionError(
                f"Téléphone ambigu : plusieurs personnes ({len(pids)}) pour "
                f"{normalize_phone_e164(phone_e164)!r}. Utiliser person_id."
            )
        person = db.query(Person).filter(Person.id == pids[0]).first()
        assert person is not None
        client = get_pe_client_for_person_or_raise(db, person.id)

    else:
        assert pe_client_id is not None
        source = "pe_client_id"
        client = db.query(Client).filter(Client.id == pe_client_id).first()
        if client is None:
            raise PersonNotFoundForCustodyError(f"pe_client introuvable : {pe_client_id}")
        if client.person_id is None:
            raise OrphanPeClientError(f"pe_client {pe_client_id} sans person_id (orphelin).")
        person = db.query(Person).filter(Person.id == client.person_id).first()
        if person is None:
            raise OrphanPeClientError(
                f"pe_client {pe_client_id} pointe vers person_id={client.person_id} inexistant."
            )

    phone_disp = _phone_for_display(db, person)
    email_coll = _collected_business_email(person)
    raw_pe = client.email
    pe_email = raw_pe.strip() if raw_pe else None

    return CustodyIdentityResolution(
        person_id=person.id,
        pe_client_id=client.id,
        person_email_collected=email_coll,
        pe_client_email=pe_email,
        phone_e164=phone_disp,
        source=source,
    )


def enrichment_fields_for_pe_client(db: Session, client: Client | None) -> dict:
    """Champs identité pour enrichir AccountRead (liste custody / admin)."""
    if client is None or not client.person_id:
        return {
            "person_id": None,
            "person_email_collected": None,
            "phone_e164": None,
        }
    person = db.query(Person).filter(Person.id == client.person_id).first()
    if person is None:
        return {
            "person_id": client.person_id,
            "person_email_collected": None,
            "phone_e164": None,
        }
    return {
        "person_id": person.id,
        "person_email_collected": _collected_business_email(person),
        "phone_e164": _phone_for_display(db, person),
    }
