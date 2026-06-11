"""HTTP — primitive swap wallet virtuel (ADR 008)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.portfolio_engine.clients.models import Client as PeClient
from services.portfolio_engine.hardening.security.context import ActorContext
from services.test_clients.mobile_identity import mobile_app_client

from .run_wallet_swap import (
    VirtualWalletSwapError,
    VirtualWalletSwapRequest,
    quote_virtual_wallet_swap,
    run_virtual_wallet_swap,
)

router = APIRouter(prefix="/api/app/trade", tags=["trade-core"])


class WalletSwapQuoteBody(BaseModel):
    wallet_from_id: str
    wallet_to_id: str
    quantity_from: str = Field(..., description="volumeFrom — montant source (crypto ou USDC)")
    estimated_quantity_to: str | None = Field(
        None,
        description="volumeTo — estimation réception pour review slippage",
    )
    side: Literal["buy", "sell"]
    portfolio_id: str
    correlation_id: str
    leg_id: str
    batch_id: str
    bundle_action: str = "rebalance_v3"
    leg_action: str
    chain: str = "base"
    metadata: dict[str, Any] = Field(default_factory=dict)


class WalletSwapCompleteBody(WalletSwapQuoteBody):
    swap_id: str
    tx_hash: str
    signing_wallet_address: str | None = None


def _parse_uuid(value: str, field: str) -> UUID:
    try:
        return UUID(str(value).strip())
    except (TypeError, ValueError, AttributeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"invalid_{field}",
        ) from exc


def _parse_decimal(value: str, field: str) -> Decimal:
    try:
        parsed = Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"invalid_{field}",
        ) from exc
    if parsed <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"invalid_{field}",
        )
    return parsed


def _body_to_request(body: WalletSwapQuoteBody, client_id: UUID) -> VirtualWalletSwapRequest:
    est: Decimal | None = None
    if body.estimated_quantity_to and str(body.estimated_quantity_to).strip():
        est = _parse_decimal(body.estimated_quantity_to, "estimated_quantity_to")
    return VirtualWalletSwapRequest(
        wallet_from_id=_parse_uuid(body.wallet_from_id, "wallet_from_id"),
        wallet_to_id=_parse_uuid(body.wallet_to_id, "wallet_to_id"),
        quantity_from=_parse_decimal(body.quantity_from, "quantity_from"),
        estimated_quantity_to=est,
        side=body.side,
        correlation_id=_parse_uuid(body.correlation_id, "correlation_id"),
        client_id=client_id,
        portfolio_id=_parse_uuid(body.portfolio_id, "portfolio_id"),
        leg_id=body.leg_id,
        batch_id=body.batch_id,
        bundle_action=body.bundle_action,
        leg_action=body.leg_action,
        chain=body.chain,
        metadata=dict(body.metadata or {}),
    )


def _quote_to_response(quote) -> dict[str, Any]:
    snap = quote.review_snapshot
    return {
        "phase": "awaiting_signature",
        "swap_id": str(quote.swap_id),
        "from_asset": quote.from_asset,
        "to_asset": quote.to_asset,
        "amount_in": str(quote.amount_in),
        "estimated_receive": (
            str(quote.estimated_receive) if quote.estimated_receive is not None else None
        ),
        "status": quote.status,
        "requires_client_signature": quote.requires_client_signature,
        "review_snapshot": {
            "review_amount_in": snap.review_amount_in,
            "review_estimated_receive": snap.review_estimated_receive,
        },
    }


def _run_to_response(result) -> dict[str, Any]:
    payload: dict[str, Any] = {"phase": result.phase}
    if result.quote is not None:
        payload.update(_quote_to_response(result.quote))
    if result.finalize is not None:
        fin = result.finalize
        payload["finalize"] = {
            "swap_id": str(fin.swap_id),
            "status": fin.status,
            "tx_hash": fin.tx_hash,
            "settled": fin.settled,
            "settlement_scope": fin.settlement_scope,
            "error": fin.error,
        }
    return payload


@router.post("/wallet-swap/quote")
def wallet_swap_quote(
    body: WalletSwapQuoteBody,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Quote LI.FI pour une paire de wallets virtuels — avant signature Privy."""
    actor = ActorContext(actor_type="client", actor_id=str(client.id))
    try:
        quote = quote_virtual_wallet_swap(
            db,
            _body_to_request(body, client.id),
            actor,
        )
        db.commit()
        return _quote_to_response(quote)
    except VirtualWalletSwapError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.code) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/wallet-swap/run")
def wallet_swap_run(
    body: WalletSwapCompleteBody,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    """Quote + submit tx signée + settlement — usage serveur post-signature."""
    actor = ActorContext(actor_type="client", actor_id=str(client.id))
    person_id = client.person_id
    if person_id is None:
        raise HTTPException(status_code=400, detail="client_has_no_person_id")

    try:
        req = _body_to_request(body, client.id)
        result = run_virtual_wallet_swap(
            db,
            req,
            actor,
            person_id=person_id,
            tx_hash=body.tx_hash.strip(),
            signing_wallet_address=body.signing_wallet_address,
        )
        return _run_to_response(result)
    except VirtualWalletSwapError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.code) from exc
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
