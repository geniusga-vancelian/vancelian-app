"""Garde-fous au démarrage : production exige Redis pour le rate limit auth + validations env sécurité."""
from __future__ import annotations

import logging

from services.security.security_env import (
    auth_rate_limit_backend_for_bootstrap,
    auth_redis_env_strategy,
    is_auth_redis_required_env,
    is_auth_redis_required_env_legacy,
    is_auth_redis_required_env_target,
    validate_security_environment_startup,
)

logger = logging.getLogger("arquantix.auth.bootstrap")


def is_production_environment() -> bool:
    """
    Indique si les règles « prod » du rate-limit auth s’appliquent (Redis obligatoire).

    Délégué à ``is_auth_redis_required_env()`` — voir ``AUTH_REDIS_ENV_STRATEGY`` (``legacy`` vs ``normalized``).
    """
    return is_auth_redis_required_env()


def enforce_auth_infrastructure_bootstrap(*, testing: bool) -> None:
    """
    Combinaisons dangereuses (OTP dev, fake SMS, etc.) : ``validate_security_environment_startup``.

    Si Redis auth est requis pour cet environnement : ``AUTH_RL_BACKEND=redis`` + Redis joignable,
    puis validations WebAuthn strictes et e-mail admin. La condition « prod » dépend de
    ``AUTH_REDIS_ENV_STRATEGY`` (voir ``security_env``).
    """
    if testing:
        return

    validate_security_environment_startup(testing=False)

    strategy = auth_redis_env_strategy()
    legacy_on = is_auth_redis_required_env_legacy()
    target_on = is_auth_redis_required_env_target()
    effective = is_auth_redis_required_env()
    logger.info(
        "Auth infrastructure bootstrap: AUTH_REDIS_ENV_STRATEGY=%s "
        "(legacy_redis_required=%s, normalized_production_target=%s, effective_redis_required=%s)",
        strategy,
        legacy_on,
        target_on,
        effective,
    )

    if not effective:
        return

    backend = auth_rate_limit_backend_for_bootstrap()
    if backend != "redis":
        raise RuntimeError(
            "AUTH_RL_BACKEND must be redis when auth Redis is required for this deployment "
            f"(AUTH_REDIS_ENV_STRATEGY={strategy}). "
            "In-memory rate limiting is not permitted."
        )
    from services.auth.auth_redis import ping_auth_redis

    if not ping_auth_redis():
        raise RuntimeError(
            "Auth rate limiting requires a reachable Redis server (set AUTH_REDIS_URL). "
            "Production cannot start without distributed rate limiting."
        )

    from services.auth.webauthn_config import (
        validate_admin_email_otp_at_startup,
        validate_webauthn_at_startup,
    )

    validate_webauthn_at_startup(testing=testing)
    validate_admin_email_otp_at_startup(testing=testing)
