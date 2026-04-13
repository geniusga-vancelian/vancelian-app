"""PR F — moteur de risque antifraude unifié (score 0–100, allow / step_up / block)."""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple

from fastapi import Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import AuthSecurityEvent, AuthSession, AuthUserDeviceProfile
from services.auth.device_sensitive_action_velocity import get_sensitive_action_count
from services.auth.device_signature_failure_rl import get_signature_failure_count
from services.auth.refresh_session import normalize_device_id
from services.security.device_reputation.device_reputation_service import resolve_device_hash_from_request
from services.security.login_device_trust_service import resolve_user_device_profile
from services.security.security_env import (
    device_risk_f_allow_threshold,
    device_risk_f_attestation_stale_days,
    device_risk_f_block_threshold,
)

logger = logging.getLogger("arquantix.auth.device_risk_pr_f")

RiskDecision = Literal["allow", "step_up", "block"]


@dataclass
class RiskEvaluationResult:
    """Résultat PR F / F.2 : score, décision, contexte, raisons explicables."""

    score: int
    decision: RiskDecision
    context: "RiskEvaluationContext"
    risk_reasons: List[str] = field(default_factory=list)
    dry_run_result: Optional[Dict[str, Any]] = None
    triggered_rule_name: Optional[str] = None
    triggered_rule_conditions: Optional[Dict[str, Any]] = None


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _client_ip(request: Request) -> Optional[str]:
    xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()[:45]
    if request.client:
        return (request.client.host or "")[:45] or None
    return None


def _transfer_amount_eur_hint(request: Request) -> Optional[float]:
    h = request.headers.get("x-transfer-amount-eur") or request.headers.get("X-Transfer-Amount-Eur")
    if not h:
        return None
    try:
        return float(str(h).strip().replace(",", "."))
    except ValueError:
        return None


def _country_hint(request: Request) -> Optional[str]:
    v = (
        request.headers.get("cf-ipcountry")
        or request.headers.get("CF-IPCountry")
        or request.headers.get("x-country-code")
        or ""
    )
    v = str(v).strip().upper()
    return v[:8] if v else None


@dataclass(frozen=True)
class RiskEvaluationContext:
    """Signaux agrégés pour ``compute_risk_score`` (PR F)."""

    device_trust_level: str
    attestation_absent: bool
    attestation_stale: bool
    last_ip: Optional[str]
    current_ip: Optional[str]
    last_country: Optional[str]
    current_country: Optional[str]
    velocity_count: int
    signature_failure_count: int
    device_churn_distinct_24h: int
    session_is_new: bool
    login_failures_recent: int
    refresh_failures_recent: int
    # PR F.3 — baseline temporelle (UTC)
    current_hour_utc: Optional[int] = None
    weekday_utc: Optional[int] = None
    session_duration_sec: Optional[float] = None
    action_type: str = "unknown"
    amount_eur: Optional[float] = None


def compute_risk_score(ctx: RiskEvaluationContext) -> int:
    """Agrège les signaux en un score 0–100 (borné)."""
    score = 0
    tl = (ctx.device_trust_level or "UNKNOWN").strip().upper()
    if tl == "LOW":
        score += 40
    elif tl == "MEDIUM":
        score += 15
    elif tl == "HIGH":
        pass
    else:
        score += 25

    if ctx.attestation_absent:
        score += 40
    elif ctx.attestation_stale:
        score += 20

    if ctx.current_ip and ctx.last_ip and ctx.current_ip != ctx.last_ip:
        score += 15
    if ctx.current_country and ctx.last_country:
        if ctx.current_country.strip().upper() != (ctx.last_country or "").strip().upper():
            score += 25

    if ctx.velocity_count > 3:
        score += 20

    if ctx.signature_failure_count > 0:
        score += min(30, ctx.signature_failure_count * 15)

    if ctx.device_churn_distinct_24h >= 3:
        score += 25
    elif ctx.device_churn_distinct_24h == 2:
        score += 12

    if ctx.session_is_new:
        score += 10

    score += min(20, (ctx.login_failures_recent + ctx.refresh_failures_recent) * 5)

    return min(100, score)


