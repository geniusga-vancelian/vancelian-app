"""
Stockage en mémoire des événements risque pour le dashboard produit (Phase 5).

Limites : un seul processus API — en cluster, prévoir Redis / agrégation externe plus tard.
"""
from __future__ import annotations

import threading
import time
from collections import Counter, deque
from dataclasses import dataclass
from typing import Any, Deque, Dict, List, Optional, Sequence

_MAX_EVAL_EVENTS = 20_000
_MAX_FEEDBACK_EVENTS = 5_000


@dataclass
class RiskEvalSnapshot:
    ts: float
    action_key: str
    risk_score: float
    risk_level: str
    recommended_outcome: str
    user_segment: str
    factor_codes: List[str]
    experiment_id: Optional[str]
    variant: str
    calibration_version: str
    behavioral_anomaly: bool


@dataclass
class FeedbackSnapshot:
    ts: float
    feedback_type: str
    factor_codes: List[str]
    action_key: str


_lock = threading.Lock()
_eval_events: Deque[RiskEvalSnapshot] = deque(maxlen=_MAX_EVAL_EVENTS)
_feedback_events: Deque[FeedbackSnapshot] = deque(maxlen=_MAX_FEEDBACK_EVENTS)


def record_risk_evaluation_event(
    *,
    action_key: str,
    risk_score: float,
    risk_level: str,
    recommended_outcome: str,
    user_segment: str,
    factors: Sequence[Any],
    experiment_id: Optional[str],
    variant: str,
    calibration_version: str,
    behavioral_flags: Sequence[str],
) -> None:
    codes = [getattr(f, "code", str(f)) for f in factors]
    snap = RiskEvalSnapshot(
        ts=time.time(),
        action_key=(action_key or "")[:128],
        risk_score=float(risk_score),
        risk_level=(risk_level or "")[:32],
        recommended_outcome=(recommended_outcome or "")[:32],
        user_segment=(user_segment or "normal_user")[:64],
        factor_codes=[str(c) for c in codes if c],
        experiment_id=(experiment_id or None),
        variant=(variant or "control")[:32],
        calibration_version=(calibration_version or "1")[:32],
        behavioral_anomaly=bool(behavioral_flags),
    )
    with _lock:
        _eval_events.append(snap)


def record_risk_feedback_snapshot(
    *,
    feedback_type: str,
    factor_codes: Sequence[str],
    action_key: str,
) -> None:
    snap = FeedbackSnapshot(
        ts=time.time(),
        feedback_type=(feedback_type or "")[:64],
        factor_codes=[str(x) for x in factor_codes if x],
        action_key=(action_key or "")[:128],
    )
    with _lock:
        _feedback_events.append(snap)


def get_eval_snapshots_copy() -> List[RiskEvalSnapshot]:
    with _lock:
        return list(_eval_events)


def get_feedback_snapshots_copy() -> List[FeedbackSnapshot]:
    with _lock:
        return list(_feedback_events)


def _filter_window(snapshots: Sequence[Any], window_seconds: float) -> List[Any]:
    cutoff = time.time() - window_seconds
    return [s for s in snapshots if s.ts >= cutoff]


def aggregate_summary(window_hours: float = 24.0) -> Dict[str, Any]:
    ws = window_hours * 3600.0
    evs = _filter_window(get_eval_snapshots_copy(), ws)
    n = len(evs)
    if n == 0:
        return {
            "window_hours": window_hours,
            "sample_size": 0,
            "avg_risk_score": None,
            "distribution": {"low": 0, "medium": 0, "high": 0, "critical": 0},
            "step_up_rate": None,
            "reauth_rate": None,
            "allow_rate": None,
            "anomaly_detection_rate": None,
        }
    scores = [e.risk_score for e in evs]
    dist = Counter(e.risk_level for e in evs)
    outc = Counter(e.recommended_outcome for e in evs)
    anomalies = sum(1 for e in evs if e.behavioral_anomaly)
    return {
        "window_hours": window_hours,
        "sample_size": n,
        "avg_risk_score": round(sum(scores) / n, 2),
        "distribution": {
            "low": dist.get("low", 0),
            "medium": dist.get("medium", 0),
            "high": dist.get("high", 0),
            "critical": dist.get("critical", 0),
        },
        "step_up_rate": round(outc.get("step_up", 0) / n, 4),
        "reauth_rate": round(outc.get("reauth", 0) / n, 4),
        "allow_rate": round(outc.get("allow", 0) / n, 4),
        "anomaly_detection_rate": round(anomalies / n, 4),
    }


def aggregate_factors(window_hours: float = 24.0) -> Dict[str, Any]:
    ws = window_hours * 3600.0
    evs = _filter_window(get_eval_snapshots_copy(), ws)
    freq: Counter[str] = Counter()
    for e in evs:
        for f in e.factor_codes:
            freq[f] += 1
    top_freq = freq.most_common(25)
    fbs = _filter_window(get_feedback_snapshots_copy(), ws)
    fraud_codes: Counter[str] = Counter()
    fp_codes: Counter[str] = Counter()
    for fb in fbs:
        if fb.feedback_type in ("fraud_confirmed", "fraud_suspected"):
            for c in fb.factor_codes:
                fraud_codes[c] += 1
        if fb.feedback_type == "false_positive":
            for c in fb.factor_codes:
                fp_codes[c] += 1
    return {
        "window_hours": window_hours,
        "eval_sample_size": len(evs),
        "feedback_sample_size": len(fbs),
        "top_factors_by_frequency": [{"factor_code": k, "count": v} for k, v in top_freq],
        "top_factors_in_fraud_feedback": fraud_codes.most_common(15),
        "top_factors_in_false_positive_feedback": fp_codes.most_common(15),
        "fraud_feedback_rate": (
            round(
                sum(1 for f in fbs if f.feedback_type in ("fraud_confirmed", "fraud_suspected")) / len(fbs),
                4,
            )
            if fbs
            else None
        ),
        "false_positive_rate": (
            round(sum(1 for f in fbs if f.feedback_type == "false_positive") / len(fbs), 4) if fbs else None
        ),
    }


