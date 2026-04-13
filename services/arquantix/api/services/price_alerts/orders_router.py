"""Trigger Orders REST endpoints — mounted under /api/app/orders.

Reuses the price_alerts table with action_type='order' and a structured order_payload.
"""
import logging
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from database import get_db
from services.portfolio_engine.clients.models import Client as PeClient
from services.price_alerts.models import PriceAlert
from services.test_clients.mobile_identity import mobile_app_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/app/orders", tags=["trigger-orders"])

ORDER_TYPE_MAP = {
    ("buy", "limit"):  {"direction": "down", "price_source": "ask"},
    ("buy", "stop"):   {"direction": "up",   "price_source": "ask"},
    ("sell", "limit"): {"direction": "up",   "price_source": "bid"},
    ("sell", "stop"):  {"direction": "down", "price_source": "bid"},
}


class CreateOrderRequest(BaseModel):
    asset: str = Field(..., min_length=1, max_length=20)
    side: str = Field(..., pattern="^(buy|sell)$")
    order_type: str = Field(..., pattern="^(limit|stop)$")
    trigger_price: float = Field(..., gt=0)
    amount: float = Field(..., gt=0)
    slippage_bps: Optional[int] = Field(None, ge=0, le=500)


def _order_to_response(a: PriceAlert) -> dict:
    payload = a.order_payload or {}
    meta = a.metadata_ or {}
    return {
        "id": str(a.id),
        "asset": a.asset,
        "side": payload.get("side"),
        "order_type": payload.get("order_type"),
        "trigger_price": float(a.target_price),
        "amount": payload.get("amount"),
        "slippage_bps": payload.get("slippage_bps"),
        "direction": a.direction,
        "price_source": a.price_source,
        "status": a.status,
        "execution_status": a.execution_status,
        "execution_price": meta.get("execution_price"),
        "filled_amount": meta.get("filled_amount"),
        "remaining_amount": meta.get("remaining_amount"),
        "order_id": meta.get("order_id"),
        "failure_reason": meta.get("failure_reason"),
        "can_retry_remaining": meta.get("can_retry_remaining", False),
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
        "triggered_price": float(a.triggered_price) if a.triggered_price is not None else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_order(
    body: CreateOrderRequest,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):

    key = (body.side, body.order_type)
    mapping = ORDER_TYPE_MAP.get(key)
    if not mapping:
        raise HTTPException(status_code=400, detail=f"Invalid side/order_type combination: {key}")

    order_payload = {
        "side": body.side,
        "order_type": body.order_type,
        "amount": body.amount,
    }
    if body.slippage_bps is not None:
        order_payload["slippage_bps"] = body.slippage_bps

    alert = PriceAlert(
        client_id=client.id,
        asset=body.asset.upper(),
        target_price=Decimal(str(body.trigger_price)),
        direction=mapping["direction"],
        price_source=mapping["price_source"],
        action_type="order",
        order_payload=order_payload,
        trigger_mode="once",
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    from services.redis_client import get_redis
    from services.price_alerts.cache import add_alert_to_cache, _bucket_for, _direction_key
    r = get_redis()
    add_alert_to_cache(r, alert)

    bucket = _bucket_for(str(alert.id))
    redis_key = _direction_key(alert.asset, mapping["direction"], bucket)
    logger.info(
        "Order created: id=%s asset=%s side=%s type=%s trigger=%.2f amount=%.4f "
        "dir=%s src=%s redis_key=%s bucket=%d redis_connected=%s",
        alert.id, alert.asset, body.side, body.order_type,
        body.trigger_price, body.amount, mapping["direction"], mapping["price_source"],
        redis_key, bucket, r is not None,
    )
    return _order_to_response(alert)


@router.get("")
def list_orders(
    status_filter: Optional[str] = Query(None, alias="status"),
    asset_filter: Optional[str] = Query(None, alias="asset"),
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    q = (
        db.query(PriceAlert)
        .filter(PriceAlert.client_id == client.id, PriceAlert.action_type == "order")
    )
    if status_filter:
        q = q.filter(PriceAlert.status == status_filter)
    if asset_filter:
        q = q.filter(PriceAlert.asset == asset_filter.upper())
    orders = q.order_by(PriceAlert.created_at.desc()).all()
    return [_order_to_response(o) for o in orders]


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_order(
    order_id: str,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    alert = (
        db.query(PriceAlert)
        .filter(
            PriceAlert.id == order_id,
            PriceAlert.client_id == client.id,
            PriceAlert.action_type == "order",
        )
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Order not found")
    if alert.status == "active":
        alert.status = "cancelled"
        db.commit()

        from services.redis_client import get_redis
        from services.price_alerts.cache import remove_alert_from_cache
        r = get_redis()
        remove_alert_from_cache(r, str(alert.id), alert.asset, alert.direction)

    return None
