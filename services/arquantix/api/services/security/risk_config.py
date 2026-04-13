"""
Configuration centralisée des poids / seuils du moteur de risque (Phase 5F).

- Valeurs par défaut déterministes (alignées sur l’historique Phase 5D).
- Surcharges via ``RISK_WEIGHTS_JSON`` (JSON objet) et/ou ``RISK_WEIGHT_<KEY>`` (scalaires).
- Overrides runtime (A/B) via ``risk_experiments`` + ContextVar — jamais d’application silencieuse.
"""
from __future__ import annotations

import json
import logging
import os
from contextvars import ContextVar
from typing import Any, Dict, Optional

logger = logging.getLogger("arquantix.security.risk_config")

# Poids comportementaux & géo (clés stables pour calibration / expériences)
DEFAULT_RISK_WEIGHTS: Dict[str, float] = {
    # Appareil (5D.1)
    "device_new": 20.0,
    "device_known": -10.0,
    "device_no_baseline": 5.0,
    "device_multi_new": 25.0,
    # Vélocité géographique (branches)
    "geo_velocity_no_delta": 5.0,
    "geo_velocity_30min": 40.0,
    "geo_velocity_2h": 25.0,
    "geo_velocity_6h": 15.0,
    "geo_velocity_slow": 5.0,
    # Risque pays
    "geo_country_unknown": 5.0,
    "geo_country_high_risk": 15.0,
    "geo_country_medium": 5.0,
    "geo_country_low": 0.0,
    "geo_stability_bonus": -5.0,
    # Rafales
    "action_burst_moderate": 10.0,
    "action_burst_high": 25.0,
    "action_burst_homogeneous": 20.0,
    "action_burst_mixed": 10.0,
    "action_burst_homogeneous_cap": 25.0,
    # Sessions / compte / login (comportemental)
    "multi_session_few": 5.0,
    "multi_session_many": 15.0,
    "account_age_lt1d": 30.0,
    "account_age_lt7d": 20.0,
    "account_age_lt30d": 10.0,
    "login_passkey": -10.0,
    "login_password_only": 10.0,
    # Phase 5E — ajustement segment (clés = segment_adjustment_<segment>)
    "segment_adjustment_trusted_user": -10.0,
    "segment_adjustment_high_value_user": -5.0,
    "segment_adjustment_new_user": 10.0,
    "segment_adjustment_risky_user": 20.0,
    "segment_adjustment_normal_user": 0.0,
}

_WEIGHT_OVERRIDES_CTX: ContextVar[Optional[Dict[str, float]]] = ContextVar(
    "risk_weight_overrides_ctx",
    default=None,
)


def calibration_version() -> str:
    """Version logique de la config (pas d’auto-mutation)."""
    return (os.getenv("RISK_CALIBRATION_VERSION") or "1").strip() or "1"


def _parse_env_scalar_overrides() -> Dict[str, float]:
    """Ex. ``RISK_WEIGHT_DEVICE_NEW=22`` → clé ``device_new``."""
    out: Dict[str, float] = {}
    skip = frozenset({"RISK_WEIGHTS_JSON", "RISK_CALIBRATION_VERSION"})
    for k, v in os.environ.items():
        if not k.startswith("RISK_WEIGHT_") or k in skip:
            continue
        key = k[len("RISK_WEIGHT_") :].lower()
        try:
            out[key] = float(str(v).strip())
        except ValueError:
            logger.warning("Invalid %s=%r — ignored", k, v)
    return out


def _parse_json_overrides() -> Dict[str, float]:
    raw = (os.getenv("RISK_WEIGHTS_JSON") or "").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        return {str(k): float(v) for k, v in data.items()}
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning("Invalid RISK_WEIGHTS_JSON — ignored: %s", e)
        return {}


def _merged_static_weights() -> Dict[str, float]:
    merged = dict(DEFAULT_RISK_WEIGHTS)
    merged.update(_parse_json_overrides())
    merged.update(_parse_env_scalar_overrides())
    return merged


def get_risk_weight(key: str, *, default: Optional[float] = None) -> float:
    """
    Poids effectif pour une clé logique.
    Ordre : défauts → JSON env → RISK_WEIGHT_* → overrides runtime (A/B).
    """
    static = _merged_static_weights()
    if default is None:
        default = static.get(key, 0.0)
    base = float(static.get(key, default))
    runtime = _WEIGHT_OVERRIDES_CTX.get()
    if runtime and key in runtime:
        return float(runtime[key])
    return base


def push_runtime_weight_overrides(overrides: Dict[str, float]):
    """Retourne un jeton pour ``pop_runtime_weight_overrides`` (safe requête par requête)."""
    return _WEIGHT_OVERRIDES_CTX.set(dict(overrides))


def pop_runtime_weight_overrides(token) -> None:
    _WEIGHT_OVERRIDES_CTX.reset(token)


class runtime_weight_overrides:
    """Context manager pour overrides A/B (async-safe via ContextVar)."""

    def __init__(self, overrides: Optional[Dict[str, float]]) -> None:
        self._overrides = overrides
        self._token: Any = None

    def __enter__(self) -> None:
        prev = _WEIGHT_OVERRIDES_CTX.get()
        merged: Dict[str, float] = {}
        if prev:
            merged.update(prev)
        if self._overrides:
            merged.update(self._overrides)
        self._token = _WEIGHT_OVERRIDES_CTX.set(merged if merged else None)

    def __exit__(self, *args: Any) -> None:
        if self._token is not None:
            _WEIGHT_OVERRIDES_CTX.reset(self._token)
        self._token = None


def snapshot_effective_weights() -> Dict[str, float]:
    """Instantané des poids effectifs (défaut + env + runtime) pour logs / audit."""
    static = _merged_static_weights()
    runtime = _WEIGHT_OVERRIDES_CTX.get() or {}
    out = dict(static)
    out.update(runtime)
    return out
