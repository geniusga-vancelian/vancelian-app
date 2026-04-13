"""Suppression des challenges WebAuthn expirés (anti-croissance table)."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from database import (
    AuthAdminEmailOtpChallenge,
    AuthMobileLoginOtpChallenge,
    AuthWebAuthnChallenge,
)

logger = logging.getLogger("arquantix.auth.passkeys")


def cleanup_webauthn_challenges(db: Session) -> int:
    """
    Supprime les lignes ``auth_webauthn_challenges`` avec ``expires_at`` < maintenant (UTC).
    Retourne le nombre de lignes supprimées.
    """
    now = datetime.now(timezone.utc)
    res = db.execute(delete(AuthWebAuthnChallenge).where(AuthWebAuthnChallenge.expires_at < now))
    db.commit()
    n = res.rowcount or 0
    if n:
        logger.info("webauthn_challenges_cleanup removed %s row(s)", n)
    return int(n)


def cleanup_expired_admin_email_otp_challenges(db: Session) -> int:
    now = datetime.now(timezone.utc)
    res = db.execute(
        delete(AuthAdminEmailOtpChallenge).where(AuthAdminEmailOtpChallenge.expires_at < now)
    )
    db.commit()
    n = res.rowcount or 0
    if n:
        logger.info("admin_email_otp_cleanup removed %s row(s)", n)
    return int(n)


def cleanup_expired_mobile_login_otp_challenges(db: Session) -> int:
    now = datetime.now(timezone.utc)
    res = db.execute(
        delete(AuthMobileLoginOtpChallenge).where(AuthMobileLoginOtpChallenge.expires_at < now)
    )
    db.commit()
    n = res.rowcount or 0
    if n:
        logger.info("mobile_login_otp_cleanup removed %s row(s)", n)
    return int(n)
