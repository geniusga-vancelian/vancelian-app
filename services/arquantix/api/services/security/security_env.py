"""
Source de vérité centralisée pour environnement déploiement + feature flags sécurité / auth.

Lecture **à chaque appel** (pas de cache) pour tests et workers qui mutent ``os.environ``.

Priorité des variables d’environnement (identité déploiement) ::
    ``APP_ENV`` → ``ARQUANTIX_ENV`` → ``ENVIRONMENT`` → ``ENV``

Les alias (``dev`` → ``development``, etc.) sont normalisés ; le code métier compare des valeurs canoniques.
"""
from __future__ import annotations

import logging
import os
import re
from typing import Optional

logger = logging.getLogger("arquantix.security.env")

_TRUTHY = frozenset({"1", "true", "yes", "on"})
_FALSY = frozenset({"0", "false", "no", "off"})

# Valeurs canoniques internes (toujours minuscules après normalisation)
def normalize_app_env(raw: str) -> str:
    """
    Mappe les alias courants vers une étiquette canonique.

    - ``dev``, ``local`` → ``development``
    - ``testing`` → ``test``
    - ``stage`` → ``staging``
    - ``prod``, ``live`` → ``production``
    - Valeur inconnue : renvoyée en minuscules (compatibilité forward).
    """
    s = (raw or "").strip().lower()
    if not s:
        return "development"
    aliases = {
        "dev": "development",
        "development": "development",
        "local": "development",
        "test": "test",
        "testing": "test",
        "stage": "staging",
        "staging": "staging",
        "prod": "production",
        "production": "production",
        "live": "production",
    }
    return aliases.get(s, s)


def get_raw_deployment_env() -> str:
    """Chaîne brute avant normalisation (première variable non vide)."""
    return (
        os.getenv("APP_ENV")
        or os.getenv("ARQUANTIX_ENV")
        or os.getenv("ENVIRONMENT")
        or os.getenv("ENV")
        or ""
    ).strip()


def get_normalized_app_env() -> str:
    """
    Environnement déploiement normalisé.

    Si aucune variable n’est définie, retourne ``development`` (comportement dev implicite
    aligné sur l’absence d’APP_ENV historique = non « prod-like » pour 2FA).
    """
    return normalize_app_env(get_raw_deployment_env())


def is_development_env() -> bool:
    return get_normalized_app_env() == "development"


def is_test_env() -> bool:
    """``test`` explicite ou exécution pytest."""
    if get_normalized_app_env() == "test":
        return True
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def is_staging_env() -> bool:
    return get_normalized_app_env() == "staging"


def is_production_env() -> bool:
    """Production stricte (pas staging)."""
    return get_normalized_app_env() == "production"


def is_production_like_env() -> bool:
    """
    Environnements où les règles « prod-like » s’appliquent (2FA, noop interdits, etc.).

    Inclut **staging** : même garde-fous que la production pour OTP dev / fournisseurs factices.
    """
    return get_normalized_app_env() in ("production", "staging")


def is_non_production_env() -> bool:
    return not is_production_like_env()


def auth_redis_env_strategy() -> str:
    """
    Stratégie pour décider si Redis auth rate-limit est **obligatoire**.

    - ``legacy`` (défaut) : ``is_auth_redis_required_env_legacy()`` — ``ENVIRONMENT`` / ``ENV`` uniquement.
    - ``normalized`` : ``is_auth_redis_required_env_target()`` — ``get_normalized_app_env() == "production"``.

    Valeurs acceptées : ``legacy``, ``normalized`` (alias ``normalised``). Toute autre valeur : warning + ``legacy``.
    """
    raw = (os.getenv("AUTH_REDIS_ENV_STRATEGY") or "legacy").strip().lower()
    if raw in ("normalized", "normalised"):
        return "normalized"
    if raw in ("legacy", ""):
        return "legacy"
    logger.warning(
        "Unknown AUTH_REDIS_ENV_STRATEGY=%r — falling back to legacy",
        os.getenv("AUTH_REDIS_ENV_STRATEGY"),
    )
    return "legacy"


