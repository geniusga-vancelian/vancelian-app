"""Client Identity Service — centralizes all person<->client operations.

This service is the single entry point for:
- Creating a unified person + client pair
- Linking existing records
- Synchronizing KYC status (persons -> pe_clients)
- Reading consolidated identity data
- Eligibility checks
"""
import logging
import uuid as uuid_mod
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from database import AuditEvent, Person

logger = logging.getLogger(__name__)


def _get_client_model():
    """Lazy import to break circular dependency with portfolio_engine package."""
    from services.portfolio_engine.clients.models import Client
    return Client


# KYC status mapping: persons.kyc_status -> pe_clients.kyc_status
# 1:1 direct mapping — pe_clients now supports pending_review natively.
_PERSON_TO_CLIENT_KYC_MAP: Dict[str, str] = {
    "not_started": "not_started",
    "in_progress": "in_progress",
    "pending_review": "pending_review",
    "approved": "approved",
    "rejected": "rejected",
}

VALID_KYC_STATUSES = {"not_started", "in_progress", "pending_review", "approved", "rejected"}


class ClientIdentityError(Exception):
    """Base error for client identity operations."""


class PersonNotFoundError(ClientIdentityError):
    def __init__(self, person_id: UUID):
        super().__init__(f"Person {person_id} not found")
        self.person_id = person_id


class ClientNotFoundError(ClientIdentityError):
    def __init__(self, client_id: UUID):
        super().__init__(f"Client {client_id} not found")
        self.client_id = client_id


class AlreadyLinkedError(ClientIdentityError):
    def __init__(self, msg: str):
        super().__init__(msg)


class InvalidKycStatusError(ClientIdentityError):
    def __init__(self, status: str):
        super().__init__(f"Invalid KYC status: '{status}'. Valid: {VALID_KYC_STATUSES}")


