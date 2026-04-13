"""
Moteur de risque déterministe (Phase 5C) — scores pondérés, facteurs explicables, sans ML.

S’intègre **après** la politique stricte + friction adaptative ; ne remplace pas ``sensitive_action_map``.
"""
from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Union

from pydantic import BaseModel, Field

from services.security.sensitive_action_map import (
    SensitiveActionPolicy,
    auth_level_to_tier,
)
from services.security.risk_config import (
    calibration_version,
    get_risk_weight,
    runtime_weight_overrides,
    snapshot_effective_weights,
)
from services.security.risk_experiments import assign_variant, load_variant_weight_overrides
from services.security.security_env import (
    is_adaptive_friction_enabled,
    is_adaptive_intelligence_enabled,
    is_behavioral_risk_enabled,
    is_device_risk_enabled,
    is_geo_velocity_enabled,
    is_risk_experiments_enabled,
    low_risk_recent_auth_seconds,
    low_risk_transfer_amount_eur,
)
from services.security.session_intelligence_service import (
    should_force_reauth,
    should_require_step_up,
)

logger = logging.getLogger("arquantix.security.risk_engine")

# ---------------------------------------------------------------------------
# Modèles
# ---------------------------------------------------------------------------


class RiskFactorContribution(BaseModel):
    code: str
    weight: float
    value: Union[str, float, int, bool, None] = None
    description: str


class RiskEvaluation(BaseModel):
    risk_score: float = Field(ge=0.0, le=100.0)
    risk_level: str
    factors: List[RiskFactorContribution] = Field(default_factory=list)
    base_action_score: float
    final_action_key: str
    recommended_outcome: str  # "allow" | "step_up" | "reauth"
    override_reason: Optional[str] = None  # behavioral_force_reauth | behavioral_force_step_up
    behavioral_flags: List[str] = Field(default_factory=list)
    user_segment: str = "normal_user"
    dynamic_thresholds_used: Optional[Dict[str, Any]] = None
    experiment_id: Optional[str] = None
    variant: str = "control"
    calibration_version: str = "1"


@dataclass
class BehavioralRiskContext:
    """Entrées comportementales Phase 5D (dégradation gracieuse si champs absents)."""

    ip_address: Optional[str] = None
    geo_country: Optional[str] = None
    previous_geo_country: Optional[str] = None
    last_action_timestamp: Optional[datetime] = None
    last_action_geo: Optional[str] = None
    device_fingerprint_id: Optional[str] = None
    known_device_ids: Optional[List[str]] = None
    session_count_recent: Optional[int] = None
    action_count_last_5min: Optional[int] = None
    action_count_last_1h: Optional[int] = None
    account_creation_age_days: Optional[float] = None
    login_method: Optional[str] = None
    new_devices_recent_count: Optional[int] = None
    action_type: Optional[str] = None
    recent_action_types: Optional[List[str]] = None
    same_type_action_count_5min: Optional[int] = None
    raw_meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UserSegmentationInput:
    """Entrées optionnelles Phase 5E — dégradation gracieuse si champs absents."""

    account_age_days: Optional[float] = None
    total_volume_eur: Optional[float] = None
    successful_actions_count: Optional[int] = None
    historical_anomaly_count: Optional[int] = None
    kyc_level: Optional[str] = None
    trust_level: Optional[str] = None


# Seuils volume / anomalies (déterministes, documentés dans PHASE_5E)
_HIGH_VOLUME_EUR_THRESHOLD = 50_000.0
_RISKY_ANOMALY_COUNT_MIN = 2


def _norm_kyc(k: Optional[str]) -> Optional[str]:
    if not k:
        return None
    return str(k).strip().upper() or None


def _kyc_allows_trusted(kyc_level: Optional[str]) -> bool:
    k = _norm_kyc(kyc_level)
    if k is None:
        return True
    return k in ("VERIFIED", "FULL", "GOLD", "ADVANCED")


def derive_user_segment(inp: Optional[UserSegmentationInput]) -> str:
    """Règles déterministes, ordre de priorité fixe (sans ML)."""
    if inp is None:
        return "normal_user"
    anomalies = inp.historical_anomaly_count
    if anomalies is not None and int(anomalies) >= _RISKY_ANOMALY_COUNT_MIN:
        return "risky_user"
    age = inp.account_age_days
    if age is not None and float(age) < 7.0:
        return "new_user"
    vol = inp.total_volume_eur
    if vol is not None and float(vol) >= _HIGH_VOLUME_EUR_THRESHOLD:
        return "high_value_user"
    if (
        age is not None
        and float(age) >= 90.0
        and (anomalies is None or int(anomalies) == 0)
        and _kyc_allows_trusted(inp.kyc_level)
    ):
        return "trusted_user"
    return "normal_user"


def segment_score_adjustment_weight(segment: str) -> float:
    return get_risk_weight(f"segment_adjustment_{segment}", default=0.0)


def segment_risk_thresholds(
    segment: str,
    *,
    default_high: float,
    default_critical: float,
) -> tuple[float, float]:
    if segment == "trusted_user":
        return 60.0, 80.0
    if segment in ("new_user", "risky_user"):
        return 40.0, 65.0
    if segment == "high_value_user":
        return 55.0, 75.0
    return float(default_high), float(default_critical)


def resolve_low_risk_transfer_amount_eur_for_segment(segment: str) -> float:
    """Seuil transfert bas risque (friction adaptive) par segment — Phase 5E."""
    return {
        "new_user": 100.0,
        "normal_user": 500.0,
        "trusted_user": 2000.0,
        "high_value_user": 5000.0,
        "risky_user": 50.0,
    }.get(segment, low_risk_transfer_amount_eur())


def resolve_low_risk_recent_auth_seconds_for_segment(segment: str) -> int:
    return {
        "new_user": 300,
        "normal_user": 900,
        "trusted_user": 1200,
        "high_value_user": 900,
        "risky_user": 120,
    }.get(segment, low_risk_recent_auth_seconds())


def resolve_device_tolerance_for_segment(segment: str) -> float:
    """1.0 = neutre ; >1 = plus tolérant ; <1 = plus strict (observabilité / extensions)."""
    return {
        "trusted_user": 1.2,
        "high_value_user": 1.1,
        "normal_user": 1.0,
        "new_user": 0.9,
        "risky_user": 0.65,
    }.get(segment, 1.0)


def build_dynamic_thresholds_dict(segment: str) -> Dict[str, Any]:
    return {
        "low_risk_transfer_amount_eur": resolve_low_risk_transfer_amount_eur_for_segment(segment),
        "recent_auth_seconds": resolve_low_risk_recent_auth_seconds_for_segment(segment),
        "device_tolerance": resolve_device_tolerance_for_segment(segment),
    }


