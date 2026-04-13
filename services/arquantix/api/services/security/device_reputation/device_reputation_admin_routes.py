"""Admin — réputation device, findings, blacklist (contrôle explicite)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import exists, or_
from sqlalchemy.orm import Session

from auth import get_current_user
from database import (
    AdminUser,
    AuthDeviceBlacklist,
    AuthDeviceGraphFinding,
    AuthDeviceReputation,
    AuthDeviceUsageEdge,
    get_db,
)
from schemas import (
    DeviceBlacklistRequest,
    DeviceGraphFindingItem,
    DeviceReputationActionResponse,
    DeviceReputationItem,
    DeviceUnblacklistRequest,
)

router = APIRouter(prefix="/admin/security/devices", tags=["admin-device-reputation"])


@router.get("/", response_model=List[DeviceReputationItem])
def list_device_reputations(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
    reputation_level: Optional[str] = None,
    user_id: Optional[int] = None,
    ip: Optional[str] = None,
    blocked_only: bool = False,
    limit: int = Query(default=200, ge=1, le=1000),
):
    _ = current_user
    q = db.query(AuthDeviceReputation)
    if reputation_level:
        q = q.filter(AuthDeviceReputation.reputation_level == reputation_level.strip().upper()[:16])
    if user_id is not None:
        q = q.filter(
            exists().where(
                AuthDeviceUsageEdge.device_hash == AuthDeviceReputation.device_hash,
                AuthDeviceUsageEdge.user_id == user_id,
            )
        )
    if ip:
        ip_s = ip.strip()[:45]
        q = q.filter(
            exists().where(
                AuthDeviceUsageEdge.device_hash == AuthDeviceReputation.device_hash,
                AuthDeviceUsageEdge.ip_address == ip_s,
            )
        )
    now = datetime.now(timezone.utc)
    if blocked_only:
        q = q.filter(
            or_(
                AuthDeviceReputation.reputation_level == "BLOCKED",
                exists().where(
                    AuthDeviceBlacklist.device_hash == AuthDeviceReputation.device_hash,
                    or_(
                        AuthDeviceBlacklist.blocked_until.is_(None),
                        AuthDeviceBlacklist.blocked_until > now,
                    ),
                ),
            )
        )
    rows = q.order_by(AuthDeviceReputation.global_risk_score.desc()).limit(limit).all()
    return list(rows)


@router.get("/high-risk", response_model=List[DeviceReputationItem])
def list_high_risk_devices(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=500),
):
    _ = current_user
    rows = (
        db.query(AuthDeviceReputation)
        .filter(
            or_(
                AuthDeviceReputation.global_risk_score >= 55,
                AuthDeviceReputation.reputation_level.in_(("HIGH", "CRITICAL", "BLOCKED")),
            )
        )
        .order_by(AuthDeviceReputation.global_risk_score.desc())
        .limit(limit)
        .all()
    )
    return list(rows)


@router.get("/findings", response_model=List[DeviceGraphFindingItem])
def list_device_graph_findings(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
    finding_type: Optional[str] = None,
    device_hash: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=1000),
):
    _ = current_user
    q = db.query(AuthDeviceGraphFinding).order_by(AuthDeviceGraphFinding.created_at.desc())
    if finding_type:
        q = q.filter(AuthDeviceGraphFinding.finding_type == finding_type[:128])
    if device_hash:
        q = q.filter(AuthDeviceGraphFinding.device_hash == device_hash[:64])
    return list(q.limit(limit).all())


@router.post("/blacklist", response_model=DeviceReputationActionResponse)
def post_device_blacklist(
    body: DeviceBlacklistRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    from services.security.device_reputation.device_reputation_service import blacklist_device

    blacklist_device(
        db,
        body.device_hash.strip(),
        reason=body.reason,
        blocked_until=body.blocked_until,
        created_by=current_user.id,
    )
    db.commit()
    return DeviceReputationActionResponse(ok=True, detail="blacklisted")


@router.post("/unblacklist", response_model=DeviceReputationActionResponse)
def post_device_unblacklist(
    body: DeviceUnblacklistRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    from services.security.device_reputation.device_reputation_service import unblacklist_device

    _ = current_user
    n = unblacklist_device(db, body.device_hash.strip())
    db.commit()
    return DeviceReputationActionResponse(ok=True, detail=f"removed_{n}")


@router.get("/{device_hash}", response_model=DeviceReputationItem)
def get_device_reputation_detail(
    device_hash: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    _ = current_user
    row = db.get(AuthDeviceReputation, device_hash.strip()[:64])
    if row is None:
        raise HTTPException(status_code=404, detail="device_reputation_not_found")
    return row
