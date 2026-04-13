"""PR F.7 — score complémentaire par écart aux habitudes (pseudo-ML / anomalies vectorielles)."""
from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from database import AuthSession, AuthSessionIntelligence, AuthUserIntentEvent, AuthUserRiskFeatures
from services.security.security_env import (
    device_risk_ml_safe_update_threshold,
    device_risk_ml_score_weight,
    is_device_risk_ml_enabled,
)

logger = logging.getLogger("arquantix.auth.device_risk_ml_engine")

FEATURE_KEYS = (
    "actions_per_hour",
    "unique_devices_24h",
    "unique_countries_24h",
    "avg_session_duration",
    "withdrawal_frequency",
    "beneficiary_add_frequency",
)

# Échelles par défaut pour z-score lorsque l’écart-type empirique n’est pas encore disponible
_SIGMA_DEFAULT: Dict[str, float] = {
    "actions_per_hour": 4.0,
    "unique_devices_24h": 2.0,
    "unique_countries_24h": 1.5,
    "avg_session_duration": 900.0,
    "withdrawal_frequency": 3.0,
    "beneficiary_add_frequency": 3.0,
}

_EMA_ALPHA = 0.25


def extract_user_risk_features(db: Session, user_id: int) -> Dict[str, float]:
    """
    Vecteur de features comportementales sur fenêtres glissantes 24h (et 1h pour le débit).
    """
    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)
    since_1h = now - timedelta(hours=1)

    # Intent events (PR F.6) — débit et fréquences métier
    ie = AuthUserIntentEvent
    n_24h = (
        db.query(func.count(ie.id))
        .filter(ie.user_id == user_id, ie.created_at >= since_24h)
        .scalar()
        or 0
    )
    n_1h = (
        db.query(func.count(ie.id)).filter(ie.user_id == user_id, ie.created_at >= since_1h).scalar() or 0
    )
    actions_per_hour = float(n_24h) / 24.0 if n_24h else float(n_1h)

    ud = (
        db.query(func.count(func.distinct(ie.device_id)))
        .filter(ie.user_id == user_id, ie.created_at >= since_24h)
        .scalar()
        or 0
    )
    unique_devices_24h = float(ud)

    w_count = (
        db.query(func.count(ie.id))
        .filter(
            ie.user_id == user_id,
            ie.created_at >= since_24h,
            ie.action_type == "withdrawal",
        )
        .scalar()
        or 0
    )
    withdrawal_frequency = float(w_count) / 24.0

    b_count = (
        db.query(func.count(ie.id))
        .filter(
            ie.user_id == user_id,
            ie.created_at >= since_24h,
            ie.action_type == "beneficiary_add",
        )
        .scalar()
        or 0
    )
    beneficiary_add_frequency = float(b_count) / 24.0

    # Pays distincts — session intelligence (dernière activité récente)
    si = AuthSessionIntelligence
    uc = (
        db.query(func.count(func.distinct(si.last_country)))
        .filter(
            si.user_id == user_id,
            si.last_activity_at >= since_24h,
            si.last_country.isnot(None),
        )
        .scalar()
        or 0
    )
    unique_countries_24h = float(uc)

    # Durée moyenne de session (sessions touchées sur 24h)
    sess_rows = (
        db.query(AuthSession.last_used_at, AuthSession.created_at)
        .filter(AuthSession.user_id == user_id, AuthSession.last_used_at >= since_24h)
        .all()
    )
    durations: list[float] = []
    for lu, cr in sess_rows:
        if lu and cr:
            durations.append(max(0.0, (lu - cr).total_seconds()))
    avg_session_duration = sum(durations) / len(durations) if durations else 0.0

    return {
        "actions_per_hour": float(actions_per_hour),
        "unique_devices_24h": unique_devices_24h,
        "unique_countries_24h": unique_countries_24h,
        "avg_session_duration": avg_session_duration,
        "withdrawal_frequency": withdrawal_frequency,
        "beneficiary_add_frequency": beneficiary_add_frequency,
    }