def extract_segmentation_inputs(
    request: Any,
    current_user: Any,
    intelligence: Any,
) -> UserSegmentationInput:
    """En-têtes optionnels + champs utilisateur / SI (sans journaliser de PII)."""
    h = request.headers if request is not None else {}
    get = _header_get

    age_days: Optional[float] = None
    if current_user is not None:
        ca = getattr(current_user, "created_at", None)
        if ca is not None:
            if getattr(ca, "tzinfo", None) is None:
                ca = ca.replace(tzinfo=timezone.utc)
            age_days = max(0.0, (_utcnow() - ca).total_seconds() / 86400.0)
    kyc = (get(h, "x-user-kyc-level") or "").strip() or None
    if not kyc and current_user is not None:
        kyc = getattr(current_user, "kyc_tier", None) or getattr(current_user, "kyc_level", None)
        if kyc is not None:
            kyc = str(kyc).strip() or None

    try:
        vol_raw = get(h, "x-user-lifetime-volume-eur")
        vol = float(str(vol_raw).strip()) if vol_raw is not None and str(vol_raw).strip() != "" else None
    except (TypeError, ValueError):
        vol = None

    try:
        sac_raw = get(h, "x-user-successful-actions-count")
        sac = int(str(sac_raw).strip()) if sac_raw is not None and str(sac_raw).strip() != "" else None
    except (TypeError, ValueError):
        sac = None

    try:
        hac_raw = get(h, "x-user-historical-anomaly-count")
        hac = int(str(hac_raw).strip()) if hac_raw is not None and str(hac_raw).strip() != "" else None
    except (TypeError, ValueError):
        hac = None
    if hac is None and intelligence is not None:
        hac = getattr(intelligence, "historical_anomaly_count", None)
        if hac is not None:
            try:
                hac = int(hac)
            except (TypeError, ValueError):
                hac = None

    trust = (get(h, "x-user-trust-level") or "").strip() or None
    if not trust and intelligence is not None:
        trust = str(getattr(intelligence, "device_trust_level", "") or "").strip() or None

    return UserSegmentationInput(
        account_age_days=age_days,
        total_volume_eur=vol,
        successful_actions_count=sac,
        historical_anomaly_count=hac,
        kyc_level=kyc,
        trust_level=trust,
    )


def _segment_soften_blocked(
    *,
    prelim_score: float,
    geo_velocity_raw: float,
    strict_require_reauth: bool,
) -> bool:
    """Ne pas appliquer d’ajustement négatif si le score « nu » est déjà critique ou contexte dangereux."""
    if strict_require_reauth:
        return True
    if float(geo_velocity_raw) >= 40.0:
        return True
    if derive_risk_level(prelim_score, high_threshold=50.0, critical_threshold=75.0) == "critical":
        return True
    return False


def _apply_segment_adjustment_weight(
    segment: str,
    raw_weight: float,
    *,
    prelim_score: float,
    geo_velocity_raw: float,
    strict_require_reauth: bool,
) -> float:
    w = float(raw_weight)
    if w >= 0:
        return clamp_behavioral_weight(w)
    if _segment_soften_blocked(
        prelim_score=prelim_score,
        geo_velocity_raw=geo_velocity_raw,
        strict_require_reauth=strict_require_reauth,
    ):
        return 0.0
    return clamp_behavioral_weight(w)


# ---------------------------------------------------------------------------
# Scores de base par action (3C.A)
# ---------------------------------------------------------------------------

_BASE_ACTION_SCORES: Dict[str, float] = {
    "withdrawal": 55.0,
    "wallet_transfer": 45.0,
    "internal_transfer_low": 20.0,
    "beneficiary_add": 50.0,
    "api_key_create": 60.0,
    "security_settings_change": 50.0,
    "passcode_reset": 55.0,
    "biometric_disable": 45.0,
    "contact_change": 45.0,
    "view_sensitive_data": 30.0,
    "view_portfolio": 25.0,
    "data_export": 50.0,
    "session_revoke_all": 35.0,
    "change_password": 35.0,
}


def base_score_for_action(action_key: str) -> float:
    k = (action_key or "").strip().lower()
    return _BASE_ACTION_SCORES.get(k, 30.0)


def clamp_risk_score(score: float) -> float:
    return max(0.0, min(100.0, float(score)))


def derive_risk_level(
    score: float,
    *,
    high_threshold: float = 50.0,
    critical_threshold: float = 75.0,
) -> str:
    s = clamp_risk_score(score)
    if s >= critical_threshold:
        return "critical"
    if s >= high_threshold:
        return "high"
    if s >= 25.0:
        return "medium"
    return "low"


def summarize_risk_factors(factors: Sequence[RiskFactorContribution]) -> str:
    parts = [f"{f.code}({f.weight:+.0f})" for f in factors]
    return "; ".join(parts) if parts else ""


def clamp_behavioral_weight(w: float) -> float:
    """Phase 5D — borne chaque facteur comportemental (spéc : −20 … +40)."""
    return max(-20.0, min(40.0, float(w)))


# Pays ISO2 — cartes statiques internes (déterministes, sans appel externe)
_GEO_LOW = frozenset(
    {"AT", "BE", "CH", "DE", "FR", "IE", "LU", "NL", "NO", "SE", "DK", "FI", "IS", "NZ", "SG", "JP", "KR", "AU", "CA"}
)
_GEO_MEDIUM = frozenset(
    {"US", "GB", "UK", "ES", "IT", "PT", "PL", "CZ", "GR", "CY", "MT", "HU", "RO", "BG", "HR", "BR", "MX", "IN", "AE"}
)
_GEO_HIGH = frozenset(
    {"AF", "IR", "KP", "SY", "RU", "BY", "MM", "VE", "CU"}
)


def _norm_cc(code: Optional[str]) -> Optional[str]:
    if not code:
        return None
    s = str(code).strip().upper()
    if len(s) >= 2:
        return s[:2]
    return None


def _geo_country_risk_weight(geo_country: Optional[str]) -> tuple[float, str]:
    cc = _norm_cc(geo_country)
    if cc is None:
        return get_risk_weight("geo_country_unknown"), "Pays actuel inconnu — prudence modérée."
    if cc in _GEO_HIGH:
        return get_risk_weight("geo_country_high_risk"), "Zone géographique à vigilance renforcée."
    if cc in _GEO_MEDIUM:
        return get_risk_weight("geo_country_medium"), "Zone géographique à vigilance standard."
    if cc in _GEO_LOW:
        return get_risk_weight("geo_country_low"), "Zone géographique habituellement stable."
    return get_risk_weight("geo_country_unknown"), "Zone géographique non classée — prudence modérée."


