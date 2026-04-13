"""FastAPI router for Custody admin endpoints."""
import logging
import uuid as uuid_lib
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from database import AdminUser, Person, get_db
from services.portfolio_engine.clients.models import Client
from services.portfolio_engine.hardening.security.context import ActorContext
from services.portfolio_engine.hardening.security.dependencies import require_admin_or_ops

from .enums import CustodyAccountType
from .identity_resolution import (
    CustodyIdentityResolution,
    CustodyIdentityResolutionError,
    enrichment_fields_for_pe_client,
    resolve_person_and_pe_client_for_custody,
)
from .models import CustodyAccount, CustodyProvider
from .schemas import (
    AccountCreate,
    AccountListResponse,
    AccountRead,
    CanonicalClientAccountCreate,
    SimpleEuroAccountCreateRequest,
    SimpleEuroAccountCreateResponse,
    CustodyIdentityResolveRequest,
    CustodyIdentityResolveResponse,
    DepositSimulationClientItem,
    DepositSimulationClientsResponse,
    BalanceListResponse,
    BalanceRead,
    InternalTransferRequest,
    InternalTransferResponse,
    ProviderCreate,
    ProviderListResponse,
    ProviderRead,
    SimulateDepositRequest,
    SimulateResponse,
    SimulateWithdrawalRequest,
    TransactionListResponse,
    TransactionRead,
    WebhookEventListResponse,
    WebhookEventRead,
)
from services.security.sensitive_action_events import (
    record_sensitive_action_completed,
    record_sensitive_action_failed,
)
from services.auth.device_attestation_dependencies import require_device_attestation
from services.auth.device_risk_pr_f_dependencies import require_low_risk_action
from services.security.session_intelligence_dependencies import require_continuous_auth_for_action

from .cms_operator_audit import custody_audit_extra
from .repository import CustodyAccountRepository, CustodyProviderRepository
from .service import (
    AccountNotFoundError,
    CurrencyMismatchError,
    CustodyService,
    DuplicateAccountError,
    DuplicateReferenceError,
    InsufficientFundsError,
    InvalidTransferError,
    SettlementAccountNotFoundError,
)

admin_router = APIRouter(prefix="/api/admin/custody", tags=["custody"])
_svc = CustodyService()
_guard = require_admin_or_ops()
logger = logging.getLogger(__name__)


def _dev(request: Request) -> str:
    return (request.headers.get("x-device-id") or "")[:128]


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------

