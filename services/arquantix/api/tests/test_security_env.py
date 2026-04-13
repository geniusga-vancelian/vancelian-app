"""Tests unitaires — module ``services.security.security_env`` (normalisation + garde-fous)."""
from __future__ import annotations

import pytest

from services.security import security_env as se


def test_normalize_app_env_aliases():
    assert se.normalize_app_env("dev") == "development"
    assert se.normalize_app_env("DEV") == "development"
    assert se.normalize_app_env("prod") == "production"
    assert se.normalize_app_env("live") == "production"
    assert se.normalize_app_env("stage") == "staging"
    assert se.normalize_app_env("testing") == "test"


def test_get_normalized_app_env_priority_app_first(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert se.get_normalized_app_env() == "development"


def test_is_production_like_includes_staging(monkeypatch):
    monkeypatch.setenv("APP_ENV", "staging")
    assert se.is_production_like_env() is True
    monkeypatch.setenv("APP_ENV", "stage")
    assert se.is_production_like_env() is True


def test_is_auth_redis_required_only_production(monkeypatch):
    """Mode legacy (défaut) : Redis obligatoire via ENVIRONMENT/ENV uniquement, pas APP_ENV."""
    monkeypatch.setenv("AUTH_REDIS_ENV_STRATEGY", "legacy")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert se.is_auth_redis_required_env() is False
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert se.is_auth_redis_required_env() is True
    monkeypatch.setenv("ENVIRONMENT", "staging")
    assert se.is_auth_redis_required_env() is False


def test_is_auth_redis_legacy_default_unset_strategy(monkeypatch):
    """Sans AUTH_REDIS_ENV_STRATEGY : comportement identique au legacy."""
    monkeypatch.delenv("AUTH_REDIS_ENV_STRATEGY", raising=False)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert se.is_auth_redis_required_env() is False
    assert se.auth_redis_env_strategy() == "legacy"


def test_is_auth_redis_normalized_production_without_environment(monkeypatch):
    """APP_ENV=production, pas de ENVIRONMENT : normalized exige Redis ; legacy non."""
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.setenv("APP_ENV", "production")

    monkeypatch.setenv("AUTH_REDIS_ENV_STRATEGY", "legacy")
    assert se.is_auth_redis_required_env_legacy() is False
    assert se.is_auth_redis_required_env_target() is True
    assert se.is_auth_redis_required_env() is False

    monkeypatch.setenv("AUTH_REDIS_ENV_STRATEGY", "normalized")
    assert se.is_auth_redis_required_env() is True


def test_is_auth_redis_normalized_not_staging(monkeypatch):
    monkeypatch.setenv("AUTH_REDIS_ENV_STRATEGY", "normalized")
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert se.is_auth_redis_required_env_legacy() is True
    assert se.is_auth_redis_required_env_target() is False
    assert se.is_auth_redis_required_env() is False


def test_should_expose_dev_otp_never_prod_like(monkeypatch):
    monkeypatch.setenv("TWO_FACTOR_DEV_EXPOSE_CODE", "true")
    monkeypatch.setenv("APP_ENV", "development")
    assert se.should_expose_dev_otp_code() is True
    monkeypatch.setenv("APP_ENV", "staging")
    assert se.should_expose_dev_otp_code() is False


def test_validate_startup_rejects_prod_with_fixed_code(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "111111")
    with pytest.raises(RuntimeError, match="TWO_FACTOR_DEV_FIXED_CODE"):
        se.validate_security_environment_startup(testing=False)


def test_validate_startup_allows_development_with_fixed_code(monkeypatch):
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "111111")
    se.validate_security_environment_startup(testing=False)


def test_validate_startup_testing_skips(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("TWO_FACTOR_DEV_FIXED_CODE", "111111")
    se.validate_security_environment_startup(testing=True)


def test_security_correlation_on_emit_tuple_excludes_on(monkeypatch):
    """Historique : ``on`` ne compte pas comme vrai (contrairement aux autres flags)."""
    monkeypatch.setenv("SECURITY_CORRELATION_ON_EMIT", "on")
    assert se.is_security_correlation_on_emit_enabled() is False
    monkeypatch.setenv("SECURITY_CORRELATION_ON_EMIT", "true")
    assert se.is_security_correlation_on_emit_enabled() is True


def test_passkey_auto_max_login_risk_bounds(monkeypatch):
    monkeypatch.setenv("PASSKEY_AUTO_MAX_LOGIN_RISK", "999")
    assert se.passkey_auto_max_login_risk() == 95
    monkeypatch.setenv("PASSKEY_AUTO_MAX_LOGIN_RISK", "not-int")
    assert se.passkey_auto_max_login_risk() == 48


def test_auth_rate_limit_backend_for_bootstrap_empty_when_unset(monkeypatch):
    monkeypatch.delenv("AUTH_RL_BACKEND", raising=False)
    assert se.auth_rate_limit_backend_for_bootstrap() == ""