def _geo_velocity_factor(
    *,
    current_cc: Optional[str],
    previous_cc: Optional[str],
    delta_seconds: Optional[float],
) -> tuple[float, float, str]:
    """
    Retourne (poids brut pour override, poids clampé, description).
    Même pays → 0. Changement de pays selon délai.
    """
    cur = _norm_cc(current_cc)
    prev = _norm_cc(previous_cc)
    if cur is None or prev is None:
        return 0.0, 0.0, "Position géographique incomplète — vélocité non évaluée."
    if cur == prev:
        return 0.0, 0.0, "Même pays qu’auparavant."
    if delta_seconds is None or delta_seconds < 0:
        w = get_risk_weight("geo_velocity_no_delta")
        return w, clamp_behavioral_weight(w), "Changement de pays sans horodatage fiable."
    if delta_seconds <= 30 * 60:
        w = get_risk_weight("geo_velocity_30min")
        return w, clamp_behavioral_weight(w), "Déplacement entre pays très rapide — situation inhabituelle."
    if delta_seconds <= 2 * 3600:
        w = get_risk_weight("geo_velocity_2h")
        return w, clamp_behavioral_weight(w), "Changement de pays dans un délai court."
    if delta_seconds <= 6 * 3600:
        w = get_risk_weight("geo_velocity_6h")
        return w, clamp_behavioral_weight(w), "Changement de pays dans les dernières heures."
    w = get_risk_weight("geo_velocity_slow")
    return w, clamp_behavioral_weight(w), "Changement de pays sur une période plus longue."


def _device_consistency_factor(
    *,
    fingerprint: Optional[str],
    known_ids: Optional[List[str]],
    new_devices_recent_count: Optional[int],
) -> RiskFactorContribution:
    """Phase 5D.1 — baseline vide (+5) vs nouveau vs connu ; clamp par facteur."""
    fp = (fingerprint or "").strip()[:128] or None
    known = [str(x).strip() for x in (known_ids or []) if str(x).strip()]
    w = 0.0
    if fp and known:
        if fp in known:
            w = get_risk_weight("device_known")
            code = "device_known"
            desc = "Appareil reconnu et de confiance."
        else:
            w = get_risk_weight("device_new")
            code = "device_new"
            desc = "Nouvel appareil par rapport à la liste connue."
    elif fp and not known:
        w = get_risk_weight("device_no_baseline")
        code = "device_no_baseline"
        desc = "Pas encore de référence d’appareils — prudence légère."
    else:
        code = "device_signal_absent"
        desc = "Empreinte appareil absente — cohérence non vérifiée."
    if new_devices_recent_count is not None and int(new_devices_recent_count) >= 3:
        w += get_risk_weight("device_multi_new")
        desc = (desc + " ") if desc else ""
        desc += "Plusieurs nouveaux appareils récemment."
    if not fp and (new_devices_recent_count is None or int(new_devices_recent_count) < 3):
        return RiskFactorContribution(
            code="device_signal_absent",
            weight=0.0,
            value=None,
            description="Cohérence appareil non évaluée (signaux manquants).",
        )
    return RiskFactorContribution(
        code=code,
        weight=clamp_behavioral_weight(w),
        value=fp[:16] + "…" if fp and len(fp) > 16 else fp,
        description=desc.strip(),
    )


def _count_same_type_actions(
    action_type: Optional[str],
    recent_action_types: Optional[List[str]],
) -> Optional[int]:
    if not action_type or not recent_action_types:
        return None
    at = str(action_type).strip().lower()
    n = 0
    for x in recent_action_types:
        if str(x).strip().lower() == at:
            n += 1
    return n


def _behavioral_action_burst(
    action_count_last_5min: Optional[int],
    action_type: Optional[str],
    recent_action_types: Optional[List[str]],
    same_type_action_count_5min: Optional[int],
) -> RiskFactorContribution:
    """Rafale 5 min — logique historique ou raffinement homogène / mixte (5D.1)."""
    if action_count_last_5min is None:
        return RiskFactorContribution(
            code="action_burst",
            weight=0.0,
            value=None,
            description="Fréquence d’actions (5 min) non fournie.",
        )
    n = int(action_count_last_5min)
    if n <= 2:
        return RiskFactorContribution(
            code="action_burst",
            weight=0.0,
            value=n,
            description="Peu d’actions récentes (5 min).",
        )

    st_count = same_type_action_count_5min
    if st_count is None:
        st_count = _count_same_type_actions(action_type, recent_action_types)

    refined = st_count is not None and (action_type and str(action_type).strip())

    if refined:
        homogeneous = int(st_count) >= 3
        if homogeneous:
            w = get_risk_weight("action_burst_homogeneous")
            code = "action_burst_homogeneous"
            desc = "Même type d’action répété plusieurs fois — vigilance accrue."
        else:
            w = get_risk_weight("action_burst_mixed")
            code = "action_burst_mixed"
            desc = "Plusieurs actions de types différents en peu de temps."
        if n > 5:
            w = min(get_risk_weight("action_burst_homogeneous_cap"), w)
        return RiskFactorContribution(
            code=code,
            weight=clamp_behavioral_weight(w),
            value=n,
            description=desc,
        )

    if n <= 5:
        return RiskFactorContribution(
            code="action_burst",
            weight=clamp_behavioral_weight(get_risk_weight("action_burst_moderate")),
            value=n,
            description="Plusieurs actions en peu de temps.",
        )
    return RiskFactorContribution(
        code="action_burst",
        weight=clamp_behavioral_weight(get_risk_weight("action_burst_high")),
        value=n,
        description="Nombre élevé d’actions en peu de temps.",
    )


def _geo_stability_bonus_factor(
    b: BehavioralRiskContext,
    raw_geo_velocity: float,
    intelligence: Any,
) -> Optional[RiskFactorContribution]:
    """Bonus léger si pays stable — jamais si anomalie de vélocité géographique."""
    if raw_geo_velocity > 0:
        return None
    cur = _norm_cc(b.geo_country)
    prev = _norm_cc(b.previous_geo_country)
    if not cur or not prev or cur != prev:
        return None
    delta = _behavioral_delta_seconds(b)
    recent_ok = delta is not None and 0 <= float(delta) <= 86400.0
    intel_ok = False
    if intelligence is not None:
        if "country_changed" not in _intel_reasons(intelligence):
            if _norm_cc(getattr(intelligence, "last_country", None)) == cur:
                intel_ok = True
    if not (recent_ok or intel_ok):
        return None
    return RiskFactorContribution(
        code="geo_stability_bonus",
        weight=clamp_behavioral_weight(get_risk_weight("geo_stability_bonus")),
        value=cur,
        description="Comportement géographique cohérent sur la période récente.",
    )


