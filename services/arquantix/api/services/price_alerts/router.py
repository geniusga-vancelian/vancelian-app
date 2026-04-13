"""Price Alerts REST endpoints — mounted under /api/app/alerts."""
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

router = APIRouter(prefix="/api/app/alerts", tags=["price-alerts"])


class CreateAlertRequest(BaseModel):
    asset: str = Field(..., min_length=1, max_length=20)
    target_price: float = Field(..., gt=0)
    direction: str = Field(..., pattern="^(up|down)$")
    price_source: str = Field(default="mid", pattern="^(bid|ask|mid)$")
    cooldown_seconds: int = Field(default=0, ge=0, le=86400)
    trigger_mode: str = Field(default="once", pattern="^(once|recurring)$")


def _alert_to_response(a: PriceAlert) -> dict:
    return {
        "id": str(a.id),
        "asset": a.asset,
        "target_price": float(a.target_price),
        "direction": a.direction,
        "price_source": a.price_source,
        "status": a.status,
        "action_type": a.action_type,
        "trigger_mode": getattr(a, "trigger_mode", None) or "once",
        "trigger_count": getattr(a, "trigger_count", None) or 0,
        "cooldown_seconds": a.cooldown_seconds or 0,
        "execution_status": a.execution_status,
        "created_at": a.created_at.isoformat() if a.created_at else None,
        "triggered_at": a.triggered_at.isoformat() if a.triggered_at else None,
        "triggered_price": float(a.triggered_price) if a.triggered_price is not None else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
def create_alert(
    body: CreateAlertRequest,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):

    alert = PriceAlert(
        client_id=client.id,
        asset=body.asset.upper(),
        target_price=Decimal(str(body.target_price)),
        direction=body.direction,
        price_source=body.price_source,
        cooldown_seconds=body.cooldown_seconds,
        trigger_mode=body.trigger_mode,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    from services.redis_client import get_redis
    from services.price_alerts.cache import add_alert_to_cache
    r = get_redis()
    add_alert_to_cache(r, alert)

    logger.info(
        "Alert created: id=%s asset=%s target=%.2f dir=%s source=%s cooldown=%ds",
        alert.id, alert.asset, float(alert.target_price),
        alert.direction, alert.price_source, alert.cooldown_seconds,
    )
    return _alert_to_response(alert)


@router.get("")
def list_alerts(
    status_filter: Optional[str] = Query(None, alias="status"),
    asset_filter: Optional[str] = Query(None, alias="asset"),
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    q = db.query(PriceAlert).filter(PriceAlert.client_id == client.id)
    if status_filter:
        q = q.filter(PriceAlert.status == status_filter)
    if asset_filter:
        q = q.filter(PriceAlert.asset == asset_filter.upper())
    alerts = q.order_by(PriceAlert.created_at.desc()).all()
    return [_alert_to_response(a) for a in alerts]


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    alert = (
        db.query(PriceAlert)
        .filter(PriceAlert.id == alert_id, PriceAlert.client_id == client.id)
        .first()
    )
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    if alert.status == "active":
        alert.status = "cancelled"
        db.commit()

        from services.redis_client import get_redis
        from services.price_alerts.cache import remove_alert_from_cache
        r = get_redis()
        remove_alert_from_cache(r, str(alert.id), alert.asset, alert.direction)

    return None


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_all_alerts(
    asset_filter: Optional[str] = Query(None, alias="asset"),
    db: Session = Depends(get_db),
    client: PeClient = Depends(mobile_app_client),
):
    q = db.query(PriceAlert).filter(
        PriceAlert.client_id == client.id,
        PriceAlert.action_type != "order",
    )
    if asset_filter:
        q = q.filter(PriceAlert.asset == asset_filter.upper())

    alerts = q.all()
    from services.redis_client import get_redis
    from services.price_alerts.cache import remove_alert_from_cache
    r = get_redis()
    for a in alerts:
        if a.status == "active":
            remove_alert_from_cache(r, str(a.id), a.asset, a.direction)
        db.delete(a)
    db.commit()
    logger.info("Deleted %d alert(s) for client %s (asset=%s)", len(alerts), client.id, asset_filter)
    return None


@router.get("/metrics")
def alert_metrics(
    _client: PeClient = Depends(mobile_app_client),
):
    """Observability endpoint — engine stats (même garde d’identité que le reste de /api/app)."""
    from services.price_alerts.metrics import get_metrics
    from services.notifications.dispatcher import get_dispatcher
    data = get_metrics().snapshot()
    dispatcher = get_dispatcher()
    if dispatcher is not None:
        data["notification_dispatcher"] = dispatcher.stats
    return data
