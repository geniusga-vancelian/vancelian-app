"""PR F.7.2 — extraction de distributions temporelles depuis ``auth_user_intent_events``."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from database import AuthUserIntentEvent

_WINDOW_DAYS = 30
_TRANSITION_PAIR_LIMIT = 500


def _normalize_dist(counts: Dict[str, float]) -> Dict[str, float]:
    s = sum(counts.values())
    if s <= 0:
        return {k: 0.0 for k in counts}
    return {k: float(v) / s for k, v in counts.items()}


def extract_temporal_features(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Distributions horaires / jour / transitions sur 30 jours + débit d’activité 7 jours.

    Clés ``weekday_distribution`` : 0=lundi … 6=dimanche (aligné ``weekday_utc`` PR F).
    """
    now = datetime.now(timezone.utc)
    since_30d = now - timedelta(days=_WINDOW_DAYS)
    since_7d = now - timedelta(days=7)

    ie = AuthUserIntentEvent

    total_30d = (
        db.query(func.count(ie.id)).filter(ie.user_id == user_id, ie.created_at >= since_30d).scalar() or 0
    )

    # Heures 0–23 (UTC)
    hour_rows = db.execute(
        text(
            """
            SELECT EXTRACT(HOUR FROM created_at AT TIME ZONE 'UTC')::int AS hr, COUNT(*)::float
            FROM auth_user_intent_events
            WHERE user_id = :uid AND created_at >= :since
            GROUP BY 1
            """
        ),
        {"uid": user_id, "since": since_30d},
    ).fetchall()
    hour_counts: Dict[str, float] = {str(h): 0.0 for h in range(24)}
    for hr, c in hour_rows:
        hour_counts[str(int(hr))] = float(c)
    hour_distribution = _normalize_dist(hour_counts)

    # Jour semaine Mon=0 … Sun=6 (UTC)
    wd_rows = db.execute(
        text(
            """
            SELECT (
              CASE WHEN EXTRACT(ISODOW FROM created_at AT TIME ZONE 'UTC')::int = 7
              THEN 6 ELSE EXTRACT(ISODOW FROM created_at AT TIME ZONE 'UTC')::int - 1 END
            ) AS wd,
            COUNT(*)::float
            FROM auth_user_intent_events
            WHERE user_id = :uid AND created_at >= :since
            GROUP BY 1
            """
        ),
        {"uid": user_id, "since": since_30d},
    ).fetchall()
    wd_counts: Dict[str, float] = {str(d): 0.0 for d in range(7)}
    for wd, c in wd_rows:
        wd_counts[str(int(wd))] = float(c)
    weekday_distribution = _normalize_dist(wd_counts)

    # Transitions (ordre chronologique, fenêtre 30j)
    rows = (
        db.query(ie.action_type, ie.created_at)
        .filter(ie.user_id == user_id, ie.created_at >= since_30d)
        .order_by(ie.created_at.asc())
        .limit(_TRANSITION_PAIR_LIMIT)
        .all()
    )
    pair_counts: Dict[str, float] = {}
    prev: str | None = None
    for at, _ts in rows:
        a = (at or "unknown").strip() or "unknown"
        if prev is not None:
            key = f"{prev}->{a}"
            pair_counts[key] = pair_counts.get(key, 0.0) + 1.0
        prev = a
    transition_matrix = _normalize_dist(pair_counts) if pair_counts else {}

    n_7d = (
        db.query(func.count(ie.id)).filter(ie.user_id == user_id, ie.created_at >= since_7d).scalar() or 0
    )
    activity_rate_7d = float(n_7d) / 7.0

    return {
        "hour_distribution": hour_distribution,
        "weekday_distribution": weekday_distribution,
        "action_transition_matrix": transition_matrix,
        "activity_rate_7d": activity_rate_7d,
        "total_samples_30d": int(total_30d),
    }


def get_last_action_before_now(db: Session, user_id: int) -> str | None:
    """Dernière action enregistrée (la plus récente avant la requête courante)."""
    ie = AuthUserIntentEvent
    row = (
        db.query(ie.action_type)
        .filter(ie.user_id == user_id)
        .order_by(ie.created_at.desc())
        .first()
    )
    if row is None:
        return None
    return (row[0] or "unknown").strip() or "unknown"