def decide_risk_action(score: int) -> RiskDecision:
    """Seuils configurables via ``DEVICE_RISK_*_THRESHOLD`` (voir ``security_env``)."""
    allow_below = device_risk_f_allow_threshold()
    block_at = device_risk_f_block_threshold()
    if allow_below > block_at:
        allow_below, block_at = block_at, allow_below
    if score < allow_below:
        return "allow"
    if score >= block_at:
        return "block"
    return "step_up"


def _count_auth_events(
    db: Session,
    *,
    user_id: int,
    since: datetime,
    event_types: tuple[str, ...],
) -> int:
    q = (
        db.query(func.count(AuthSecurityEvent.id))
        .filter(
            AuthSecurityEvent.user_id == user_id,
            AuthSecurityEvent.created_at >= since,
            AuthSecurityEvent.event_type.in_(event_types),
        )
    )
    return int(q.scalar() or 0)


def _distinct_devices_24h(db: Session, *, user_id: int, now: datetime) -> int:
    since = now - timedelta(hours=24)
    n = (
        db.query(func.count(func.distinct(AuthSession.device_id)))
        .filter(
            AuthSession.user_id == user_id,
            AuthSession.created_at >= since,
        )
        .scalar()
    )
    return int(n or 0)


def build_risk_evaluation_context(
    db: Session,
    *,
    request: Request,
    user_id: int,
    device_id_normalized: str,
    session: Optional[AuthSession],
    profile: Optional[AuthUserDeviceProfile],
) -> RiskEvaluationContext:
    """Assemble les signaux (device, réseau, comportement, session)."""
    now = _utcnow()
    ip = _client_ip(request)
    country = _country_hint(request)

    trust = "UNKNOWN"
    if session and (session.device_trust_level or "").strip():
        trust = str(session.device_trust_level).strip().upper()
    elif profile and (profile.trust_level or "").strip():
        trust = str(profile.trust_level).strip().upper()

    att_verified: Optional[datetime] = session.attestation_verified_at if session else None
    attestation_absent = att_verified is None
    stale_days = device_risk_f_attestation_stale_days()
    attestation_stale = False
    if att_verified is not None:
        av = att_verified
        if av.tzinfo is None:
            av = av.replace(tzinfo=timezone.utc)
        attestation_stale = (now - av) > timedelta(days=stale_days)

    last_ip = profile.last_ip if profile else None
    last_country = profile.last_country if profile else None

    vel = get_sensitive_action_count(user_id, device_id_normalized)
    sig_key = f"{user_id}:{device_id_normalized}"
    sig_fails = get_signature_failure_count(sig_key)

    churn = _distinct_devices_24h(db, user_id=user_id, now=now)

    session_is_new = False
    if session and session.created_at:
        cr = session.created_at
        if cr.tzinfo is None:
            cr = cr.replace(tzinfo=timezone.utc)
        session_is_new = (now - cr) < timedelta(minutes=10)

    recent_cut = now - timedelta(hours=1)
    login_fails = _count_auth_events(db, user_id=user_id, since=recent_cut, event_types=("auth.login.failed",))
    refresh_fails = _count_auth_events(db, user_id=user_id, since=recent_cut, event_types=("auth.refresh.rejected",))

    from services.auth.device_risk_engine_pr_f3 import infer_risk_action_type

    session_duration_sec: Optional[float] = None
    if session and session.created_at:
        cr = session.created_at
        if cr.tzinfo is None:
            cr = cr.replace(tzinfo=timezone.utc)
        session_duration_sec = max(0.0, (now - cr).total_seconds())

    return RiskEvaluationContext(
        device_trust_level=trust,
        attestation_absent=attestation_absent,
        attestation_stale=attestation_stale and not attestation_absent,
        last_ip=last_ip,
        current_ip=ip,
        last_country=last_country,
        current_country=country,
        velocity_count=vel,
        signature_failure_count=sig_fails,
        device_churn_distinct_24h=churn,
        session_is_new=session_is_new,
        login_failures_recent=login_fails,
        refresh_failures_recent=refresh_fails,
        current_hour_utc=now.hour,
        weekday_utc=now.weekday(),
        session_duration_sec=session_duration_sec,
        action_type=infer_risk_action_type(request),
        amount_eur=_transfer_amount_eur_hint(request),
    )