def is_auth_redis_required_env_legacy() -> bool:
    """
    Redis auth obligatoire — **règle historique**.

    Uniquement ``ENVIRONMENT`` / ``ENV`` ∈ ``production`` | ``prod`` | ``live`` — **sans** prioriser ``APP_ENV``.
    """
    v = (os.getenv("ENVIRONMENT") or os.getenv("ENV") or "").strip().lower()
    return v in ("production", "prod", "live")


def is_auth_redis_required_env_target() -> bool:
    """
    Cible de migration : Redis obligatoire lorsque l’environnement **normalisé** est ``production``.

    Utilise la chaîne prioritaire ``APP_ENV`` → ``ARQUANTIX_ENV`` → ``ENVIRONMENT`` → ``ENV``
    puis ``normalize_app_env`` (ex. ``prod`` → ``production``).
    """
    return is_production_env()


def is_auth_redis_required_env() -> bool:
    """
    Rate-limit auth distribué obligatoire (Redis).

    Routé par ``AUTH_REDIS_ENV_STRATEGY`` (défaut ``legacy`` pour ne pas casser les déploiements existants) :

    - **legacy** : ``is_auth_redis_required_env_legacy()``
    - **normalized** : ``is_auth_redis_required_env_target()``
    """
    if auth_redis_env_strategy() == "normalized":
        return is_auth_redis_required_env_target()
    return is_auth_redis_required_env_legacy()


def is_phone_validation_production_strict() -> bool:
    """
    Règles strictes téléphone (MOBILE only, etc.) — **production** uniquement.

    Ordre de lecture **legacy** (conservation registration) ::
        ``ENVIRONMENT`` → ``ENV`` → ``APP_ENV`` → ``ARQUANTIX_ENV``
    """
    raw = (
        os.getenv("ENVIRONMENT")
        or os.getenv("ENV")
        or os.getenv("APP_ENV")
        or os.getenv("ARQUANTIX_ENV")
        or ""
    ).strip()
    if not raw:
        return False
    return normalize_app_env(raw) == "production"


def is_two_factor_relaxed(*, app_testing: bool = False) -> bool:
    """Fournisseurs noop / limites assouplies — voir aussi ``TWO_FACTOR_RELAXED``."""
    if app_testing:
        return True
    if os.getenv("TWO_FACTOR_RELAXED", "").lower() in ("1", "true", "yes"):
        return True
    if os.getenv("PYTEST_CURRENT_TEST"):
        return True
    if not is_production_like_env():
        return True
    return False


def _env_truthy(name: str, *, default: str = "false") -> bool:
    return (os.getenv(name) or default).strip().lower() in _TRUTHY


def _env_not_falsy(name: str, *, default: str = "true") -> bool:
    v = (os.getenv(name) or default).strip().lower()
    return v not in _FALSY


# ——— Feature flags auth / sécurité (centralisés) ———


def is_passkeys_enabled() -> bool:
    v = (os.getenv("AUTH_PASSKEYS_ENABLED") or "true").strip().lower()
    return v not in _FALSY


def is_mobile_otp_login_enabled() -> bool:
    return _env_truthy("AUTH_MOBILE_OTP_LOGIN_ENABLED", default="false")


def is_admin_email_otp_enabled() -> bool:
    return _env_truthy("AUTH_ADMIN_EMAIL_OTP_ENABLED", default="false")


def is_security_events_enabled() -> bool:
    return _env_not_falsy("AUTH_SECURITY_EVENTS_ENABLED", default="true")


def is_login_device_trust_enabled() -> bool:
    return _env_truthy("LOGIN_DEVICE_TRUST_ENABLED", default="true")


def is_login_auth_strategy_enabled() -> bool:
    return _env_truthy("LOGIN_AUTH_STRATEGY_ENABLED", default="true")


def is_adaptive_auth_enabled() -> bool:
    return _env_truthy("ADAPTIVE_AUTH_ENABLED", default="false")


def is_adaptive_friction_enabled() -> bool:
    """Phase 5B — règles déterministes (montant / confiance / récence) avant moteur de risque complet."""
    return _env_truthy("ADAPTIVE_FRICTION_ENABLED", default="false")


def low_risk_transfer_amount_eur() -> float:
    """Seuil (EUR) en dessous duquel un transfert peut être traité en basse friction si le contexte le permet."""
    try:
        return max(0.0, float(os.getenv("LOW_RISK_TRANSFER_AMOUNT", "100")))
    except ValueError:
        return 100.0