class ClientIdentityService:

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    @staticmethod
    def create_person_and_client(
        db: Session,
        *,
        email: str,
        jurisdiction: Optional[str] = None,
        status: str = "active",
        profile_json: Optional[Dict[str, Any]] = None,
        reference_currency: str = "EUR",
        actor_type: str = "system",
        actor_id: Optional[str] = None,
    ) -> tuple:
        """Atomically create a Person and a linked Client (pe_client).

        Returns (person, client) after flush (not committed — caller controls tx).
        """
        Client = _get_client_model()

        person = Person(
            id=uuid_mod.uuid4(),
            status=status,
            jurisdiction=jurisdiction,
            profile_json=profile_json or {},
            kyc_status="not_started",
        )
        db.add(person)
        db.flush()

        client = Client(
            id=uuid_mod.uuid4(),
            email=email,
            status="pending",
            kyc_status="not_started",
            reference_currency=reference_currency,
            person_id=person.id,
        )
        db.add(client)
        db.flush()

        # Bidirectional link
        person.client_id = client.id
        db.flush()

        # Audit
        ClientIdentityService._log_audit(
            db,
            person_id=person.id,
            event_type="PERSON_CREATED",
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "person_id": str(person.id),
                "client_id": str(client.id),
                "jurisdiction": jurisdiction,
                "email": email,
            },
        )
        ClientIdentityService._log_audit(
            db,
            person_id=person.id,
            event_type="CLIENT_LINKED",
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "person_id": str(person.id),
                "client_id": str(client.id),
            },
        )

        logger.info(
            "Created person %s + client %s (email=%s, jurisdiction=%s)",
            person.id, client.id, email, jurisdiction,
        )
        return person, client

    @staticmethod
    def ensure_pe_client_for_login_user(
        db: Session,
        *,
        person_id: UUID,
        client_email: Optional[str] = None,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
    ):
        """Garantit une ligne ``pe_clients`` liée à la personne (résolution ``/api/app/*``).

        Certains flux (ex. inscription SMS) créent ``Person`` + ``AdminUser`` sans ``PeClient``.
        Sans cela, ``pe_client_from_jwt_payload`` ne résout rien → **404** sur ``/api/app/profile``.
        Idempotent : si un client existe déjà pour ``person_id``, le retourne.
        ``client_email`` peut être ``None`` (identité = ``person_id`` / ``admin_users.id``).
        """
        Client = _get_client_model()
        existing = db.query(Client).filter(Client.person_id == person_id).first()
        if existing is not None:
            return existing

        person = db.query(Person).filter(Person.id == person_id).with_for_update().first()
        if person is None:
            raise PersonNotFoundError(person_id)

        if person.client_id is not None:
            linked = db.query(Client).filter(Client.id == person.client_id).first()
            if linked is not None:
                return linked

        ce = (client_email or "").strip() if client_email else None

        if ce:
            taken = db.query(Client).filter(Client.email == ce).first()
            if taken is not None and taken.person_id != person_id:
                raise AlreadyLinkedError(
                    f"PeClient email {ce!r} already bound to person {taken.person_id}"
                )

        client = Client(
            id=uuid_mod.uuid4(),
            email=ce,
            status="pending",
            kyc_status="not_started",
            reference_currency="EUR",
            person_id=person.id,
        )
        db.add(client)
        db.flush()
        person.client_id = client.id
        db.flush()

        mapped = _PERSON_TO_CLIENT_KYC_MAP.get(person.kyc_status, "not_started")
        if client.kyc_status != mapped:
            client.kyc_status = mapped
            db.flush()

        ClientIdentityService._log_audit(
            db,
            person_id=person.id,
            event_type="CLIENT_AUTO_PROVISIONED_LOGIN",
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "person_id": str(person.id),
                "client_id": str(client.id),
                "email": ce,
            },
        )
        logger.info(
            "Auto-provisioned PeClient %s for person %s (login ensure, email=%s)",
            client.id,
            person.id,
            ce,
        )
        return client

    # ------------------------------------------------------------------
    # Link
    # ------------------------------------------------------------------

    @staticmethod
    def link_person_to_client(
        db: Session,
        *,
        person_id: UUID,
        client_id: UUID,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
    ) -> tuple:
        """Establish a 1:1 link between an existing Person and an existing Client."""
        Client = _get_client_model()

        person = db.query(Person).filter(Person.id == person_id).with_for_update().first()
        if person is None:
            raise PersonNotFoundError(person_id)

        client = db.query(Client).filter(Client.id == client_id).with_for_update().first()
        if client is None:
            raise ClientNotFoundError(client_id)

        if person.client_id is not None and person.client_id != client_id:
            raise AlreadyLinkedError(
                f"Person {person_id} is already linked to client {person.client_id}"
            )
        if client.person_id is not None and client.person_id != person_id:
            raise AlreadyLinkedError(
                f"Client {client_id} is already linked to person {client.person_id}"
            )

        person.client_id = client.id
        client.person_id = person.id

        # Sync KYC status from person (source of truth) to client
        mapped = _PERSON_TO_CLIENT_KYC_MAP.get(person.kyc_status, "not_started")
        if client.kyc_status != mapped:
            client.kyc_status = mapped

        db.flush()

        ClientIdentityService._log_audit(
            db,
            person_id=person.id,
            event_type="CLIENT_LINKED",
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "person_id": str(person.id),
                "client_id": str(client.id),
            },
        )

        logger.info("Linked person %s <-> client %s", person_id, client_id)
        return person, client

    # ------------------------------------------------------------------
    # KYC Sync
    # ------------------------------------------------------------------

    @staticmethod
    def sync_client_kyc_status_from_person(
        db: Session,
        person: Person,
        *,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
    ):
        """Propagate persons.kyc_status -> pe_clients.kyc_status.

        Returns the updated Client, or None if no client linked.
        """
        Client = _get_client_model()

        if person.client_id is None:
            logger.debug("Person %s has no linked client, skipping KYC sync", person.id)
            return None

        client = db.query(Client).filter(Client.id == person.client_id).first()
        if client is None:
            logger.warning("Person %s references client_id %s but client not found", person.id, person.client_id)
            return None

        new_status = _PERSON_TO_CLIENT_KYC_MAP.get(person.kyc_status, "not_started")
        old_status = client.kyc_status

        if old_status == new_status:
            return client

        client.kyc_status = new_status
        db.flush()

        ClientIdentityService._log_audit(
            db,
            person_id=person.id,
            event_type="KYC_STATUS_SYNCED",
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "person_id": str(person.id),
                "client_id": str(client.id),
                "old_client_kyc_status": old_status,
                "new_client_kyc_status": new_status,
                "person_kyc_status": person.kyc_status,
            },
        )

        logger.info(
            "KYC sync: person %s (%s) -> client %s (%s -> %s)",
            person.id, person.kyc_status, client.id, old_status, new_status,
        )
        return client

    @staticmethod
    def update_person_kyc_status(
        db: Session,
        person_id: UUID,
        new_status: str,
        *,
        actor_type: str = "system",
        actor_id: Optional[str] = None,
    ) -> tuple:
        """Update a person's KYC status and sync to the linked client."""
        if new_status not in VALID_KYC_STATUSES:
            raise InvalidKycStatusError(new_status)

        person = db.query(Person).filter(Person.id == person_id).with_for_update().first()
        if person is None:
            raise PersonNotFoundError(person_id)

        old_status = person.kyc_status
        person.kyc_status = new_status
        person.updated_at = datetime.now(timezone.utc)
        db.flush()

        ClientIdentityService._log_audit(
            db,
            person_id=person.id,
            event_type="KYC_STATUS_CHANGED",
            actor_type=actor_type,
            actor_id=actor_id,
            payload={
                "person_id": str(person.id),
                "old_status": old_status,
                "new_status": new_status,
            },
        )

        client = ClientIdentityService.sync_client_kyc_status_from_person(
            db, person, actor_type=actor_type, actor_id=actor_id,
        )

        return person, client

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    @staticmethod
    def get_client_identity_by_person_id(
        db: Session,
        person_id: UUID,
    ) -> Dict[str, Any]:
        """Return a consolidated view of a person and their linked client."""
        Client = _get_client_model()

        person = db.query(Person).filter(Person.id == person_id).first()
        if person is None:
            raise PersonNotFoundError(person_id)

        client = None
        if person.client_id is not None:
            client = db.query(Client).filter(Client.id == person.client_id).first()

        return ClientIdentityService._build_identity_response(person, client)

    @staticmethod
    def get_client_identity_by_client_id(
        db: Session,
        client_id: UUID,
    ) -> Dict[str, Any]:
        """Return a consolidated view starting from a client_id."""
        Client = _get_client_model()

        client = db.query(Client).filter(Client.id == client_id).first()
        if client is None:
            raise ClientNotFoundError(client_id)

        person = None
        if client.person_id is not None:
            person = db.query(Person).filter(Person.id == client.person_id).first()

        return ClientIdentityService._build_identity_response(person, client)

    # ------------------------------------------------------------------
    # Eligibility
    # ------------------------------------------------------------------

    @staticmethod
    def is_client_eligible_for_products(
        db: Session,
        person_id: UUID,
    ) -> tuple[bool, str]:
        """Check if a person is eligible for product access (trading, lending, offers).

        Delegates to the centralized EligibilityService.
        Returns (is_eligible, reason).
        """
        from services.compliance.eligibility_service import EligibilityService

        result = EligibilityService.evaluate_by_person_id(db, person_id)
        reason = "; ".join(result.reasons) if result.reasons else "eligible"
        return result.eligible, reason

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _build_identity_response(
        person: Optional[Person],
        client,
    ) -> Dict[str, Any]:
        person_data = None
        if person is not None:
            person_data = {
                "id": str(person.id),
                "status": person.status,
                "jurisdiction": person.jurisdiction,
                "kyc_status": person.kyc_status,
                "client_id": str(person.client_id) if person.client_id else None,
                "created_at": person.created_at.isoformat() if person.created_at else None,
                "updated_at": person.updated_at.isoformat() if person.updated_at else None,
            }

        client_data = None
        if client is not None:
            client_data = {
                "id": str(client.id),
                "email": client.email,
                "status": client.status,
                "kyc_status": client.kyc_status,
                "reference_currency": client.reference_currency,
                "person_id": str(client.person_id) if client.person_id else None,
                "created_at": client.created_at.isoformat() if client.created_at else None,
                "updated_at": client.updated_at.isoformat() if client.updated_at else None,
            }

        return {
            "person": person_data,
            "client": client_data,
            "jurisdiction": person.jurisdiction if person else None,
            "kyc_status": person.kyc_status if person else (client.kyc_status if client else None),
            "is_linked": person is not None and client is not None,
        }

    @staticmethod
    def _log_audit(
        db: Session,
        *,
        person_id: UUID,
        event_type: str,
        actor_type: str,
        actor_id: Optional[str],
        payload: Dict[str, Any],
    ) -> AuditEvent:
        event = AuditEvent(
            id=uuid_mod.uuid4(),
            person_id=person_id,
            event_type=event_type,
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=uuid_mod.uuid4(),
            payload=payload,
            schema_version=1,
            created_at=datetime.now(timezone.utc),
        )
        db.add(event)
        db.flush()
        return event
