"""POST /auth/privy/exchange — échange token Privy vérifié contre session Vancelian ``au:<id>``."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import AdminUser, Person, PersonCryptoWallet, get_db
from services.auth.account_policy import is_web_only_mobile_app_user
from services.auth.person_identity_bridge import (
    PROVIDER_PRIVY,
    DuplicateExternalIdentityError,
    get_or_create_login_account_for_person_if_needed,
    get_pe_client_for_person,
    get_person_from_external_identity,
    link_external_identity_to_person,
    upsert_person_crypto_wallet,
)
from services.auth.refresh_session import MOBILE_APP_NOT_ALLOWED_DETAIL
from services.auth.privy_token_verifier import (
    MODE_JWT,
    MODE_STUB,
    PrivyVerifyError,
    _exchange_mode,
    enrich_verified_privy_access,
    verify_privy_access_token,
)
from services.auth.refresh_session import issue_fresh_auth_session
from services.client_identity.service import ClientIdentityService
from services.privy_wallet.wallet_sync import normalize_privy_wallet_payload

router = APIRouter(prefix="/auth", tags=["auth-privy-exchange"])

_EVM_ADDRESS = re.compile(r"^0x[0-9a-fA-F]{40}$")


def _privy_verify_http_status(code: str) -> int:
    return {
        "privy.stub_forbidden_in_production": status.HTTP_403_FORBIDDEN,
        "privy.token_missing": status.HTTP_400_BAD_REQUEST,
        "privy.token_invalid": status.HTTP_401_UNAUTHORIZED,
        "privy.verification_not_configured": status.HTTP_503_SERVICE_UNAVAILABLE,
    }.get(code, status.HTTP_400_BAD_REQUEST)


class PrivyExchangeWalletIn(BaseModel):
    """Adresse : validation EVM stricte dans `_validate_evm_address` (évite 422 Pydantic sur taille)."""

    address: str = Field(..., min_length=1)
    chain_type: str = Field(..., min_length=1, max_length=32)
    chain_id: Optional[int] = None
    wallet_type: str = Field(..., min_length=1, max_length=32)
    privy_wallet_id: Optional[str] = Field(None, max_length=128)


class PrivyExchangeRequest(BaseModel):
    """Corps JSON : ``privy_access_token`` peut être absent (erreur ``privy.token_missing``)."""

    privy_access_token: Optional[str] = None
    privy_identity_token: Optional[str] = Field(
        None,
        description="Identity token Privy (JWT) — contient souvent l’e-mail via linked_accounts.",
    )
    email: Optional[str] = Field(
        None,
        description="Adresse OTP saisie côté client — repli JWT si access/identity token sans e-mail.",
    )
    wallets: Optional[List[PrivyExchangeWalletIn]] = None


class PrivyExchangeWalletOut(BaseModel):
    id: str
    address: str
    chain_type: str
    chain_id: Optional[int] = None
    wallet_type: str
    provider: str
    is_primary: bool


class PrivyExchangeResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    device_id: Optional[str] = None
    person_id: str
    pe_client_id: str
    wallets: List[PrivyExchangeWalletOut] = Field(default_factory=list)


def _resolved_login_email(
    verified_email: Optional[str],
    body_email: Optional[str],
) -> Optional[str]:
    """Repli e-mail OTP (web) quand le JWT Privy n’embarque pas l’adresse (prod jwt / dev stub)."""
    email = (verified_email or "").strip().lower()
    if email:
        return email
    fallback = (body_email or "").strip().lower()
    mode = _exchange_mode()
    if fallback and "@" in fallback and mode in (MODE_JWT, MODE_STUB):
        return fallback
    return None


def _validate_evm_address(addr: str) -> str:
    a = (addr or "").strip()
    if not _EVM_ADDRESS.match(a):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "privy.wallet_address_invalid",
                "message": "Adresse EVM invalide (attendu 0x + 40 hex).",
            },
        )
    return a


def _sync_privy_identity_metadata(
    db: Session,
    *,
    person_id: UUID,
    privy_user_id: str,
    email: Optional[str],
    phone: Optional[str],
) -> None:
    """Met à jour l’enregistrement ``person_external_identities`` (email/téléphone)."""
    link_external_identity_to_person(
        db,
        person_id=person_id,
        provider=PROVIDER_PRIVY,
        external_subject=privy_user_id,
        external_email=email,
        external_phone=phone,
        metadata_json=None,
    )


def _wallets_in_from_linked_raw(raw: Optional[List[Dict[str, Any]]]) -> List[PrivyExchangeWalletIn]:
    if not raw:
        return []
    out: List[PrivyExchangeWalletIn] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        if str(item.get("type") or "").strip().lower() not in ("", "wallet") and not item.get("address"):
            continue
        norm = normalize_privy_wallet_payload(item)
        if norm is None or (norm.chain_type or "").strip().lower() != "evm":
            # Ne pas bloquer login/signup si Privy expose aussi Solana / autres chaînes.
            continue
        out.append(
            PrivyExchangeWalletIn(
                address=norm.address,
                chain_type=norm.chain_type,
                chain_id=norm.chain_id,
                wallet_type=norm.wallet_type,
                privy_wallet_id=norm.privy_wallet_id,
            )
        )
    return out


def _resolve_exchange_wallets(
    body_wallets: Optional[List[PrivyExchangeWalletIn]],
    linked_wallets: Optional[List[Dict[str, Any]]],
) -> Optional[List[PrivyExchangeWalletIn]]:
    if body_wallets:
        return body_wallets
    from_token = _wallets_in_from_linked_raw(linked_wallets)
    return from_token or None


def _persist_request_wallets(
    db: Session,
    *,
    person_id: UUID,
    pe_client_id: UUID,
    wallets: Optional[List[PrivyExchangeWalletIn]],
) -> None:
    if not wallets:
        return
    for w in wallets:
        if (w.chain_type or "").strip().lower() != "evm":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "privy.wallet_chain_unsupported",
                    "message": "Seul chain_type=evm est supporté pour l’instant.",
                },
            )
        addr = _validate_evm_address(w.address)
        metadata_json = None
        privy_wallet_id = (w.privy_wallet_id or "").strip()
        if privy_wallet_id:
            metadata_json = {"privy_wallet_id": privy_wallet_id}
        upsert_person_crypto_wallet(
            db,
            person_id=person_id,
            pe_client_id=pe_client_id,
            provider=PROVIDER_PRIVY,
            wallet_type=(w.wallet_type or "embedded").strip(),
            chain_type="evm",
            address=addr.lower(),
            chain_id=w.chain_id,
            is_primary=True,
            metadata_json=metadata_json,
        )


def _serialize_active_wallets(db: Session, *, person_id: UUID) -> List[PrivyExchangeWalletOut]:
    rows = (
        db.query(PersonCryptoWallet)
        .filter(
            PersonCryptoWallet.person_id == person_id,
            PersonCryptoWallet.revoked_at.is_(None),
        )
        .all()
    )
    out: List[PrivyExchangeWalletOut] = []
    for r in rows:
        out.append(
            PrivyExchangeWalletOut(
                id=str(r.id),
                address=r.address,
                chain_type=r.chain_type,
                chain_id=r.chain_id,
                wallet_type=r.wallet_type,
                provider=r.provider,
                is_primary=bool(r.is_primary),
            )
        )
    return out


def serialize_active_crypto_wallets_for_person(
    db: Session, *, person_id: UUID,
) -> List[PrivyExchangeWalletOut]:
    """Utilisé par ``GET /auth/privy/person-wallets`` (JWT Vancelian)."""
    return _serialize_active_wallets(db, person_id=person_id)


def _resolve_person_for_privy_exchange(
    db: Session,
    *,
    privy_user_id: str,
    verified_email: Optional[str],
    verified_phone: Optional[str],
) -> Optional[Person]:
    """Identité déjà liée, sinon rattachement login e-mail (``AdminUser.email`` → ``person_id``)."""
    person = get_person_from_external_identity(
        db, provider=PROVIDER_PRIVY, external_subject=privy_user_id
    )
    if person is not None:
        return person

    email = (verified_email or "").strip().lower()
    if not email:
        return None

    user = db.query(AdminUser).filter(AdminUser.email == email).first()
    if user is None or user.person_id is None:
        return None
    if is_web_only_mobile_app_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=MOBILE_APP_NOT_ALLOWED_DETAIL,
        )

    person = db.query(Person).filter(Person.id == user.person_id).first()
    if person is None:
        return None

    try:
        link_external_identity_to_person(
            db,
            person_id=person.id,
            provider=PROVIDER_PRIVY,
            external_subject=privy_user_id,
            external_email=verified_email,
            external_phone=verified_phone,
        )
    except DuplicateExternalIdentityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "privy.exchange.identity_conflict",
                "message": str(exc),
            },
        ) from exc
    return person


@router.post(
    "/privy/exchange",
    response_model=PrivyExchangeResponse,
    summary="Échange Privy → session JWT Vancelian",
    description=(
        "Vérifie le token Privy (stub dev ou JWT ES256), résout Person → PeClient → AdminUser, "
        "enregistre les wallets EVM optionnels, émet access/refresh."
    ),
)
def post_privy_exchange(
    request: Request,
    body: PrivyExchangeRequest,
    db: Session = Depends(get_db),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
) -> PrivyExchangeResponse:
    try:
        verified = verify_privy_access_token(body.privy_access_token or "")
        verified = enrich_verified_privy_access(
            verified,
            identity_token=body.privy_identity_token,
        )
    except PrivyVerifyError as exc:
        raise HTTPException(
            status_code=_privy_verify_http_status(exc.code),
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    privy_uid = verified.privy_user_id
    resolved_email = _resolved_login_email(verified.email, body.email)
    person = _resolve_person_for_privy_exchange(
        db,
        privy_user_id=privy_uid,
        verified_email=resolved_email,
        verified_phone=verified.phone,
    )
    if person is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "privy.exchange.person_not_found",
                "message": "Aucun compte Vancelian trouvé pour cet e-mail. Vérifiez l’adresse ou contactez le support.",
            },
        )

    _sync_privy_identity_metadata(
        db,
        person_id=person.id,
        privy_user_id=privy_uid,
        email=resolved_email,
        phone=verified.phone,
    )

    pe_client = get_pe_client_for_person(db, person_id=person.id)
    if pe_client is None:
        ClientIdentityService.ensure_pe_client_for_login_user(
            db,
            person_id=person.id,
            client_email=resolved_email,
            actor_type="privy.exchange",
            actor_id=privy_uid[:128],
        )
        db.flush()
        pe_client = get_pe_client_for_person(db, person_id=person.id)
    assert pe_client is not None

    try:
        _persist_request_wallets(
            db,
            person_id=person.id,
            pe_client_id=pe_client.id,
            wallets=_resolve_exchange_wallets(body.wallets, verified.linked_wallets),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "privy.wallet_persist_error", "message": str(exc)},
        ) from exc

    user = get_or_create_login_account_for_person_if_needed(db, person_id=person.id)

    tokens = issue_fresh_auth_session(
        db=db,
        request=request,
        user=user,
        device_header=x_device_id,
        success_event_type="auth.privy.exchange",
        success_metadata={
            "person_id": str(person.id),
            "privy_subject": privy_uid[:256],
        },
        auth_strength="oauth",
    )

    wallet_out = _serialize_active_wallets(db, person_id=person.id)

    return PrivyExchangeResponse(
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        token_type=tokens.get("token_type") or "bearer",
        device_id=tokens.get("device_id"),
        person_id=str(person.id),
        pe_client_id=str(pe_client.id),
        wallets=wallet_out,
    )