def compute_ml_risk_score(
    features: Dict[str, float],
    baseline: Dict[str, float],
) -> Tuple[int, float]:
    """
    z-score par dimension, distance euclidienne des z, plafonnée 0–100.

    Retourne (score_int, distance_brute).
    """
    if not features or not baseline:
        return 0, 0.0

    z_sum = 0.0
    for k in FEATURE_KEYS:
        cur = float(features.get(k, 0.0) or 0.0)
        base = float(baseline.get(k, cur) or 0.0)
        sigma = max(_SIGMA_DEFAULT.get(k, 1.0), 1e-6)
        z = (cur - base) / sigma
        z_sum += z * z

    dist = math.sqrt(z_sum)
    # Calibration : distance ~3 → score proche de 100
    raw = min(100.0, dist * 28.0)
    return int(round(raw)), dist


def _ema_update(prev: Dict[str, float], current: Dict[str, float]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for k in FEATURE_KEYS:
        c = float(current.get(k, 0.0) or 0.0)
        p = float(prev.get(k, c) or 0.0)
        out[k] = _EMA_ALPHA * c + (1.0 - _EMA_ALPHA) * p
    return out


def load_or_init_feature_payload(db: Session, user_id: int) -> Dict[str, Any]:
    row = db.get(AuthUserRiskFeatures, user_id)
    if row is None:
        return {"ema": {}, "sample_count": 0}
    payload = row.features if isinstance(row.features, dict) else {}
    return {
        "ema": dict(payload.get("ema") or {}),
        "sample_count": int(payload.get("sample_count") or 0),
    }


def persist_user_risk_features(
    db: Session,
    user_id: int,
    current: Dict[str, float],
    payload_in: Dict[str, Any],
) -> None:
    """Met à jour EMA stocké pour la prochaine comparaison."""
    ema_old = payload_in.get("ema") or {}
    if not ema_old:
        ema_new = dict(current)
    else:
        ema_new = _ema_update(ema_old, current)
    n = int(payload_in.get("sample_count") or 0) + 1
    blob: Dict[str, Any] = {
        "ema": ema_new,
        "last_vector": current,
        "sample_count": n,
    }
    row = db.get(AuthUserRiskFeatures, user_id)
    if row is None:
        row = AuthUserRiskFeatures(user_id=user_id, features=blob)
        db.add(row)
    else:
        row.features = blob
    db.flush()


def apply_ml_risk_overlay(
    db: Session,
    *,
    user_id: int,
    base_score: int,
    risk_reasons: list,
) -> Tuple[int, Optional[float]]:
    """
    Si activé : calcule un score ML 0–100, ajoute ``weight * ml_score`` au score PR F (plafond 100).

    Retourne (nouveau_score, distance_ml ou None).
    """
    if not is_device_risk_ml_enabled():
        return base_score, None

    current = extract_user_risk_features(db, user_id)
    payload = load_or_init_feature_payload(db, user_id)
    ema = payload.get("ema") or {}
    baseline: Dict[str, float] = {k: float(ema.get(k, current.get(k, 0.0)) or 0.0) for k in FEATURE_KEYS}

    ml_score, dist = compute_ml_risk_score(current, baseline)
    w = device_risk_ml_score_weight()
    added = int(round(ml_score * w))
    new_score = min(100, base_score + added)
    if added > 0:
        risk_reasons.append(f"ml_anomaly_dist:{dist:.3f}")

    safe_thr = device_risk_ml_safe_update_threshold()
    if base_score < safe_thr:
        persist_user_risk_features(db, user_id, current, payload)
    else:
        risk_reasons.append("ml_ema_frozen_high_pr_f_baseline")
        logger.info(
            "device_risk_ml_ema_frozen",
            extra={
                "event": "device_risk_ml_ema_frozen",
                "user_id": user_id,
                "pre_ml_risk_score": base_score,
                "safe_update_threshold": safe_thr,
            },
        )

    logger.debug(
        "device_risk_ml_applied",
        extra={
            "event": "device_risk_ml_applied",
            "user_id": user_id,
            "ml_score": ml_score,
            "weight": w,
            "added": added,
            "dist": dist,
            "ema_updated": base_score < safe_thr,
        },
    )
    return new_score, dist
