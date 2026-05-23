"""Wallets crypto non custodial liés au ``person_id`` du JWT (`person_crypto_wallets`)."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import ALGORITHM, SECRET_KEY
from database import Person, get_db
from services.auth.privy_exchange_routes import (
    PrivyExchangeWalletOut,
    serialize_active_crypto_wallets_for_person,
)

router = APIRouter(prefix="/auth", tags=["auth-privy"])
_bearer_optional = HTTPBearer(auto_error=False)


class PersonCryptoWalletsResponse(BaseModel):
    wallets: list[PrivyExchangeWalletOut] = Field(default_factory=list)


def _jwt_person_uuid(token: str) -> UUID:
    try:
        payload = jwt.decode(token.strip(), SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "privy.person_wallets_invalid_session",
                "message": "JWT invalide ou expiré.",
            },
        ) from exc

    person_id_raw = payload.get("person_id")
    if person_id_raw is None or str(person_id_raw).strip() == "":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "privy.person_wallets_requires_person_claim",
                "message": "Claim person_id manquant dans le JWT.",
            },
        )
    try:
        return UUID(str(person_id_raw).strip())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "privy.person_wallets_requires_person_claim",
                "message": "person_id JWT invalide.",
            },
        ) from exc


@router.get(
    "/privy/person-wallets",
    response_model=PersonCryptoWalletsResponse,
    summary="Lister les wallets personCrypto actifs pour le JWT courant",
)
def get_person_crypto_wallets_authenticated_session(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_optional),
) -> PersonCryptoWalletsResponse:
    """Wallets persistés après ``POST /auth/privy/exchange`` (sans révoqués)."""

    if credentials is None or not (credentials.credentials or "").strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "privy.person_wallets_requires_session",
                "message": "Authorization: Bearer (JWT Vancelian) requis.",
            },
        )

    pid = _jwt_person_uuid(credentials.credentials)
    person = db.query(Person).filter(Person.id == pid).first()
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "privy.person_wallets_person_not_found",
                "message": "Person introuvable.",
            },
        )

    wallets = serialize_active_crypto_wallets_for_person(db, person_id=pid)
    return PersonCryptoWalletsResponse(wallets=wallets)
