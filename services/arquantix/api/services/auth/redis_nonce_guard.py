"""PR G — garde anti-replay distribuée pour nonces signature (SET NX, complément DB)."""
from __future__ import annotations

import logging

from services.auth.redis_client import get_redis_client
from services.auth.redis_metrics import bump_redis_error
from services.security.security_env import is_nonce_replay_redis_enabled, nonce_replay_redis_ttl_sec

logger = logging.getLogger("arquantix.auth.redis_nonce_guard")


def try_acquire_nonce_replay_slot(
    *,
    user_id: int,
    device_id: str,
    nonce_hash: str,
) -> bool:
    """
    Réserve atomiquement un créneau consommation (cross-instance).

    Retourne ``False`` si la clé existe déjà (replay ou course).
    En cas d’erreur Redis : ``True`` (fail-open vers la DB — comportement historique).
    """
    if not is_nonce_replay_redis_enabled():
        return True
    r = get_redis_client()
    if r is None:
        return True
    key = f"nonce:seen:{user_id}:{device_id.replace(':', '_')[:120]}:{nonce_hash[:64]}"
    ttl = nonce_replay_redis_ttl_sec()
    try:
        # NX : premier arrivé gagne ; les autres = replay cross-nœud
        ok = r.set(key, "1", ex=ttl, nx=True)
        return bool(ok)
    except Exception as exc:  # noqa: BLE001
        bump_redis_error()
        logger.warning("redis_nonce_guard_error: %s", exc)
        return True


def release_nonce_replay_slot(*, user_id: int, device_id: str, nonce_hash: str) -> None:
    """Libère le slot si la validation DB a échoué après réservation Redis."""
    if not is_nonce_replay_redis_enabled():
        return
    r = get_redis_client()
    if r is None:
        return
    key = f"nonce:seen:{user_id}:{device_id.replace(':', '_')[:120]}:{nonce_hash[:64]}"
    try:
        r.delete(key)
    except Exception as exc:  # noqa: BLE001
        bump_redis_error()
        logger.warning("redis_nonce_release_error: %s", exc)