def aggregate_segments(window_hours: float = 24.0) -> Dict[str, Any]:
    ws = window_hours * 3600.0
    evs = _filter_window(get_eval_snapshots_copy(), ws)
    by_seg: Dict[str, List[RiskEvalSnapshot]] = {}
    for e in evs:
        by_seg.setdefault(e.user_segment, []).append(e)
    out: Dict[str, Any] = {}
    for seg, lst in sorted(by_seg.items()):
        n = len(lst)
        scores = [x.risk_score for x in lst]
        oc = Counter(x.recommended_outcome for x in lst)
        out[seg] = {
            "sample_size": n,
            "avg_risk_score": round(sum(scores) / n, 2) if n else None,
            "allow_rate": round(oc.get("allow", 0) / n, 4) if n else None,
            "step_up_rate": round(oc.get("step_up", 0) / n, 4) if n else None,
            "reauth_rate": round(oc.get("reauth", 0) / n, 4) if n else None,
        }
    return {"window_hours": window_hours, "by_segment": out}


def aggregate_experiments(window_hours: float = 24.0) -> Dict[str, Any]:
    ws = window_hours * 3600.0
    evs = _filter_window(get_eval_snapshots_copy(), ws)
    by_var: Dict[tuple, List[RiskEvalSnapshot]] = {}
    for e in evs:
        if not e.experiment_id:
            continue
        key = (e.experiment_id, e.variant)
        by_var.setdefault(key, []).append(e)
    rows = []
    for (exp_id, variant), lst in sorted(by_var.items(), key=lambda x: (x[0][0], x[0][1])):
        n = len(lst)
        oc = Counter(x.recommended_outcome for x in lst)
        rows.append(
            {
                "experiment_id": exp_id,
                "variant": variant,
                "sample_size": n,
                "allow_rate": round(oc.get("allow", 0) / n, 4) if n else None,
                "step_up_rate": round(oc.get("step_up", 0) / n, 4) if n else None,
                "reauth_rate": round(oc.get("reauth", 0) / n, 4) if n else None,
                "avg_risk_score": round(sum(x.risk_score for x in lst) / n, 2) if n else None,
                "critical_level_rate": round(sum(1 for x in lst if x.risk_level == "critical") / n, 4) if n else None,
            }
        )
    return {"window_hours": window_hours, "variants": rows}


def compute_alerts(window_hours: float = 24.0) -> Dict[str, Any]:
    """Seuils simples — pas d’historique long (MVP)."""
    import os

    summary = aggregate_summary(window_hours=window_hours)
    alerts: List[Dict[str, Any]] = []
    try:
        reauth_thr = float(os.getenv("RISK_DASHBOARD_ALERT_REAUTH_RATE_GT", "0.35"))
    except ValueError:
        reauth_thr = 0.35
    try:
        fraud_thr = float(os.getenv("RISK_DASHBOARD_ALERT_FRAUD_FEEDBACK_RATE_GT", "0.15"))
    except ValueError:
        fraud_thr = 0.15
    try:
        anom_thr = float(os.getenv("RISK_DASHBOARD_ALERT_ANOMALY_RATE_GT", "0.30"))
    except ValueError:
        anom_thr = 0.30

    n = summary.get("sample_size") or 0
    if n >= 20:
        rr = summary.get("reauth_rate")
        if rr is not None and rr >= reauth_thr:
            alerts.append(
                {
                    "id": "spike_reauth",
                    "severity": "warning",
                    "message": f"Taux de reauth élevé ({rr:.1%} ≥ {reauth_thr:.0%}) sur la fenêtre.",
                }
            )
        ar = summary.get("anomaly_detection_rate")
        if ar is not None and ar >= anom_thr:
            alerts.append(
                {
                    "id": "surge_behavioral_anomaly",
                    "severity": "warning",
                    "message": f"Part d’anomalies comportementales élevée ({ar:.1%} ≥ {anom_thr:.0%}).",
                }
            )

    fac = aggregate_factors(window_hours=window_hours)
    fr = fac.get("fraud_feedback_rate")
    if fr is not None and fac.get("feedback_sample_size", 0) >= 10 and fr >= fraud_thr:
        alerts.append(
            {
                "id": "spike_fraud_feedback",
                "severity": "critical",
                "message": f"Taux de feedbacks fraude élevé ({fr:.1%} ≥ {fraud_thr:.0%}).",
            }
        )

    return {"window_hours": window_hours, "alerts": alerts, "thresholds": {"reauth_rate": reauth_thr, "fraud_feedback_rate": fraud_thr, "anomaly_rate": anom_thr}}


def recent_decisions(limit: int = 50) -> List[Dict[str, Any]]:
    evs = get_eval_snapshots_copy()
    evs.sort(key=lambda x: x.ts, reverse=True)
    out = []
    for e in evs[:limit]:
        out.append(
            {
                "ts": e.ts,
                "action_key": e.action_key,
                "risk_score": e.risk_score,
                "risk_level": e.risk_level,
                "recommended_outcome": e.recommended_outcome,
                "user_segment": e.user_segment,
                "variant": e.variant,
                "experiment_id": e.experiment_id,
                "behavioral_anomaly": e.behavioral_anomaly,
                "factor_codes": e.factor_codes[:20],
            }
        )
    return out
