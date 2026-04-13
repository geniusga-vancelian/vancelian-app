"""
FastAPI routes for persons — includes identity unification endpoints.

Phase 4C — Legacy surface (backward-compatible) ::
    ``GET /api/persons/{id}`` and ``POST /api/persons/{id}/fields`` predate the modèle
    identité consolidé. Ils restent exposés tant que des intégrations env
    ``ALLOW_LEGACY_UNAUTHENTICATED_KYC`` ; la cible est ``GET .../identity`` (+ auth
    continue) pour la lecture, et des flux métier explicites pour l’écriture de champs.
    Voir ``PHASE_4C_LEGACY_PERSONS_DEPRECATION_PLAN.md``.
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, Header, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from typing import Any, Dict, List, Optional
import uuid

from auth import oauth2_scheme
from database import get_db, Person, AdminUser
from services.person_fields import set_person_field_value
from schemas import PersonResponse, SetFieldRequest
from services.client_identity.service import (
    ClientIdentityService,
    PersonNotFoundError,
    ClientNotFoundError,
    AlreadyLinkedError,
    InvalidKycStatusError,
)
from sqlalchemy.exc import IntegrityError as SAIntegrityError
from services.portfolio_engine.clients.repository import DuplicateEmailError
from services.auth.dependencies import (
    get_current_user_or_admin,
    get_current_user_or_legacy,
    require_admin,
    require_person_access,
)
from services.security.zero_trust.security_guards import enforce_zero_trust_or_raise
from services.auth.models import AuthContext
from services.security.sensitive_action_events import (
    record_sensitive_action_completed,
    record_sensitive_action_failed,
)
from services.security.session_intelligence_dependencies import require_continuous_auth_for_action
from services.persons.legacy_observability import record_legacy_persons_endpoint_hit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/persons", tags=["persons"])

_identity = ClientIdentityService()

# En-têtes HTTP — signaler la dépréciation sans casser les clients (RFC 9744 style ``Deprecation``).
_LEGACY_DEPRECATION_HEADER = "true"
# RFC 7234 — ``Warning: 299`` (avertissement persistant). Texte stable, ASCII.
_LEGACY_WARNING_POST_FIELDS = (
    '299 - "Deprecated API. Use authenticated onboarding or business APIs."'
)


def _legacy_warning_get_identity(person_id: uuid.UUID) -> str:
    return f'299 - "Deprecated API. Use GET /api/persons/{person_id}/identity"'


def _apply_legacy_person_deprecation_headers(response: Response, person_id: uuid.UUID, *, successor_identity: bool) -> None:
    response.headers["Deprecation"] = _LEGACY_DEPRECATION_HEADER
    if successor_identity:
        response.headers["Link"] = f'</api/persons/{person_id}/identity>; rel="successor-version"'
        response.headers["Warning"] = _legacy_warning_get_identity(person_id)
    else:
        response.headers["Warning"] = _LEGACY_WARNING_POST_FIELDS


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class CreatePersonRequest(BaseModel):
    jurisdiction: Optional[str] = None
    email: str = Field(..., max_length=255)
    status: str = "active"
    profile_json: Dict[str, Any] = {}
    reference_currency: str = "EUR"


class CreatePersonResponse(BaseModel):
    person_id: uuid.UUID
    client_id: uuid.UUID
    kyc_status: str
    jurisdiction: Optional[str]


class EligibilityDetail(BaseModel):
    eligible: bool = False
    kyc_ok: bool = False
    aml_ok: bool = False
    aml_status: str = "not_checked"
    risk_ok: bool = True
    reasons: List[str] = []


class PersonIdentityResponse(BaseModel):
    person: Optional[Dict[str, Any]] = None
    client: Optional[Dict[str, Any]] = None
    jurisdiction: Optional[str] = None
    kyc_status: Optional[str] = None
    is_linked: bool = False
    risk_score: Optional[float] = None
    risk_tier: Optional[str] = None
    is_eligible: bool = False
    eligibility_reason: str = ""
    eligibility: Optional[EligibilityDetail] = None


class UpdateKycStatusRequest(BaseModel):
    kyc_status: str


class LinkPersonClientRequest(BaseModel):
    client_id: uuid.UUID


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("", status_code=status.HTTP_201_CREATED, response_model=CreatePersonResponse)
def create_person(
    request: CreatePersonRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_admin),
):
    """Create a Person and a linked Client (pe_client) atomically."""
    try:
        actor_type = "admin"
        actor_id = str(auth.user_id)

        person, client = _identity.create_person_and_client(
            db,
            email=request.email,
            jurisdiction=request.jurisdiction,
            status=request.status,
            profile_json=request.profile_json,
            reference_currency=request.reference_currency,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        db.commit()
        db.refresh(person)
        db.refresh(client)

        return CreatePersonResponse(
            person_id=person.id,
            client_id=client.id,
            kyc_status=person.kyc_status,
            jurisdiction=person.jurisdiction,
        )
    except (DuplicateEmailError, SAIntegrityError) as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create person")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.get("/{person_id}/identity", response_model=PersonIdentityResponse)
def get_person_identity(
    person_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_person_access),
    _continuous_auth: AdminUser = Depends(require_continuous_auth_for_action("view_sensitive_data")),
    token: str = Depends(oauth2_scheme),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    """Get consolidated identity view: person + client + risk + eligibility."""
    from services.compliance.eligibility_service import EligibilityService

    _ = _continuous_auth
    actor = db.get(AdminUser, auth.user_id)
    if actor is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin user not found")
    if not getattr(request.app.state, "testing", False):
        enforce_zero_trust_or_raise(
            db=db,
            request=request,
            user=actor,
            token=token,
            action="kyc.read",
            resource=f"person:{person_id}",
            x_device_id=x_device_id,
        )

    try:
        identity = _identity.get_client_identity_by_person_id(db, person_id)

        # Risk data from profile_json
        risk_score = None
        risk_tier = None
        person = db.query(Person).filter(Person.id == person_id).first()
        if person:
            pj = person.profile_json or {}
            rs = pj.get("risk-score-current")
            risk_score = float(rs.get("value")) if isinstance(rs, dict) and rs.get("value") is not None else (float(rs) if rs is not None else None)
            rt = pj.get("risk-tier-current")
            risk_tier = rt.get("value") if isinstance(rt, dict) else rt

        elig = EligibilityService.evaluate_by_person_id(db, person_id)

        dev = (x_device_id or "")[:128]
        resp = PersonIdentityResponse(
            person=identity["person"],
            client=identity["client"],
            jurisdiction=identity["jurisdiction"],
            kyc_status=identity["kyc_status"],
            is_linked=identity["is_linked"],
            risk_score=risk_score,
            risk_tier=risk_tier,
            is_eligible=elig.eligible,
            eligibility_reason="; ".join(elig.reasons) if elig.reasons else "eligible",
            eligibility=EligibilityDetail(
                eligible=elig.eligible,
                kyc_ok=elig.kyc_ok,
                aml_ok=elig.aml_ok,
                aml_status=elig.aml_status,
                risk_ok=elig.risk_ok,
                reasons=elig.reasons,
            ),
        )
        record_sensitive_action_completed(
            user_id=auth.user_id,
            action_key="view_sensitive_data",
            request=request,
            db=db,
            device_id=dev,
            extra={
                "endpoint": "GET /api/persons/{person_id}/identity",
                "data_scope": "kyc",
                "person_id": str(person_id),
                "sensitive_fields_accessed": ["person", "client", "eligibility", "risk"],
            },
        )
        db.commit()
        return resp
    except PersonNotFoundError:
        record_sensitive_action_failed(
            user_id=auth.user_id,
            action_key="view_sensitive_data",
            request=request,
            db=db,
            device_id=(x_device_id or "")[:128],
            reason="person_not_found",
            extra={"person_id": str(person_id), "data_scope": "kyc"},
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")


@router.patch("/{person_id}/kyc-status", status_code=status.HTTP_200_OK)
def update_kyc_status(
    person_id: uuid.UUID,
    request_body: UpdateKycStatusRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_admin),
    token: str = Depends(oauth2_scheme),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
):
    """Update a person's KYC status and sync to the linked client."""
    actor = db.get(AdminUser, auth.user_id)
    if actor is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin user not found")
    if not getattr(http_request.app.state, "testing", False):
        enforce_zero_trust_or_raise(
            db=db,
            request=http_request,
            user=actor,
            token=token,
            action="kyc.write",
            resource=f"person:{person_id}",
            x_device_id=x_device_id,
        )
    try:
        actor_type = "admin"
        actor_id = str(auth.user_id)

        person, client = _identity.update_person_kyc_status(
            db,
            person_id,
            request_body.kyc_status,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        db.commit()

        return {
            "person_id": str(person.id),
            "kyc_status": person.kyc_status,
            "client_kyc_status": client.kyc_status if client else None,
            "synced": client is not None,
        }
    except PersonNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    except InvalidKycStatusError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to update KYC status")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


@router.post("/{person_id}/link-client", status_code=status.HTTP_200_OK)
def link_person_to_client(
    person_id: uuid.UUID,
    request: LinkPersonClientRequest,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_admin),
):
    """Link an existing person to an existing client (pe_client)."""
    try:
        actor_type = "admin"
        actor_id = str(auth.user_id)

        person, client = _identity.link_person_to_client(
            db,
            person_id=person_id,
            client_id=request.client_id,
            actor_type=actor_type,
            actor_id=actor_id,
        )
        db.commit()

        return {
            "person_id": str(person.id),
            "client_id": str(client.id),
            "kyc_status": person.kyc_status,
            "is_linked": True,
        }
    except PersonNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    except ClientNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")
    except AlreadyLinkedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to link person to client")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))


