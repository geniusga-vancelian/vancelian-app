"""
Réputation device : enregistrement des usages, calcul explicable, blacklist explicite.

Garde-fous : pas de blacklist automatique au premier signal ; journalisation des blocages.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import (
    AuthDeviceBlacklist,
    AuthDeviceGraphFinding,
    AuthDeviceReputation,
    AuthDeviceUsageEdge,
)
from services.security.security_env import (
    is_device_reputation_critical_blocks_auth_enabled,
    is_device_reputation_enabled,
)

logger = logging.getLogger("arquantix.security.device_reputation")

SUSPICIOUS_EDGE_EVENTS = frozenset(
    {
        "auth.login.failed",
        "auth.refresh.rejected",
        "auth.device.attestation_failed",
        "auth.device.mismatch",
        "auth.session.ip_changed",
        "auth.device.fingerprint_changed",
        "device.reputation.manual_suspicion",
    }
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def install_id_from_request(request: Request) -> Optional[str]:
    raw = request.headers.get("x-install-id") or request.headers.get("X-Install-ID")
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    return s[:128] if len(s) > 128 else s


def resolve_device_hash_from_request(
    request: Request,
    device_id_normalized: str,
    fingerprint_hash: Optional[str],
) -> str:
    from services.security.device_reputation.device_identity import build_device_hash

    return build_device_hash(device_id_normalized, fingerprint_hash, install_id_from_request(request))


def is_device_blacklisted(db: Session, device_hash: str) -> bool:
    now = _utcnow()
    rows = db.query(AuthDeviceBlacklist).filter(AuthDeviceBlacklist.device_hash == device_hash).all()
    for r in rows:
        if r.blocked_until is None or r.blocked_until > now:
            return True
    return False


def get_device_reputation_row(db: Session, device_hash: str) -> Optional[AuthDeviceReputation]:
    """Lecture directe sans recalcul (état persisté)."""
    return db.get(AuthDeviceReputation, device_hash)


def get_device_reputation(db: Session, device_hash: str) -> AuthDeviceReputation:
    """Recalcule puis retourne la ligne de réputation à jour."""
    return compute_device_reputation(db, device_hash)


def persist_graph_finding(
    db: Session,
    *,
    finding_type: str,
    severity: str,
    device_hash: Optional[str] = None,
    user_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
    dedupe_hours: int = 24,
) -> bool:
    """Persiste un finding ; évite les doublons récents (même type + device). Retourne True si inséré."""
    since = _utcnow() - timedelta(hours=dedupe_hours)
    q = db.query(AuthDeviceGraphFinding).filter(
        AuthDeviceGraphFinding.finding_type == finding_type[:128],
        AuthDeviceGraphFinding.created_at >= since,
    )
    if device_hash:
        q = q.filter(AuthDeviceGraphFinding.device_hash == device_hash)
    else:
        q = q.filter(AuthDeviceGraphFinding.device_hash.is_(None))
    if q.first():
        return False
    row = AuthDeviceGraphFinding(
        id=uuid.uuid4(),
        device_hash=device_hash,
        user_id=user_id,
        finding_type=finding_type[:128],
        severity=severity[:16],
        metadata_json=dict(metadata or {}),
    )
    db.add(row)
    db.flush()
    logger.info(
        "device.graph_finding.persisted type=%s severity=%s device=%s",
        finding_type,
        severity,
        (device_hash or "")[:12],
    )
    return True


def _score_to_level(score: int, *, blacklisted: bool) -> str:
    if blacklisted:
        return "BLOCKED"
    if score >= 85:
        return "CRITICAL"
    if score >= 60:
        return "HIGH"
    if score >= 35:
        return "MEDIUM"
    return "LOW"


def compute_device_reputation(db: Session, device_hash: str) -> AuthDeviceReputation:
    """
    Recalcule les agrégats depuis les arêtes + blacklist.
    Règles explicites (linéaires plafonnées) — auditables.
    """
    now = _utcnow()
    blacklisted = is_device_blacklisted(db, device_hash)

    nu = int(
        db.execute(
            select(func.count(func.distinct(AuthDeviceUsageEdge.user_id))).where(
                AuthDeviceUsageEdge.device_hash == device_hash,
                AuthDeviceUsageEdge.user_id.isnot(None),
            )
        ).scalar_one()
        or 0
    )
    n_ip = int(
        db.execute(
            select(func.count(func.distinct(AuthDeviceUsageEdge.ip_address))).where(
                AuthDeviceUsageEdge.device_hash == device_hash,
                AuthDeviceUsageEdge.ip_address.isnot(None),
            )
        ).scalar_one()
        or 0
    )
    n_sess = int(
        db.execute(
            select(func.count(func.distinct(AuthDeviceUsageEdge.session_id))).where(
                AuthDeviceUsageEdge.device_hash == device_hash,
                AuthDeviceUsageEdge.session_id.isnot(None),
            )
        ).scalar_one()
        or 0
    )
    n_susp = int(
        db.execute(
            select(func.count())
            .select_from(AuthDeviceUsageEdge)
            .where(
                AuthDeviceUsageEdge.device_hash == device_hash,
                AuthDeviceUsageEdge.event_type.in_(tuple(SUSPICIOUS_EDGE_EVENTS)),
            )
        ).scalar_one()
        or 0
    )

    # Seuils progressifs (pas de saut brutal sur un seul événement)
    score = 0
    score += min(36, nu * 9)
    score += min(28, n_ip * 3)
    score += min(24, n_susp * 2)
    if n_sess > 0:
        score += min(12, n_sess // 5)

    if blacklisted:
        score = 100

    score = max(0, min(100, score))
    level = _score_to_level(score, blacklisted=blacklisted)

    row = db.get(AuthDeviceReputation, device_hash)
    if row is None:
        row = AuthDeviceReputation(device_hash=device_hash)
        db.add(row)
    row.global_risk_score = score
    row.reputation_level = level
    row.total_sessions = n_sess
    row.unique_user_count = nu
    row.unique_ip_count = n_ip
    row.suspicious_event_count = n_susp
    row.last_seen_at = now
    row.updated_at = now
    if row.first_seen_at is None:
        row.first_seen_at = now
    if blacklisted:
        row.blocked_until = None
    else:
        row.blocked_until = None
    db.flush()

    _maybe_progressive_findings(db, device_hash, row, nu, n_ip, n_susp)
    return row


def _maybe_progressive_findings(
    db: Session,
    device_hash: str,
    row: AuthDeviceReputation,
    nu: int,
    n_ip: int,
    n_susp: int,
) -> None:
    """Signaux importants uniquement au-delà de seuils (pas au premier edge)."""
    min_users = int(os.getenv("DEVICE_REPUTATION_SHARED_USER_FINDING_MIN", "3"))
    if nu >= min_users:
        persist_graph_finding(
            db,
            finding_type="device.shared_across_users",
            severity="HIGH" if nu >= min_users + 2 else "MEDIUM",
            device_hash=device_hash,
            metadata={"unique_user_count": nu, "unique_ip_count": n_ip},
        )
    min_ip = int(os.getenv("DEVICE_REPUTATION_MULTI_IP_FINDING_MIN", "8"))
    if n_ip >= min_ip:
        persist_graph_finding(
            db,
            finding_type="device.high_ip_churn",
            severity="MEDIUM",
            device_hash=device_hash,
            metadata={"unique_ip_count": n_ip},
        )
    min_susp = int(os.getenv("DEVICE_REPUTATION_SUSPICIOUS_FINDING_MIN", "6"))
    if n_susp >= min_susp:
        persist_graph_finding(
            db,
            finding_type="device.suspicious_event_burst",
            severity="HIGH",
            device_hash=device_hash,
            metadata={"suspicious_event_count": n_susp},
        )


def record_device_usage(
    db: Optional[Session],
    *,
    device_hash: str,
    user_id: Optional[int],
    event_type: str,
    ip_address: Optional[str] = None,
    session_id: Optional[Any] = None,
) -> None:
    if not is_device_reputation_enabled():
        return
    if db is None:
        from database import SessionLocal

        s = SessionLocal()
        try:
            edge = AuthDeviceUsageEdge(
                id=uuid.uuid4(),
                device_hash=device_hash,
                user_id=user_id,
                session_id=session_id,
                ip_address=(ip_address or None)[:45] if ip_address else None,
                event_type=event_type[:128],
            )
            s.add(edge)
            s.flush()
            compute_device_reputation(s, device_hash)
            s.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("device.record_usage isolated failed: %s", exc)
            s.rollback()
        finally:
            s.close()
        return

    edge = AuthDeviceUsageEdge(
        id=uuid.uuid4(),
        device_hash=device_hash,
        user_id=user_id,
        session_id=session_id,
        ip_address=(ip_address or None)[:45] if ip_address else None,
        event_type=event_type[:128],
    )
    db.add(edge)
    db.flush()
    compute_device_reputation(db, device_hash)


def mark_device_suspicious(
    db: Session,
    device_hash: str,
    *,
    reason: str = "manual",
    actor_user_id: Optional[int] = None,
) -> AuthDeviceReputation:
    """Enregistre un usage « suspicion » explicite (audit)."""
    record_device_usage(
        db,
        device_hash=device_hash,
        user_id=actor_user_id,
        event_type="device.reputation.manual_suspicion",
        ip_address=None,
        session_id=None,
    )
    persist_graph_finding(
        db,
        finding_type="device.manual_suspicion",
        severity="MEDIUM",
        device_hash=device_hash,
        metadata={"reason": reason[:256]},
        user_id=actor_user_id,
    )
    return compute_device_reputation(db, device_hash)


def blacklist_device(
    db: Session,
    device_hash: str,
    *,
    reason: str,
    blocked_until: Optional[datetime] = None,
    created_by: Optional[int] = None,
) -> AuthDeviceBlacklist:
    """Blacklist **manuelle** uniquement (appelée par l’admin API)."""
    row = AuthDeviceBlacklist(
        id=uuid.uuid4(),
        device_hash=device_hash,
        reason=reason[:512],
        blocked_until=blocked_until,
        created_by=created_by,
    )
    db.add(row)
    db.flush()
    logger.warning(
        "device.blacklist.added hash_prefix=%s created_by=%s until=%s reason=%s",
        device_hash[:12],
        created_by,
        blocked_until,
        reason[:80],
    )
    compute_device_reputation(db, device_hash)
    db.flush()
    return row


def unblacklist_device(db: Session, device_hash: str) -> int:
    """Supprime toutes les entrées de blacklist pour ce hash (déblocage admin)."""
    n = (
        db.query(AuthDeviceBlacklist)
        .filter(AuthDeviceBlacklist.device_hash == device_hash)
        .delete(synchronize_session=False)
    )
    logger.info("device.blacklist.cleared hash_prefix=%s rows=%s", device_hash[:12], n)
    compute_device_reputation(db, device_hash)
    db.flush()
    return int(n)


def evaluate_auth_impact(
    db: Session,
    device_hash: str,
    *,
    user_id: Optional[int],
) -> Tuple[bool, bool, Dict[str, Any]]:
    """
    Retourne ``(blocked, step_up_required, audit_metadata)`` pour login / refresh.

    - Liste noire active → blocage dur.
    - HIGH → step-up OTP.
    - CRITICAL → step-up ; blocage dur seulement si ``DEVICE_REPUTATION_CRITICAL_BLOCKS_AUTH``.
    - BLOCKED (niveau) → idem blacklist.
    """
    if not is_device_reputation_enabled():
        return False, False, {}

    rep = compute_device_reputation(db, device_hash)
    meta = {
        "device_reputation_score": rep.global_risk_score,
        "device_reputation_level": rep.reputation_level,
        "device_hash_prefix": device_hash[:12],
    }

    if rep.reputation_level == "BLOCKED" or is_device_blacklisted(db, device_hash):
        logger.warning(
            "device.auth.blocked blacklist/reputation user_id=%s hash_prefix=%s",
            user_id,
            device_hash[:12],
        )
        return True, False, meta

    critical_blocks = is_device_reputation_critical_blocks_auth_enabled()
    step_up = False
    if rep.reputation_level in ("HIGH", "CRITICAL"):
        step_up = True
    if rep.reputation_level == "CRITICAL" and critical_blocks:
        return True, False, meta

    if step_up:
        logger.info(
            "device.auth.step_up reputation=%s user_id=%s hash_prefix=%s",
            rep.reputation_level,
            user_id,
            device_hash[:12],
        )
    return False, step_up, meta
