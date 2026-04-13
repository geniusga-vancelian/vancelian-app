"""
Features login / refresh pour le moteur hybride fraude (signaux explicables).

Lecture seule sur ``auth_security_events``, profils device, réputation, score global.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import (
    AuthDeviceReputation,
    AuthGlobalRiskScore,
    AuthSecurityEvent,
    AuthSession,
    AuthUserDeviceProfile,
)

logger = logging.getLogger("arquantix.security.ml.login_features")

LOGIN_SUCCESS_TYPES: Tuple[str, ...] = (
    "auth.login.succeeded",
    "auth.mobile_login.otp.succeeded",
    "auth.passkey.login.succeeded",
)
LOGIN_FAIL_TYPES: Tuple[str, ...] = (
    "auth.login.failed",
    "auth.mobile_login.otp.verify_failed",
    "auth.passkey.login.failed",
)
REFRESH_OK = "auth.refresh.succeeded"
ATTEST_FAIL = "auth.device.attestation_failed"
STEP_UP_ACTION = "auth.security.action.step_up"
FP_CHANGED = "auth.device.fingerprint_changed"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _count_events(
    db: Session,
    user_id: int,
    *,
    since: datetime,
    event_types: Sequence[str],
) -> int:
    return int(
        db.execute(
            select(func.count())
            .select_from(AuthSecurityEvent)
            .where(
                AuthSecurityEvent.user_id == user_id,
                AuthSecurityEvent.created_at >= since,
                AuthSecurityEvent.event_type.in_(list(event_types)),
            )
        ).scalar_one()
        or 0
    )


def _distinct_ips_24h(db: Session, user_id: int, *, now: datetime) -> int:
    t24 = now - timedelta(hours=24)
    return int(
        db.execute(
            select(func.count(func.distinct(AuthSecurityEvent.ip_address))).where(
                AuthSecurityEvent.user_id == user_id,
                AuthSecurityEvent.created_at >= t24,
                AuthSecurityEvent.ip_address.isnot(None),
            )
        ).scalar_one()
        or 0
    )


def _distinct_devices_24h(db: Session, user_id: int, *, now: datetime) -> int:
    t24 = now - timedelta(hours=24)
    return int(
        db.execute(
            select(func.count(func.distinct(AuthSecurityEvent.device_id))).where(
                AuthSecurityEvent.user_id == user_id,
                AuthSecurityEvent.created_at >= t24,
            )
        ).scalar_one()
        or 0
    )


def _distinct_countries_24h(db: Session, user_id: int, *, now: datetime) -> int:
    """Pays distincts depuis metadata (geo_country / country) sur événements récents."""
    t24 = now - timedelta(hours=24)
    rows = db.execute(
        select(AuthSecurityEvent.metadata_payload).where(
            AuthSecurityEvent.user_id == user_id,
            AuthSecurityEvent.created_at >= t24,
        )
    ).all()
    countries: set[str] = set()
    for (meta,) in rows:
        if not isinstance(meta, dict):
            continue
        for k in ("geo_country", "country", "geoCountry"):
            v = meta.get(k)
            if isinstance(v, str) and v.strip():
                countries.add(v.strip().upper()[:8])
    prof_rows = (
        db.query(AuthUserDeviceProfile.last_country)
        .filter(
            AuthUserDeviceProfile.user_id == user_id,
            AuthUserDeviceProfile.last_seen_at >= t24,
            AuthUserDeviceProfile.last_country.isnot(None),
        )
        .distinct()
        .all()
    )
    for (c,) in prof_rows:
        if c:
            countries.add(str(c).strip().upper()[:8])
    return len(countries)


def _new_device_recently(
    db: Session,
    user_id: int,
    device_hash: Optional[str],
    *,
    now: datetime,
) -> float:
    if not device_hash:
        return 0.0
    prof = (
        db.query(AuthUserDeviceProfile)
        .filter(
            AuthUserDeviceProfile.user_id == user_id,
            AuthUserDeviceProfile.device_hash == device_hash[:64],
        )
        .first()
    )
    if prof is None:
        return 1.0
    fs = prof.first_seen_at
    if fs.tzinfo is None:
        fs = fs.replace(tzinfo=timezone.utc)
    if (now - fs) <= timedelta(hours=24):
        return 1.0
    return 0.0


def _fingerprint_change_recently(db: Session, user_id: int, *, now: datetime) -> float:
    t24 = now - timedelta(hours=24)
    n = int(
        db.execute(
            select(func.count())
            .select_from(AuthSecurityEvent)
            .where(
                AuthSecurityEvent.user_id == user_id,
                AuthSecurityEvent.created_at >= t24,
                AuthSecurityEvent.event_type == FP_CHANGED,
            )
        ).scalar_one()
        or 0
    )
    return 1.0 if n > 0 else 0.0


def _session_velocity(db: Session, user_id: int, *, now: datetime) -> float:
    t1 = now - timedelta(hours=1)
    return float(
        db.execute(
            select(func.count())
            .select_from(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.created_at >= t1)
        ).scalar_one()
        or 0
    )


def _refresh_velocity_1h(db: Session, user_id: int, *, now: datetime) -> float:
    t1 = now - timedelta(hours=1)
    return float(
        _count_events(db, user_id, since=t1, event_types=(REFRESH_OK,))
    )


def _attestation_fail_recently(db: Session, user_id: int, *, now: datetime) -> float:
    t24 = now - timedelta(hours=24)
    n = _count_events(db, user_id, since=t24, event_types=(ATTEST_FAIL,))
    return 1.0 if n > 0 else 0.0


def _step_up_events_recently(db: Session, user_id: int, *, now: datetime) -> float:
    t7 = now - timedelta(days=7)
    n = _count_events(db, user_id, since=t7, event_types=(STEP_UP_ACTION,))
    return float(min(50, n))


def _otp_fail_then_success_multi_device_1h(db: Session, user_id: int, *, now: datetime) -> float:
    t1 = now - timedelta(hours=1)
    fails = (
        db.query(AuthSecurityEvent.device_id)
        .filter(
            AuthSecurityEvent.user_id == user_id,
            AuthSecurityEvent.created_at >= t1,
            AuthSecurityEvent.event_type == "auth.mobile_login.otp.verify_failed",
        )
        .distinct()
        .all()
    )
    oks = (
        db.query(AuthSecurityEvent.device_id)
        .filter(
            AuthSecurityEvent.user_id == user_id,
            AuthSecurityEvent.created_at >= t1,
            AuthSecurityEvent.event_type == "auth.mobile_login.otp.succeeded",
        )
        .distinct()
        .all()
    )
    if not fails or not oks:
        return 0.0
    dev_fail = {d[0] for d in fails if d[0]}
    dev_ok = {d[0] for d in oks if d[0]}
    if not dev_fail or not dev_ok:
        return 0.0
    if dev_fail != dev_ok:
        return 1.0
    return 0.0


def build_login_feature_vector(
    db: Session,
    user_id: int,
    *,
    session_id: Optional[Any] = None,
    device_hash: Optional[str] = None,
    ip: Optional[str] = None,
    now: Optional[datetime] = None,
) -> Dict[str, float]:
    """
    Vecteur minimal pour login / refresh (floats, explicables).

    ``ip`` réservé pour extensions (géo IP) ; actuellement non requis pour les agrégats.
    """
    _ = ip  # future: IP reputation side-channel
    now = now or _utcnow()
    t1 = now - timedelta(hours=1)
    t24 = now - timedelta(hours=24)

    login_count_1h = float(_count_events(db, user_id, since=t1, event_types=LOGIN_SUCCESS_TYPES))
    login_count_24h = float(_count_events(db, user_id, since=t24, event_types=LOGIN_SUCCESS_TYPES))
    failed_login_count_1h = float(_count_events(db, user_id, since=t1, event_types=LOGIN_FAIL_TYPES))

    new_dev = _new_device_recently(db, user_id, device_hash, now=now)
    fp_chg = _fingerprint_change_recently(db, user_id, now=now)
    uniq_country = float(_distinct_countries_24h(db, user_id, now=now))
    uniq_ip = float(_distinct_ips_24h(db, user_id, now=now))
    uniq_dev_24h = float(_distinct_devices_24h(db, user_id, now=now))

    refresh_v = _refresh_velocity_1h(db, user_id, now=now)
    sess_v = _session_velocity(db, user_id, now=now)

    rep_score = 0.0
    if device_hash:
        row = db.get(AuthDeviceReputation, device_hash[:64])
        if row is not None:
            rep_score = float(row.global_risk_score or 0)

    g_row = db.get(AuthGlobalRiskScore, user_id)
    global_risk = float(g_row.score) if g_row is not None else 0.0

    att_fail = _attestation_fail_recently(db, user_id, now=now)
    step_up_n = _step_up_events_recently(db, user_id, now=now)

    otp_pattern = _otp_fail_then_success_multi_device_1h(db, user_id, now=now)

    _ = session_id  # réservé : corrélation refresh par session (metadata à standardiser)

    out: Dict[str, float] = {
        "login_count_1h": login_count_1h,
        "login_count_24h": login_count_24h,
        "failed_login_count_1h": failed_login_count_1h,
        "new_device_recently": new_dev,
        "fingerprint_change_recently": fp_chg,
        "unique_country_count_24h": uniq_country,
        "unique_ip_count_24h": uniq_ip,
        "unique_device_count_24h": uniq_dev_24h,
        "refresh_velocity": refresh_v,
        "session_velocity": sess_v,
        "device_reputation_score": rep_score,
        "global_risk_score": global_risk,
        "attestation_fail_recently": att_fail,
        "step_up_events_recently": step_up_n,
        "otp_fail_then_success_new_device": otp_pattern,
    }
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            "login_fraud_features user_id=%s keys=%s",
            user_id,
            {k: round(v, 4) for k, v in out.items()},
        )
    return out