def resolve_session_for_pr_f(db: Session, *, user_id: int, token: str) -> Optional[AuthSession]:
    from auth import ALGORITHM, SECRET_KEY
    from jose import JWTError, jwt

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
    sid = payload.get("sid")
    if not sid:
        return None
    try:
        suid = uuid.UUID(str(sid))
    except (ValueError, TypeError):
        return None
    row = (
        db.query(AuthSession)
        .filter(
            AuthSession.id == suid,
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
        )
        .first()
    )
    return row


def touch_user_device_profile_for_risk(
    db: Session,
    *,
    user_id: int,
    device_hash: str,
    device_id_normalized: str,
    ip: Optional[str],
    country: Optional[str],
) -> None:
    """Met à jour ``last_ip``, ``last_country``, ``last_seen_at``, ``device_id`` pour l’historique PR F."""
    row = resolve_user_device_profile(db, user_id, device_hash)
    now = _utcnow()
    if row is None:
        row = AuthUserDeviceProfile(
            id=uuid.uuid4(),
            user_id=user_id,
            device_hash=device_hash,
            device_id=device_id_normalized[:128] if device_id_normalized else None,
            fingerprint_hash=None,
            first_seen_at=now,
            last_seen_at=now,
            login_count=0,
            successful_login_count=0,
            failed_login_count=0,
            last_ip=ip[:45] if ip else None,
            last_country=country[:8].upper() if country else None,
            trust_score=0,
            trust_level="LOW",
            is_primary=None,
            last_auth_strength=None,
            last_attestation_level=None,
        )
        db.add(row)
        db.flush()
    else:
        row.last_seen_at = now
        row.device_id = device_id_normalized[:128] if device_id_normalized else row.device_id
        if ip:
            row.last_ip = ip[:45]
        if country:
            row.last_country = country[:8].upper()
        row.updated_at = now
        db.flush()


