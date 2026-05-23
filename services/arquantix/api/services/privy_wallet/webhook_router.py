"""Public webhook endpoint for Privy wallet events (Svix-signed)."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy.orm import Session

from database import get_db
from fastapi import Depends

from .enums import PrivyWebhookEventStatus
from .webhook_service import FUNDS_DEPOSITED_EVENT, PrivyWebhookProcessor
from .webhook_verifier import PrivyWebhookVerifyError, verify_svix_webhook

logger = logging.getLogger(__name__)

privy_webhook_router = APIRouter(prefix="/api/webhooks", tags=["privy-webhooks"])
_processor = PrivyWebhookProcessor()


@privy_webhook_router.post("/privy")
async def receive_privy_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """Receive a Privy webhook. Always stores raw payload before business logic."""
    body = await request.body()

    try:
        verify_svix_webhook(
            body,
            svix_id=request.headers.get("svix-id"),
            svix_timestamp=request.headers.get("svix-timestamp"),
            svix_signature=request.headers.get("svix-signature"),
        )
    except PrivyWebhookVerifyError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    event_type = str(payload.get("type") or payload.get("event_type") or "unknown")
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    external_reference = (
        payload.get("id")
        or data.get("id")
        or data.get("transaction_hash")
        or data.get("tx_hash")
    )
    idempotency_key = (
        payload.get("idempotency_key")
        or request.headers.get("svix-id")
        or (str(external_reference) if external_reference else None)
    )

    event = _processor.store_raw_event(
        db,
        event_type=event_type,
        payload=payload,
        svix_id=request.headers.get("svix-id"),
        idempotency_key=str(idempotency_key) if idempotency_key else None,
        external_reference=str(external_reference) if external_reference else None,
    )
    db.flush()

    if event.processing_status == PrivyWebhookEventStatus.DUPLICATE.value:
        db.commit()
        return {
            "status": "ok",
            "event_id": str(event.id),
            "processing_status": event.processing_status,
        }

    if event_type == FUNDS_DEPOSITED_EVENT:
        result = _processor.process_event(db, event)
    else:
        from .repository import PrivyWebhookEventRepository

        PrivyWebhookEventRepository.update_status(
            db,
            event,
            status=PrivyWebhookEventStatus.IGNORED.value,
            error_message=f"Unsupported event type: {event_type}",
        )
        result = PrivyWebhookEventStatus.IGNORED.value

    db.commit()
    return {
        "status": "ok",
        "event_id": str(event.id),
        "processing_status": result,
    }