def low_risk_recent_auth_seconds() -> int:
    """Fenêtre « step-up récent » pour l’éligibilité adaptive (secondes)."""
    try:
        return max(0, int(os.getenv("LOW_RISK_RECENT_AUTH_SECONDS", "900")))
    except ValueError:
        return 900


def is_risk_engine_enabled() -> bool:
    """Phase 5C — scoring dynamique déterministe (facteurs pondérés, sans ML)."""
    return _env_truthy("RISK_ENGINE_ENABLED", default="false")


def risk_high_threshold() -> float:
    """Seuil score (inclus) : au-dessus = niveau ``high`` tant que < critical."""
    try:
        return float(os.getenv("RISK_HIGH_THRESHOLD", "50"))
    except ValueError:
        return 50.0


def risk_critical_threshold() -> float:
    """Seuil score (inclus) : au-dessus = niveau ``critical``."""
    try:
        return float(os.getenv("RISK_CRITICAL_THRESHOLD", "75"))
    except ValueError:
        return 75.0


def is_behavioral_risk_enabled() -> bool:
    """Phase 5D — signaux comportementaux / anti-fraude déterministes (dans ``risk_engine``)."""
    return _env_truthy("BEHAVIORAL_RISK_ENABLED", default="false")


def is_adaptive_intelligence_enabled() -> bool:
    """Phase 5E — segmentation utilisateur + seuils dynamiques (déterministe, sans ML)."""
    return _env_truthy("ADAPTIVE_INTELLIGENCE_ENABLED", default="false")


def is_risk_experiments_enabled() -> bool:
    """Phase 5F — A/B testing déterministe sur les poids (``RISK_EXPERIMENT_ID`` + variantes)."""
    return _env_truthy("RISK_EXPERIMENTS_ENABLED", default="false")


def is_geo_velocity_enabled() -> bool:
    """Géo-vélocité + risque pays (sous ``BEHAVIORAL_RISK_ENABLED``)."""
    return _env_truthy("GEO_VELOCITY_ENABLED", default="false")


def is_device_risk_enabled() -> bool:
    """Cohérence appareil / empreinte (sous ``BEHAVIORAL_RISK_ENABLED``)."""
    return _env_truthy("DEVICE_RISK_ENABLED", default="false")


def is_device_risk_engine_pr_f_enabled() -> bool:
    """
    PR F — moteur risque unifié (score 0–100, allow / step_up / block) sur routes sensibles.

    Désactivé par défaut : aucun impact tant que la variable n’est pas activée.
    """
    return _env_truthy("DEVICE_RISK_ENGINE_PR_F_ENABLED", default="false")


def is_device_intent_engine_enabled() -> bool:
    """
    PR F.6 — détection d’intention (séquences d’actions) + journal ``auth_user_intent_events``.

    Sans effet si ``false`` (défaut).
    """
    return _env_truthy("DEVICE_INTENT_ENGINE_ENABLED", default="false")


def is_device_risk_ml_enabled() -> bool:
    """PR F.7 — couche score complémentaire (z-score vs EMA des features comportementales)."""
    return _env_truthy("DEVICE_RISK_ML_ENABLED", default="false")


def device_risk_ml_score_weight() -> float:
    """Poids appliqué au score ML 0–100 avant addition au score PR F (défaut 0.5)."""
    try:
        return max(0.0, min(1.0, float(os.getenv("DEVICE_RISK_ML_SCORE_WEIGHT", "0.5"))))
    except ValueError:
        return 0.5


def is_device_risk_temporal_enabled() -> bool:
    """PR F.7.2 — couche risque temporelle (distributions + transitions)."""
    return _env_truthy("DEVICE_RISK_TEMPORAL_ENABLED", default="false")


def device_risk_temporal_weight() -> float:
    """Poids appliqué au score temporel brut (0–40) avant addition au score global."""
    try:
        return max(0.0, min(1.0, float(os.getenv("DEVICE_RISK_TEMPORAL_WEIGHT", "0.5"))))
    except ValueError:
        return 0.5


