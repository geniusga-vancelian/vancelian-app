"""
Analyses graphe user ↔ device ↔ IP (clusters, fermes, partages).

Retours structurés pour audit ; persistance via ``persist_graph_finding``.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import AuthDeviceReputation, AuthDeviceUsageEdge
from services.security.device_reputation.device_reputation_service import persist_graph_finding

DEFAULT_WINDOW_DAYS = 30


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _window_start(days: int) -> datetime:
    return _utcnow() - timedelta(days=max(1, days))


def find_shared_devices(
    db: Session,
    *,
    min_user_count: int = 3,
    window_days: int = DEFAULT_WINDOW_DAYS,
    persist: bool = False,
) -> List[Dict[str, Any]]:
    """Devices vus avec au moins ``min_user_count`` utilisateurs distincts."""
    since = _window_start(window_days)
    stmt = (
        select(AuthDeviceUsageEdge.device_hash, func.count(func.distinct(AuthDeviceUsageEdge.user_id)))
        .where(
            AuthDeviceUsageEdge.created_at >= since,
            AuthDeviceUsageEdge.user_id.isnot(None),
        )
        .group_by(AuthDeviceUsageEdge.device_hash)
        .having(func.count(func.distinct(AuthDeviceUsageEdge.user_id)) >= min_user_count)
    )
    out: List[Dict[str, Any]] = []
    for dh, c in db.execute(stmt).all():
        sev = "CRITICAL" if int(c) >= min_user_count + 3 else "HIGH"
        out.append(
            {
                "finding_type": "graph.shared_device",
                "device_hash": dh,
                "distinct_users": int(c),
                "severity": sev,
                "score": min(100, 40 + int(c) * 12),
            }
        )
        if persist:
            persist_graph_finding(
                db,
                finding_type="graph.shared_device",
                severity=sev,
                device_hash=dh,
                metadata={"distinct_users": int(c), "window_days": window_days},
            )
    return out


def find_dense_ip_device_clusters(
    db: Session,
    *,
    min_devices_per_ip: int = 12,
    window_days: int = DEFAULT_WINDOW_DAYS,
    persist: bool = False,
) -> List[Dict[str, Any]]:
    """IP associées à beaucoup d’identités device distinctes (possible ferme / partage)."""
    since = _window_start(window_days)
    stmt = (
        select(AuthDeviceUsageEdge.ip_address, func.count(func.distinct(AuthDeviceUsageEdge.device_hash)))
        .where(
            AuthDeviceUsageEdge.created_at >= since,
            AuthDeviceUsageEdge.ip_address.isnot(None),
        )
        .group_by(AuthDeviceUsageEdge.ip_address)
        .having(func.count(func.distinct(AuthDeviceUsageEdge.device_hash)) >= min_devices_per_ip)
    )
    out: List[Dict[str, Any]] = []
    for ip, nd in db.execute(stmt).all():
        ip_s = str(ip)
        masked = ip_s[:8] + "…" if len(ip_s) > 8 else "***"
        sev = "HIGH" if int(nd) >= min_devices_per_ip + 8 else "MEDIUM"
        item = {
            "finding_type": "graph.dense_ip_device_cluster",
            "ip_masked": masked,
            "distinct_devices": int(nd),
            "severity": sev,
            "score": min(100, 30 + int(nd) * 2),
        }
        out.append(item)
        if persist:
            persist_graph_finding(
                db,
                finding_type="graph.dense_ip_device_cluster",
                severity=sev,
                device_hash=None,
                metadata={"distinct_devices": int(nd), "ip_prefix": ip_s[:12], "window_days": window_days},
            )
    return out


def detect_device_farms(
    db: Session,
    *,
    min_users: int = 5,
    min_ips: int = 6,
    window_days: int = DEFAULT_WINDOW_DAYS,
    persist: bool = False,
) -> List[Dict[str, Any]]:
    """Heuristique ferme : même device, beaucoup d’utilisateurs ET beaucoup d’IP."""
    since = _window_start(window_days)
    stmt = select(AuthDeviceUsageEdge.device_hash).where(AuthDeviceUsageEdge.created_at >= since).distinct()
    device_hashes = [r[0] for r in db.execute(stmt).all()]
    out: List[Dict[str, Any]] = []
    for dh in device_hashes:
        nu = int(
            db.execute(
                select(func.count(func.distinct(AuthDeviceUsageEdge.user_id))).where(
                    AuthDeviceUsageEdge.device_hash == dh,
                    AuthDeviceUsageEdge.created_at >= since,
                    AuthDeviceUsageEdge.user_id.isnot(None),
                )
            ).scalar_one()
            or 0
        )
        ni = int(
            db.execute(
                select(func.count(func.distinct(AuthDeviceUsageEdge.ip_address))).where(
                    AuthDeviceUsageEdge.device_hash == dh,
                    AuthDeviceUsageEdge.created_at >= since,
                    AuthDeviceUsageEdge.ip_address.isnot(None),
                )
            ).scalar_one()
            or 0
        )
        if nu >= min_users and ni >= min_ips:
            sev = "CRITICAL"
            out.append(
                {
                    "finding_type": "graph.device_farm_heuristic",
                    "device_hash": dh,
                    "distinct_users": nu,
                    "distinct_ips": ni,
                    "severity": sev,
                    "score": min(100, 50 + nu * 5 + ni * 2),
                }
            )
            if persist:
                persist_graph_finding(
                    db,
                    finding_type="graph.device_farm_heuristic",
                    severity=sev,
                    device_hash=dh,
                    metadata={"distinct_users": nu, "distinct_ips": ni},
                )
    return out


def detect_cross_user_high_risk_devices(
    db: Session,
    *,
    min_users: int = 2,
    min_reputation_score: int = None,
    persist: bool = False,
) -> List[Dict[str, Any]]:
    """Devices déjà HIGH/CRITICAL en réputation et liés à plusieurs comptes."""
    if min_reputation_score is None:
        min_reputation_score = int(os.getenv("DEVICE_GRAPH_HIGH_RISK_SCORE_MIN", "55"))
    since = _window_start(DEFAULT_WINDOW_DAYS)
    reps = (
        db.query(AuthDeviceReputation)
        .filter(AuthDeviceReputation.global_risk_score >= min_reputation_score)
        .all()
    )
    out: List[Dict[str, Any]] = []
    for rep in reps:
        nu = int(
            db.execute(
                select(func.count(func.distinct(AuthDeviceUsageEdge.user_id))).where(
                    AuthDeviceUsageEdge.device_hash == rep.device_hash,
                    AuthDeviceUsageEdge.created_at >= since,
                    AuthDeviceUsageEdge.user_id.isnot(None),
                )
            ).scalar_one()
            or 0
        )
        if nu >= min_users:
            sev = "CRITICAL" if rep.reputation_level in ("CRITICAL", "BLOCKED") else "HIGH"
            out.append(
                {
                    "finding_type": "graph.cross_user_high_risk_device",
                    "device_hash": rep.device_hash,
                    "distinct_users": nu,
                    "reputation_score": rep.global_risk_score,
                    "reputation_level": rep.reputation_level,
                    "severity": sev,
                    "score": rep.global_risk_score,
                }
            )
            if persist:
                persist_graph_finding(
                    db,
                    finding_type="graph.cross_user_high_risk_device",
                    severity=sev,
                    device_hash=rep.device_hash,
                    metadata={
                        "distinct_users": nu,
                        "reputation_score": rep.global_risk_score,
                        "reputation_level": rep.reputation_level,
                    },
                )
    return out


def run_all_graph_detections(
    db: Session,
    *,
    persist_findings: bool = False,
) -> Dict[str, List[Dict[str, Any]]]:
    """Exécute toutes les analyses (ex. job planifié)."""
    return {
        "shared_devices": find_shared_devices(db, persist=persist_findings),
        "dense_ip_clusters": find_dense_ip_device_clusters(db, persist=persist_findings),
        "device_farms": detect_device_farms(db, persist=persist_findings),
        "cross_user_high_risk": detect_cross_user_high_risk_devices(db, persist=persist_findings),
    }