@admin_router.get("/providers", response_model=ProviderListResponse)
def list_providers(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    items, total = _svc.list_providers(db, skip=skip, limit=limit)
    return ProviderListResponse(
        items=[ProviderRead.model_validate(p) for p in items],
        total=total,
    )


@admin_router.post("/providers", response_model=ProviderRead, status_code=status.HTTP_201_CREATED)
def create_provider(
    payload: ProviderCreate,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    provider = _svc.create_provider(db, payload, actor)
    db.commit()
    db.refresh(provider)
    return ProviderRead.model_validate(provider)


# ---------------------------------------------------------------------------
# Accounts
# ---------------------------------------------------------------------------

def _enrich_account(db: Session, account) -> AccountRead:
    """Enrich an account read with balance, provider name, client email + identité Person."""
    from .repository import CustodyBalanceRepository

    read = AccountRead.model_validate(account)
    bal = CustodyBalanceRepository.get_by_account_id(db, account.id)
    if bal:
        read.available_balance = bal.available_balance
        read.pending_balance = bal.pending_balance
    provider = db.query(CustodyProvider).filter(CustodyProvider.id == account.provider_id).first()
    if provider:
        read.provider_name = provider.name
    if account.client_id:
        client = db.query(Client).filter(Client.id == account.client_id).first()
        if client:
            read.client_email = client.email
            extra = enrichment_fields_for_pe_client(db, client)
            read.person_id = extra["person_id"]
            read.person_email_collected = extra["person_email_collected"]
            read.phone_e164 = extra["phone_e164"]
    return read


@admin_router.get("/clients-for-deposit-simulation", response_model=DepositSimulationClientsResponse)
def list_clients_for_deposit_simulation(
    currency: str = Query("EUR", min_length=3, max_length=10),
    provider_id: Optional[UUID] = Query(
        None,
        description="Filtre BAS : clients ayant un compte dépôt chez ce fournisseur.",
    ),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    """Customers avec compte dépôt custody dans la devise (simulateur webhook BAS)."""
    rows = _svc.list_clients_for_deposit_simulation(
        db, currency=currency, provider_id=provider_id
    )
    return DepositSimulationClientsResponse(
        items=[DepositSimulationClientItem(**r) for r in rows],
    )


@admin_router.get("/accounts", response_model=AccountListResponse)
def list_accounts(
    account_type: Optional[str] = Query(None),
    client_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    items, total = _svc.list_accounts(
        db, account_type=account_type, client_id=client_id, skip=skip, limit=limit
    )
    return AccountListResponse(
        items=[_enrich_account(db, a) for a in items],
        total=total,
    )


@admin_router.post(
    "/accounts/client",
    response_model=AccountRead,
    status_code=status.HTTP_201_CREATED,
)
def create_client_account(
    request: Request,
    payload: AccountCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("beneficiary_add")),
    _pr_e: None = Depends(require_device_attestation()),
    _pr_f: None = Depends(require_low_risk_action()),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    try:
        account = _svc.create_client_account(db, payload, actor)
        db.commit()
        db.refresh(account)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="beneficiary_add",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={"endpoint": "POST /api/admin/custody/accounts/client", "client_id": str(payload.client_id) if payload.client_id else None},
        )
        db.commit()
        return _enrich_account(db, account)
    except DuplicateAccountError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="beneficiary_add",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"duplicate_account:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="beneficiary_add",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"value_error:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@admin_router.post(
    "/identity/resolve",
    response_model=CustodyIdentityResolveResponse,
)
def resolve_custody_identity_endpoint(
    payload: CustodyIdentityResolveRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    """Prévisualise Person + pe_client pour un critère unique (sans créer de compte)."""
    _ = actor
    try:
        r = resolve_person_and_pe_client_for_custody(
            db,
            person_id=payload.person_id,
            phone_e164=(payload.phone_e164 or "").strip() or None,
            pe_client_id=payload.pe_client_id,
        )
    except CustodyIdentityResolutionError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return CustodyIdentityResolveResponse(
        person_id=r.person_id,
        pe_client_id=r.pe_client_id,
        person_email_collected=r.person_email_collected,
        pe_client_email=r.pe_client_email,
        phone_e164=r.phone_e164,
        resolution_source=r.source,
    )


@admin_router.post(
    "/accounts/client/canonical",
    response_model=AccountRead,
    status_code=status.HTTP_201_CREATED,
)
def create_client_account_canonical(
    request: Request,
    payload: CanonicalClientAccountCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("beneficiary_add")),
    _pr_e: None = Depends(require_device_attestation()),
    _pr_f: None = Depends(require_low_risk_action()),
    actor: ActorContext = Depends(_guard),
):
    """Création recommandée : résolution stricte Person → pe_client puis custody (même effet métier que POST /accounts/client)."""
    _ = current_user
    tel = (payload.phone_e164 or "").strip() or None
    try:
        resolution = resolve_person_and_pe_client_for_custody(
            db,
            person_id=payload.person_id,
            phone_e164=tel,
            pe_client_id=payload.pe_client_id,
        )
    except CustodyIdentityResolutionError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="beneficiary_add",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"custody_identity:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    inner = AccountCreate(
        provider_id=payload.provider_id,
        account_type=CustodyAccountType.CLIENT_DEPOSIT,
        currency=payload.currency,
        iban=payload.iban,
        bic=payload.bic,
        account_holder_name=payload.account_holder_name,
        client_id=resolution.pe_client_id,
    )
    logger.info(
        "custody_canonical_client_account",
        extra={
            "person_id": str(resolution.person_id),
            "pe_client_id": str(resolution.pe_client_id),
            "resolution_source": resolution.source,
            "phone_e164": resolution.phone_e164,
            "person_email_collected": resolution.person_email_collected,
            "pe_client_email": resolution.pe_client_email,
            "endpoint": "POST /api/admin/custody/accounts/client/canonical",
            "actor_id": actor.actor_id,
        },
    )
    try:
        account = _svc.create_client_account(db, inner, actor)
        db.commit()
        db.refresh(account)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="beneficiary_add",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={
                "endpoint": "POST /api/admin/custody/accounts/client/canonical",
                "client_id": str(resolution.pe_client_id),
                "person_id": str(resolution.person_id),
                "resolution_source": resolution.source,
            },
        )
        db.commit()
        return _enrich_account(db, account)
    except DuplicateAccountError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="beneficiary_add",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"duplicate_account:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="beneficiary_add",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"value_error:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _default_custody_provider_id(db: Session) -> UUID:
    """Provider par défaut : **Modulr** si présent, sinon le premier provider listé."""
    prov_repo = CustodyProviderRepository()
    modulr = prov_repo.get_by_name(db, "Modulr")
    if modulr is not None:
        return modulr.id
    items, _total = prov_repo.list(db, skip=0, limit=20)
    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Aucun custody provider configuré. Créez d'abord un provider "
                "(ex. Modulr) dans l'onglet Providers."
            ),
        )
    return items[0].id


