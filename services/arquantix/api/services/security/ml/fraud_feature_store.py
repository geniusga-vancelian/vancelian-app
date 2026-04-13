"""
Feature store utilisateur pour le scoring fraude ML (agrégats SIEM / sessions).
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import AuthGlobalRiskScore, AuthSecurityEvent, AuthSession

LOGIN_OK = "auth.login.succeeded"
LOGIN_FAIL = "auth.login.failed"
REFRESH_OK = "auth.refresh.succeeded"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _haversine_km(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0 * 2 * math.asin(min(1.0, math.sqrt(h)))


def _geo_points_from_meta(meta: Any) -> Optional[Tuple[float, float]]:
    if not isinstance(meta, dict):
        return None
    for lk, nk in (("geo_lat", "geo_lon"), ("lat", "lon"), ("latitude", "longitude")):
        la, lo = meta.get(lk), meta.get(nk)
        if la is not None and lo is not None:
            try:
                return float(la), float(lo)
            except (TypeError, ValueError):
                continue
    return None


def _shannon_entropy(counts: List[int]) -> float:
    total = sum(counts)
    if total <= 0:
        return 0.0
    ent = 0.0
    for c in counts:
        if c <= 0:
            continue
        p = c / total
        ent -= p * math.log(p + 1e-12, 2)
    return float(ent)


def build_feature_vector(db: Session, user_id: int) -> Dict[str, float]:
    """
    Construit un vecteur de features pour ``user_id`` (identité admin / auth).

    Toutes les valeurs sont des floats (comptages normalisés ou métriques continues).
    """
    now = _utcnow()
    t24 = now - timedelta(hours=24)
    t7 = now - timedelta(days=7)
    t30 = now - timedelta(days=30)

    login_ok_24 = int(
        db.execute(
            select(func.count())
            .select_from(AuthSecurityEvent)
            .where(
                AuthSecurityEvent.user_id == user_id,
                AuthSecurityEvent.created_at >= t24,
                AuthSecurityEvent.event_type == LOGIN_OK,
            )
        ).scalar_one()
        or 0
    )
    login_ok_7 = int(
        db.execute(
            select(func.count())
            .select_from(AuthSecurityEvent)
            .where(
                AuthSecurityEvent.user_id == user_id,
                AuthSecurityEvent.created_at >= t7,
                AuthSecurityEvent.event_type == LOGIN_OK,
            )
        ).scalar_one()
        or 0
    )
    uniq_ip_24 = int(
        db.execute(
            select(func.count(func.distinct(AuthSecurityEvent.ip_address))).where(
                AuthSecurityEvent.user_id == user_id,
                AuthSecurityEvent.created_at >= t24,
                AuthSecurityEvent.ip_address.isnot(None),
            )
        ).scalar_one()
        or 0
    )
    uniq_dev_7 = int(
        db.execute(
            select(func.count(func.distinct(AuthSecurityEvent.device_id))).where(
                AuthSecurityEvent.user_id == user_id,
                AuthSecurityEvent.created_at >= t7,
            )
        ).scalar_one()
        or 0
    )

    fail_7 = int(
        db.execute(
            select(func.count())
            .select_from(AuthSecurityEvent)
            .where(
                AuthSecurityEvent.user_id == user_id,
                AuthSecurityEvent.created_at >= t7,
                AuthSecurityEvent.event_type == LOGIN_FAIL,
            )
        ).scalar_one()
        or 0
    )
    denom = fail_7 + login_ok_7
    failed_login_ratio = float(fail_7 / denom) if denom > 0 else 0.0

    refresh_24 = int(
        db.execute(
            select(func.count())
            .select_from(AuthSecurityEvent)
            .where(
                AuthSecurityEvent.user_id == user_id,
                AuthSecurityEvent.created_at >= t24,
                AuthSecurityEvent.event_type == REFRESH_OK,
            )
        ).scalar_one()
        or 0
    )
    refresh_rate_per_hour = float(refresh_24) / 24.0

    rows = db.execute(
        select(AuthSecurityEvent.metadata_payload, AuthSecurityEvent.created_at).where(
            AuthSecurityEvent.user_id == user_id,
            AuthSecurityEvent.created_at >= t7,
        )
    ).all()

    hours = [0] * 24
    geo_pts: List[Tuple[float, float]] = []
    risk_vals: List[float] = []
    for meta, ts in rows:
        if ts:
            hours[ts.hour] += 1
        gp = _geo_points_from_meta(meta)
        if gp:
            geo_pts.append(gp)
        if isinstance(meta, dict) and meta.get("global_risk_score") is not None:
            try:
                risk_vals.append(float(meta["global_risk_score"]))
            except (TypeError, ValueError):
                pass

    time_of_day_entropy = _shannon_entropy(hours)

    if len(geo_pts) >= 2:
        dists = []
        for i in range(len(geo_pts)):
            for j in range(i + 1, len(geo_pts)):
                dists.append(_haversine_km(geo_pts[i], geo_pts[j]))
        mean = sum(dists) / len(dists)
        geo_distance_variance = float(sum((d - mean) ** 2 for d in dists) / len(dists))
    else:
        geo_distance_variance = 0.0

    sess_rows = db.execute(
        select(AuthSession.created_at, AuthSession.last_used_at, AuthSession.revoked_at).where(
            AuthSession.user_id == user_id,
            AuthSession.created_at >= t30,
        )
    ).all()
    durations_h: List[float] = []
    for cr, lu, rv in sess_rows:
        end = lu or cr
        if cr and end:
            dt = (end - cr).total_seconds() / 3600.0
            if dt >= 0:
                durations_h.append(dt)
    avg_session_duration = float(sum(durations_h) / len(durations_h)) if durations_h else 0.0

    trust_rows = db.execute(
        select(AuthSession.device_trust_level, func.count())
        .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None), AuthSession.expires_at > now)
        .group_by(AuthSession.device_trust_level)
    ).all()
    trust_map = {str(l or "UNKNOWN"): int(c) for l, c in trust_rows}
    t_total = sum(trust_map.values()) or 1
    suspicious = trust_map.get("SUSPICIOUS", 0) + trust_map.get("BLOCKED", 0)
    device_trust_distribution = float(suspicious / t_total)

    row = db.get(AuthGlobalRiskScore, user_id)
    current_risk = float(row.score) if row else 0.0
    if risk_vals:
        historical_risk_score_avg = float(sum(risk_vals) / len(risk_vals))
        historical_risk_score_max = float(max(risk_vals))
    else:
        historical_risk_score_avg = current_risk
        historical_risk_score_max = current_risk

    return {
        "login_count_24h": float(login_ok_24),
        "login_count_7d": float(login_ok_7),
        "unique_ip_count_24h": float(uniq_ip_24),
        "unique_device_count_7d": float(uniq_dev_7),
        "avg_session_duration": avg_session_duration,
        "refresh_rate_per_hour": refresh_rate_per_hour,
        "failed_login_ratio": failed_login_ratio,
        "geo_distance_variance": geo_distance_variance,
        "time_of_day_entropy": time_of_day_entropy,
        "device_trust_distribution": device_trust_distribution,
        "historical_risk_score_avg": historical_risk_score_avg,
        "historical_risk_score_max": historical_risk_score_max,
    }
