"""Corrélation légère sur ``auth_security_events`` (flags uniquement, pas de blocage)."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from database import AuthSecurityEvent

logger = logging.getLogger("arquantix.auth.security")


class SecuritySignalService:
    @staticmethod
    def count_events_by_ip(db: Session, ip: str, window_sec: int) -> int:
        if not ip:
            return 0
        since = datetime.now(timezone.utc) - timedelta(seconds=window_sec)
        q = select(func.count()).select_from(AuthSecurityEvent).where(
            AuthSecurityEvent.ip_address == ip[:45],
            AuthSecurityEvent.created_at >= since,
        )
        return int(db.execute(q).scalar_one() or 0)

    @staticmethod
    def count_events_by_device(db: Session, device_id: str, window_sec: int) -> int:
        if not device_id:
            return 0
        since = datetime.now(timezone.utc) - timedelta(seconds=window_sec)
        q = select(func.count()).select_from(AuthSecurityEvent).where(
            AuthSecurityEvent.device_id == device_id[:128],
            AuthSecurityEvent.created_at >= since,
        )
        return int(db.execute(q).scalar_one() or 0)

    @staticmethod
    def count_events_by_user(db: Session, user_id: int, window_sec: int) -> int:
        since = datetime.now(timezone.utc) - timedelta(seconds=window_sec)
        q = select(func.count()).select_from(AuthSecurityEvent).where(
            AuthSecurityEvent.user_id == user_id,
            AuthSecurityEvent.created_at >= since,
        )
        return int(db.execute(q).scalar_one() or 0)

    @staticmethod
    def _count_event_type_since(
        db: Session, event_type: str, since: datetime, user_id: Optional[int] = None
    ) -> int:
        q = select(func.count()).select_from(AuthSecurityEvent).where(
            AuthSecurityEvent.event_type == event_type,
            AuthSecurityEvent.created_at >= since,
        )
        if user_id is not None:
            q = q.where(AuthSecurityEvent.user_id == user_id)
        return int(db.execute(q).scalar_one() or 0)

    @staticmethod
    def _users_with_both_event_types(
        db: Session, types: Tuple[str, str], window_sec: int
    ) -> List[int]:
        since = datetime.now(timezone.utc) - timedelta(seconds=window_sec)
        stmt = (
            select(AuthSecurityEvent.user_id)
            .where(
                AuthSecurityEvent.user_id.isnot(None),
                AuthSecurityEvent.created_at >= since,
                AuthSecurityEvent.event_type.in_(types),
            )
            .group_by(AuthSecurityEvent.user_id)
            .having(func.count(distinct(AuthSecurityEvent.event_type)) >= 2)
        )
        rows = db.execute(stmt).scalars().all()
        return [int(u) for u in rows if u is not None]

    @classmethod
    def detect_anomalies(cls, db: Session) -> Dict[str, Any]:
        """
        Heuristiques Phase 3.1 : log uniquement, pas d’action automatique.
        """
        now = datetime.now(timezone.utc)
        flags: Dict[str, Any] = {
            "suspicious_ip": False,
            "suspicious_device": False,
            "suspicious_user": False,
            "details": {},
        }

        since_60 = now - timedelta(seconds=60)
        n_reject = cls._count_event_type_since(db, "auth.refresh.rejected", since_60)
        if n_reject > 10:
            flags["suspicious_ip"] = True
            flags["details"]["refresh_rejects_60s"] = n_reject

        since_300 = now - timedelta(seconds=300)
        n_burst = cls._count_event_type_since(db, "auth.refresh.rapid_burst", since_300)
        if n_burst > 5:
            flags["suspicious_device"] = True
            flags["details"]["rapid_burst_300s"] = n_burst

        users_combo = cls._users_with_both_event_types(
            db,
            ("auth.session.ip_changed", "auth.device.fingerprint_changed"),
            window_sec=120,
        )
        if users_combo:
            flags["suspicious_user"] = True
            flags["details"]["users_ip_and_fingerprint_change"] = users_combo[:20]

        if any(flags[k] for k in ("suspicious_ip", "suspicious_device", "suspicious_user")):
            logger.info("security_signal.anomaly_flags %s", flags)

        return flags