def _account_holder_from_person(
    db: Session, person: Person, resolution: CustodyIdentityResolution
) -> str:
    """Titulaire : prénom/nom ou téléphone collecté — jamais d'e-mail (pas de dépendance e-mail pour la création)."""
    _ = resolution
    from services.customers_admin.service import _extract_identity_fields

    fields = _extract_identity_fields(person, db)
    fn = (fields.get("first_name") or "").strip()
    ln = (fields.get("last_name") or "").strip()
    full = f"{fn} {ln}".strip()
    if full:
        return full[:255]
    tel = (fields.get("mobile") or "").strip()
    if tel:
        return tel[:255]
    return "Client"


@admin_router.post(
    "/accounts/client/simple-create",
    response_model=SimpleEuroAccountCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_client_euro_account_simple(
    request: Request,
    payload: SimpleEuroAccountCreateRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("beneficiary_add")),
    _pr_e: None = Depends(require_device_attestation()),
    actor: ActorContext = Depends(_guard),
):
    """Création **EUR** pour l'ops : uniquement ``person_id`` → pe_client ; titulaire nom/téléphone collectés (sans e-mail)."""
    _audit_cms = custody_audit_extra(
        request=request,
        action="create_euro_account_simple",
        person_id=str(payload.person_id),
        actor_jwt_user_id=current_user.id,
    )
    person = db.query(Person).filter(Person.id == payload.person_id).first()
    if person is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")

    try:
        resolution = resolve_person_and_pe_client_for_custody(
            db,
            person_id=payload.person_id,
        )
    except CustodyIdentityResolutionError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="beneficiary_add",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"custody_identity:{exc}",
            extra=dict(_audit_cms),
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    existing = CustodyAccountRepository.find_client_account(
        db, resolution.pe_client_id, "EUR"
    )
    if existing is not None:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="beneficiary_add",
            request=request,
            db=db,
            device_id=_dev(request),
            reason="duplicate_eur_custody_account",
            extra=dict(_audit_cms),
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce client a déjà un compte EUR custody actif.",
        )

    provider_id = _default_custody_provider_id(db)
    iban = f"DE{uuid_lib.uuid4().hex[:16].upper()}"
    bic = "MODULRXXX"
    holder = _account_holder_from_person(db, person, resolution)

    inner = AccountCreate(
        provider_id=provider_id,
        account_type=CustodyAccountType.CLIENT_DEPOSIT,
        currency="EUR",
        iban=iban,
        bic=bic,
        account_holder_name=holder,
        client_id=resolution.pe_client_id,
    )
    _log_extra = {
        "person_id": str(resolution.person_id),
        "pe_client_id": str(resolution.pe_client_id),
        "provider_id": str(provider_id),
        "endpoint": "POST /api/admin/custody/accounts/client/simple-create",
        "actor_id": actor.actor_id,
        **{k: v for k, v in _audit_cms.items() if v is not None},
    }
    logger.info("custody_simple_euro_account", extra=_log_extra)
    try:
        account = _svc.create_client_account(db, inner, actor)
        db.commit()
        db.refresh(account)
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="beneficiary_add",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={
                **_audit_cms,
                "endpoint": "POST /api/admin/custody/accounts/client/simple-create",
                "client_id": str(resolution.pe_client_id),
                "person_id": str(resolution.person_id),
            },
        )
        db.commit()
        enriched = _enrich_account(db, account)
        return SimpleEuroAccountCreateResponse(
            message="Euro deposit account created successfully.",
            account=enriched,
        )
    except DuplicateAccountError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="beneficiary_add",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"duplicate_account:{exc}",
            extra=dict(_audit_cms),
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="beneficiary_add",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"value_error:{exc}",
            extra=dict(_audit_cms),
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@admin_router.post(
    "/accounts/settlement",
    response_model=AccountRead,
    status_code=status.HTTP_201_CREATED,
)
def create_settlement_account(
    payload: AccountCreate,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        account = _svc.create_settlement_account(db, payload, actor)
        db.commit()
        db.refresh(account)
        return _enrich_account(db, account)
    except DuplicateAccountError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# ---------------------------------------------------------------------------
# Balances
# ---------------------------------------------------------------------------

@admin_router.get("/balances", response_model=BalanceListResponse)
def list_balances(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    items, total = _svc.list_balances(db, skip=skip, limit=limit)
    return BalanceListResponse(
        items=[BalanceRead.model_validate(b) for b in items],
        total=total,
    )


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------

def _enrich_transaction(db: Session, tx) -> TransactionRead:
    """Enrich a transaction read with client email and provider name."""
    read = TransactionRead.model_validate(tx)
    account = db.query(CustodyAccount).filter(CustodyAccount.id == tx.account_id).first()
    if account and account.client_id:
        client = db.query(Client).filter(Client.id == account.client_id).first()
        if client:
            read.client_email = client.email
    if tx.provider_id:
        provider = db.query(CustodyProvider).filter(CustodyProvider.id == tx.provider_id).first()
        if provider:
            read.provider_name = provider.name
    return read


@admin_router.get("/transactions", response_model=TransactionListResponse)
def list_transactions(
    account_id: Optional[UUID] = Query(None),
    client_id: Optional[UUID] = Query(None),
    transaction_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None, alias="status"),
    provider_id: Optional[UUID] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    items, total = _svc.list_transactions(
        db,
        account_id=account_id,
        client_id=client_id,
        transaction_type=transaction_type,
        status=status,
        provider_id=provider_id,
        skip=skip,
        limit=limit,
    )
    return TransactionListResponse(
        items=[_enrich_transaction(db, t) for t in items],
        total=total,
    )


# ---------------------------------------------------------------------------
# Webhook Events (admin read-only list + replay)
# ---------------------------------------------------------------------------

@admin_router.get("/webhook-events", response_model=WebhookEventListResponse)
def list_webhook_events(
    provider_id: Optional[UUID] = Query(None),
    processing_status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    items, total = _svc.list_webhook_events(
        db,
        provider_id=provider_id,
        processing_status=processing_status,
        skip=skip,
        limit=limit,
    )
    return WebhookEventListResponse(
        items=[WebhookEventRead.model_validate(e) for e in items],
        total=total,
    )


@admin_router.post("/webhook-events/{event_id}/replay")
def replay_webhook_event(
    request: Request,
    event_id: UUID,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("withdrawal")),
    _pr_e: None = Depends(require_device_attestation()),
    _pr_f: None = Depends(require_low_risk_action()),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    from .webhook_service import WebhookProcessor

    repo = _svc._webhook_repo
    event = repo.get_by_id(db, event_id)
    if event is None:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="withdrawal",
            request=request,
            db=db,
            device_id=_dev(request),
            reason="webhook_event_not_found",
            extra={"event_id": str(event_id)},
        )
        db.commit()
        raise HTTPException(status_code=404, detail="Webhook event not found")

    processor = WebhookProcessor()
    try:
        result = processor.process_event(db, event, is_replay=True)
        db.commit()
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="withdrawal",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={"endpoint": "POST /webhook-events/replay", "event_id": str(event_id), "replay": True},
        )
        db.commit()
        return {"event_id": str(event_id), "processing_status": result}
    except Exception as exc:  # noqa: BLE001 — audit path
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="withdrawal",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"webhook_replay:{exc}",
            extra={"event_id": str(event_id)},
        )
        db.commit()
        raise