def _multi_session_risk(session_count_recent: Optional[int]) -> tuple[float, str]:
    if session_count_recent is None:
        return 0.0, "Nombre de sessions actives non fourni."
    n = int(session_count_recent)
    if n <= 1:
        return 0.0, "Une session active (ou non précisée)."
    if n <= 3:
        return clamp_behavioral_weight(get_risk_weight("multi_session_few")), "Plusieurs sessions actives."
    return clamp_behavioral_weight(get_risk_weight("multi_session_many")), "Nombre élevé de sessions actives."


def _account_age_risk(age_days: Optional[float]) -> tuple[float, str]:
    if age_days is None:
        return 0.0, "Ancienneté du compte non connue."
    d = float(age_days)
    if d < 1:
        return clamp_behavioral_weight(get_risk_weight("account_age_lt1d")), "Compte très récent."
    if d < 7:
        return clamp_behavioral_weight(get_risk_weight("account_age_lt7d")), "Compte créé récemment."
    if d < 30:
        return clamp_behavioral_weight(get_risk_weight("account_age_lt30d")), "Compte encore jeune."
    return 0.0, "Compte établi."


def _login_method_trust(login_method: Optional[str]) -> tuple[float, str]:
    m = (login_method or "").strip().lower()
    if m in ("passkey", "webauthn", "fido2"):
        return clamp_behavioral_weight(get_risk_weight("login_passkey")), "Connexion renforcée (clé de sécurité)."
    if m in ("otp", "sms_otp", "email_otp", "password_otp"):
        return 0.0, "Connexion avec code à usage unique."
    if m in ("password", ""):
        return clamp_behavioral_weight(get_risk_weight("login_password_only")), "Connexion par mot de passe seul."
    return 0.0, "Méthode de connexion non précisée."


def _collect_behavioral_factors(
    b: BehavioralRiskContext,
    intelligence: Optional[Any] = None,
) -> List[RiskFactorContribution]:
    out: List[RiskFactorContribution] = []
    if not is_behavioral_risk_enabled():
        return out

    # Géo (sous-flags)
    if is_geo_velocity_enabled():
        raw_vel, w_vel, desc_vel = _geo_velocity_factor(
            current_cc=b.geo_country,
            previous_cc=b.previous_geo_country,
            delta_seconds=_behavioral_delta_seconds(b),
        )
        b.raw_meta["geo_velocity_raw"] = raw_vel
        out.append(
            RiskFactorContribution(
                code="geo_velocity_anomaly",
                weight=w_vel,
                value=round(raw_vel, 1),
                description=desc_vel,
            )
        )
        wr, desc_r = _geo_country_risk_weight(b.geo_country)
        out.append(
            RiskFactorContribution(
                code="geo_country_risk",
                weight=clamp_behavioral_weight(wr),
                value=_norm_cc(b.geo_country),
                description=desc_r,
            )
        )
        gs = _geo_stability_bonus_factor(b, raw_vel, intelligence)
        if gs is not None:
            out.append(gs)

    if is_device_risk_enabled():
        out.append(
            _device_consistency_factor(
                fingerprint=b.device_fingerprint_id,
                known_ids=b.known_device_ids,
                new_devices_recent_count=b.new_devices_recent_count,
            )
        )

    # Comportement général (master BEHAVIORAL)
    out.append(
        _behavioral_action_burst(
            b.action_count_last_5min,
            b.action_type,
            b.recent_action_types,
            b.same_type_action_count_5min,
        )
    )

    wm, dm = _multi_session_risk(b.session_count_recent)
    out.append(RiskFactorContribution(code="multi_session_risk", weight=wm, value=b.session_count_recent, description=dm))

    wa, da = _account_age_risk(b.account_creation_age_days)
    out.append(RiskFactorContribution(code="account_age_risk", weight=wa, value=b.account_creation_age_days, description=da))

    wl, dl = _login_method_trust(b.login_method)
    out.append(RiskFactorContribution(code="login_method_risk", weight=wl, value=b.login_method, description=dl))

    return out


def _behavioral_delta_seconds(b: BehavioralRiskContext) -> Optional[float]:
    t0 = b.last_action_timestamp
    if t0 is None:
        return None
    if getattr(t0, "tzinfo", None) is None:
        t0 = t0.replace(tzinfo=timezone.utc)
    return (_utcnow() - t0).total_seconds()


def _parse_iso_datetime(s: Optional[str]) -> Optional[datetime]:
    if not s or not str(s).strip():
        return None
    raw = str(s).strip()
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        t = datetime.fromisoformat(raw)
        if t.tzinfo is None:
            t = t.replace(tzinfo=timezone.utc)
        return t
    except ValueError:
        return None


def _parse_known_device_ids(header_val: Optional[str]) -> Optional[List[str]]:
    if not header_val:
        return None
    parts = [p.strip() for p in re.split(r"[,;]", str(header_val)) if p.strip()]
    return parts or None


def _parse_action_types_list(val: Optional[str]) -> Optional[List[str]]:
    if not val or not str(val).strip():
        return None
    parts = [p.strip() for p in re.split(r"[,;]", str(val)) if p.strip()]
    return parts or None


def _header_get(headers: Any, key: str, default: Any = None) -> Any:
    if not headers:
        return default
    return headers.get(key) or headers.get(key.upper()) or headers.get(key.lower()) or default


