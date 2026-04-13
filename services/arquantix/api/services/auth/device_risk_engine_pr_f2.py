"""PR F.2 — règles combinées, baseline utilisateur, score pondéré, raisons explicites."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from fastapi import Request
from sqlalchemy.orm import Session

from database import AuthSession, AuthUserDeviceProfile, AuthUserRiskBaseline
from services.auth.device_risk_engine_pr_f import (
    RiskDecision,
    RiskEvaluationContext,
    compute_risk_score,
    decide_risk_action,
)
from services.security.security_env import (
    device_risk_f_allow_threshold,
    device_risk_f_block_threshold,
    device_risk_weight_behavior,
    device_risk_weight_device,
    device_risk_weight_history,
    device_risk_weight_network,
    is_device_risk_baseline_enabled,
    is_device_risk_combination_rules_enabled,
    is_device_risk_weighted_score_enabled,
)


@dataclass(frozen=True)
class CombinationRuleOutcome:
    """Résultat du moteur de règles (court-circuit éventuel)."""

    triggered: bool
    decision: Optional[RiskDecision] = None
    forced_score: Optional[int] = None
    reasons: Tuple[str, ...] = ()


def _attestation_low(ctx: RiskEvaluationContext) -> bool:
    tl = (ctx.device_trust_level or "").strip().upper()
    if tl == "LOW":
        return True
    if ctx.attestation_absent or ctx.attestation_stale:
        return True
    return False


def _country_changed(ctx: RiskEvaluationContext) -> bool:
    if not ctx.current_country or not ctx.last_country:
        return False
    return ctx.current_country.strip().upper() != (ctx.last_country or "").strip().upper()


def _ip_changed(ctx: RiskEvaluationContext) -> bool:
    if not ctx.current_ip or not ctx.last_ip:
        return False
    return ctx.current_ip != ctx.last_ip


def _high_velocity(ctx: RiskEvaluationContext) -> bool:
    return ctx.velocity_count > 3


def combination_rule_signals(
    *,
    ctx: RiskEvaluationContext,
    profile: Optional[AuthUserDeviceProfile],
    is_known_device_override: Optional[bool] = None,
) -> Dict[str, bool]:
    """
    Signaux nommés pour règles combinées statiques (PR F.2) et dynamiques (PR F.4).

    Clés stables : ``new_device``, ``country_changed``, ``ip_changed``, ``attestation_low``,
    ``high_velocity``, ``device_churn_and_velocity``.

    ``is_known_device_override`` (F.5.2 simulation isolée) : si fourni, ``new_device = not override``,
    sinon comportement historique : ``new_device = (profile is None)``.
    """
    if is_known_device_override is not None:
        new_device = not is_known_device_override
    else:
        new_device = profile is None
    churn = ctx.device_churn_distinct_24h
    vel = ctx.velocity_count
    return {
        "new_device": new_device,
        "country_changed": _country_changed(ctx),
        "ip_changed": _ip_changed(ctx),
        "attestation_low": _attestation_low(ctx),
        "high_velocity": _high_velocity(ctx),
        "device_churn_and_velocity": churn >= 2 and vel > 0,
    }


def evaluate_combination_rules(
    *,
    ctx: RiskEvaluationContext,
    profile: Optional[AuthUserDeviceProfile],
    is_known_device_override: Optional[bool] = None,
) -> CombinationRuleOutcome:
    """
    Règles non linéaires (PR H) — évaluées avant le score agrégé.

    Ordre : règles les plus strictes d’abord.

    Voir ``is_known_device_override`` sur ``combination_rule_signals``.
    """
    if not is_device_risk_combination_rules_enabled():
        return CombinationRuleOutcome(triggered=False)

    sig = combination_rule_signals(
        ctx=ctx,
        profile=profile,
        is_known_device_override=is_known_device_override,
    )
    new_device = sig["new_device"]
    cc = sig["country_changed"]
    ic = sig["ip_changed"]
    al = sig["attestation_low"]
    hv = sig["high_velocity"]
    churn = ctx.device_churn_distinct_24h
    vel = ctx.velocity_count

    # 1) Nouveau device + changement pays
    if new_device and cc:
        return CombinationRuleOutcome(
            triggered=True,
            decision="block",
            forced_score=100,
            reasons=("rule_new_device_and_country_change",),
        )

    # 2) IP change + attestation faible
    if ic and al:
        return CombinationRuleOutcome(
            triggered=True,
            decision="block",
            forced_score=100,
            reasons=("rule_ip_change_and_attestation_low",),
        )

    # 3) Churn + vélocité
    if churn >= 2 and vel > 0:
        return CombinationRuleOutcome(
            triggered=True,
            decision="block",
            forced_score=100,
            reasons=("rule_device_churn_and_velocity",),
        )

    # 4) Nouveau device + vélocité élevée → step-up
    if new_device and hv:
        return CombinationRuleOutcome(
            triggered=True,
            decision="step_up",
            forced_score=None,
            reasons=("rule_new_device_and_high_velocity",),
        )

    return CombinationRuleOutcome(triggered=False)


def step_up_zone_score() -> int:
    """Score dans la zone step-up (sous le seuil block) pour règles combinées."""
    block_at = device_risk_f_block_threshold()
    allow_below = device_risk_f_allow_threshold()
    target = max(allow_below, block_at - 1)
    return min(99, max(allow_below, target))


def compute_dimension_raw_scores(ctx: RiskEvaluationContext) -> Tuple[int, int, int, int]:
    """Retourne (device, network, behavior, history) bruts (même découpe que PR F)."""
    device = 0
    tl = (ctx.device_trust_level or "UNKNOWN").strip().upper()
    if tl == "LOW":
        device += 40
    elif tl == "MEDIUM":
        device += 15
    elif tl != "HIGH":
        device += 25
    if ctx.attestation_absent:
        device += 40
    elif ctx.attestation_stale:
        device += 20

    network = 0
    if ctx.current_ip and ctx.last_ip and ctx.current_ip != ctx.last_ip:
        network += 15
    if ctx.current_country and ctx.last_country:
        if ctx.current_country.strip().upper() != (ctx.last_country or "").strip().upper():
            network += 25

    behavior = 0
    if ctx.velocity_count > 3:
        behavior += 20
    if ctx.signature_failure_count > 0:
        behavior += min(30, ctx.signature_failure_count * 15)
    behavior += min(20, (ctx.login_failures_recent + ctx.refresh_failures_recent) * 5)

    history = 0
    if ctx.device_churn_distinct_24h >= 3:
        history += 25
    elif ctx.device_churn_distinct_24h == 2:
        history += 12
    if ctx.session_is_new:
        history += 10

    return device, network, behavior, history


# Plafonds pour normalisation [0,1] par dimension (alignés sur PR F)
_DIM_MAX_DEVICE = 80.0
_DIM_MAX_NETWORK = 40.0
_DIM_MAX_BEHAVIOR = 70.0
_DIM_MAX_HISTORY = 35.0


def compute_weighted_risk_score(ctx: RiskEvaluationContext) -> Tuple[int, List[str]]:
    """Score 0–100 par moyenne pondérée des dimensions normalisées."""
    d, n, b, h = compute_dimension_raw_scores(ctx)
    wd = device_risk_weight_device()
    wn = device_risk_weight_network()
    wb = device_risk_weight_behavior()
    wh = device_risk_weight_history()
    wsum = wd + wn + wb + wh
    if wsum <= 0:
        wsum = 1.0
    nd = min(1.0, d / _DIM_MAX_DEVICE)
    nn = min(1.0, n / _DIM_MAX_NETWORK)
    nb = min(1.0, b / _DIM_MAX_BEHAVIOR)
    nh = min(1.0, h / _DIM_MAX_HISTORY)
    score = int(round(100.0 * (wd * nd + wn * nn + wb * nb + wh * nh) / wsum))
    score = min(100, max(0, score))

    reasons: List[str] = []
    if d:
        reasons.append("dim_device")
    if n:
        reasons.append("dim_network")
    if b:
        reasons.append("dim_behavior")
    if h:
        reasons.append("dim_history")
    return score, reasons


def _get_or_create_baseline(db: Session, user_id: int) -> AuthUserRiskBaseline:
    row = db.get(AuthUserRiskBaseline, user_id)
    if row is None:
        row = AuthUserRiskBaseline(user_id=user_id)
        db.add(row)
        db.flush()
    return row


def baseline_deviation_bonus(
    db: Session,
    *,
    user_id: int,
    ctx: RiskEvaluationContext,
) -> Tuple[int, List[str]]:
    """
    Écart par rapport à la baseline persistée (+ pénalité 0–100 additionnelle bornée).

    Cold start : ``baseline_sample_count`` < seuil → pas de pénalité.
    """
    if not is_device_risk_baseline_enabled():
        return 0, []

    from services.security.security_env import device_risk_baseline_min_samples

    row = _get_or_create_baseline(db, user_id)
    if row.baseline_sample_count < device_risk_baseline_min_samples():
        return 0, []

    bonus = 0
    reasons: List[str] = []
    countries = row.countries_json if isinstance(row.countries_json, dict) else {}
    cc = (ctx.current_country or "").strip().upper()
    if cc:
        cnt = int(countries.get(cc, 0) or 0)
        if cnt < 2:
            bonus += 15
            reasons.append("baseline_country_unusual")

    ips: List[str] = []
    raw_ips = row.frequent_ips_json
    if isinstance(raw_ips, list):
        ips = [str(x) for x in raw_ips]
    cur_ip = (ctx.current_ip or "").strip()
    if cur_ip and ips and cur_ip not in ips:
        bonus += 10
        reasons.append("baseline_ip_unusual")

    ema = float(row.device_count_ema or 1.0)
    churn = float(ctx.device_churn_distinct_24h)
    if ema > 0.5 and churn > ema * 2.0 + 1.0:
        bonus += 20
        reasons.append("baseline_device_churn_deviation")

    return min(40, bonus), reasons


def update_user_risk_baseline_from_observation(
    db: Session,
    *,
    user_id: int,
    ctx: RiskEvaluationContext,
    request: Optional[Request] = None,
    session: Optional[AuthSession] = None,
) -> None:
    """Met à jour la baseline après une requête autorisée (EMA pays / IP / churn)."""
    if not is_device_risk_baseline_enabled():
        if request is not None:
            from services.security.security_env import is_device_risk_advanced_baseline_enabled

            if is_device_risk_advanced_baseline_enabled():
                from services.auth.device_risk_engine_pr_f3 import update_advanced_baseline_from_observation

                update_advanced_baseline_from_observation(
                    db,
                    user_id=user_id,
                    ctx=ctx,
                    request=request,
                    session=session,
                    increment_sample_count=True,
                )
        return

    row = _get_or_create_baseline(db, user_id)
    alpha = 0.25
    countries = dict(row.countries_json) if isinstance(row.countries_json, dict) else {}
    cc = (ctx.current_country or "").strip().upper()
    if cc:
        countries[cc] = int(countries.get(cc, 0) or 0) + 1
        row.primary_country = max(countries, key=lambda k: countries.get(k, 0))

    ips: List[str] = []
    if isinstance(row.frequent_ips_json, list):
        ips = [str(x) for x in row.frequent_ips_json[:20]]
    cur = (ctx.current_ip or "").strip()
    if cur and cur not in ips:
        ips.insert(0, cur)
    ips = ips[:20]
    row.frequent_ips_json = ips
    row.countries_json = countries

    obs_devices = float(ctx.device_churn_distinct_24h)
    row.device_count_ema = (1.0 - alpha) * float(row.device_count_ema or 1.0) + alpha * max(1.0, obs_devices)

    vel = float(ctx.velocity_count)
    row.actions_per_hour_ema = (1.0 - alpha) * float(row.actions_per_hour_ema or 0.0) + alpha * vel

    row.baseline_sample_count = int(row.baseline_sample_count or 0) + 1
    db.flush()

    if request is not None:
        from services.security.security_env import is_device_risk_advanced_baseline_enabled

        if is_device_risk_advanced_baseline_enabled():
            from services.auth.device_risk_engine_pr_f3 import update_advanced_baseline_from_observation

            update_advanced_baseline_from_observation(
                db,
                user_id=user_id,
                ctx=ctx,
                request=request,
                session=session,
                increment_sample_count=False,
            )


def build_legacy_risk_reasons(ctx: RiskEvaluationContext) -> List[str]:
    """Raisons lisibles pour le score additif historique (PR F)."""
    r: List[str] = []
    tl = (ctx.device_trust_level or "").strip().upper()
    if tl == "LOW":
        r.append("device_trust_low")
    elif tl == "MEDIUM":
        r.append("device_trust_medium")
    elif tl not in ("HIGH",):
        r.append("device_trust_unknown")
    if ctx.attestation_absent:
        r.append("attestation_absent")
    elif ctx.attestation_stale:
        r.append("attestation_stale")
    if ctx.current_ip and ctx.last_ip and ctx.current_ip != ctx.last_ip:
        r.append("ip_change")
    if ctx.current_country and ctx.last_country:
        if ctx.current_country.strip().upper() != (ctx.last_country or "").strip().upper():
            r.append("country_change")
    if ctx.velocity_count > 3:
        r.append("velocity_high")
    if ctx.signature_failure_count > 0:
        r.append("signature_failures_recent")
    if ctx.device_churn_distinct_24h >= 3:
        r.append("device_churn_high")
    elif ctx.device_churn_distinct_24h == 2:
        r.append("device_churn_medium")
    if ctx.session_is_new:
        r.append("session_new")
    if ctx.login_failures_recent or ctx.refresh_failures_recent:
        r.append("auth_failures_recent")
    return r