# ---------------------------------------------------------------------------
# Simulations
# ---------------------------------------------------------------------------

@admin_router.post("/simulate-deposit", response_model=SimulateResponse)
def simulate_deposit(
    payload: SimulateDepositRequest,
    db: Session = Depends(get_db),
    actor: ActorContext = Depends(_guard),
):
    try:
        tx, balance = _svc.simulate_deposit(db, payload, actor)
        db.commit()
        return SimulateResponse(
            transaction_id=tx.id,
            account_id=tx.account_id,
            direction=tx.direction,
            amount=tx.amount,
            new_available_balance=balance.available_balance,
            message=f"Deposit of {payload.amount} {payload.currency} simulated successfully",
        )
    except AccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SettlementAccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except CurrencyMismatchError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@admin_router.post("/simulate-withdrawal", response_model=SimulateResponse)
def simulate_withdrawal(
    request: Request,
    payload: SimulateWithdrawalRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("withdrawal")),
    _pr_e: None = Depends(require_device_attestation()),
    _pr_f: None = Depends(require_low_risk_action()),
    actor: ActorContext = Depends(_guard),
):
    _ = current_user
    try:
        tx, balance = _svc.simulate_withdrawal(db, payload, actor)
        db.commit()
        record_sensitive_action_completed(
            user_id=current_user.id,
            action_key="withdrawal",
            request=request,
            db=db,
            device_id=_dev(request),
            extra={
                "endpoint": "POST /api/admin/custody/simulate-withdrawal",
                "currency": str(payload.currency),
                "amount": str(payload.amount),
            },
        )
        db.commit()
        return SimulateResponse(
            transaction_id=tx.id,
            account_id=tx.account_id,
            direction=tx.direction,
            amount=tx.amount,
            new_available_balance=balance.available_balance,
            message=f"Withdrawal of {payload.amount} {payload.currency} simulated successfully",
        )
    except AccountNotFoundError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="withdrawal",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"account_not_found:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SettlementAccountNotFoundError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="withdrawal",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"settlement_not_found:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InsufficientFundsError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="withdrawal",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"insufficient_funds:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except CurrencyMismatchError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="withdrawal",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"currency_mismatch:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