def device_risk_temporal_min_samples() -> int:
    """Nombre minimum d’événements intent sur 30j pour activer le scoring temporel."""
    try:
        return max(0, min(100_000, int(os.getenv("DEVICE_RISK_TEMPORAL_MIN_SAMPLES", "10"))))
    except ValueError:
        return 10


def device_risk_ml_safe_update_threshold() -> int:
    """
    PR F.7.1 — ne met à jour l’EMA des features ML que si le score PR F **avant** couche ML
    est strictement inférieur à ce seuil (évite contamination par comportements à risque).
    """
    try:
        return max(0, min(100, int(os.getenv("DEVICE_RISK_ML_SAFE_UPDATE_THRESHOLD", "40"))))
    except ValueError:
        return 40


def device_risk_f_allow_threshold() -> int:
    """Scores strictement inférieurs → ``allow`` (défaut 40)."""
    try:
        return max(0, min(100, int(os.getenv("DEVICE_RISK_ALLOW_THRESHOLD", "40"))))
    except ValueError:
        return 40


def device_risk_f_block_threshold() -> int:
    """Scores supérieurs ou égaux → ``block`` (défaut 70)."""
    try:
        return max(0, min(100, int(os.getenv("DEVICE_RISK_BLOCK_THRESHOLD", "70"))))
    except ValueError:
        return 70


def device_risk_f_attestation_stale_days() -> int:
    """Attestation considérée comme périmée au-delà de N jours (signal +20)."""
    try:
        return max(1, min(365, int(os.getenv("DEVICE_RISK_ATTESTATION_STALE_DAYS", "30"))))
    except ValueError:
        return 30


def device_risk_engine_pr_f_cache_ttl_sec() -> int:
    """Réservé : cache distribué futur ; TTL processus (0 = désactivé)."""
    try:
        return max(0, min(3600, int(os.getenv("DEVICE_RISK_ENGINE_PR_F_CACHE_TTL_SEC", "0"))))
    except ValueError:
        return 0


def is_device_risk_combination_rules_enabled() -> bool:
    """PR F.2 — règles combinées (non linéaires) avant le score."""
    return _env_truthy("DEVICE_RISK_ENABLE_COMBINATION_RULES", default="false")


def is_device_risk_dynamic_rules_enabled() -> bool:
    """
    PR F.4 — règles depuis ``auth_risk_rules`` (conditions JSON).

    Si ``false`` : uniquement règles statiques PR F.2 lorsque ``DEVICE_RISK_ENABLE_COMBINATION_RULES``.
    """
    return _env_truthy("DEVICE_RISK_ENABLE_DYNAMIC_RULES", default="false")


def is_device_risk_rules_dry_run() -> bool:
    """
    PR F.4.1 — si ``true``, les règles dynamiques sont évaluées mais n’appliquent pas
    d’action (simulation ; journalisation ``device_risk_rule_dry_run``).

    PR F.5 : override Redis ``arquantix:risk:device_rules_dry_run`` si ``REDIS_ENABLED``.
    """
    try:
        from services.auth.risk_runtime_settings import get_dry_run_effective

        return bool(get_dry_run_effective()[0])
    except Exception:
        return _env_truthy("DEVICE_RISK_RULES_DRY_RUN", default="false")


def device_risk_rules_ruleset() -> str:
    """Jeu de règles chargé depuis ``auth_risk_rules`` (défaut : ``default``)."""
    raw = (os.getenv("DEVICE_RISK_RULES_RULESET") or "default").strip()
    return raw if raw else "default"


def is_device_risk_baseline_enabled() -> bool:
    """PR F.2 — baseline utilisateur (écart vs historique)."""
    return _env_truthy("DEVICE_RISK_ENABLE_BASELINE", default="false")


def is_device_risk_weighted_score_enabled() -> bool:
    """
    PR F.2 — score pondéré par dimension (device / réseau / comportement / historique).

    Si ``false`` : conserve l’agrégat additif historique ``compute_risk_score`` (PR F).
    """
    return _env_truthy("DEVICE_RISK_USE_WEIGHTED_SCORE", default="false")


def device_risk_weight_device() -> float:
    try:
        return max(0.0, min(1.0, float(os.getenv("DEVICE_RISK_WEIGHT_DEVICE", "0.3"))))
    except ValueError:
        return 0.3


