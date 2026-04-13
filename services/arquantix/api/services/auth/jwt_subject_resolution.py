"""
Résolution du sujet JWT (``sub``) vers ``AdminUser``.

Format **unique** supporté pour les sessions utilisateur : ``au:<admin_users.id>``
(``<id>`` entier décimal > 0). Tout autre ``sub`` est rejeté ; les rejets hors
``registration:*`` sont journalisés (``jwt_sub_rejected``) pour le monitoring.

Les jetons spéciaux (ex. ``registration:*``) ne correspondent à aucun utilisateur.
"""
from __future__ import annotations

import logging
import threading
from typing import Literal, Optional, Tuple

from sqlalchemy.orm import Session

from database import AdminUser

logger = logging.getLogger(__name__)

ResolutionKind = Literal["ok", "not_found", "non_user", "invalid"]

_metrics_lock = threading.Lock()
_jwt_sub_user_id_count = 0
_jwt_sub_rejected_count = 0


class NonUserJWTSubjectError(Exception):
    """``sub`` réservé (ex. ``registration:2fa``) — aucun ``AdminUser``."""

    pass


def get_jwt_sub_resolution_metrics() -> dict[str, int]:
    """Snapshot des compteurs (tests / diagnostics / monitoring post-déploiement)."""
    with _metrics_lock:
        return {
            "jwt_sub_user_id_count": _jwt_sub_user_id_count,
            "jwt_sub_rejected_count": _jwt_sub_rejected_count,
        }


def reset_jwt_sub_resolution_metrics() -> None:
    """Réinitialise les compteurs (tests uniquement)."""
    global _jwt_sub_user_id_count, _jwt_sub_rejected_count
    with _metrics_lock:
        _jwt_sub_user_id_count = 0
        _jwt_sub_rejected_count = 0


def _bump_user_metric() -> None:
    global _jwt_sub_user_id_count
    with _metrics_lock:
        _jwt_sub_user_id_count += 1


def _bump_rejected_metric() -> None:
    global _jwt_sub_rejected_count
    with _metrics_lock:
        _jwt_sub_rejected_count += 1


def _sub_preview(raw: str, *, max_len: int = 96) -> str:
    t = (raw or "").strip()
    if len(t) <= max_len:
        return t
    return t[: max_len - 3] + "..."


def _log_reject_non_canonical_sub(raw: str, *, reason: str) -> None:
    """Guard rail : seul ``au:<id>`` est valide pour les sessions utilisateur."""
    _bump_rejected_metric()
    preview = _sub_preview(raw)
    extra = {
        "event": "jwt_sub_rejected",
        "reason": reason,
        "sub_preview": preview,
    }
    if reason == "not_au_prefix" and "@" in preview:
        logger.error(
            "jwt_sub_rejected: non-canonical sub (possible legacy email-shaped subject)",
            extra={**extra, "legacy_email_shape": True},
        )
    elif reason == "not_au_prefix":
        logger.warning("jwt_sub_rejected", extra=extra)
    else:
        logger.warning("jwt_sub_rejected", extra=extra)


def is_non_user_subject_token(sub: str) -> bool:
    """Jetons d’accès spéciaux (ex. inscription 2FA) — pas d’``AdminUser`` associé au ``sub``."""
    s = (sub or "").strip()
    return s.startswith("registration:")


def classify_sub_format(sub: str) -> str:
    """Format du ``sub`` : ``au`` si préfixe canonique, sinon ``other``."""
    s = (sub or "").strip().lower()
    if s.startswith("au:"):
        return "au"
    return "other"


def resolve_user_from_jwt_sub(
    db: Session,
    sub: Optional[str],
    *,
    record_metric: bool = True,
    allow_non_user_subject: bool = False,
) -> Tuple[Optional[AdminUser], str, ResolutionKind]:
    """
    Résout ``sub`` vers une ligne ``AdminUser``.

    - ``registration:*`` → :class:`NonUserJWTSubjectError` si ``allow_non_user_subject`` est False.
    - ``au:<id>`` uniquement (id entier > 0). Tout autre format → ``invalid``.

    Retourne ``(user, sub_typ, kind)`` avec ``sub_typ`` parmi
    ``user_id`` | ``registration_special`` | ``invalid``.
    """
    if sub is None:
        return None, "invalid", "invalid"
    s = str(sub).strip()
    if not s:
        return None, "invalid", "invalid"

    if is_non_user_subject_token(s):
        if allow_non_user_subject:
            return None, "registration_special", "non_user"
        raise NonUserJWTSubjectError(
            "JWT subject is a non-user session token (e.g. registration flow); use a user access token."
        )

    if len(s) > 3 and s.lower().startswith("au:"):
        rest = s[3:].strip()
        if not rest.isdigit():
            _log_reject_non_canonical_sub(s, reason="malformed_au")
            return None, "invalid", "invalid"
        uid = int(rest)
        if uid <= 0:
            _log_reject_non_canonical_sub(s, reason="au_id_non_positive")
            return None, "invalid", "invalid"
        user = db.query(AdminUser).filter(AdminUser.id == uid).first()
        if user is not None:
            if record_metric:
                _bump_user_metric()
            return user, "user_id", "ok"
        return None, "user_id", "not_found"

    _log_reject_non_canonical_sub(s, reason="not_au_prefix")
    return None, "invalid", "invalid"
