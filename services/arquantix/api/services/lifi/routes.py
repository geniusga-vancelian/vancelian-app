"""Routes swap LI.FI — orchestrateur backend (jamais d'appel LI.FI côté front)."""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database import get_db
from services.auth.privy_person_wallets_routes import _jwt_person_uuid
from services.lifi.config import (
    MAX_SLIPPAGE_BPS,
    build_lifi_client,
    default_slippage_bps,
    lifi_api_configured,
    swap_fee_bps,
    swaps_enabled,
    swaps_mock_mode,
)
from services.lifi.lifi_client import LifiClientError
from services.lifi.lifi_confirm_service import LifiConfirmService
from services.lifi.lifi_execute_service import LifiExecuteService
from services.lifi.lifi_quote_service import LifiQuoteService
from services.lifi.lifi_validation_service import SwapPriceChangedError, SwapValidationError
from services.lifi.schemas import (
    SwapAbandonRequest,
    SwapApprovalSubmitRequest,
    SwapConfirmExecuteRequest,
    SwapConfirmExecuteResponse,
    SwapExecuteRequest,
    SwapExecuteResponse,
    SwapFailureRecordRequest,
    SwapPriceChangedDetail,
    SwapQuoteRequest,
    SwapQuoteResponse,
    SwapStatusResponse,
    SwapSubmitRequest,
    SwapSupportedAssetsResponse,
)
from services.lifi.swap_failure_service import record_swap_failure
from config.supported_swap_assets import (
    list_supported_chains_public,
    list_supported_destination_assets_public,
    list_supported_source_assets_public,
)
from services.test_clients.mobile_identity import mobile_bearer

logger = logging.getLogger(__name__)

swaps_router = APIRouter(prefix="/api/swaps", tags=["swaps"])

_lifi_client = build_lifi_client()
_quote_svc = LifiQuoteService(lifi_client=_lifi_client)
_execute_svc = LifiExecuteService(lifi_client=_lifi_client)
_confirm_svc = LifiConfirmService(quote_service=_quote_svc, execute_service=_execute_svc)


def _resolve_person_id(
    credentials: Optional[HTTPAuthorizationCredentials],
) -> UUID:
    if credentials is None or not (credentials.credentials or "").strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "swap.auth_required",
                "message": "Authorization: Bearer (JWT Vancelian) requis.",
            },
        )
    return _jwt_person_uuid(credentials.credentials)


def _ensure_swaps_enabled() -> None:
    if not swaps_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "swap.disabled",
                "message": "Swaps LI.FI désactivés.",
            },
        )
    if not lifi_api_configured() and not swaps_mock_mode():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "swap.lifi_not_configured",
                "message": "LI.FI non configuré côté serveur.",
            },
        )


def _validation_error(exc: SwapValidationError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"code": exc.code, "message": str(exc)},
    )


@swaps_router.get("/supported-assets", response_model=SwapSupportedAssetsResponse)
def get_supported_swap_assets():
    source_assets = list_supported_source_assets_public()
    destination_assets = list_supported_destination_assets_public()
    return SwapSupportedAssetsResponse(
        assets=source_assets,
        source_assets=source_assets,
        destination_assets=destination_assets,
        chains=list_supported_chains_public(),
        swap_fee_bps=swap_fee_bps(),
        default_slippage_bps=default_slippage_bps(),
        max_slippage_bps=MAX_SLIPPAGE_BPS,
        mock_mode=swaps_mock_mode(),
    )