def device_risk_weight_network() -> float:
    try:
        return max(0.0, min(1.0, float(os.getenv("DEVICE_RISK_WEIGHT_NETWORK", "0.2"))))
    except ValueError:
        return 0.2


def device_risk_weight_behavior() -> float:
    try:
        return max(0.0, min(1.0, float(os.getenv("DEVICE_RISK_WEIGHT_BEHAVIOR", "0.3"))))
    except ValueError:
        return 0.3


def device_risk_weight_history() -> float:
    try:
        return max(0.0, min(1.0, float(os.getenv("DEVICE_RISK_WEIGHT_HISTORY", "0.2"))))
    except ValueError:
        return 0.2


def device_risk_baseline_min_samples() -> int:
    """Nombre minimum d’observations avant d’appliquer les pénalités baseline."""
    try:
        return max(0, min(10_000, int(os.getenv("DEVICE_RISK_BASELINE_MIN_SAMPLES", "5"))))
    except ValueError:
        return 5


def is_device_risk_advanced_baseline_enabled() -> bool:
    """PR F.3 — patterns temporels, durée session, types d’actions (Welford + last 10)."""
    return _env_truthy("DEVICE_RISK_ENABLE_ADVANCED_BASELINE", default="false")


def device_risk_baseline_time_weight() -> float:
    """Multiplicateur des pénalités temporelles PR F.3 (défaut 1.0)."""
    try:
        return max(0.0, min(3.0, float(os.getenv("DEVICE_RISK_BASELINE_TIME_WEIGHT", "1.0"))))
    except ValueError:
        return 1.0


def device_risk_advanced_baseline_min_samples() -> int:
    """Observations mini avant scoring anomalie temporelle (PR F.3)."""
    try:
        return max(0, min(10_000, int(os.getenv("DEVICE_RISK_ADVANCED_BASELINE_MIN_SAMPLES", "8"))))
    except ValueError:
        return 8


def is_redis_cache_enabled() -> bool:
    """
    PR G — cache distribué + rate-limit partagés (identité, risque, signatures).

    Si ``false`` : comportement historique (mémoire locale uniquement), aucune connexion Redis.
    """
    return _env_truthy("REDIS_ENABLED", default="false")


def is_redis_fallback_local_enabled() -> bool:
    """Si Redis indisponible : continuer avec les caches / RL process-local (défaut : oui)."""
    return _env_not_falsy("REDIS_FALLBACK_LOCAL", default="true")


def device_risk_cache_ttl_sec() -> int:
    """TTL snapshot risque PR F (secondes), 5–10s recommandé."""
    try:
        return max(0, min(120, int(os.getenv("DEVICE_RISK_CACHE_TTL_SEC", "8"))))
    except ValueError:
        return 8


def device_risk_cache_rules_version() -> str:
    """Suffixe de clé cache risque (bump manuel lors d’un changement de règles critiques)."""
    return (os.getenv("DEVICE_RISK_CACHE_RULES_VERSION") or "").strip()[:32]


def is_signature_failure_rl_redis_enabled() -> bool:
    """RL échecs signature device via Redis (sinon fenêtre mémoire locale)."""
    return is_redis_cache_enabled() and _env_not_falsy("DEVICE_SIGNATURE_FAILURE_RL_REDIS", default="true")


def is_nonce_replay_redis_enabled() -> bool:
    """Anti-replay nonce cross-instance via Redis (en complément de la DB)."""
    return is_redis_cache_enabled() and _env_not_falsy("DEVICE_NONCE_REPLAY_REDIS", default="true")


def nonce_replay_redis_ttl_sec() -> int:
    try:
        return max(15, min(600, int(os.getenv("NONCE_REPLAY_REDIS_TTL_SEC", "90"))))
    except ValueError:
        return 90


def is_session_intelligence_enabled() -> bool:
    return _env_truthy("SESSION_INTELLIGENCE_ENABLED", default="false")


def is_continuous_auth_enabled() -> bool:
    return _env_truthy("CONTINUOUS_AUTH_ENABLED", default="false")


