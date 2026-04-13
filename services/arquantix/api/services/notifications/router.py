"""Notifications REST endpoints — mounted under /api/app/notifications."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import get_db
from services.notifications.models import Notification
from services.portfolio_engine.clients.models import Client as PeClient
from services.test_clients.mobile_identity import mobile_app_client

router = APIRouter(prefix="/api/app/notifications", tags=["notifications"])


def _notif_to_dict(n: Notification) -> dict:
    return {
        "id": str(n.id),
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "payload": n.payload,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("")
def list_notifications(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    q = (
        db.query(Notification)
        .filter(Notification.client_id == client.id)
        .order_by(Notification.created_at.desc())
    )
    total = q.count()
    items = q.offset(offset).limit(limit).all()
    return {
        "items": [_notif_to_dict(n) for n in items],
        "total": total,
    }


@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    count = (
        db.query(func.count(Notification.id))
        .filter(Notification.client_id == client.id, Notification.is_read == False)
        .scalar()
    ) or 0
    return {"count": count}


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(
    notification_id: str,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    notif = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.client_id == client.id)
        .first()
    )
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return None


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    db.query(Notification).filter(
        Notification.client_id == client.id,
        Notification.is_read == False,
    ).update({"is_read": True})
    db.commit()
    return None
