"""Simulation risque isolée (F.5.1 / F.5.2) — déterministe, sans cache, sans baseline DB, sans effets de bord."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.auth.device_risk_dynamic_rules import evaluate_condition_node_with_trace
from services.auth.device_risk_engine_pr_f import (
    RiskEvaluationContext,
    compute_risk_score,
    decide_risk_action,
)
from services.auth.device_risk_engine_pr_f2 import (
    build_legacy_risk_reasons,
    combination_rule_signals,
    compute_weighted_risk_score,
    evaluate_combination_rules,
    step_up_zone_score,
)
from services.security.security_env import (
    device_risk_advanced_baseline_min_samples,
    device_risk_baseline_time_weight,
    is_device_risk_weighted_score_enabled,
)

logger = logging.getLogger("arquantix.auth.risk_simulation_isolated")


def _profile_override_as_dict(body: Any) -> Optional[Dict[str, Any]]:
    po = getattr(body, "profile_override", None)
    if po is None:
        return None
    if hasattr(po, "model_dump"):
        return po.model_dump()
    if isinstance(po, dict):
        return po
    return None


def _isolated_known_device_override(body: Any) -> Optional[bool]:
    """Si ``profile_override`` absent → None (même logique que profile=None). Sinon → ``is_known_device``."""
    d = _profile_override_as_dict(body)
    if d is None:
        return None
    return bool(d.get("is_known_device", False))


def _weekday_distance(a: float, b: float) -> float:
    d = abs(a - b)
    return min(d, 7.0 - d)


class _BaselineOverrideRow:
    """Sous-ensemble des champs AuthUserRiskBaseline pour le calcul temporel in-memory."""

    def __init__(self, d: Dict[str, Any]) -> None:
        self.baseline_sample_count = int(d.get("baseline_sample_count", 999))
        self.avg_hour_of_day = d.get("avg_hour_of_day")
        self.std_hour_of_day = d.get("std_hour_of_day")
        self.avg_weekday = d.get("avg_weekday")
        self.std_weekday = d.get("std_weekday")
        self.avg_session_duration_sec = d.get("avg_session_duration_sec")
        self.std_session_duration_sec = d.get("std_session_duration_sec")
        ema = d.get("actions_per_hour_ema")
        if ema is None:
            ema = d.get("avg_actions_per_hour")
        self.actions_per_hour_ema = float(ema or 0.0)
        raw = d.get("last_10_actions_types")
        self.last_10_actions_types = raw if isinstance(raw, list) else []


def baseline_temporal_anomaly_score_from_override(
    ctx: RiskEvaluationContext,
    override: Dict[str, Any],
) -> Tuple[int, List[str]]:
    """
    Même logique que PR F.3 ``baseline_temporal_anomaly_score`` mais sur une baseline injectée.
    Ignore ``is_device_risk_advanced_baseline_enabled`` : l’override est explicite.
    """
    if ctx.current_hour_utc is None or ctx.weekday_utc is None:
        return 0, []

    row = _BaselineOverrideRow(override)
    if row.baseline_sample_count < device_risk_advanced_baseline_min_samples():
        return 0, []

    w = float(device_risk_baseline_time_weight())
    if w <= 0:
        return 0, []

    bonus = 0
    reasons: List[str] = []

    eps_h = max(float(row.std_hour_of_day or 1.5), 1.5)
    if row.avg_hour_of_day is not None:
        if abs(float(ctx.current_hour_utc) - float(row.avg_hour_of_day)) > 2.0 * eps_h:
            bonus += int(round(15 * w))
            reasons.append("baseline_time_anomaly")

    eps_wd = max(float(row.std_weekday or 1.0), 1.0)
    if row.avg_weekday is not None:
        dist = _weekday_distance(float(ctx.weekday_utc), float(row.avg_weekday))
        if dist > 2.0 * eps_wd:
            bonus += int(round(10 * w))
            reasons.append("baseline_weekday_anomaly")

    if ctx.session_duration_sec is not None and row.avg_session_duration_sec is not None:
        avg_sd = max(30.0, float(row.avg_session_duration_sec))
        std_sd = max(float(row.std_session_duration_sec or 60.0), 15.0)
        cur = float(ctx.session_duration_sec)
        if cur > avg_sd + 2.0 * std_sd and cur > avg_sd * 2.2:
            bonus += int(round(10 * w))
            reasons.append("baseline_session_duration_anomaly")

    ema_act = float(row.actions_per_hour_ema or 0.0)
    if ema_act > 0.1 and float(ctx.velocity_count) > max(4.0, ema_act * 2.5 + 2.0):
        bonus += int(round(15 * w))
        reasons.append("baseline_behavior_anomaly")

    recent = [str(x) for x in row.last_10_actions_types]
    at = (ctx.action_type or "unknown").strip() or "unknown"
    if recent and at != "unknown":
        if at not in recent:
            bonus += int(round(10 * w))
            reasons.append("baseline_behavior_anomaly")
        elif recent.count(at) <= 1 and len(recent) >= 6:
            bonus += int(round(5 * w))
            reasons.append("baseline_behavior_anomaly")

    out = min(55, bonus)
    uniq = list(dict.fromkeys(reasons))
    return out, uniq


def _parse_now_utc_iso(s: str) -> Tuple[int, int]:
    ss = (s or "").strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(ss)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    dt = dt.astimezone(timezone.utc)
    return dt.hour, dt.weekday()


def build_isolated_risk_context(body: Any) -> RiskEvaluationContext:
    """
    Contexte uniquement à partir du payload (pas de profil device DB).
    Heure / jour : ``now_utc`` > ``current_hour_utc``/``weekday_utc`` > défauts fixes (12h, jour 1).
    Pays / IP « stockés » : ``profile_override`` (F.5.2) ou champs directs ``last_*``.
    """
    cc = (getattr(body, "country", None) or "").strip().upper()[:8] or None
    po = _profile_override_as_dict(body)
    det = getattr(body, "deterministic", None)
    now_s = getattr(body, "now_utc", None)

    ch: Optional[int] = None
    wd: Optional[int] = None
    if isinstance(now_s, str) and now_s.strip():
        try:
            ch, wd = _parse_now_utc_iso(now_s)
        except (ValueError, TypeError):
            ch, wd = 12, 1
    else:
        ch = getattr(body, "current_hour_utc", None)
        wd = getattr(body, "weekday_utc", None)
        if det is True and (ch is None or wd is None):
            ch = 12 if ch is None else ch
            wd = 1 if wd is None else wd
    if ch is None:
        ch = 12
    if wd is None:
        wd = 1

    def _i(name: str, default: int) -> int:
        v = getattr(body, name, None)
        return int(v) if v is not None else default

    def _f(name: str, default: float) -> float:
        v = getattr(body, name, None)
        return float(v) if v is not None else default

    def _b(name: str, default: bool) -> bool:
        v = getattr(body, name, None)
        return bool(v) if v is not None else default

    lip = getattr(body, "last_ip", None)
    cip = getattr(body, "current_ip", None)
    if po:
        if po.get("last_ip") is not None and str(po.get("last_ip")).strip():
            lip = str(po.get("last_ip")).strip()
        elif lip is None:
            lip = "127.0.0.1"
        if cip is None:
            cip = "127.0.0.1"
        raw_plc = po.get("last_country")
        if raw_plc is not None and str(raw_plc).strip():
            lc = str(raw_plc).strip().upper()[:8] or None
        else:
            lc = None
        if getattr(body, "last_country", None) is not None:
            lc = str(getattr(body, "last_country")).strip().upper()[:8] or None
    else:
        if lip is None:
            lip = "127.0.0.1"
        if cip is None:
            cip = "127.0.0.1"
        lc = getattr(body, "last_country", None)
        if lc is not None:
            lc = str(lc).strip().upper()[:8] or None
        else:
            lc = cc

    if cip is None:
        cip = "127.0.0.1"
    if lip is None:
        lip = "127.0.0.1"

    if getattr(body, "device_churn_distinct_24h", None) is not None:
        churn = _i("device_churn_distinct_24h", 0)
    elif po is not None:
        churn = int(po.get("device_count_24h", 0) or 0)
    else:
        churn = _i("device_churn_distinct_24h", 0)

    return RiskEvaluationContext(
        device_trust_level=(getattr(body, "device_trust_level", None) or "HIGH").strip().upper(),
        attestation_absent=_b("attestation_absent", False),
        attestation_stale=_b("attestation_stale", False),
        last_ip=str(lip).strip() or "127.0.0.1",
        current_ip=str(cip).strip() or "127.0.0.1",
        last_country=lc,
        current_country=cc,
        velocity_count=_i("velocity_count", 0),
        signature_failure_count=_i("signature_failure_count", 0),
        device_churn_distinct_24h=churn,
        session_is_new=_b("session_is_new", False),
        login_failures_recent=_i("login_failures_recent", 0),
        refresh_failures_recent=_i("refresh_failures_recent", 0),
        current_hour_utc=int(ch),
        weekday_utc=int(wd),
        session_duration_sec=_f("session_duration_sec", 120.0),
        action_type=(getattr(body, "action_type", None) or "unknown").strip(),
        amount_eur=getattr(body, "amount_eur", None),
    )


def _simulation_explain_meta(body: Any) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    if getattr(body, "simulation_seed", None) is not None:
        meta["simulation_seed"] = getattr(body, "simulation_seed")
    if getattr(body, "deterministic", None) is not None:
        meta["deterministic"] = getattr(body, "deterministic")
    nu = getattr(body, "now_utc", None)
    if isinstance(nu, str) and nu.strip():
        meta["now_utc"] = nu.strip()
    po = _profile_override_as_dict(body)
    if po and po.get("last_seen_at"):
        meta["profile_last_seen_at"] = po.get("last_seen_at")
    return meta


def evaluate_risk_simulation_isolated(
    *,
    cond: Dict[str, Any],
    rule_name: str,
    act_upper: str,
    body: Any,
    baseline_override: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Évalue la règle DSL + pipeline PR F / F.2 / F.3 (sans PR F.2 baseline_deviation DB).
    Pas de lecture profil device, pas de cache Redis, pas d’écriture.
    F.5.2 : ``profile_override`` injecte pays/IP/churn connus sans DB.
    """
    ctx = build_isolated_risk_context(body)
    known_ov = _isolated_known_device_override(body)
    used_profile_override = _profile_override_as_dict(body) is not None
    sim_meta = _simulation_explain_meta(body)

    signals = combination_rule_signals(
        ctx=ctx,
        profile=None,
        is_known_device_override=known_ov,
    )
    matched, trace = evaluate_condition_node_with_trace(cond, signals, ctx)

    reasons: List[str] = []
    if not matched:
        reasons.append("rule_conditions_not_matched")
    used_baseline = bool(baseline_override)
    temporal_pts = 0
    tr: List[str] = []
    if baseline_override:
        temporal_pts, tr = baseline_temporal_anomaly_score_from_override(ctx, baseline_override)
        reasons.extend(tr)

    comb = evaluate_combination_rules(
        ctx=ctx,
        profile=None,
        is_known_device_override=known_ov,
    )

    if is_device_risk_weighted_score_enabled():
        base_score, wr = compute_weighted_risk_score(ctx)
        reasons.extend(wr)
    else:
        base_score = compute_risk_score(ctx)
        reasons.extend(build_legacy_risk_reasons(ctx))

    score = min(100, base_score + temporal_pts)
    decision = decide_risk_action(score)
    rule_triggered: Optional[str] = None
    would_action: Optional[str] = None

    # Ordre aligné sur evaluate_pr_f : règle dynamique simulée d’abord, puis combinaison, puis score.
    if matched:
        rule_triggered = rule_name
        would_action = act_upper
        if act_upper == "BLOCK":
            logger.debug(
                "device_risk_simulation_isolated",
                extra={
                    "event": "device_risk_simulation_isolated",
                    "phase": "dynamic_rule",
                    "decision": "block",
                    "rule_name": rule_name,
                },
            )
            return _response_dict(
                simulate_mode="isolated",
                matched=matched,
                trace=trace,
                cond=cond,
                rule_name=rule_name,
                decision="block",
                risk_score=100,
                risk_reason=reasons + [f"dynamic_rule_would:{act_upper}"],
                rule_triggered=rule_triggered,
                rule_conditions=cond,
                would_action=would_action,
                used_baseline=used_baseline,
                used_cache=False,
                used_runtime_state=False,
                used_profile_override=used_profile_override,
                simulation_explain=sim_meta,
                estimated_score_note="Règle dynamique — BLOCK (simulation isolée)",
            )
        if act_upper == "STEP_UP":
            logger.debug(
                "device_risk_simulation_isolated",
                extra={
                    "event": "device_risk_simulation_isolated",
                    "phase": "dynamic_rule",
                    "decision": "step_up",
                    "rule_name": rule_name,
                },
            )
            return _response_dict(
                simulate_mode="isolated",
                matched=matched,
                trace=trace,
                cond=cond,
                rule_name=rule_name,
                decision="step_up",
                risk_score=step_up_zone_score(),
                risk_reason=reasons + [f"dynamic_rule_would:{act_upper}"],
                rule_triggered=rule_triggered,
                rule_conditions=cond,
                would_action=would_action,
                used_baseline=used_baseline,
                used_cache=False,
                used_runtime_state=False,
                used_profile_override=used_profile_override,
                simulation_explain=sim_meta,
                estimated_score_note="Règle dynamique — STEP_UP (simulation isolée)",
            )
        # ALLOW : poursuite
        reasons.append(f"dynamic_rule_would:{act_upper}")

    if comb.triggered and comb.decision:
        if comb.decision == "block":
            fs = comb.forced_score if comb.forced_score is not None else 100
            reasons.extend(list(comb.reasons))
            return _response_dict(
                simulate_mode="isolated",
                matched=matched,
                trace=trace,
                cond=cond,
                rule_name=rule_name,
                decision="block",
                risk_score=int(fs),
                risk_reason=reasons,
                rule_triggered=rule_triggered,
                rule_conditions=cond,
                would_action=would_action,
                used_baseline=used_baseline,
                used_cache=False,
                used_runtime_state=False,
                used_profile_override=used_profile_override,
                simulation_explain=sim_meta,
                estimated_score_note="Règle de combinaison PR F.2 — block",
            )
        if comb.decision == "step_up":
            reasons.extend(list(comb.reasons))
            return _response_dict(
                simulate_mode="isolated",
                matched=matched,
                trace=trace,
                cond=cond,
                rule_name=rule_name,
                decision="step_up",
                risk_score=step_up_zone_score(),
                risk_reason=reasons,
                rule_triggered=rule_triggered,
                rule_conditions=cond,
                would_action=would_action,
                used_baseline=used_baseline,
                used_cache=False,
                used_runtime_state=False,
                used_profile_override=used_profile_override,
                simulation_explain=sim_meta,
                estimated_score_note="Règle de combinaison PR F.2 — step_up",
            )

    reasons = list(dict.fromkeys(reasons))
    logger.debug(
        "device_risk_simulation_isolated",
        extra={
            "event": "device_risk_simulation_isolated",
            "phase": "score",
            "decision": decision,
            "score": score,
            "rule_name": rule_name,
        },
    )
    return _response_dict(
        simulate_mode="isolated",
        matched=matched,
        trace=trace,
        cond=cond,
        rule_name=rule_name,
        decision=decision,
        risk_score=score,
        risk_reason=reasons,
        rule_triggered=rule_triggered,
        rule_conditions=cond if matched else None,
        would_action=would_action,
        used_baseline=used_baseline,
        used_cache=False,
        used_runtime_state=False,
        used_profile_override=used_profile_override,
        simulation_explain=sim_meta,
        estimated_score_note="Score agrégé (isolated, sans baseline pays/IP persistée)",
    )