@swaps_router.post("/quote", response_model=SwapQuoteResponse)
def post_swap_quote(
    body: SwapQuoteRequest,
    db=Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    _ensure_swaps_enabled()
    person_id = _resolve_person_id(credentials)
    try:
        return _quote_svc.create_quote(
            db,
            person_id=person_id,
            from_asset=body.from_asset,
            to_asset=body.to_asset,
            amount=body.amount,
            from_chain=body.from_chain,
            to_chain=body.to_chain,
            slippage_bps=body.slippage_bps,
            signing_wallet_mode=body.signing_wallet_mode,
            signing_wallet_address=body.signing_wallet_address,
        )
    except SwapValidationError as exc:
        raise _validation_error(exc) from exc
    except LifiClientError as exc:
        logger.warning("swap.quote.lifi_error", extra={"code": exc.code})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


def _price_changed_error(exc: SwapPriceChangedError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=SwapPriceChangedDetail(
            code=exc.code,
            message=exc.message,
            quote=exc.quote,
            delta_bps=exc.delta_bps,
            slippage_bps=exc.slippage_bps,
        ).model_dump(mode="json"),
    )


@swaps_router.post("/confirm-execute", response_model=SwapConfirmExecuteResponse)
def post_swap_confirm_execute(
    body: SwapConfirmExecuteRequest,
    db=Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    _ensure_swaps_enabled()
    person_id = _resolve_person_id(credentials)
    try:
        return _confirm_svc.confirm_execute(
            db,
            person_id=person_id,
            swap_id=body.swap_id,
            review_estimated_receive=body.review_estimated_receive,
            review_amount_in=body.review_amount_in,
        )
    except SwapPriceChangedError as exc:
        raise _price_changed_error(exc) from exc
    except SwapValidationError as exc:
        raise _validation_error(exc) from exc
    except LifiClientError as exc:
        logger.warning("swap.confirm.lifi_error", extra={"code": exc.code})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@swaps_router.post("/{swap_id}/refresh-quote", response_model=SwapQuoteResponse)
def post_swap_refresh_quote(
    swap_id: UUID,
    db=Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    _ensure_swaps_enabled()
    person_id = _resolve_person_id(credentials)
    try:
        return _quote_svc.refresh_quote(db, person_id=person_id, swap_id=swap_id)
    except SwapValidationError as exc:
        raise _validation_error(exc) from exc
    except LifiClientError as exc:
        logger.warning("swap.refresh.lifi_error", extra={"code": exc.code})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc


@swaps_router.post("/{swap_id}/failure", response_model=SwapStatusResponse)
def post_swap_failure(
    swap_id: UUID,
    body: SwapFailureRecordRequest,
    db=Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    _ensure_swaps_enabled()
    person_id = _resolve_person_id(credentials)
    try:
        record_swap_failure(
            db,
            person_id=person_id,
            swap_id=swap_id,
            failure_phase=body.failure_phase,
            error_code=body.error_code,
            technical_message=body.technical_message,
            wallet_address=body.signing_wallet_address,
        )
        return _execute_svc.get_status(db, person_id=person_id, swap_id=swap_id)
    except SwapValidationError as exc:
        raise _validation_error(exc) from exc


@swaps_router.post("/{swap_id}/abandon", response_model=SwapStatusResponse)
def post_swap_abandon(
    swap_id: UUID,
    body: SwapAbandonRequest | None = None,
    db=Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    _ensure_swaps_enabled()
    person_id = _resolve_person_id(credentials)
    payload = body or SwapAbandonRequest()
    try:
        return _execute_svc.abandon_swap(
            db,
            person_id=person_id,
            swap_id=swap_id,
            reason=payload.reason,
            explicit_user_abandon=payload.explicit_user_abandon,
            failure_phase=payload.failure_phase,
        )
    except SwapValidationError as exc:
        raise _validation_error(exc) from exc


@swaps_router.post("/execute", response_model=SwapExecuteResponse)
def post_swap_execute(
    body: SwapExecuteRequest,
    db=Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    """Legacy — préférer ``/confirm-execute`` (refresh + slippage + prepare)."""
    _ensure_swaps_enabled()
    person_id = _resolve_person_id(credentials)
    try:
        return _execute_svc.prepare_execute(db, person_id=person_id, swap_id=body.swap_id)
    except SwapValidationError as exc:
        raise _validation_error(exc) from exc


@swaps_router.post("/{swap_id}/submit", response_model=SwapStatusResponse)
def post_swap_submit(
    swap_id: UUID,
    body: SwapSubmitRequest,
    db=Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    _ensure_swaps_enabled()
    person_id = _resolve_person_id(credentials)
    try:
        return _execute_svc.submit_signed_tx(
            db,
            person_id=person_id,
            swap_id=swap_id,
            tx_hash=body.tx_hash,
            signing_wallet_address=body.signing_wallet_address,
        )
    except SwapValidationError as exc:
        raise _validation_error(exc) from exc


@swaps_router.post("/{swap_id}/approval", response_model=SwapStatusResponse)
def post_swap_approval(
    swap_id: UUID,
    body: SwapApprovalSubmitRequest,
    db=Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    _ensure_swaps_enabled()
    person_id = _resolve_person_id(credentials)
    try:
        return _execute_svc.record_token_approval(
            db,
            person_id=person_id,
            swap_id=swap_id,
            tx_hash=body.tx_hash,
            signing_wallet_address=body.signing_wallet_address,
        )
    except SwapValidationError as exc:
        raise _validation_error(exc) from exc


@swaps_router.get("/{swap_id}", response_model=SwapStatusResponse)
def get_swap_status(
    swap_id: UUID,
    db=Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(mobile_bearer),
):
    person_id = _resolve_person_id(credentials)
    try:
        return _execute_svc.get_status(db, person_id=person_id, swap_id=swap_id)
    except SwapValidationError as exc:
        raise _validation_error(exc) from exc
