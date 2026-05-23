"""Authenticated read routes for Privy user-wallet ledger (/api/app/privy-wallet/*)."""
from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import Person, get_db
from services.auth.privy_person_wallets_routes import _jwt_person_uuid
from services.test_clients.mobile_identity import mobile_bearer

from .schemas import (
    PrivyWalletBalancesResponse,
    PrivyWalletDepositPayload,
    PrivyWalletDepositsResponse,
)
from .service import PrivyWalletLedgerService

privy_wallet_app_router = APIRouter(prefix="/api/app/privy-wallet", tags=["app-privy-wallet"])
_svc = PrivyWalletLedgerService()


def _resolve_person_id(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> UUID:
    if credentials is None or not (credentials.credentials or "").strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "privy.wallet_requires_session",
                "message": "Authorization: Bearer (JWT Vancelian) requis.",
            },
        )
    return _jwt_person_uuid(credentials.credentials)


@privy_wallet_app_router.get("/balances", response_model=PrivyWalletBalancesResponse)
def get_privy_wallet_balances(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    person_id = _resolve_person_id(credentials)
    person = db.query(Person).filter(Person.id == person_id).first()
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "privy.wallet_person_not_found",
                "message": "Person introuvable.",
            },
        )
    return _svc.get_balances(db, person_id=person_id)


@privy_wallet_app_router.get("/deposits", response_model=PrivyWalletDepositsResponse)
def list_privy_wallet_deposits(
    asset: Optional[str] = Query(None, description="Filtrer par symbole (ex. ETH, USDC)"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    person_id = _resolve_person_id(credentials)
    person = db.query(Person).filter(Person.id == person_id).first()
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "privy.wallet_person_not_found",
                "message": "Person introuvable.",
            },
        )
    return _svc.list_deposits(db, person_id=person_id, asset=asset, limit=limit)


@privy_wallet_app_router.get(
    "/deposits/{deposit_id}",
    response_model=PrivyWalletDepositPayload,
)
def get_privy_wallet_deposit(
    deposit_id: UUID,
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    person_id = _resolve_person_id(credentials)
    deposit = _svc.get_deposit(db, person_id=person_id, deposit_id=deposit_id)
    if deposit is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "privy.wallet_deposit_not_found",
                "message": "Dépôt introuvable.",
            },
        )
    return deposit