def _response_dict(
    *,
    simulate_mode: str,
    matched: bool,
    trace: List[str],
    cond: Dict[str, Any],
    rule_name: str,
    decision: str,
    risk_score: int,
    risk_reason: List[str],
    rule_triggered: Optional[str],
    rule_conditions: Optional[Dict[str, Any]],
    would_action: Optional[str],
    used_baseline: bool,
    used_cache: bool,
    used_runtime_state: bool,
    used_profile_override: bool,
    simulation_explain: Optional[Dict[str, Any]] = None,
    estimated_score_note: str,
) -> Dict[str, Any]:
    explain: Dict[str, Any] = {
        "rule_name": rule_name,
        "matched": matched,
        "matched_conditions": trace,
        "raw_conditions": cond,
        "simulate_mode": simulate_mode,
        "used_profile_override": used_profile_override,
    }
    if simulation_explain:
        explain.update(simulation_explain)
    out: Dict[str, Any] = {
        "simulate_mode": simulate_mode,
        "decision": decision,
        "risk_score": risk_score,
        "risk_reason": risk_reason,
        "rule_triggered": rule_triggered,
        "rule_conditions": rule_conditions,
        "used_baseline": used_baseline,
        "used_cache": used_cache,
        "used_runtime_state": used_runtime_state,
        "used_profile_override": used_profile_override,
        "matched_conditions": trace,
        "raw_conditions": cond,
        "rule_name": rule_name,
        "explain": explain,
        "estimated_score_note": estimated_score_note,
    }
    if matched:
        out["would_trigger"] = rule_name
        if would_action is not None:
            out["would_action"] = would_action
    return out
