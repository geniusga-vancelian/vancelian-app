"""Bridge d’identité : Privy / providers externes → Person → PeClient → AdminUser (session JWT technique).

Toute identité externe est ancrée sur ``persons.id`` (voir ``PersonExternalIdentity``).
Le compte ``AdminUser`` reste le moteur de session / ``sub=au:<id>`` jusqu’à refonte éventuelle.
"""

from __future__ import annotations

import logging
import uuid as uuid_mod
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import AdminUser, Person, PersonExternalIdentity, PersonCryptoWallet
from services.portfolio_engine.clients.models import Client as PeClient

logger = logging.getLogger(__name__)

PROVIDER_PRIVY = "privy"


class PersonIdentityBridgeError(Exception):
    """Erreur métier du bridge (message sûr client possible)."""


class DuplicateExternalIdentityError(PersonIdentityBridgeError):
    """Un autre ``person_id`` possède déjà (provider, external_subject)."""


class PersonNotFoundBridgeError(PersonIdentityBridgeError):
    pass


def get_person_from_external_identity(
    db: Session,
    *,
    provider: str,
    external_subject: str,
) -> Optional[Person]:
    """Résout ``Person`` depuis une identité externe enregistrée."""
    prov = (provider or "").strip()
    subj = (external_subject or "").strip()
    if not prov or not subj:
        return None
    row = (
        db.query(PersonExternalIdentity)
        .filter(
            PersonExternalIdentity.provider == prov,
            PersonExternalIdentity.external_subject == subj,
        )
        .first()
    )
    if row is None:
        return None
    return db.query(Person).filter(Person.id == row.person_id).first()


def link_external_identity_to_person(
    db: Session,
    *,
    person_id: UUID,
    provider: str,
    external_subject: str,
    external_email: Optional[str] = None,
    external_phone: Optional[str] = None,
    metadata_json: Optional[Dict[str, Any]] = None,
) -> PersonExternalIdentity:
    """Lie (provider, external_subject) à ``person_id``. Idempotent si même personne.

    Lève :class:`DuplicateExternalIdentityError` si le couple est déjà lié à une autre personne.
    """
    prov = (provider or "").strip()
    subj = (external_subject or "").strip()
    if not prov or not subj:
        raise PersonIdentityBridgeError("provider et external_subject requis")

    person = db.query(Person).filter(Person.id == person_id).first()
    if person is None:
        raise PersonNotFoundBridgeError(f"Person {person_id} introuvable")

    existing = (
        db.query(PersonExternalIdentity)
        .filter(
            PersonExternalIdentity.provider == prov,
            PersonExternalIdentity.external_subject == subj,
        )
        .first()
    )
    if existing is not None:
        if existing.person_id != person_id:
            raise DuplicateExternalIdentityError(
                f"Identité {prov}/{subj} déjà liée à une autre personne"
            )
        if external_email is not None:
            existing.external_email = external_email
        if external_phone is not None:
            existing.external_phone = external_phone
        if metadata_json is not None:
            existing.metadata_json = metadata_json
        db.add(existing)
        db.flush()
        return existing

    row = PersonExternalIdentity(
        id=uuid_mod.uuid4(),
        person_id=person_id,
        provider=prov,
        external_subject=subj,
        external_email=(external_email or "").strip() or None,
        external_phone=(external_phone or "").strip() or None,
        metadata_json=metadata_json,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError as exc:
        logger.warning("person_identity_bridge.link_integrity_error", exc_info=True)
        raise DuplicateExternalIdentityError("Conflit d’identité externe") from exc
    return row


def get_pe_client_for_person(db: Session, *, person_id: UUID) -> Optional[PeClient]:
    """Retourne le ``pe_clients`` lié à la personne s’il existe."""
    return db.query(PeClient).filter(PeClient.person_id == person_id).first()


def get_or_create_login_account_for_person_if_needed(
    db: Session,
    *,
    person_id: UUID,
) -> AdminUser:
    """Retourne l’``AdminUser`` lié à ``person_id``, ou en crée un (mot de passe aléatoire inutilisable)."""
    existing = (
        db.query(AdminUser)
        .filter(AdminUser.person_id == person_id)
        .order_by(AdminUser.id.asc())
        .first()
    )
    if existing is not None:
        return existing

    from auth import get_password_hash

    # Mot de passe aléatoire : auth prévu via OTP / passkeys / Privy — pas login mot de passe.
    random_secret = uuid_mod.uuid4().hex + uuid_mod.uuid4().hex
    user = AdminUser(
        email=None,
        hashed_password=get_password_hash(random_secret),
        person_id=person_id,
        mobile_app_allowed=True,
    )
    db.add(user)
    db.flush()
    logger.info(
        "person_identity_bridge.created_login_admin_user",
        extra={"person_id": str(person_id), "admin_user_id": user.id},
    )
    return user


def upsert_person_crypto_wallet(
    db: Session,
    *,
    person_id: UUID,
    provider: str,
    wallet_type: str,
    chain_type: str,
    address: str,
    chain_id: Optional[int] = None,
    pe_client_id: Optional[UUID] = None,
    is_primary: bool = True,
    metadata_json: Optional[Dict[str, Any]] = None,
) -> PersonCryptoWallet:
    """Crée ou met à jour un wallet user-controlled (unicité provider+chain_type+address)."""
    prov = (provider or "").strip()
    wtype = (wallet_type or "").strip()
    ctype = (chain_type or "").strip()
    addr = (address or "").strip()
    if not prov or not wtype or not ctype or not addr:
        raise PersonIdentityBridgeError("champs wallet incomplets")

    row = (
        db.query(PersonCryptoWallet)
        .filter(
            PersonCryptoWallet.provider == prov,
            PersonCryptoWallet.chain_type == ctype,
            PersonCryptoWallet.address == addr,
        )
        .first()
    )
    if row is not None:
        if row.person_id != person_id:
            raise PersonIdentityBridgeError("adresse déjà enregistrée pour une autre personne")
        row.wallet_type = wtype
        row.chain_id = chain_id
        row.pe_client_id = pe_client_id
        row.is_primary = is_primary
        if metadata_json is not None:
            row.metadata_json = metadata_json
        row.revoked_at = None
        db.add(row)
        db.flush()
        return row

    wallet = PersonCryptoWallet(
        id=uuid_mod.uuid4(),
        person_id=person_id,
        pe_client_id=pe_client_id,
        provider=prov,
        wallet_type=wtype,
        chain_type=ctype,
        chain_id=chain_id,
        address=addr,
        is_primary=is_primary,
        metadata_json=metadata_json,
    )
    db.add(wallet)
    try:
        db.flush()
    except IntegrityError as exc:
        raise PersonIdentityBridgeError("conflit d’unicité wallet") from exc
    return wallet