# ------------------------------------------------------------------
# Legacy endpoints (backward-compatible) — Phase 4C: dépréciation progressive
# ------------------------------------------------------------------

@router.post(
    "/{person_id}/fields",
    status_code=status.HTTP_200_OK,
    deprecated=True,
    summary="[DEPRECATED] Définir un champ personne (profil)",
    description=(
        "Écriture atomique profile_json + audit. **Déprécié** : prévoir migration vers "
        "des flux d’onboarding / API métier authentifiés. L’accès sans JWT dépend de "
        "``ALLOW_LEGACY_UNAUTHENTICATED_KYC`` (voir ``core.env``)."
    ),
)
def set_field(
    person_id: uuid.UUID,
    request: SetFieldRequest,
    response: Response,
    http_request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_current_user_or_legacy),
):
    """
    Set a field value for a person.
    Creates audit_event and updates profile_json atomically.
    """
    record_legacy_persons_endpoint_hit(
        request=http_request,
        db=db,
        person_id=person_id,
        endpoint_key="legacy_set_field",
        method="POST",
        auth=auth,
    )
    # TODO Phase 4C: supprimer l’accès non authentifié (flag OFF par défaut en prod) puis retirer l’endpoint
    if auth is None:
        logger.warning("legacy_unauthenticated_access endpoint=POST /api/persons/%s/fields", person_id)
        actor_type = "system"
        actor_id = None
    else:
        if not auth.is_admin and (auth.person_id is None or auth.person_id != person_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        actor_type = "admin"
        actor_id = str(auth.user_id)
    try:

        person, audit_event = set_person_field_value(
            db=db,
            person_id=person_id,
            slug=request.slug,
            field_definition_id=request.field_definition_id,
            value=request.value,
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=request.correlation_id,
        )

        _apply_legacy_person_deprecation_headers(response, person_id, successor_identity=False)
        return {
            "person_id": str(person.id),
            "slug": request.slug or "unknown",
            "audit_event_id": str(audit_event.id),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/{person_id}",
    response_model=PersonResponse,
    deprecated=True,
    summary="[DEPRECATED] Personne brute (ORM)",
    description=(
        "Retourne l’enregistrement ``Person`` (dont ``profile_json``). **Déprécié** au profit de "
        "``GET /api/persons/{person_id}/identity`` (vue consolidée, Zero Trust, auth continue). "
        "L’accès sans JWT dépend de ``ALLOW_LEGACY_UNAUTHENTICATED_KYC``."
    ),
)
def get_person(
    person_id: uuid.UUID,
    response: Response,
    http_request: Request,
    db: Session = Depends(get_db),
    auth: Optional[AuthContext] = Depends(get_current_user_or_legacy),
):
    """
    Get a person by ID.
    Returns profile_json (backward-compatible).
    """
    record_legacy_persons_endpoint_hit(
        request=http_request,
        db=db,
        person_id=person_id,
        endpoint_key="legacy_get_person",
        method="GET",
        auth=auth,
    )
    # TODO Phase 4C: après coupure du flag legacy, exiger JWT puis retirer ou réduire à usage interne
    if auth is None:
        logger.warning("legacy_unauthenticated_access endpoint=GET /api/persons/%s", person_id)
    elif not auth.is_admin and (auth.person_id is None or auth.person_id != person_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    _apply_legacy_person_deprecation_headers(response, person_id, successor_identity=True)
    return person
