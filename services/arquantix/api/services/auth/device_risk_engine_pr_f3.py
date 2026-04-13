"""PR F.3 — baseline temporelle avancée (attaques lentes / mimétiques)."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Request
from sqlalchemy.orm import Session

from database import AuthSession, AuthUserRiskBaseline
from services.auth.device_risk_engine_pr_f import RiskEvaluationContext
from services.auth.device_risk_engine_pr_f2 import _get_or_create_baseline
from services.security.security_env import (
    device_risk_advanced_baseline_min_samples,
    device_risk_baseline_time_weight,
    is_device_risk_advanced_baseline_enabled,
)


def infer_risk_action_type(request: Request) -> str:
    """Libellé stable pour ``last_10_actions_types`` (routes sensibles PR F)."""
    path = (request.url.path or "").lower()
    if "internal-transfer" in path:
        return "wallet_transfer"
    if "simulate-withdrawal" in path or ("webhook-events" in path and "replay" in path):
        return "withdrawal"
    if "accounts/client" in path or "simple-create" in path or "canonical" in path:
        return "beneficiary_add"
    if "auth/login" in path or path.endswith("/login"):
        return "login"
    if "refresh" in path and "auth" in path:
        return "refresh"
    return "sensitive_other"


def _welford_append(inner: Optional[Dict[str, Any]], x: float) -> Dict[str, Any]:
    state = inner or {}
    n = int(state.get("n") or 0)
    mean = float(state.get("mean") or 0.0)
    m2 = float(state.get("m2") or 0.0)
    n += 1
    delta = x - mean
    mean = mean + delta / n
    delta2 = x - mean
    m2 = m2 + delta * delta2
    return {"n": n, "mean": mean, "m2": m2}


def _welford_std(n: int, m2: float) -> float:
    if n < 2:
        return 1.5
    v = m2 / max(1, n - 1)
    return max(0.8, math.sqrt(max(0.0, v)))


def _weekday_distance(a: float, b: float) -> float:
    """Distance circulaire sur 0..6 (lun..dim)."""
    d = abs(a - b)
    return min(d, 7.0 - d)


def baseline_temporal_anomaly_score(
    db: Session,
    *,
    user_id: int,
    ctx: RiskEvaluationContext,
) -> Tuple[int, List[str]]:
    """
    Détection d’anomalie vs baseline apprise (heure, jour, durée session, fréquence, type d’action).

    Pénalités bornées ; ``std`` effectif = max(std stocké, epsilon) pour éviter explosion si peu de données.
    """
    if not is_device_risk_advanced_baseline_enabled():
        return 0, []

    if ctx.current_hour_utc is None or ctx.weekday_utc is None:
        return 0, []

    row = _get_or_create_baseline(db, user_id)
    if int(row.baseline_sample_count or 0) < device_risk_advanced_baseline_min_samples():
        return 0, []

    w = float(device_risk_baseline_time_weight())
    if w <= 0:
        return 0, []

    bonus = 0
    reasons: List[str] = []

    eps_h = max(float(row.std_hour_of_day or 1.5), 1.5)
    if row.avg_hour_of_day is not None:
        if abs(float(ctx.current_hour_utc) - float(row.avg_hour_of_day)) > 2.0 * eps_h:
            bonus += int(round(15 * w))
            reasons.append("baseline_time_anomaly")

    eps_wd = max(float(row.std_weekday or 1.0), 1.0)
    if row.avg_weekday is not None:
        dist = _weekday_distance(float(ctx.weekday_utc), float(row.avg_weekday))
        if dist > 2.0 * eps_wd:
            bonus += int(round(10 * w))
            reasons.append("baseline_weekday_anomaly")

    if ctx.session_duration_sec is not None and row.avg_session_duration_sec is not None:
        avg_sd = max(30.0, float(row.avg_session_duration_sec))
        std_sd = max(float(row.std_session_duration_sec or 60.0), 15.0)
        cur = float(ctx.session_duration_sec)
        if cur > avg_sd + 2.0 * std_sd and cur > avg_sd * 2.2:
            bonus += int(round(10 * w))
            reasons.append("baseline_session_duration_anomaly")

    ema_act = float(row.actions_per_hour_ema or 0.0)
    if ema_act > 0.1 and float(ctx.velocity_count) > max(4.0, ema_act * 2.5 + 2.0):
        bonus += int(round(15 * w))
        reasons.append("baseline_behavior_anomaly")

    raw_actions = row.last_10_actions_types
    recent: List[str] = []
    if isinstance(raw_actions, list):
        recent = [str(x) for x in raw_actions]
    at = (ctx.action_type or "unknown").strip() or "unknown"
    if recent and at != "unknown":
        if at not in recent:
            bonus += int(round(10 * w))
            reasons.append("baseline_behavior_anomaly")
        elif recent.count(at) <= 1 and len(recent) >= 6:
            bonus += int(round(5 * w))
            reasons.append("baseline_behavior_anomaly")

    out = min(55, bonus)
    uniq = list(dict.fromkeys(reasons))
    return out, uniq


def _sync_welford_columns(row: AuthUserRiskBaseline, wf: Dict[str, Any]) -> None:
    h = wf.get("hour")
    if isinstance(h, dict) and int(h.get("n") or 0) >= 1:
        hn = int(h["n"])
        row.avg_hour_of_day = float(h.get("mean") or 0.0)
        row.std_hour_of_day = _welford_std(hn, float(h.get("m2") or 0.0))
    wd = wf.get("weekday")
    if isinstance(wd, dict) and int(wd.get("n") or 0) >= 1:
        wdn = int(wd["n"])
        row.avg_weekday = float(wd.get("mean") or 0.0)
        row.std_weekday = _welford_std(wdn, float(wd.get("m2") or 0.0))
    sd = wf.get("session_sec")
    if isinstance(sd, dict) and int(sd.get("n") or 0) >= 1:
        sdn = int(sd["n"])
        row.avg_session_duration_sec = float(sd.get("mean") or 0.0)
        row.std_session_duration_sec = _welford_std(sdn, float(sd.get("m2") or 0.0))


def update_advanced_baseline_from_observation(
    db: Session,
    *,
    user_id: int,
    ctx: RiskEvaluationContext,
    request: Request,
    session: Optional[AuthSession],
    increment_sample_count: bool = True,
) -> None:
    """Met à jour Welford + last actions (uniquement appelé après décision ALLOW côté Depends)."""
    if not is_device_risk_advanced_baseline_enabled():
        return

    if ctx.current_hour_utc is None or ctx.weekday_utc is None:
        return

    row = _get_or_create_baseline(db, user_id)
    wf: Dict[str, Any] = {}
    if isinstance(row.temporal_welford_json, dict):
        wf = dict(row.temporal_welford_json)

    wf["hour"] = _welford_append(wf.get("hour") if isinstance(wf.get("hour"), dict) else None, float(ctx.current_hour_utc))
    wf["weekday"] = _welford_append(
        wf.get("weekday") if isinstance(wf.get("weekday"), dict) else None, float(ctx.weekday_utc)
    )

    dur = ctx.session_duration_sec
    if dur is not None and dur >= 0:
        wf["session_sec"] = _welford_append(
            wf.get("session_sec") if isinstance(wf.get("session_sec"), dict) else None, float(dur)
        )

    row.temporal_welford_json = wf
    _sync_welford_columns(row, wf)

    act = infer_risk_action_type(request)
    lst: List[str] = []
    if isinstance(row.last_10_actions_types, list):
        lst = [str(x) for x in row.last_10_actions_types]
    lst.insert(0, act)
    row.last_10_actions_types = lst[:10]

    if increment_sample_count:
        row.baseline_sample_count = int(row.baseline_sample_count or 0) + 1

    db.flush()