def extract_behavioral_context(
    request: Any,
    current_user: Any,
    intelligence: Any,
    session: Any,
) -> BehavioralRiskContext:
    """Construit le contexte comportemental à partir des en-têtes, session, SI et utilisateur."""
    h = request.headers if request is not None else {}
    get = _header_get

    geo = _norm_cc(get(h, "x-geo-country")) or _norm_cc(get(h, "cf-ipcountry"))
    prev = _norm_cc(get(h, "x-previous-geo-country")) or _norm_cc(
        getattr(intelligence, "last_country", None) if intelligence is not None else None
    )
    last_geo = _norm_cc(get(h, "x-last-action-geo")) or prev

    last_ts = _parse_iso_datetime(get(h, "x-last-action-at"))
    if last_ts is None and intelligence is not None:
        last_ts = getattr(intelligence, "last_sensitive_action_at", None) or getattr(
            intelligence, "last_activity_at", None
        )

    fp = (get(h, "x-device-fingerprint") or getattr(session, "fingerprint_hash", None) or "")[:128] or None
    known = _parse_known_device_ids(get(h, "x-known-device-ids"))

    try:
        sc = int(str(get(h, "x-session-count-recent")).strip()) if get(h, "x-session-count-recent") else None
    except (TypeError, ValueError):
        sc = None
    try:
        ac5 = int(str(get(h, "x-action-count-last-5min")).strip()) if get(h, "x-action-count-last-5min") else None
    except (TypeError, ValueError):
        ac5 = None
    try:
        ac1 = int(str(get(h, "x-action-count-last-1h")).strip()) if get(h, "x-action-count-last-1h") else None
    except (TypeError, ValueError):
        ac1 = None
    try:
        nd = int(str(get(h, "x-new-devices-recent-count")).strip()) if get(h, "x-new-devices-recent-count") else None
    except (TypeError, ValueError):
        nd = None

    at = (get(h, "x-action-type") or "").strip() or None
    rat = _parse_action_types_list(get(h, "x-recent-action-types"))
    try:
        stc_raw = get(h, "x-same-type-action-count-5min")
        stc = (
            int(str(stc_raw).strip())
            if stc_raw is not None and str(stc_raw).strip() != ""
            else None
        )
    except (TypeError, ValueError):
        stc = None

    age_days: Optional[float] = None
    if current_user is not None:
        ca = getattr(current_user, "created_at", None)
        if ca is not None:
            if getattr(ca, "tzinfo", None) is None:
                ca = ca.replace(tzinfo=timezone.utc)
            age_days = max(0.0, (_utcnow() - ca).total_seconds() / 86400.0)

    lm = (get(h, "x-login-method") or "").strip().lower() or None
    if not lm and intelligence is not None:
        lm = str(getattr(intelligence, "auth_strength", "") or "").lower() or None
    if not lm and session is not None:
        lm = str(getattr(session, "auth_strength", "") or "").lower() or None

    ip = None
    if request and request.client:
        ip = request.client.host

    return BehavioralRiskContext(
        ip_address=ip,
        geo_country=geo,
        previous_geo_country=prev,
        last_action_timestamp=last_ts,
        last_action_geo=last_geo,
        device_fingerprint_id=fp,
        known_device_ids=known,
        session_count_recent=sc,
        action_count_last_5min=ac5,
        action_count_last_1h=ac1,
        account_creation_age_days=age_days,
        login_method=lm,
        new_devices_recent_count=nd,
        action_type=at,
        recent_action_types=rat,
        same_type_action_count_5min=stc,
        raw_meta={},
    )


def _is_high_value_action(action_key: str, amount_eur: Optional[float]) -> bool:
    k = (action_key or "").strip().lower()
    if k not in ("withdrawal", "wallet_transfer", "beneficiary_add"):
        return False
    if amount_eur is None:
        return k in ("withdrawal", "wallet_transfer")
    return float(amount_eur) >= 1000.0


def _is_new_device(fingerprint: Optional[str], known_ids: Optional[List[str]]) -> bool:
    fp = (fingerprint or "").strip()
    known = [str(x).strip() for x in (known_ids or []) if str(x).strip()]
    if not fp or not known:
        return False
    return fp not in known


def _apply_hard_behavioral_overrides(
    *,
    action_key: str,
    amount_eur: Optional[float],
    b: BehavioralRiskContext,
    factors: List[RiskFactorContribution],
    geo_velocity_raw: float,
    action_burst_count: Optional[int],
) -> tuple[Optional[str], List[str]]:
    """
    Règles dures Phase 5D. Retourne (override_reason, behavioral_flags).
    """
    flags: List[str] = []
    reason: Optional[str] = None
    if not is_behavioral_risk_enabled():
        return None, flags

    if is_geo_velocity_enabled() and geo_velocity_raw >= 40.0:
        flags.append("geo_impossible_travel")
        reason = "behavioral_force_reauth"

    if (
        is_device_risk_enabled()
        and _is_new_device(b.device_fingerprint_id, b.known_device_ids)
        and amount_eur is not None
        and float(amount_eur) > 10000.0
        and (action_key or "").strip().lower() in ("withdrawal", "wallet_transfer")
    ):
        flags.append("new_device_high_amount")
        reason = "behavioral_force_reauth"

    if (
        action_burst_count is not None
        and int(action_burst_count) > 5
        and _is_high_value_action(action_key, amount_eur)
    ):
        flags.append("burst_high_value")
        if reason is None:
            reason = "behavioral_force_step_up"

    return reason, flags


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _intel_reasons(intelligence: Any) -> List[str]:
    raw = getattr(intelligence, "reason_codes_json", None) if intelligence is not None else None
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return []


def _seconds_since_step_up(last_step_up_at: Any) -> Optional[float]:
    if last_step_up_at is None:
        return None
    t = last_step_up_at
    if getattr(t, "tzinfo", None) is None:
        t = t.replace(tzinfo=timezone.utc)
    return (_utcnow() - t).total_seconds()


def _device_trust_adjustment(device_trust_level: Optional[str]) -> tuple[float, RiskFactorContribution]:
    dt = (device_trust_level or "").strip().upper()
    if dt in ("TRUSTED", "HIGH"):
        return -15.0, RiskFactorContribution(
            code="device_trusted",
            weight=-15.0,
            value=dt,
            description="Appareil considéré comme fiable.",
        )
    if dt == "MEDIUM":
        return 0.0, RiskFactorContribution(
            code="device_medium",
            weight=0.0,
            value=dt,
            description="Confiance appareil intermédiaire.",
        )
    return 20.0, RiskFactorContribution(
        code="device_untrusted",
        weight=20.0,
        value=dt or None,
        description="Appareil peu ou non fiable / inconnu.",
    )


def _auth_freshness_adjustment(last_step_up_at: Any) -> tuple[float, RiskFactorContribution]:
    sec = _seconds_since_step_up(last_step_up_at)
    if sec is None:
        return 15.0, RiskFactorContribution(
            code="auth_freshness_missing",
            weight=15.0,
            value=None,
            description="Pas d’horodatage de step-up récent.",
        )
    m = sec / 60.0
    if sec <= 300:
        return -15.0, RiskFactorContribution(
            code="auth_fresh_le_5min",
            weight=-15.0,
            value=round(sec, 1),
            description="Step-up très récent (≤ 5 min).",
        )
    if sec <= 900:
        return -8.0, RiskFactorContribution(
            code="auth_fresh_le_15min",
            weight=-8.0,
            value=round(sec, 1),
            description="Step-up récent (≤ 15 min).",
        )
    if sec <= 3600:
        return 0.0, RiskFactorContribution(
            code="auth_fresh_le_60min",
            weight=0.0,
            value=round(sec, 1),
            description="Step-up dans la dernière heure.",
        )
    return 15.0, RiskFactorContribution(
        code="auth_stale_gt_60min",
        weight=15.0,
        value=round(sec, 1),
        description="Step-up ancien ou absent (> 60 min).",
    )


