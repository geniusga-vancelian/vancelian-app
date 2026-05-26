"""Admin routes for Privy user-wallet ledger."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from services.portfolio_engine.hardening.security.dependencies import require_admin_or_ops

from services.privy_wallet.privy_api_client import PrivyApiError
from .admin_service import (
    PrivySimulateDepositError,
    PrivyWalletAdminService,
    PrivyWalletNotFoundError,
)
from .readiness import get_customer_wallet_readiness, get_privy_infra_readiness
from .schemas import (
    PrivyBackfillDepositRequest,
    PrivyBackfillDepositResponse,
    PrivyCustomerReadinessResponse,
    PrivyInfraReadinessResponse,
    PrivyReconcileWalletsRequest,
    PrivyReconcileWalletsResponse,
    PrivyReconciliationRunRequest,
    PrivyReconciliationRunResponse,
    PrivyReplayWebhookResponse,
    PrivySimulateDepositRequest,
    PrivySimulateDepositResponse,
    PrivyVoidDepositRequest,
    PrivyVoidDepositResponse,
)

privy_wallet_admin_router = APIRouter(
    prefix="/api/admin/privy-wallet",
    tags=["admin-privy-wallet"],
)
_guard = require_admin_or_ops()
_svc = PrivyWalletAdminService()


@privy_wallet_admin_router.post(
    "/simulate-deposit",
    response_model=PrivySimulateDepositResponse,
)
def simulate_privy_deposit(
    payload: PrivySimulateDepositRequest,
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Simule un webhook ``wallet.funds_deposited`` pour créditer le ledger Privy d'un client."""
    try:
        result = _svc.simulate_deposit(db, payload)
        db.commit()
        return result
    except PrivyWalletNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PrivySimulateDepositError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@privy_wallet_admin_router.get(
    "/infra-readiness",
    response_model=PrivyInfraReadinessResponse,
)
def privy_infra_readiness(
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Checklist infra prod Privy (secrets, migration 158, webhook) — sans exposer de secrets."""
    return get_privy_infra_readiness(db)


@privy_wallet_admin_router.get(
    "/customer-readiness/{person_id}",
    response_model=PrivyCustomerReadinessResponse,
)
def privy_customer_readiness(
    person_id: UUID,
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Checklist wallet client — prêt pour un dépôt live crédité en ledger."""
    result = get_customer_wallet_readiness(db, person_id)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return result


@privy_wallet_admin_router.post(
    "/replay-webhook/{event_id}",
    response_model=PrivyReplayWebhookResponse,
)
def replay_privy_webhook(
    event_id: UUID,
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Rejoue un webhook Privy échoué ou en attente (ex. retry dashboard Privy)."""
    try:
        result = _svc.replay_webhook_event(db, event_id)
        db.commit()
        return result
    except PrivyWalletNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@privy_wallet_admin_router.post(
    "/reconcile-wallets",
    response_model=PrivyReconcileWalletsResponse,
)
def reconcile_privy_wallets(
    payload: PrivyReconcileWalletsRequest,
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Synchronise ``person_crypto_wallets`` depuis l’API Privy (adresses uniquement)."""
    try:
        result = _svc.reconcile_wallets(db, payload)
        db.commit()
        return result
    except PrivyWalletNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PrivyApiError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY
            if exc.http_status and exc.http_status >= 500
            else status.HTTP_400_BAD_REQUEST,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@privy_wallet_admin_router.post(
    "/backfill-deposit",
    response_model=PrivyBackfillDepositResponse,
)
def backfill_privy_deposit(
    payload: PrivyBackfillDepositRequest,
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Crédite le ledger depuis une transaction on-chain (tx hash + chain_id)."""
    try:
        result = _svc.backfill_deposit(db, payload)
        db.commit()
        return result
    except PrivyWalletNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PrivySimulateDepositError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@privy_wallet_admin_router.post(
    "/void-deposit",
    response_model=PrivyVoidDepositResponse,
)
def void_privy_deposit(
    payload: PrivyVoidDepositRequest,
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Annule un dépôt confirmé (doublon / phantom) et débite le ledger."""
    try:
        result = _svc.void_deposit(db, payload)
        db.commit()
        return result
    except PrivyWalletNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PrivySimulateDepositError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@privy_wallet_admin_router.post(
    "/reconciliation/run",
    response_model=PrivyReconciliationRunResponse,
)
def run_privy_wallet_reconciliation(
    payload: PrivyReconciliationRunRequest,
    db: Session = Depends(get_db),
    _actor=Depends(_guard),
):
    """Compare soldes on-chain vs ledger, rejoue webhooks failed et backfill auto si possible."""
    try:
        result = _svc.run_reconciliation(
            db,
            person_id=payload.person_id,
            auto_heal=payload.auto_heal,
        )
        db.commit()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
