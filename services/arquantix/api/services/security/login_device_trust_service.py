"""
Profil device / utilisateur : confiance login explicable (pas de second moteur SIEM).

S’appuie sur ``auth_user_device_profiles``, réputation globale ``auth_device_reputation``,
et signaux explicites (empreinte, ancienneté, compteurs).
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from database import AdminUser, AuthDeviceReputation, AuthUserDeviceProfile
from services.security.security_env import is_login_device_trust_enabled

logger = logging.getLogger("arquantix.security.login_device_trust")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class DeviceTrustComputationInput:
    """Entrées documentées pour ``compute_device_trust_score`` (audit / tests)."""

    days_since_first_seen: float
    successful_login_count: int
    failed_login_count: int
    fingerprint_stable: bool
    ip_country_stable: bool
    attestation_trusted: bool
    device_reputation_risk_0_100: int  # global_risk_score sur la ligne réputation device
    reputation_level: str


def resolve_user_device_profile(
    db: Session,
    user_id: int,
    device_hash: str,
) -> Optional[AuthUserDeviceProfile]:
    return (
        db.query(AuthUserDeviceProfile)
        .filter(
            AuthUserDeviceProfile.user_id == user_id,
            AuthUserDeviceProfile.device_hash == device_hash,
        )
        .first()
    )


def compute_device_trust_score(inp: DeviceTrustComputationInput) -> int:
    """
    Score 0–100, **plus haut = plus digne de confiance** (explicable, déterministe).

    Composantes (bornées) :
    - ancienneté : +2 pts / jour jusqu’à +24
    - succès : +2 pts / login réussi jusqu’à +30
    - échecs : −3 pts / échec jusqu’à −24
    - empreinte instable : −18
    - pays / IP instable (indicateur pays) : −12
    - attestation validée : +12
    - pénalité réputation globale device : − min(40, reputation_risk * 0.35)
    - niveau réputation textuel HIGH/CRITICAL : −10 / −20 supplémentaires
    """
    score = 28  # base « device inconnu / peu d’historique »

    score += min(24, int(max(0.0, inp.days_since_first_seen) * 2))
    score += min(30, int(inp.successful_login_count) * 2)
    score -= min(24, int(inp.failed_login_count) * 3)

    if not inp.fingerprint_stable:
        score -= 18
    if not inp.ip_country_stable:
        score -= 12
    if inp.attestation_trusted:
        score += 12

    rep_pen = min(40, int(inp.device_reputation_risk_0_100 * 0.35))
    score -= rep_pen

    lvl = (inp.reputation_level or "LOW").upper()
    if lvl == "HIGH":
        score -= 10
    elif lvl in ("CRITICAL", "BLOCKED"):
        score -= 20

    return max(0, min(100, score))


def compute_device_trust_level(trust_score: int) -> str:
    if trust_score >= 72:
        return "HIGH"
    if trust_score >= 44:
        return "MEDIUM"
    return "LOW"


def session_device_trust_from_profile_level(level: str) -> str:
    """Mappe vers les libellés ``auth_sessions.device_trust_level`` existants."""
    from services.auth.device_attestation_service import (
        DEVICE_TRUST_SUSPICIOUS,
        DEVICE_TRUST_TRUSTED,
        DEVICE_TRUST_UNKNOWN,
    )

    u = (level or "LOW").upper()
    if u == "HIGH":
        return DEVICE_TRUST_TRUSTED
    if u == "MEDIUM":
        return DEVICE_TRUST_UNKNOWN
    return DEVICE_TRUST_SUSPICIOUS


def _load_reputation_tuple(db: Session, device_hash: str) -> Tuple[int, str]:
    row = db.get(AuthDeviceReputation, device_hash)
    if row is None:
        return 0, "LOW"
    return int(row.global_risk_score or 0), str(row.reputation_level or "LOW")


def build_trust_input_for_profile(
    db: Session,
    profile: Optional[AuthUserDeviceProfile],
    *,
    current_fingerprint_hash: Optional[str],
    current_country: Optional[str],
    attestation_trusted: bool,
    device_hash: str,
) -> DeviceTrustComputationInput:
    now = _utcnow()
    if profile is None:
        rep_risk, rep_lvl = _load_reputation_tuple(db, device_hash)
        return DeviceTrustComputationInput(
            days_since_first_seen=0.0,
            successful_login_count=0,
            failed_login_count=0,
            fingerprint_stable=True,
            ip_country_stable=True,
            attestation_trusted=attestation_trusted,
            device_reputation_risk_0_100=rep_risk,
            reputation_level=rep_lvl,
        )

    first = profile.first_seen_at or now
    days = max(0.0, (now - first).total_seconds() / 86400.0)

    fp_stored = profile.fingerprint_hash
    cur_fp = (current_fingerprint_hash or "").strip() or None
    fp_stable = True
    if fp_stored and cur_fp and fp_stored != cur_fp:
        fp_stable = False
    if fp_stored and not cur_fp:
        fp_stable = False

    cc = (current_country or "").strip().upper() or None
    lc = (profile.last_country or "").strip().upper() or None
    country_stable = True
    if lc and cc and lc != cc:
        country_stable = False

    rep_risk, rep_lvl = _load_reputation_tuple(db, device_hash)

    return DeviceTrustComputationInput(
        days_since_first_seen=days,
        successful_login_count=int(profile.successful_login_count or 0),
        failed_login_count=int(profile.failed_login_count or 0),
        fingerprint_stable=fp_stable,
        ip_country_stable=country_stable,
        attestation_trusted=attestation_trusted,
        device_reputation_risk_0_100=rep_risk,
        reputation_level=rep_lvl,
    )


def refresh_profile_trust_fields(
    db: Session,
    profile: AuthUserDeviceProfile,
    *,
    current_fingerprint_hash: Optional[str],
    current_country: Optional[str],
    attestation_trusted: bool,
    device_hash: str,
) -> Tuple[int, str]:
    inp = build_trust_input_for_profile(
        db,
        profile,
        current_fingerprint_hash=current_fingerprint_hash,
        current_country=current_country,
        attestation_trusted=attestation_trusted,
        device_hash=device_hash,
    )
    ts = compute_device_trust_score(inp)
    tl = compute_device_trust_level(ts)
    profile.trust_score = ts
    profile.trust_level = tl
    profile.updated_at = _utcnow()
    return ts, tl


def update_user_device_profile_on_login(
    db: Session,
    *,
    user: AdminUser,
    device_hash: str,
    device_id_normalized: str,
    fingerprint_hash: Optional[str],
    ip_address: Optional[str],
    country_code: Optional[str],
    success: bool,
    auth_strength: Optional[str] = None,
    attestation_level: Optional[str] = None,
    attestation_trusted: bool = False,
) -> AuthUserDeviceProfile:
    """
    Crée ou met à jour le profil après une tentative de login (succès ou échec).

    Les compteurs sont explicites : ``login_count`` += 1 ; succès / échec incrémentés séparément.
    """
    row = resolve_user_device_profile(db, user.id, device_hash)
    now = _utcnow()
    if row is None:
        row = AuthUserDeviceProfile(
            id=uuid.uuid4(),
            user_id=user.id,
            device_hash=device_hash,
            device_id=device_id_normalized[:128] if device_id_normalized else None,
            fingerprint_hash=(fingerprint_hash[:64] if fingerprint_hash else None),
            first_seen_at=now,
            last_seen_at=now,
            login_count=0,
            successful_login_count=0,
            failed_login_count=0,
            last_ip=(ip_address[:45] if ip_address else None),
            last_country=(country_code[:8] if country_code else None),
            trust_score=0,
            trust_level="LOW",
            is_primary=None,
            last_auth_strength=auth_strength,
            last_attestation_level=attestation_level,
        )
        db.add(row)
        db.flush()

    row.login_count = int(row.login_count or 0) + 1
    if success:
        row.successful_login_count = int(row.successful_login_count or 0) + 1
    else:
        row.failed_login_count = int(row.failed_login_count or 0) + 1

    row.last_seen_at = now
    row.device_id = device_id_normalized[:128] if device_id_normalized else row.device_id
    if fingerprint_hash:
        row.fingerprint_hash = fingerprint_hash[:64]
    if ip_address:
        row.last_ip = ip_address[:45]
    if country_code:
        row.last_country = country_code[:8].upper()
    if auth_strength:
        row.last_auth_strength = auth_strength[:64]
    if attestation_level:
        row.last_attestation_level = attestation_level[:64]

    refresh_profile_trust_fields(
        db,
        row,
        current_fingerprint_hash=fingerprint_hash,
        current_country=country_code,
        attestation_trusted=attestation_trusted,
        device_hash=device_hash,
    )
    db.flush()
    return row


def snapshot_profile_for_audit(profile: Optional[AuthUserDeviceProfile]) -> Dict[str, Any]:
    if profile is None:
        return {"profile_present": False}
    return {
        "profile_present": True,
        "trust_score": profile.trust_score,
        "trust_level": profile.trust_level,
        "successful_login_count": profile.successful_login_count,
        "failed_login_count": profile.failed_login_count,
        "first_seen_at": profile.first_seen_at.isoformat() if profile.first_seen_at else None,
    }