def _amount_adjustment(
    action_key: str,
    amount_eur: Optional[float],
) -> tuple[float, RiskFactorContribution]:
    k = (action_key or "").strip().lower()
    transfer_like = k in (
        "withdrawal",
        "wallet_transfer",
        "internal_transfer_low",
    )
    if not transfer_like:
        return 0.0, RiskFactorContribution(
            code="amount_not_applicable",
            weight=0.0,
            value=None,
            description="Montant non pris en compte pour cette action.",
        )
    if amount_eur is None:
        return 5.0, RiskFactorContribution(
            code="amount_missing_penalty",
            weight=5.0,
            value=None,
            description="Montant inconnu pour une opération de transfert — prudence légère.",
        )
    a = float(amount_eur)
    if a < 100:
        return -10.0, RiskFactorContribution(
            code="amount_lt_100",
            weight=-10.0,
            value=a,
            description="Montant faible (< 100 EUR).",
        )
    if a < 1000:
        return 0.0, RiskFactorContribution(
            code="amount_100_1000",
            weight=0.0,
            value=a,
            description="Montant modéré (100–1000 EUR).",
        )
    if a < 10000:
        return 10.0, RiskFactorContribution(
            code="amount_1000_10000",
            weight=10.0,
            value=a,
            description="Montant élevé (1k–10k EUR).",
        )
    if a < 50000:
        return 20.0, RiskFactorContribution(
            code="amount_10000_50000",
            weight=20.0,
            value=a,
            description="Montant très élevé (10k–50k EUR).",
        )
    return 30.0, RiskFactorContribution(
        code="amount_ge_50000",
        weight=30.0,
        value=a,
        description="Montant critique (≥ 50k EUR).",
    )


def _same_owner_adjustment(same_owner: Optional[bool]) -> tuple[float, RiskFactorContribution]:
    if same_owner is True:
        return -10.0, RiskFactorContribution(
            code="same_owner_true",
            weight=-10.0,
            value=True,
            description="Transfert même titulaire / destination sûre indiquée.",
        )
    if same_owner is False:
        return 10.0, RiskFactorContribution(
            code="same_owner_false",
            weight=10.0,
            value=False,
            description="Destination autre titulaire — prudence accrue.",
        )
    return 0.0, RiskFactorContribution(
        code="same_owner_unknown",
        weight=0.0,
        value=None,
        description="Titulaire destination inconnu.",
    )


def _session_intel_adjustments(
    intelligence: Any,
    tier: str,
) -> List[RiskFactorContribution]:
    out: List[RiskFactorContribution] = []
    if intelligence is None:
        return out
    if should_require_step_up(intelligence, tier):
        out.append(
            RiskFactorContribution(
                code="si_requires_step_up",
                weight=20.0,
                value=True,
                description="Intelligence session : step-up requis.",
            )
        )
    if should_force_reauth(intelligence, tier):
        out.append(
            RiskFactorContribution(
                code="si_requires_reauth",
                weight=35.0,
                value=True,
                description="Intelligence session : réauth complète requise.",
            )
        )
    rs = int(getattr(intelligence, "last_risk_score", 0) or 0)
    if rs >= 70:
        out.append(
            RiskFactorContribution(
                code="session_risk_elevated",
                weight=15.0,
                value=rs,
                description="Score de risque session élevé.",
            )
        )
    reasons = _intel_reasons(intelligence)
    if any(x in reasons for x in ("country_changed",)):
        out.append(
            RiskFactorContribution(
                code="country_changed_signal",
                weight=35.0,
                value="country_changed",
                description="Changement de pays détecté (classe réauth).",
            )
        )
    return out


def _burst_adjustment(recent_similar_count: Optional[int]) -> tuple[float, RiskFactorContribution]:
    if recent_similar_count is None:
        return 0.0, RiskFactorContribution(
            code="burst_signal_unavailable",
            weight=0.0,
            value=None,
            description="Fréquence d’actions similaires non fournie (signal absent).",
        )
    n = int(recent_similar_count)
    if n <= 1:
        return 0.0, RiskFactorContribution(
            code="burst_0_1",
            weight=0.0,
            value=n,
            description="Peu d’actions similaires récentes.",
        )
    if n <= 4:
        return 10.0, RiskFactorContribution(
            code="burst_2_4",
            weight=10.0,
            value=n,
            description="Rafale modérée d’actions similaires.",
        )
    return 20.0, RiskFactorContribution(
        code="burst_5_plus",
        weight=20.0,
        value=n,
        description="Rafale élevée d’actions similaires.",
    )


def _sensitive_read_breadth(action_key: str) -> tuple[float, RiskFactorContribution]:
    k = (action_key or "").strip().lower()
    if k == "view_sensitive_data":
        return 10.0, RiskFactorContribution(
            code="read_scope_identity_kyc",
            weight=10.0,
            value=k,
            description="Lecture sensible (KYC / identité / intelligence session).",
        )
    if k == "data_export":
        return 20.0, RiskFactorContribution(
            code="read_scope_bulk_export",
            weight=20.0,
            value=k,
            description="Export / accès large de données.",
        )
    if k in ("view_portfolio", "view_balances_summary"):
        return 0.0, RiskFactorContribution(
            code="read_scope_simple",
            weight=0.0,
            value=k,
            description="Lecture protégée simple.",
        )
    return 0.0, RiskFactorContribution(
        code="read_scope_default",
        weight=0.0,
        value=k,
        description="Lecture — périmètre par défaut.",
    )


def _incomplete_signal_penalty(
    action_key: str,
    amount_eur: Optional[float],
    same_owner: Optional[bool],
) -> tuple[float, RiskFactorContribution]:
    """+5 si signal attendu manquant (sans doubler la pénalité « montant absent » déjà dans _amount_adjustment)."""
    k = (action_key or "").strip().lower()
    if k in ("withdrawal", "wallet_transfer") and amount_eur is None:
        return 0.0, RiskFactorContribution(
            code="legacy_uncertainty_none",
            weight=0.0,
            value=None,
            description="Montant déjà pénalisé ailleurs.",
        )
    if k == "wallet_transfer" and same_owner is None:
        return 5.0, RiskFactorContribution(
            code="legacy_uncertainty_same_owner",
            weight=5.0,
            value=None,
            description="Titulaire destination non indiqué — prudence.",
        )
    return 0.0, RiskFactorContribution(
        code="legacy_uncertainty_none",
        weight=0.0,
        value=None,
        description="Pénalité d’incomplétude non applicable.",
    )