def is_adaptive_passkey_auto_enabled() -> bool:
    return _env_not_falsy("ADAPTIVE_AUTH_PASSKEY_AUTO", default="true")


def is_adaptive_block_high_risk_enabled() -> bool:
    return _env_not_falsy("ADAPTIVE_AUTH_BLOCK_HIGH_RISK", default="true")


def is_adaptive_email_fallback_enabled() -> bool:
    return _env_not_falsy("ADAPTIVE_AUTH_EMAIL_FALLBACK", default="true")


def is_session_step_up_enabled() -> bool:
    return _env_not_falsy("SESSION_STEP_UP_ENABLED", default="true")


def is_session_reauth_enabled() -> bool:
    return _env_not_falsy("SESSION_REAUTH_ENABLED", default="true")


def is_login_strategy_persist_decisions_enabled() -> bool:
    return _env_not_falsy("LOGIN_STRATEGY_PERSIST_DECISIONS", default="true")


def is_security_response_engine_enabled() -> bool:
    return _env_not_falsy("SECURITY_RESPONSE_ENGINE_ENABLED", default="true")


def is_device_reputation_risk_engine_integration_enabled() -> bool:
    return _env_not_falsy("DEVICE_REPUTATION_RISK_ENGINE_INTEGRATION", default="true")


def is_security_correlation_on_emit_enabled() -> bool:
    """Tuple ``("1","true","yes")`` uniquement (pas ``on``) — aligné sur l’historique du pipeline SIEM."""
    return (os.getenv("SECURITY_CORRELATION_ON_EMIT") or "true").strip().lower() in ("1", "true", "yes")


def is_security_response_engine_on_emit_enabled() -> bool:
    return (os.getenv("SECURITY_RESPONSE_ENGINE_ON_EMIT") or "true").strip().lower() in ("1", "true", "yes")


def is_device_reputation_enabled() -> bool:
    return _env_not_falsy("DEVICE_REPUTATION_ENABLED", default="true")


def is_device_reputation_critical_blocks_auth_enabled() -> bool:
    return _env_truthy("DEVICE_REPUTATION_CRITICAL_BLOCKS_AUTH", default="false")


def is_login_fraud_ml_evaluation_enabled() -> bool:
    return _env_not_falsy("LOGIN_FRAUD_ML_EVALUATION_ENABLED", default="true")


def is_auth_device_fingerprint_enabled() -> bool:
    v = (os.getenv("AUTH_DEVICE_FINGERPRINT_ENABLED") or "true").strip().lower()
    return v not in _FALSY


def is_passkey_auto_trigger_enabled() -> bool:
    return _env_not_falsy("PASSKEY_AUTO_TRIGGER_ENABLED", default="true")


def is_passkey_auto_expose_login_email_enabled() -> bool:
    return _env_not_falsy("PASSKEY_AUTO_EXPOSE_LOGIN_EMAIL", default="true")


def passkey_auto_max_login_risk() -> int:
    try:
        return max(20, min(95, int(os.getenv("PASSKEY_AUTO_MAX_LOGIN_RISK", "48"))))
    except ValueError:
        return 48


def is_fraud_ml_inference_enabled() -> bool:
    return _env_not_falsy("FRAUD_ML_INFERENCE_ENABLED", default="true")


def security_events_sink_name() -> str:
    return (os.getenv("SECURITY_EVENTS_SINK") or "none").strip().lower()


def security_account_lock_hours() -> int:
    try:
        return max(1, min(168, int(os.getenv("SECURITY_ACCOUNT_LOCK_HOURS", "24"))))
    except ValueError:
        return 24


def global_risk_ml_weight() -> float:
    try:
        return max(0.0, min(1.0, float(os.getenv("ML_WEIGHT", "0.4"))))
    except ValueError:
        return 0.4


def fraud_ml_enforce_min_heuristic() -> int:
    try:
        return max(0, min(100, int(os.getenv("FRAUD_ML_ENFORCE_MIN_HEURISTIC", "45"))))
    except ValueError:
        return 45


def login_fraud_pattern_weight() -> float:
    try:
        return max(0.0, min(1.0, float(os.getenv("LOGIN_FRAUD_PATTERN_WEIGHT", "0.45"))))
    except ValueError:
        return 0.45


