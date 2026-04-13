"""PR F.7.2 — scoring anomalies temporelles (explainable, sans ML externe)."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Request
from sqlalchemy.orm import Session

from database import AuthUserTemporalFeatures
from services.auth.device_risk_engine_pr_f import RiskEvaluationContext
from services.auth.device_risk_engine_pr_f3 import infer_risk_action_type
from services.auth.device_risk_temporal_features import extract_temporal_features, get_last_action_before_now
from services.security.security_env import (
    device_risk_ml_safe_update_threshold,
    device_risk_temporal_min_samples,
    device_risk_temporal_weight,
    is_device_risk_temporal_enabled,
)

logger = logging.getLogger("arquantix.auth.device_risk_temporal_engine")

_HOUR_PROB_TH = 0.04
_WDAY_PROB_TH = 0.06
_TRANSITION_RARE_TH = 0.07
_DRIFT_RATIO_TH = 0.45

_POINTS_HOUR = 12
_POINTS_WDAY = 10
_POINTS_TRANSITION = 14
_POINTS_DRIFT = 12
_MAX_RAW = 40

_EMA_ALPHA = 0.15


def _norm_merge(old: Dict[str, float], new: Dict[str, float], keys: List[str]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for k in keys:
        o = float(old.get(k, 0) or 0)
        n = float(new.get(k, 0) or 0)
        out[k] = _EMA_ALPHA * n + (1.0 - _EMA_ALPHA) * o
    s = sum(out.values())
    if s <= 0:
        return {k: 1.0 / len(keys) for k in keys} if keys else {}
    return {k: float(out[k]) / s for k in keys}


def compute_temporal_risk_score(
    current: Dict[str, Any],
    baseline: Optional[Dict[str, Any]],
    *,
    ctx: RiskEvaluationContext,
    request: Request,
    db: Session,
    user_id: int,
) -> Tuple[int, List[str]]:
    """Score brut 0–40 + raisons (voir seuils internes)."""
    reasons: List[str] = []
    if not baseline:
        return 0, reasons

    total = int(current.get("total_samples_30d") or 0)
    if total < device_risk_temporal_min_samples():
        return 0, reasons

    score_f = 0.0

    ch = ctx.current_hour_utc
    if ch is not None:
        hd = baseline.get("hour_distribution") or {}
        if isinstance(hd, dict):
            p = float(hd.get(str(int(ch)), 0) or 0)
            if p < _HOUR_PROB_TH:
                score_f += _POINTS_HOUR
                reasons.append("temporal_hour_anomaly")

    wd = ctx.weekday_utc
    if wd is not None:
        wdd = baseline.get("weekday_distribution") or {}
        if isinstance(wdd, dict):
            p = float(wdd.get(str(int(wd)), 0) or 0)
            if p < _WDAY_PROB_TH:
                score_f += _POINTS_WDAY
                reasons.append("temporal_weekday_anomaly")

    prev = get_last_action_before_now(db, user_id)
    cur = infer_risk_action_type(request)
    if prev:
        key = f"{prev}->{cur}"
        tm = baseline.get("action_transition_matrix") or {}
        if isinstance(tm, dict):
            p = float(tm.get(key, 0) or 0)
            if p < _TRANSITION_RARE_TH:
                score_f += _POINTS_TRANSITION
                reasons.append("temporal_transition_anomaly")

    cur_rate = float(current.get("activity_rate_7d") or 0)
    br = baseline.get("activity_rate_ema")
    if isinstance(br, (int, float)) and float(br) > 1e-6:
        ratio = abs(cur_rate - float(br)) / max(float(br), 0.01)
        if ratio > _DRIFT_RATIO_TH:
            score_f += _POINTS_DRIFT
            reasons.append("temporal_drift_detected")

    raw = min(_MAX_RAW, int(round(score_f)))
    return raw, reasons


def _snapshot_to_baseline(row: AuthUserTemporalFeatures) -> Dict[str, Any]:
    return {
        "hour_distribution": row.hour_distribution if isinstance(row.hour_distribution, dict) else {},
        "weekday_distribution": row.weekday_distribution if isinstance(row.weekday_distribution, dict) else {},
        "action_transition_matrix": row.action_transition_matrix
        if isinstance(row.action_transition_matrix, dict)
        else {},
        "activity_rate_ema": float(row.activity_rate_ema or 0),
    }


def persist_user_temporal_features(
    db: Session,
    user_id: int,
    snapshot: Dict[str, Any],
    *,
    allow_update: bool,
) -> None:
    if not allow_update:
        return

    hour_keys = [str(h) for h in range(24)]
    wd_keys = [str(d) for d in range(7)]

    cur_h = snapshot.get("hour_distribution") or {}
    cur_w = snapshot.get("weekday_distribution") or {}
    cur_t = snapshot.get("action_transition_matrix") or {}
    rate = float(snapshot.get("activity_rate_7d") or 0)
    n_events = int(snapshot.get("total_samples_30d") or 0)

    row = db.get(AuthUserTemporalFeatures, user_id)
    if row is None:
        h = {k: float(cur_h.get(k, 0) or 0) for k in hour_keys}
        w = {k: float(cur_w.get(k, 0) or 0) for k in wd_keys}
        sh, sw = sum(h.values()), sum(w.values())
        if sh > 0:
            h = {k: h[k] / sh for k in hour_keys}
        if sw > 0:
            w = {k: w[k] / sw for k in wd_keys}
        tm = dict(cur_t) if isinstance(cur_t, dict) else {}
        feat = AuthUserTemporalFeatures(
            user_id=user_id,
            hour_distribution=h,
            weekday_distribution=w,
            action_transition_matrix=tm,
            ema_activity_drift=0.0,
            activity_rate_ema=rate,
            sample_count=max(1, n_events),
        )
        db.add(feat)
        db.flush()
        return

    new_h = _norm_merge(
        row.hour_distribution if isinstance(row.hour_distribution, dict) else {},
        cur_h if isinstance(cur_h, dict) else {},
        hour_keys,
    )
    new_w = _norm_merge(
        row.weekday_distribution if isinstance(row.weekday_distribution, dict) else {},
        cur_w if isinstance(cur_w, dict) else {},
        wd_keys,
    )
    old_tm = row.action_transition_matrix if isinstance(row.action_transition_matrix, dict) else {}
    cur_td = cur_t if isinstance(cur_t, dict) else {}
    keys_t = set(old_tm.keys()) | set(cur_td.keys())
    merged_tm: Dict[str, float] = {}
    for k in keys_t:
        merged_tm[k] = _EMA_ALPHA * float(cur_td.get(k, 0) or 0) + (1.0 - _EMA_ALPHA) * float(
            old_tm.get(k, 0) or 0
        )
    ts = sum(merged_tm.values())
    if ts > 0:
        merged_tm = {k: merged_tm[k] / ts for k in merged_tm}

    prev_rate = float(row.activity_rate_ema or rate)
    new_rate_ema = _EMA_ALPHA * rate + (1.0 - _EMA_ALPHA) * prev_rate
    drift_meas = abs(rate - prev_rate) / max(prev_rate, 0.01)
    prev_drift = float(row.ema_activity_drift or 0)
    new_drift = _EMA_ALPHA * drift_meas + (1.0 - _EMA_ALPHA) * prev_drift

    row.hour_distribution = new_h
    row.weekday_distribution = new_w
    row.action_transition_matrix = merged_tm
    row.activity_rate_ema = new_rate_ema
    row.ema_activity_drift = new_drift
    row.sample_count = max(int(row.sample_count or 0), n_events)
    db.flush()


def apply_temporal_risk_overlay(
    db: Session,
    *,
    user_id: int,
    request: Request,
    ctx: RiskEvaluationContext,
    score_after_ml: int,
    risk_reasons: List[str],
) -> int:
    if not is_device_risk_temporal_enabled():
        return score_after_ml

    current = extract_temporal_features(db, user_id)
    row = db.get(AuthUserTemporalFeatures, user_id)
    baseline: Optional[Dict[str, Any]] = None
    if row is not None:
        baseline = _snapshot_to_baseline(row)

    raw, treasons = compute_temporal_risk_score(
        current,
        baseline,
        ctx=ctx,
        request=request,
        db=db,
        user_id=user_id,
    )

    w = device_risk_temporal_weight()
    added = int(round(min(_MAX_RAW, raw) * w))
    new_score = min(100, score_after_ml + added)
    risk_reasons.extend(treasons)

    safe_thr = device_risk_ml_safe_update_threshold()
    allow_ema = score_after_ml < safe_thr

    if not allow_ema:
        risk_reasons.append("temporal_ema_frozen_high_risk")
        logger.info(
            "device_risk_temporal_ema_frozen",
            extra={
                "event": "device_risk_temporal_ema_frozen",
                "user_id": user_id,
                "score_after_ml": score_after_ml,
                "threshold": safe_thr,
            },
        )
    else:
        persist_user_temporal_features(db, user_id, current, allow_update=True)

    logger.info(
        "device_risk_temporal_evaluated",
        extra={
            "event": "device_risk_temporal_evaluated",
            "user_id": user_id,
            "temporal_raw": raw,
            "temporal_score": added,
            "temporal_added": added,
            "temporal_reasons": treasons,
            "ema_updated": allow_ema,
        },
    )
    return new_score