def _downgrade_wallet_to_internal_transfer_low(
    *,
    action_key: str,
    risk_score: float,
    amount_eur: Optional[float],
    same_owner: Optional[bool],
    device_trust_level: Optional[str],
    intelligence: Any,
    tier: str,
) -> tuple[str, List[RiskFactorContribution]]:
    """Retourne (final_key, facteurs additionnels si downgrade)."""
    fk = action_key
    extra: List[RiskFactorContribution] = []
    if not is_adaptive_friction_enabled():
        return fk, extra
    if (action_key or "").strip().lower() != "wallet_transfer":
        return fk, extra
    if amount_eur is None:
        return fk, extra
    if same_owner is not True:
        return fk, extra
    if float(amount_eur) >= low_risk_transfer_amount_eur():
        return fk, extra
    dt = (device_trust_level or "").strip().upper()
    if dt not in ("HIGH", "TRUSTED"):
        return fk, extra
    if intelligence is None:
        return fk, extra
    if not _recent_auth_within(intelligence, low_risk_recent_auth_seconds()):
        return fk, extra
    if should_require_step_up(intelligence, tier) or should_force_reauth(intelligence, tier):
        return fk, extra
    if risk_score >= 25.0:
        return fk, extra
    extra.append(
        RiskFactorContribution(
            code="downgraded_to_internal_transfer_low",
            weight=0.0,
            value="internal_transfer_low",
            description="Reclassement sûr vers internal_transfer_low (Phase 5C).",
        )
    )
    return "internal_transfer_low", extra


def _recent_auth_within(intelligence: Any, max_age_seconds: int) -> bool:
    t = getattr(intelligence, "last_step_up_at", None)
    if t is None:
        return False
    if getattr(t, "tzinfo", None) is None:
        t = t.replace(tzinfo=timezone.utc)
    return (_utcnow() - t).total_seconds() <= float(max_age_seconds)


def _recommended_outcome(
    *,
    risk_level: str,
    strict_require_reauth: bool,
    adaptive_friction_applied: bool,
    user_segment: str = "normal_user",
    adaptive_intelligence_enabled: bool = False,
) -> str:
    if strict_require_reauth:
        return "reauth"
    if risk_level == "critical":
        return "reauth"
    if risk_level == "high":
        return "step_up"
    if risk_level == "medium":
        if adaptive_intelligence_enabled and user_segment == "trusted_user":
            return "allow"
        if adaptive_intelligence_enabled and user_segment == "risky_user":
            return "step_up"
        return "allow" if adaptive_friction_applied else "step_up"
    return "allow"