def auth_rate_limit_backend_for_bootstrap() -> str:
    """``AUTH_RL_BACKEND`` tel que lu par ``auth_bootstrap`` (défaut vide si absent)."""
    return (os.getenv("AUTH_RL_BACKEND") or "").strip().lower()


def is_webauthn_strict_environment() -> bool:
    """
    Exiger HTTPS / RP ID / origines cohérentes — prod-like ou ``WEBAUTHN_STRICT_CONFIG``."""
    if is_production_like_env():
        return True
    return _env_truthy("WEBAUTHN_STRICT_CONFIG", default="false")


def current_environment_label() -> str:
    """Libellé affichage diagnostics (valeur normalisée)."""
    return get_normalized_app_env()


def should_expose_dev_otp_code() -> bool:
    """JSON ``dev_code`` (SMS / e-mail / 2FA) — jamais en prod-like."""
    if is_production_like_env():
        return False
    return (os.getenv("TWO_FACTOR_DEV_EXPOSE_CODE") or "").strip().lower() in _TRUTHY


def should_use_dev_fixed_otp() -> bool:
    """
    Indique si le code fixe ``TWO_FACTOR_DEV_FIXED_CODE`` *peut* s’appliquer (non prod-like + format valide).

    Pour le texte OTP réel, utiliser ``two_factor_dev_fixed_code`` dans ``two_factor_env``.
    """
    if is_production_like_env():
        return False
    raw = (os.getenv("TWO_FACTOR_DEV_FIXED_CODE") or "").strip()
    return bool(raw) and bool(re.compile(r"^\d{6}$").match(raw))


def should_require_real_email_provider_for_admin_otp() -> bool:
    """En prod-like, e-mail admin OTP nécessite un vrai fournisseur (pas noop)."""
    return is_production_like_env() and is_admin_email_otp_enabled()


def should_require_real_sms_provider_in_prod_like() -> bool:
    """Prod-like : pas de ``FAKE_SMS_PROVIDER`` (déjà appliqué dans ``sms_provider``)."""
    return is_production_like_env()


def should_require_redis_auth_rate_limit() -> bool:
    """Alias de ``is_auth_redis_required_env``."""
    return is_auth_redis_required_env()


def auth_rate_limit_backend_raw() -> str:
    return (os.getenv("AUTH_RL_BACKEND") or "auto").strip().lower()


def validate_security_environment_startup(*, testing: bool) -> None:
    """
    Garde-fous explicites au démarrage : combinaisons dangereuses lorsque Redis auth est requis.

    Aligné sur ``is_auth_redis_required_env()`` (stratégie ``AUTH_REDIS_ENV_STRATEGY`` : legacy vs normalized).

    Ne remplace pas les validations WebAuthn / e-mail admin (``webauthn_config``).
    """
    if testing:
        return
    if is_auth_redis_required_env():
        if (os.getenv("TWO_FACTOR_DEV_FIXED_CODE") or "").strip():
            raise RuntimeError(
                "TWO_FACTOR_DEV_FIXED_CODE must be unset when auth Redis is required for this environment "
                "(see AUTH_REDIS_ENV_STRATEGY / is_auth_redis_required_env)."
            )
        if (os.getenv("TWO_FACTOR_DEV_EXPOSE_CODE") or "").strip().lower() in _TRUTHY:
            raise RuntimeError(
                "TWO_FACTOR_DEV_EXPOSE_CODE must be unset/false when auth Redis is required for this environment."
            )
        if (os.getenv("FAKE_SMS_PROVIDER") or "").strip().lower() in _TRUTHY:
            raise RuntimeError(
                "FAKE_SMS_PROVIDER is forbidden when auth Redis is required for this environment."
            )
        logger.info(
            "Security env: auth Redis required (strategy=%s) — dev OTP / fake SMS flags cleared or absent.",
            auth_redis_env_strategy(),
        )

    if is_production_like_env() and (os.getenv("FAKE_SMS_PROVIDER") or "").strip().lower() in _TRUTHY:
        raise RuntimeError(
            "FAKE_SMS_PROVIDER is forbidden in production-like environments "
            "(normalized APP_ENV / ARQUANTIX_ENV: production or staging)."
        )