def evaluate_pr_f_for_request(
    db: Session,
    *,
    request: Request,
    user_id: int,
    token: str,
    device_id_raw: Optional[str],
) -> RiskEvaluationResult:
    """
    Calcule score + décision + raisons.

    PR F.2 (flags) : règles combinées → baseline → score pondéré ou additif historique.
    """
    did = normalize_device_id(device_id_raw)
    fp = request.headers.get("x-fingerprint-hash") or request.headers.get("X-Fingerprint-Hash")
    fp_norm = (str(fp).strip()[:64] if fp else None) or None
    device_hash = resolve_device_hash_from_request(request, did, fp_norm)

    session = resolve_session_for_pr_f(db, user_id=user_id, token=token)
    prof = resolve_user_device_profile(db, user_id, device_hash)
    ctx = build_risk_evaluation_context(
        db,
        request=request,
        user_id=user_id,
        device_id_normalized=did,
        session=session,
        profile=prof,
    )
    reasons: List[str] = []

    from services.auth.risk_cache import (
        get_risk_cache_payload,
        maybe_cache_risk_evaluation_result,
        risk_evaluation_result_from_payload,
    )
    from services.security.security_env import (
        device_risk_cache_ttl_sec,
        is_device_risk_rules_dry_run,
        is_redis_cache_enabled,
    )

    _cache_write_ok = (
        is_redis_cache_enabled()
        and device_risk_cache_ttl_sec() > 0
        and not is_device_risk_rules_dry_run()
    )

    if _cache_write_ok:
        snap = get_risk_cache_payload(user_id, did)
        if snap:
            try:
                res = risk_evaluation_result_from_payload(snap, ctx)
                return _risk_finish(res)
            except Exception:
                pass

    def _risk_finish(res: RiskEvaluationResult) -> RiskEvaluationResult:
        from services.auth.device_intent_engine import evaluate_intent_engine

        res = evaluate_intent_engine(
            db,
            request=request,
            user_id=user_id,
            device_id=did,
            result=res,
        )
        maybe_cache_risk_evaluation_result(user_id, did, res, allow=_cache_write_ok)
        return res

    from services.auth.device_risk_dynamic_rules import evaluate_dynamic_rules
    from services.auth.device_risk_engine_pr_f2 import (
        baseline_deviation_bonus,
        build_legacy_risk_reasons,
        compute_weighted_risk_score,
        evaluate_combination_rules,
        step_up_zone_score,
    )
    from services.auth.device_risk_engine_pr_f3 import baseline_temporal_anomaly_score
    from services.security.security_env import is_device_risk_weighted_score_enabled

    dyn = evaluate_dynamic_rules(
        db, ctx=ctx, profile=prof, request=request, user_id=user_id
    )
    dry_payload = dyn.dry_run
    dyn_explain = dyn.explain or {}
    dyn_rule_name = dyn_explain.get("rule_name")
    dyn_rule_conds = dyn_explain.get("raw_conditions")
    dyn_rule_conds_dict = dyn_rule_conds if isinstance(dyn_rule_conds, dict) else None

    if not dry_payload and dyn.outcome.triggered and dyn.outcome.decision:
        if dyn.outcome.decision == "block":
            fs = dyn.forced_score if dyn.forced_score is not None else 100
            reasons.extend(dyn.outcome.reasons)
            return _risk_finish(
                RiskEvaluationResult(
                    score=fs,
                    decision="block",
                    context=ctx,
                    risk_reasons=reasons,
                    dry_run_result=None,
                    triggered_rule_name=str(dyn_rule_name) if dyn_rule_name else None,
                    triggered_rule_conditions=dyn_rule_conds_dict,
                )
            )
        if dyn.outcome.decision == "step_up":
            reasons.extend(dyn.outcome.reasons)
            return _risk_finish(
                RiskEvaluationResult(
                    score=step_up_zone_score(),
                    decision="step_up",
                    context=ctx,
                    risk_reasons=reasons,
                    dry_run_result=None,
                    triggered_rule_name=str(dyn_rule_name) if dyn_rule_name else None,
                    triggered_rule_conditions=dyn_rule_conds_dict,
                )
            )

    comb = evaluate_combination_rules(ctx=ctx, profile=prof)
    if comb.triggered and comb.decision:
        if comb.decision == "block":
            fs = comb.forced_score if comb.forced_score is not None else 100
            reasons.extend(comb.reasons)
            return _risk_finish(
                RiskEvaluationResult(
                    score=fs,
                    decision="block",
                    context=ctx,
                    risk_reasons=reasons,
                    dry_run_result=dry_payload,
                )
            )
        if comb.decision == "step_up":
            reasons.extend(comb.reasons)
            return _risk_finish(
                RiskEvaluationResult(
                    score=step_up_zone_score(),
                    decision="step_up",
                    context=ctx,
                    risk_reasons=reasons,
                    dry_run_result=dry_payload,
                )
            )

    baseline_pts, br = baseline_deviation_bonus(db, user_id=user_id, ctx=ctx)
    reasons.extend(br)

    temporal_pts, tr = baseline_temporal_anomaly_score(db, user_id=user_id, ctx=ctx)
    reasons.extend(tr)

    if is_device_risk_weighted_score_enabled():
        base_score, wr = compute_weighted_risk_score(ctx)
        reasons.extend(wr)
    else:
        base_score = compute_risk_score(ctx)
        reasons.extend(build_legacy_risk_reasons(ctx))

    score = min(100, base_score + baseline_pts + temporal_pts)

    from services.auth.device_risk_ml_engine import apply_ml_risk_overlay

    score, _ml_dist = apply_ml_risk_overlay(db, user_id=user_id, base_score=score, risk_reasons=reasons)

    from services.auth.device_risk_temporal_engine import apply_temporal_risk_overlay

    score = apply_temporal_risk_overlay(
        db,
        user_id=user_id,
        request=request,
        ctx=ctx,
        score_after_ml=score,
        risk_reasons=reasons,
    )

    decision = decide_risk_action(score)
    return _risk_finish(
        RiskEvaluationResult(
            score=score,
            decision=decision,
            context=ctx,
            risk_reasons=reasons,
            dry_run_result=dry_payload,
        )
    )
