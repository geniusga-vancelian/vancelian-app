"""Moteur de corrélation sur ``auth_security_events`` (heuristiques, scores, pas de blocage)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import AuthSecurityEvent
from services.auth.security_alerting import send_security_alert
from services.auth.security_signal_service import SecuritySignalService


@dataclass
class CorrelationFinding:
    rule: str
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    detail: Dict[str, Any]


def detect_multiple_ip_sessions(
    db: Session, *, window_hours: int = 24, min_ips: int = 4, min_events: int = 3
) -> List[CorrelationFinding]:
    """Utilisateurs avec plusieurs IP distinctes sur la fenêtre."""
    since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    stmt = (
        select(AuthSecurityEvent.user_id, func.count(func.distinct(AuthSecurityEvent.ip_address)))
        .where(
            AuthSecurityEvent.user_id.isnot(None),
            AuthSecurityEvent.created_at >= since,
            AuthSecurityEvent.ip_address.isnot(None),
        )
        .group_by(AuthSecurityEvent.user_id)
        .having(func.count(func.distinct(AuthSecurityEvent.ip_address)) >= min_ips)
    )
    rows = db.execute(stmt).all()
    out: List[CorrelationFinding] = []
    for uid, n_ip in rows:
        cnt = (
            db.execute(
                select(func.count())
                .select_from(AuthSecurityEvent)
                .where(
                    AuthSecurityEvent.user_id == uid,
                    AuthSecurityEvent.created_at >= since,
                )
            ).scalar_one()
            or 0
        )
        if int(cnt) < min_events:
            continue
        sev = "HIGH" if int(n_ip) >= 8 else "MEDIUM"
        out.append(
            CorrelationFinding(
                rule="multiple_ip_sessions",
                severity=sev,
                detail={"user_id": int(uid), "distinct_ips": int(n_ip), "window_hours": window_hours},
            )
        )
    return out


def detect_device_anomaly(
    db: Session, *, window_minutes: int = 15, threshold: int = 80
) -> List[CorrelationFinding]:
    """Volume anormal d’événements par device_id."""
    since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    stmt = (
        select(AuthSecurityEvent.device_id, func.count())
        .where(AuthSecurityEvent.created_at >= since)
        .group_by(AuthSecurityEvent.device_id)
        .having(func.count() >= threshold)
    )
    rows = db.execute(stmt).all()
    out: List[CorrelationFinding] = []
    for did, n in rows:
        sev = "CRITICAL" if int(n) >= 200 else "HIGH"
        out.append(
            CorrelationFinding(
                rule="device_event_burst",
                severity=sev,
                detail={"device_id_prefix": (did or "")[:8], "count": int(n), "window_minutes": window_minutes},
            )
        )
    return out


def detect_bruteforce_pattern(
    db: Session, *, window_minutes: int = 10, threshold: int = 25
) -> List[CorrelationFinding]:
    """Nombre élevé d’échecs login / refresh rejetés par IP."""
    since = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
    types = ("auth.login.failed", "auth.refresh.rejected", "auth.passkey.login.failed")
    stmt = (
        select(AuthSecurityEvent.ip_address, func.count())
        .where(
            AuthSecurityEvent.created_at >= since,
            AuthSecurityEvent.ip_address.isnot(None),
            AuthSecurityEvent.event_type.in_(types),
        )
        .group_by(AuthSecurityEvent.ip_address)
        .having(func.count() >= threshold)
    )
    rows = db.execute(stmt).all()
    return [
        CorrelationFinding(
            rule="bruteforce_pattern",
            severity="CRITICAL" if int(n) >= 2 * threshold else "HIGH",
            detail={"ip_masked": _mask_ip_for_display(str(ip)), "count": int(n), "window_minutes": window_minutes},
        )
        for ip, n in rows
    ]


def _mask_ip_for_display(ip: str) -> str:
    if "." in ip:
        p = ip.split(".")
        return f"{p[0]}.{p[1]}.{p[2]}.*" if len(p) == 4 else ip[:8] + "…"
    return ip[:12] + "…" if len(ip) > 12 else ip


def detect_geo_jump(db: Session, *, window_hours: int = 2) -> List[CorrelationFinding]:
    """
    Saut géographique si ``metadata.country`` ou ``metadata.geo_country`` change pour un même user.
    Sans geo en base, retourne vide (extensible quand le client envoie le pays).
    """
    since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    rows = db.execute(
        select(AuthSecurityEvent.user_id, AuthSecurityEvent.metadata_payload)
        .where(
            AuthSecurityEvent.user_id.isnot(None),
            AuthSecurityEvent.created_at >= since,
        )
        .order_by(AuthSecurityEvent.created_at.desc())
        .limit(5000)
    ).all()
    by_user: Dict[int, set] = {}
    for uid, meta in rows:
        if uid is None or not isinstance(meta, dict):
            continue
        c = meta.get("country") or meta.get("geo_country")
        if not c or not isinstance(c, str):
            continue
        by_user.setdefault(int(uid), set()).add(c.strip().upper())
    out: List[CorrelationFinding] = []
    for uid, countries in by_user.items():
        if len(countries) >= 2:
            out.append(
                CorrelationFinding(
                    rule="geo_jump",
                    severity="MEDIUM",
                    detail={"user_id": uid, "countries": sorted(countries), "window_hours": window_hours},
                )
            )
    return out


def run_all_detections(db: Session) -> List[CorrelationFinding]:
    findings: List[CorrelationFinding] = []
    findings.extend(detect_bruteforce_pattern(db))
    findings.extend(detect_device_anomaly(db))
    findings.extend(detect_multiple_ip_sessions(db))
    findings.extend(detect_geo_jump(db))
    return findings


def max_severity(findings: List[CorrelationFinding]) -> str:
    order = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    best = "LOW"
    for f in findings:
        if order.index(f.severity) > order.index(best):
            best = f.severity
    return best


def evaluate_and_alert(db: Session) -> List[CorrelationFinding]:
    """Exécute les règles et envoie webhook pour HIGH/CRITICAL (une alerte agrégée max)."""
    findings = run_all_detections(db)
    if not findings:
        return findings
    top = max_severity(findings)
    high_or_critical = [f for f in findings if f.severity in ("HIGH", "CRITICAL")]
    if high_or_critical:
        send_security_alert(
            severity=top,
            title="Security correlation findings",
            body={
                "count": len(findings),
                "max_severity": top,
                "rules": [f.rule for f in high_or_critical[:20]],
            },
        )
    return findings


def quick_check_after_event(
    db: Optional[Session],
    *,
    event_type: str,
    user_id: Optional[int],
    ip_address: Optional[str],
) -> None:
    """Contrôles ciblés après persistance (léger). Ouvre une session si ``db`` est absent."""
    if not ip_address:
        return
    if event_type not in ("auth.login.failed", "auth.refresh.rejected", "auth.passkey.login.failed"):
        return

    from database import SessionLocal

    own_session = False
    sess = db
    if sess is None:
        sess = SessionLocal()
        own_session = True
    try:
        since = datetime.now(timezone.utc) - timedelta(minutes=5)
        q = select(func.count()).select_from(AuthSecurityEvent).where(
            AuthSecurityEvent.ip_address == ip_address[:45],
            AuthSecurityEvent.created_at >= since,
            AuthSecurityEvent.event_type.in_(
                ("auth.login.failed", "auth.refresh.rejected", "auth.passkey.login.failed")
            ),
        )
        n = int(sess.execute(q).scalar_one() or 0)
        if n >= 40:
            send_security_alert(
                severity="CRITICAL",
                title="Possible brute-force burst",
                body={"ip_masked": _mask_ip_for_display(ip_address), "failures_5m": n},
            )
    finally:
        if own_session:
            sess.close()


def user_risk_profile(db: Session, user_id: int, *, window_hours: int = 168) -> Tuple[str, List[CorrelationFinding], int]:
    since = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    n = int(
        db.execute(
            select(func.count())
            .select_from(AuthSecurityEvent)
            .where(AuthSecurityEvent.user_id == user_id, AuthSecurityEvent.created_at >= since)
        ).scalar_one()
        or 0
    )
    findings: List[CorrelationFinding] = []
    stmt = (
        select(func.count(func.distinct(AuthSecurityEvent.ip_address)))
        .where(
            AuthSecurityEvent.user_id == user_id,
            AuthSecurityEvent.created_at >= since,
            AuthSecurityEvent.ip_address.isnot(None),
        )
    )
    n_ip = int(db.execute(stmt).scalar_one() or 0)
    if n_ip >= 6:
        findings.append(
            CorrelationFinding(
                rule="user_multiple_ips",
                severity="HIGH" if n_ip >= 10 else "MEDIUM",
                detail={"user_id": user_id, "distinct_ips": n_ip, "window_hours": window_hours},
            )
        )
    legacy = SecuritySignalService.detect_anomalies(db)
    if legacy.get("suspicious_user") and user_id in (legacy.get("details") or {}).get("users_ip_and_fingerprint_change", []):
        findings.append(
            CorrelationFinding(
                rule="legacy_ip_fingerprint_combo",
                severity="HIGH",
                detail={"user_id": user_id},
            )
        )
    score = max_severity(findings) if findings else "LOW"
    return score, findings, n


def findings_to_dicts(findings: List[CorrelationFinding]) -> List[Dict[str, Any]]:
    return [{"rule": f.rule, "severity": f.severity, "detail": f.detail} for f in findings]