def evaluate_request_risk(
    *,
    action_key: str,
    policy: SensitiveActionPolicy,
    request: Any,
    current_user: Any,
    intelligence: Any,
    device_trust_level: Optional[str],
    last_step_up_at: Any,
    amount_eur: Optional[float],
    same_owner: Optional[bool],
    strict_decision_context: Optional[Dict[str, Any]] = None,
    high_threshold: float = 50.0,
    critical_threshold: float = 75.0,
    burst_recent_count_override: Optional[int] = None,
    behavioral_context: Optional[BehavioralRiskContext] = None,
    session: Optional[Any] = None,
    segmentation_inputs: Optional[UserSegmentationInput] = None,
) -> RiskEvaluation:
    """
    Évalue un score de risque déterministe. Les entrées manquantes sont gérées sans lever
    (facteurs documentés, pénalités légères si pertinent). Phase 5D : signaux comportementaux optionnels.
    Phase 5E (si ``ADAPTIVE_INTELLIGENCE_ENABLED``) : segmentation + ajustement + seuils dynamiques.
    """
    uid = ""
    if current_user is not None:
        uid = str(getattr(current_user, "id", "") or "")
    if request is not None and hasattr(request, "headers"):
        uid = uid or str(_header_get(request.headers, "x-user-id") or "")

    exp_id = (os.getenv("RISK_EXPERIMENT_ID") or "").strip() or None
    variant = "control"
    ov_exp: Dict[str, float] = {}
    if is_risk_experiments_enabled() and exp_id and uid:
        variant = assign_variant(uid, exp_id)
        ov_exp = load_variant_weight_overrides(exp_id, variant)

    with runtime_weight_overrides(ov_exp if ov_exp else None):
        ctx = dict(strict_decision_context or {})
        strict_require_reauth = bool(ctx.get("require_reauth"))
        adaptive_friction_applied = bool(ctx.get("adaptive_friction_applied"))
    
        _ = current_user  # réservé audit futur — pas de journalisation d’identité ici
    
        tier = auth_level_to_tier(policy.required_auth_level)
    
        base = base_score_for_action(action_key)
        factors: List[RiskFactorContribution] = [
            RiskFactorContribution(
                code=f"base_action_{(action_key or 'unknown').lower()}",
                weight=base,
                value=action_key,
                description="Score de base selon sensibilité de l’action.",
            )
        ]
    
        _, f = _device_trust_adjustment(device_trust_level)
        factors.append(f)
    
        _, f2 = _auth_freshness_adjustment(
            last_step_up_at if last_step_up_at is not None else getattr(intelligence, "last_step_up_at", None)
        )
        factors.append(f2)
    
        _, f3 = _amount_adjustment(action_key, amount_eur)
        factors.append(f3)
    
        _, f4 = _same_owner_adjustment(same_owner)
        factors.append(f4)
    
        factors.extend(_session_intel_adjustments(intelligence, tier))
    
        burst_raw = burst_recent_count_override
        if burst_raw is None and request is not None:
            h = request.headers.get("x-recent-similar-actions") or request.headers.get("X-Recent-Similar-Actions")
            if h is not None and str(h).strip() != "":
                try:
                    burst_raw = int(str(h).strip())
                except ValueError:
                    burst_raw = None
        _, f5 = _burst_adjustment(burst_raw)
        factors.append(f5)
    
        _, f6 = _sensitive_read_breadth(action_key)
        factors.append(f6)
    
        _, f7 = _incomplete_signal_penalty(action_key, amount_eur, same_owner)
        factors.append(f7)
    
        bctx = behavioral_context
        if bctx is None and is_behavioral_risk_enabled() and request is not None and session is not None:
            bctx = extract_behavioral_context(request, current_user, intelligence, session)
        if bctx is None:
            bctx = BehavioralRiskContext()
    
        factors.extend(_collect_behavioral_factors(bctx, intelligence))
    
        geo_vel_raw_pre = float(bctx.raw_meta.get("geo_velocity_raw", 0.0))
        prelim_score = sum(f.weight for f in factors)
    
        user_segment = "normal_user"
        dyn_thresholds: Optional[Dict[str, Any]] = None
        eff_high = float(high_threshold)
        eff_crit = float(critical_threshold)
        seg_adj_applied = 0.0
    
        if is_adaptive_intelligence_enabled():
            sinp = segmentation_inputs
            if sinp is None and request is not None:
                sinp = extract_segmentation_inputs(request, current_user, intelligence)
            user_segment = derive_user_segment(sinp)
            dyn_thresholds = build_dynamic_thresholds_dict(user_segment)
            eff_high, eff_crit = segment_risk_thresholds(
                user_segment,
                default_high=high_threshold,
                default_critical=critical_threshold,
            )
            raw_seg_w = segment_score_adjustment_weight(user_segment)
            seg_adj_applied = _apply_segment_adjustment_weight(
                user_segment,
                raw_seg_w,
                prelim_score=prelim_score,
                geo_velocity_raw=geo_vel_raw_pre,
                strict_require_reauth=strict_require_reauth,
            )
            factors.append(
                RiskFactorContribution(
                    code="user_segment_adjustment",
                    weight=seg_adj_applied,
                    value=user_segment,
                    description="Ajustement déterministe selon segment utilisateur (Phase 5E).",
                )
            )
    
        raw_score = sum(f.weight for f in factors)
        score = clamp_risk_score(raw_score)
        risk_level = derive_risk_level(score, high_threshold=eff_high, critical_threshold=eff_crit)
    
        final_key, downgrade_extra = _downgrade_wallet_to_internal_transfer_low(
            action_key=action_key,
            risk_score=score,
            amount_eur=amount_eur,
            same_owner=same_owner,
            device_trust_level=device_trust_level,
            intelligence=intelligence,
            tier=tier,
        )
        factors.extend(downgrade_extra)
        if downgrade_extra:
            _log_risk_event(
                "continuous_auth.risk_downgrade_applied",
                {
                    "action_key": action_key,
                    "final_action_key": final_key,
                    "risk_score": round(score, 2),
                    "risk_level": risk_level,
                    "factor_codes": [f.code for f in downgrade_extra],
                },
            )
    
        rec = _recommended_outcome(
            risk_level=risk_level,
            strict_require_reauth=strict_require_reauth,
            adaptive_friction_applied=adaptive_friction_applied,
            user_segment=user_segment,
            adaptive_intelligence_enabled=is_adaptive_intelligence_enabled(),
        )
    
        geo_vel_raw = float(bctx.raw_meta.get("geo_velocity_raw", 0.0))
        ov_reason, beh_flags = _apply_hard_behavioral_overrides(
            action_key=action_key,
            amount_eur=amount_eur,
            b=bctx,
            factors=factors,
            geo_velocity_raw=geo_vel_raw,
            action_burst_count=bctx.action_count_last_5min,
        )
        if ov_reason == "behavioral_force_reauth":
            rec = "reauth"
            risk_level = "critical"
        elif ov_reason == "behavioral_force_step_up" and not strict_require_reauth:
            rec = "step_up"
            if risk_level == "low":
                risk_level = "medium"
    
        if is_behavioral_risk_enabled() and (
            any(
                f.code.startswith(
                    (
                        "geo_",
                        "device_",
                        "action_burst",
                        "multi_session",
                        "account_age",
                        "login_method",
                    )
                )
                for f in factors
            )
            or beh_flags
        ):
            _log_risk_event(
                "continuous_auth.behavioral_anomaly_detected",
                {
                    "action_key": action_key,
                    "risk_score": round(score, 2),
                    "risk_level": risk_level,
                    "geo_change": bool(
                        _norm_cc(bctx.geo_country) and _norm_cc(bctx.previous_geo_country)
                        and _norm_cc(bctx.geo_country) != _norm_cc(bctx.previous_geo_country)
                    ),
                    "device_new": _is_new_device(bctx.device_fingerprint_id, bctx.known_device_ids),
                    "action_burst": bctx.action_count_last_5min,
                    "account_age_bucket": (
                        "lt1d"
                        if (bctx.account_creation_age_days or 999) < 1
                        else (
                            "lt7d"
                            if (bctx.account_creation_age_days or 999) < 7
                            else ("lt30d" if (bctx.account_creation_age_days or 999) < 30 else "ge30d")
                        )
                    )
                    if bctx.account_creation_age_days is not None
                    else "unknown",
                    "flags": list(beh_flags),
                    "override": ov_reason,
                },
            )
    
        ev = RiskEvaluation(
            risk_score=score,
            risk_level=risk_level,
            factors=factors,
            base_action_score=base,
            final_action_key=final_key,
            recommended_outcome=rec,
            override_reason=ov_reason,
            behavioral_flags=list(beh_flags),
            user_segment=user_segment,
            dynamic_thresholds_used=dyn_thresholds,
            experiment_id=exp_id,
            variant=variant,
            calibration_version=calibration_version(),
        )
    
        _log_risk_event(
            "continuous_auth.risk_evaluated",
            {
                "action_key": action_key,
                "final_action_key": ev.final_action_key,
                "risk_score": round(score, 2),
                "risk_level": risk_level,
                "factor_codes": [f.code for f in factors],
                "amount_present": amount_eur is not None,
                "device_trust_level": (device_trust_level or "")[:32] or None,
                "same_owner": same_owner,
                "recommended_outcome": rec,
                "behavioral_flags": beh_flags,
                "override_reason": ov_reason,
                "user_segment": user_segment,
                "segment_adjustment": round(seg_adj_applied, 2) if is_adaptive_intelligence_enabled() else None,
                "dynamic_thresholds_used": dyn_thresholds,
                "experiment_id": exp_id,
                "variant": variant,
                "calibration_version": calibration_version(),
                "risk_weights_effective_sample": dict(
                    list(sorted(snapshot_effective_weights().items()))[:16]
                ),
            },
        )

        try:
            from services.security.risk_dashboard_store import record_risk_evaluation_event

            record_risk_evaluation_event(
                action_key=action_key,
                risk_score=score,
                risk_level=risk_level,
                recommended_outcome=rec,
                user_segment=user_segment,
                factors=factors,
                experiment_id=exp_id,
                variant=variant,
                calibration_version=calibration_version(),
                behavioral_flags=list(beh_flags),
            )
        except Exception:  # noqa: BLE001
            pass

        return ev



def _log_risk_event(event_name: str, metadata: Dict[str, Any]) -> None:
    """Logs structurés sans PII financière brute (montants uniquement via codes de facteurs)."""
    try:
        logger.info("%s %s", event_name, json.dumps(metadata, default=str, ensure_ascii=False))
    except Exception:  # noqa: BLE001
        logger.info("%s", event_name)


def log_risk_outcome_event(event_name: str, metadata: Dict[str, Any]) -> None:
    _log_risk_event(event_name, metadata)
