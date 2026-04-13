"""Résolution du client portfolio (PeClient) pour l’app mobile : JWT obligatoire."""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from auth import ALGORITHM, SECRET_KEY
from database import AdminUser, get_db
from services.auth.security_setup_state import (
    NEEDS_SECURITY_SETUP_DETAIL,
    ensure_pe_client_if_passcode_ack,
    person_has_local_passcode_ack,
)
from services.portfolio_engine.clients.models import Client as PeClient

logger = logging.getLogger(__name__)


def _assert_mobile_app_security_complete(db: Session, payload: dict[str, Any]) -> None:
    """Garde-fous identité : ACK passcode → PeClient ; cas orphelins PeClient sans lien admin."""
    u = _admin_user_from_mobile_jwt_payload(db, payload)
    if u is not None:
        ensure_pe_client_if_passcode_ack(db, u)
    c = pe_client_from_jwt_payload(db, payload)
    if c is not None:
        u2 = db.query(AdminUser).filter(AdminUser.person_id == c.person_id).first()
        if u2 is not None:
            ensure_pe_client_if_passcode_ack(db, u2)
        if u2 is None and not person_has_local_passcode_ack(db, c.person_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=NEEDS_SECURITY_SETUP_DETAIL,
            )


def decode_bearer_payload(token: str) -> dict[str, Any]:
    """Décode le JWT ; lève 401 si signature / expiration invalides."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        logger.warning(
            "security_mobile: bearer_token_invalid",
            extra={"error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def pe_client_from_jwt_payload(db: Session, payload: dict[str, Any]) -> Optional[PeClient]:
    """Retourne le PeClient lié aux claims ``person_id`` / ``pid`` / ``sub`` (``au:<id>``)."""
    from uuid import UUID

    raw_pid = payload.get("person_id") or payload.get("pid")
    if raw_pid:
        try:
            pid = UUID(str(raw_pid))
        except ValueError:
            pid = None
        if pid is not None:
            c = db.query(PeClient).filter(PeClient.person_id == pid).first()
            if c is not None:
                return c

    sub = payload.get("sub")
    if sub is not None and str(sub).strip():
        from services.auth.jwt_subject_resolution import NonUserJWTSubjectError, resolve_user_from_jwt_sub

        try:
            u, _st, kind = resolve_user_from_jwt_sub(db, str(sub), record_metric=False)
        except NonUserJWTSubjectError:
            return None
        if kind == "ok" and u is not None and u.person_id is not None:
            c = db.query(PeClient).filter(PeClient.person_id == u.person_id).first()
            if c is not None:
                return c

    return None


def _admin_user_from_mobile_jwt_payload(
    db: Session, payload: dict[str, Any]
) -> Optional[AdminUser]:
    """Retourne l’``AdminUser`` dont l’identité correspond au JWT (``sub`` = ``au:<id>`` ou ``person_id``/``pid``)."""
    from uuid import UUID

    raw_pid = payload.get("person_id") or payload.get("pid")
    if raw_pid:
        try:
            pid = UUID(str(raw_pid))
        except ValueError:
            pid = None
        if pid is not None:
            u = db.query(AdminUser).filter(AdminUser.person_id == pid).first()
            if u is not None:
                return u

    sub = payload.get("sub")
    if sub is not None and str(sub).strip():
        from services.auth.jwt_subject_resolution import NonUserJWTSubjectError, resolve_user_from_jwt_sub

        try:
            u, _st, kind = resolve_user_from_jwt_sub(db, str(sub), record_metric=False)
        except NonUserJWTSubjectError:
            return None
        if kind == "ok" and u is not None:
            return u

    return None


def _try_ensure_pe_client_for_mobile_jwt(db: Session, payload: dict[str, Any]) -> bool:
    """Si JWT valide mais aucun PeClient : provisionne depuis ``AdminUser`` (idempotent)."""
    user = _admin_user_from_mobile_jwt_payload(db, payload)
    if user is None or getattr(user, "person_id", None) is None:
        return False

    try:
        from services.client_identity.service import ClientIdentityService

        _raw = getattr(user, "email", None)
        _ce = str(_raw).strip() if _raw else None
        ClientIdentityService.ensure_pe_client_for_login_user(
            db,
            person_id=user.person_id,
            client_email=_ce,
            actor_type="mobile_identity.lazy_ensure",
            actor_id=str(user.id),
        )
        db.flush()
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "security_mobile: lazy_ensure_pe_client_failed user_id=%s: %s",
            user.id,
            exc,
        )
        return False

    logger.info(
        "security_mobile: pe_client_lazy_provisioned user_id=%s person_id=%s",
        user.id,
        user.person_id,
    )
    return True


def _assert_client_id_claim_matches_jwt(client: PeClient, payload: dict[str, Any]) -> None:
    """Si le JWT contient ``client_id`` ou ``cid``, il doit correspondre au client résolu en base."""
    raw = payload.get("client_id") or payload.get("cid")
    if raw is None:
        return
    claim = str(raw).strip()
    if not claim:
        return
    if str(client.id) != claim:
        logger.error(
            "security_mobile: jwt_client_id_claim_mismatch",
            extra={"resolved_client_id": str(client.id), "claim": claim},
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client identity mismatch.",
        )


def client_from_access_token(db: Session, token: str) -> Optional[PeClient]:
    """Retourne le [PeClient] lié au JWT (``pid`` / ``person_id`` / ``sub`` = ``au:<id>``).

    Si le token est mal formé ou expiré, lève **401** (ne plus confondre avec « pas de client »).
    Si le JWT est valide mais aucun PeClient : tente un provisionnement idempotent lié à ``AdminUser``.
    """
    payload = decode_bearer_payload(token)
    _assert_mobile_app_security_complete(db, payload)
    client = pe_client_from_jwt_payload(db, payload)
    if client is None:
        if _try_ensure_pe_client_for_mobile_jwt(db, payload):
            client = pe_client_from_jwt_payload(db, payload)
    if client is not None:
        _assert_client_id_claim_matches_jwt(client, payload)
        raw_pid = payload.get("person_id") or payload.get("pid")
        logger.info(
            "mobile_identity: bearer_resolved client_id=%s person_id=%s",
            client.id,
            raw_pid if raw_pid is not None else "",
        )
    return client


def resolve_bootstrap_client(
    db: Session,
    credentials: Optional[HTTPAuthorizationCredentials],
) -> PeClient:
    """Bearer obligatoire : client issu du JWT uniquement."""
    if not credentials or not credentials.credentials:
        logger.warning("security_mobile: unauthenticated_app_route_blocked")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    client = client_from_access_token(db, credentials.credentials)
    if client is not None:
        return client

    logger.warning(
        "security_mobile: bearer_valid_but_no_pe_client",
        extra={"detail": "no_client_profile"},
    )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No client profile linked to this session.",
    )


mobile_bearer = HTTPBearer(auto_error=False)


def mobile_app_client(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
) -> PeClient:
    """Dépendance FastAPI : même résolution que ``/api/app/bootstrap`` (JWT uniquement)."""
    return resolve_bootstrap_client(db, credentials)
