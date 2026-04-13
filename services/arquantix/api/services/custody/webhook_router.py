"""Public webhook endpoint for BAS (Bank-as-a-Service) custody events.

Accepts raw webhook payloads, stores them immediately, then processes them.
Storage always happens before any business logic — no exception.
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException, Path, Request
from sqlalchemy.orm import Session

from database import get_db
from .repository import CustodyProviderRepository
from .webhook_service import WebhookProcessor

logger = logging.getLogger(__name__)

webhook_router = APIRouter(prefix="/api/webhooks/custody", tags=["custody-webhooks"])
_processor = WebhookProcessor()
_provider_repo = CustodyProviderRepository()


@webhook_router.post("/{provider}")
async def receive_webhook(
    provider: str = Path(..., description="Provider slug (e.g. modular, zand)"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Receive a BAS webhook. Always stores raw payload before processing."""

    prov = _provider_repo.get_by_name(db, provider)
    if prov is None:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("event_type") or payload.get("type") or "unknown"
    external_reference = (
        payload.get("external_reference")
        or payload.get("reference")
        or payload.get("id")
    )

    # Layer 1: store raw — before any business logic
    event = _processor.store_raw_event(
        db,
        provider_id=prov.id,
        event_type=event_type,
        external_reference=str(external_reference) if external_reference else None,
        payload=payload,
    )
    db.flush()

    from .enums import WebhookEventStatus

    if event.processing_status in (
        WebhookEventStatus.DUPLICATE.value,
        WebhookEventStatus.FAILED.value,
    ):
        db.commit()
        return {
            "status": "ok",
            "event_id": str(event.id),
            "processing_status": event.processing_status,
        }

    # Layers 2+3: normalize & apply
    result = _processor.process_event(db, event)
    db.commit()

    return {
        "status": "ok",
        "event_id": str(event.id),
        "processing_status": result,
    }
