"""
Réévaluation continue du contexte : refresh, changement IP / empreinte / confiance.

S’appuie sur les signaux déjà journalisés dans ``perform_refresh`` ; renforce ``step_up_otp_required``.
"""
from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database import AuthSession

logger = logging.getLogger("arquantix.security.zero_trust")


def _truthy(name: str, default: str = "true") -> bool:
    return (os.getenv(name) or default).strip().lower() in ("1", "true", "yes", "on")


def maybe_require_step_up_after_refresh_signals(
    *,
    session: "AuthSession",
    ip_changed: bool,
    fingerprint_changed: bool,
    device_trust_degraded: bool = False,
) -> None:
    """
    Si le contexte réseau / device change pendant un refresh, exiger un nouveau step-up serveur.

    Activé par défaut via ``ZERO_TRUST_REFRESH_CONTEXT_CHANGE_STEP_UP`` (true).
    """
    if not _truthy("ZERO_TRUST_REFRESH_CONTEXT_CHANGE_STEP_UP", "true"):
        return
    if ip_changed or fingerprint_changed or device_trust_degraded:
        session.step_up_otp_required = True
        logger.info(
            "zero_trust.continuous_auth.step_up_flagged %s",
            {"session_id": str(session.id), "ip_changed": ip_changed, "fp_changed": fingerprint_changed},
        )


def reevaluate_security_on_critical_action(*, user_id: int, action: str) -> None:
    """Hook documenté pour corrélation SIEM / risk engine (pas d’effet de bord DB ici)."""
    logger.debug("zero_trust.critical_action user_id=%s action=%s", user_id, action)
