"""
Moteur de corrélation SIEM (scores 0–100, signaux multi-dimensionnels).

S’appuie sur ``auth_security_events``. Pas d’action automatique sur les comptes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import AuthSecurityEvent


@dataclass
class CorrelationSignal:
    rule: str
    points: int
    detail: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CorrelationAssessment:
    risk_score: int  # 0–100
    risk_level: str  # LOW / MEDIUM / HIGH / CRITICAL
    signals: List[CorrelationSignal] = field(default_factory=list)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _level_from_score(score: int) -> str:
    if score >= 85:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


def _cap_score(raw: int) -> int:
    return max(0, min(100, raw))


def detect_ip_anomaly(
    db: Session,
    user_id: int,
    *,
    window_hours: int = 24,
    distinct_ip_threshold: int = 6,
) -> List[CorrelationSignal]:
    """Trop d’IP distinctes pour un utilisateur sur la fenêtre."""
    since = _utcnow() - timedelta(hours=window_hours)
    n_ip = int(
        db.execute(
            select(func.count(func.distinct(AuthSecurityEvent.ip_address))).where(
                AuthSecurityEvent.user_id == user_id,
                AuthSecurityEvent.created_at >= since,
                AuthSecurityEvent.ip_address.isnot(None),
            )
        ).scalar_one()
        or 0
    )
    if n_ip < distinct_ip_threshold:
        return []
    pts = 25 + min(35, (n_ip - distinct_ip_threshold) * 5)
    return [
        CorrelationSignal(
            rule="ip_anomaly",
            points=pts,
            detail={"user_id": user_id, "distinct_ips": n_ip, "window_hours": window_hours},
        )
    ]


def detect_multi_device_abuse(
    db: Session,
    user_id: int,
    *,
    window_hours: int = 48,
    device_threshold: int = 4,
) -> List[CorrelationSignal]:
    """Plusieurs appareils actifs pour le même compte."""
    since = _utcnow() - timedelta(hours=window_hours)
    n_dev = int(
        db.execute(
            select(func.count(func.distinct(AuthSecurityEvent.device_id))).where(
                AuthSecurityEvent.user_id == user_id,
                AuthSecurityEvent.created_at >= since,
            )
        ).scalar_one()
        or 0
    )
    if n_dev < device_threshold:
        return []
    pts = 20 + min(30, (n_dev - device_threshold) * 6)
    return [
        CorrelationSignal(
            rule="multi_device_abuse",
            points=pts,
            detail={"user_id": user_id, "distinct_devices": n_dev, "window_hours": window_hours},
        )
    ]


def detect_bruteforce(
    db: Session,
    ip: str,
    *,
    window_minutes: int = 10,
    threshold: int = 25,
) -> List[CorrelationSignal]:
    """Échecs auth concentrés sur une IP."""
    since = _utcnow() - timedelta(minutes=window_minutes)
    types = ("auth.login.failed", "auth.refresh.rejected", "auth.passkey.login.failed")
    n = int(
        db.execute(
            select(func.count())
            .select_from(AuthSecurityEvent)
            .where(
                AuthSecurityEvent.ip_address == ip[:45],
                AuthSecurityEvent.created_at >= since,
                AuthSecurityEvent.event_type.in_(types),
            )
        ).scalar_one()
        or 0
    )
    if n < threshold:
        return []
    pts = 40 + min(45, (n - threshold) * 2)
    return [
        CorrelationSignal(
            rule="bruteforce",
            points=pts,
            detail={"ip_prefix": ip[:12], "count": n, "window_minutes": window_minutes},
        )
    ]


def detect_refresh_abuse(
    db: Session,
    device_id: str,
    *,
    window_minutes: int = 5,
    threshold: int = 15,
) -> List[CorrelationSignal]:
    """Refresh rejetés / rafales sur un device_id."""
    since = _utcnow() - timedelta(minutes=window_minutes)
    types = ("auth.refresh.rejected", "auth.refresh.rapid_burst")
    n = int(
        db.execute(
            select(func.count())
            .select_from(AuthSecurityEvent)
            .where(
                AuthSecurityEvent.device_id == device_id[:128],
                AuthSecurityEvent.created_at >= since,
                AuthSecurityEvent.event_type.in_(types),
            )
        ).scalar_one()
        or 0
    )
    if n < threshold:
        return []
    pts = 30 + min(40, n * 2)
    return [
        CorrelationSignal(
            rule="refresh_abuse",
            points=pts,
            detail={"device_prefix": device_id[:8], "count": n, "window_minutes": window_minutes},
        )
    ]


def detect_geo_velocity(
    db: Session,
    user_id: int,
    *,
    window_hours: int = 2,
    min_minutes_between_countries: int = 60,
) -> List[CorrelationSignal]:
    """
    Changement de pays (metadata) trop rapide pour un même utilisateur.
    Sans pays dans les métadonnées → aucun signal.
    """
    since = _utcnow() - timedelta(hours=window_hours)
    rows = db.execute(
        select(AuthSecurityEvent.created_at, AuthSecurityEvent.metadata_payload)
        .where(AuthSecurityEvent.user_id == user_id, AuthSecurityEvent.created_at >= since)
        .order_by(AuthSecurityEvent.created_at.asc())
    ).all()
    last_country: Optional[str] = None
    last_ts: Optional[datetime] = None
    for ts, meta in rows:
        if not isinstance(meta, dict):
            continue
        c = meta.get("country") or meta.get("geo_country")
        if not c or not isinstance(c, str):
            continue
        c = c.strip().upper()
        if last_country and c != last_country and last_ts is not None:
            delta_min = (ts - last_ts).total_seconds() / 60.0
            if delta_min < min_minutes_between_countries:
                return [
                    CorrelationSignal(
                        rule="geo_velocity",
                        points=55,
                        detail={
                            "user_id": user_id,
                            "from_country": last_country,
                            "to_country": c,
                            "delta_minutes": round(delta_min, 2),
                        },
                    )
                ]
        last_country = c
        last_ts = ts
    return []


def detect_geo_velocity_from_ip_sequence(
    ip_sequence: List[str],
    *,
    km_per_hour_threshold: float = 800.0,
) -> List[CorrelationSignal]:
    """
    Placeholder : sans géolocalisation IP, retourne vide.
    Brancher un service GeoIP pour estimer vitesses entre hops.
    """
    _ = ip_sequence, km_per_hour_threshold
    return []


def aggregate_signals(signals: List[CorrelationSignal]) -> CorrelationAssessment:
    """Agrège les points (saturé 100) et dérive le niveau."""
    total = sum(s.points for s in signals)
    return CorrelationAssessment(
        risk_score=_cap_score(total),
        risk_level=_level_from_score(_cap_score(total)),
        signals=list(signals),
    )


def assess_user_risk(db: Session, user_id: int, *, window_hours: int = 168) -> CorrelationAssessment:
    """Vue consolidée pour un utilisateur (admin / SIEM)."""
    sigs: List[CorrelationSignal] = []
    sigs.extend(detect_ip_anomaly(db, user_id, window_hours=min(24, window_hours)))
    sigs.extend(detect_multi_device_abuse(db, user_id, window_hours=min(48, window_hours)))
    sigs.extend(detect_geo_velocity(db, user_id, window_hours=2))
    return aggregate_signals(sigs)


def assess_global_peers(db: Session) -> CorrelationAssessment:
    """Agrégat léger pour dashboard (bruteforce + devices + geo sauts)."""
    from services.auth.security_correlation_service import (
        detect_bruteforce_pattern,
        detect_device_anomaly,
        detect_geo_jump,
    )

    sigs: List[CorrelationSignal] = []
    for f in detect_bruteforce_pattern(db):
        sigs.append(CorrelationSignal(rule=f.rule, points=50 if f.severity == "CRITICAL" else 35, detail=f.detail))
    for f in detect_device_anomaly(db):
        sigs.append(CorrelationSignal(rule=f.rule, points=45 if f.severity == "CRITICAL" else 30, detail=f.detail))
    for f in detect_geo_jump(db):
        sigs.append(CorrelationSignal(rule=f.rule, points=20, detail=f.detail))
    return aggregate_signals(sigs)


def signals_to_dicts(signals: List[CorrelationSignal]) -> List[Dict[str, Any]]:
    return [{"rule": s.rule, "points": s.points, "detail": s.detail} for s in signals]
