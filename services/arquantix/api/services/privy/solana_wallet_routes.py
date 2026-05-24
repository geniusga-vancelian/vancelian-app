"""Routes wallet Solana Privy — authentifiées JWT Vancelian."""
from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import Person, get_db
from services.auth.privy_person_wallets_routes import _jwt_person_uuid
from services.privy.privy_wallet_service import (
    PrivySolanaWalletError,
    SolanaWalletResult,
    SolanaWalletStatus,
    get_or_create_user_solana_wallet,
    get_user_solana_wallet_status,
)
from services.test_clients.mobile_identity import mobile_bearer

solana_wallet_router = APIRouter(prefix="/api/wallets", tags=["wallets"])


class SolanaWalletResponse(BaseModel):
    chain_type: str = Field(default="solana")
    address: str
    wallet_id: str
    created: bool
    person_wallet_id: UUID


class SolanaWalletStatusResponse(BaseModel):
    status: Literal["missing", "unlinked", "linked"]
    chain_type: str = Field(default="solana")
    address: Optional[str] = None
    wallet_id: Optional[str] = None
    person_wallet_id: Optional[UUID] = None
    created: bool = False


def _to_response(result: SolanaWalletResult) -> SolanaWalletResponse:
    return SolanaWalletResponse(
        chain_type=result.chain_type,
        address=result.address,
        wallet_id=result.wallet_id,
        created=result.created,
        person_wallet_id=result.person_wallet_id,
    )


def _to_status_response(row: SolanaWalletStatus) -> SolanaWalletStatusResponse:
    return SolanaWalletStatusResponse(
        status=row.status,  # type: ignore[arg-type]
        chain_type=row.chain_type,
        address=row.address,
        wallet_id=row.wallet_id,
        person_wallet_id=row.person_wallet_id,
        created=row.created,
    )


def _resolve_person_id(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> UUID:
    if credentials is None or not (credentials.credentials or "").strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "privy.solana_wallet_requires_session",
                "message": "Authorization: Bearer (JWT Vancelian) requis.",
            },
        )
    return _jwt_person_uuid(credentials.credentials)


def _ensure_person(db: Session, person_id: UUID) -> Person:
    person = db.query(Person).filter(Person.id == person_id).first()
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "privy.solana_wallet_person_not_found",
                "message": "Person introuvable.",
            },
        )
    return person


def _handle_service_error(exc: PrivySolanaWalletError) -> HTTPException:
    return HTTPException(
        status_code=exc.http_status,
        detail={"code": exc.code, "message": str(exc)},
    )


@solana_wallet_router.get("/solana", response_model=SolanaWalletStatusResponse)
def get_solana_wallet(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    """Statut wallet Solana : absent, présent côté Privy (unlinked), ou lié Vancelian."""
    person_id = _resolve_person_id(credentials)
    _ensure_person(db, person_id)
    return _to_status_response(get_user_solana_wallet_status(db, person_id))


@solana_wallet_router.post("/solana/create", response_model=SolanaWalletResponse)
def create_solana_wallet(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    """Crée ou retourne le wallet Solana Privy (get_or_create, idempotent)."""
    person_id = _resolve_person_id(credentials)
    _ensure_person(db, person_id)
    try:
        result = get_or_create_user_solana_wallet(db, person_id)
        db.commit()
        return _to_response(result)
    except PrivySolanaWalletError as exc:
        db.rollback()
        raise _handle_service_error(exc) from exc