# ---------------------------------------------------------------------------
# Financial test state reset (admin/ops only)
# ---------------------------------------------------------------------------

@admin_router.post("/reset-financial-test-state")
def reset_financial_test_state(
    dry_run: bool = Query(False, description="If true, only report counts without modifying data"),
    actor: ActorContext = Depends(_guard),
):
    """
    Remet à zéro l'état financier de test : transactions, webhooks, ledger entries,
    orders, positions, settlement deltas ; remet les balances custody à 0.
    Conserve : comptes, clients, providers, ledger_accounts, produits/templates/bundles.
    Protégé admin/ops.
    """
    from services.financial_reset import run_reset
    report = run_reset(dry_run=dry_run)
    return report


# ---------------------------------------------------------------------------
# Internal Transfer Engine
# ---------------------------------------------------------------------------

transfer_router = APIRouter(tags=["internal-transfer"])
_transfer_guard = require_admin_or_ops()


@transfer_router.post("/api/internal-transfer", response_model=InternalTransferResponse)
def internal_transfer(
    request: Request,
    payload: InternalTransferRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(require_continuous_auth_for_action("wallet_transfer")),
    _pr_e: None = Depends(require_device_attestation()),
    _pr_f: None = Depends(require_low_risk_action()),
    actor: ActorContext = Depends(_transfer_guard),
):
    _ = current_user
    try:
        result = _svc.execute_internal_transfer(db, payload, actor)
        db.commit()
        st = result.get("status")
        if st == "completed":
            record_sensitive_action_completed(
                user_id=current_user.id,
                action_key="wallet_transfer",
                request=request,
                db=db,
                device_id=_dev(request),
                extra={
                    "endpoint": "POST /api/internal-transfer",
                    "outcome": "completed",
                    "external_reference": payload.external_reference,
                    "currency": str(payload.currency),
                    "amount": str(payload.amount),
                },
            )
        elif st == "ignored":
            record_sensitive_action_completed(
                user_id=current_user.id,
                action_key="wallet_transfer",
                request=request,
                db=db,
                device_id=_dev(request),
                extra={
                    "endpoint": "POST /api/internal-transfer",
                    "outcome": "ignored_duplicate",
                    "external_reference": payload.external_reference,
                },
            )
        db.commit()
        return InternalTransferResponse(**result)
    except InsufficientFundsError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"insufficient_funds:{exc}",
            extra={"external_reference": payload.external_reference},
        )
        db.commit()
        return InternalTransferResponse(status="failed", error="insufficient_funds")
    except AccountNotFoundError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"account_not_found:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except SettlementAccountNotFoundError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"settlement_not_found:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except InvalidTransferError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"invalid_transfer:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except CurrencyMismatchError as exc:
        record_sensitive_action_failed(
            user_id=current_user.id,
            action_key="wallet_transfer",
            request=request,
            db=db,
            device_id=_dev(request),
            reason=f"currency_mismatch:{exc}",
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
