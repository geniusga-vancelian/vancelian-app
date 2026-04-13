"""PR F.5 — administration des règles dynamiques (auth_risk_rules)."""
from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from auth import get_current_user
from database import AdminUser, AuthRiskRule, AuthSecurityEvent, get_db
from services.auth.device_risk_dynamic_rules import (
    evaluate_condition_node_with_trace,
    validate_risk_rule_conditions,
)
from services.auth.device_risk_engine_pr_f import RiskEvaluationContext
from services.auth.device_risk_engine_pr_f2 import combination_rule_signals
from services.auth.refresh_session import normalize_device_id
from services.security.login_device_trust_service import resolve_user_device_profile
from services.security.security_env import device_risk_rules_ruleset

logger = logging.getLogger("arquantix.auth.risk_rules_admin")

router = APIRouter(prefix="/admin/risk", tags=["admin-risk-rules"])


def _device_hash_synthetic(user_id: int, device_id: str) -> str:
    raw = f"{user_id}|{normalize_device_id(device_id)}".encode()
    return hashlib.sha256(raw).hexdigest()[:64]


class RiskRuleOut(BaseModel):
    id: str
    name: Optional[str]
    priority: int
    conditions: Dict[str, Any]
    action: str
    enabled: bool
    is_active: bool
    ruleset: str
    version: int
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RiskRuleUpdate(BaseModel):
    name: Optional[str] = None
    priority: Optional[int] = None
    conditions: Optional[Dict[str, Any]] = None
    action: Optional[str] = None
    enabled: Optional[bool] = None
    is_active: Optional[bool] = None
    ruleset: Optional[str] = Field(default=None, max_length=64)


class RiskRuleCreate(BaseModel):
    name: str = Field(..., max_length=128)
    priority: int = 100
    conditions: Dict[str, Any] = Field(default_factory=dict)
    action: str = Field(..., max_length=16)
    ruleset: str = Field(default="default", max_length=64)
    is_active: bool = True
    enabled: bool = True


class ValidateBody(BaseModel):
    conditions: Dict[str, Any]


class ValidateResponse(BaseModel):
    valid: bool
    error: Optional[str] = None


class ProfileOverrideIn(BaseModel):
    """F.5.2 — profil device injecté (simulation isolée, sans DB)."""

    is_known_device: bool = False
    last_country: Optional[str] = None
    last_ip: Optional[str] = None
    device_count_24h: int = 0
    last_seen_at: Optional[str] = None


class SimulateBody(BaseModel):
    rule_id: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    """Si fourni, remplace les conditions persistées (test brouillon)."""
    user_id: int = Field(..., ge=1)
    device_id: str = ""
    action_type: str = "wallet_transfer"
    country: Optional[str] = None
    amount_eur: Optional[float] = None
    route: str = "/api/test"
    device_trust_level: str = "HIGH"
    simulate_mode: Optional[Literal["runtime", "isolated"]] = None
    """Défaut implicite runtime (comportement historique si absent)."""
    baseline_override: Optional[Dict[str, Any]] = None
    # Contexte explicite pour isolated (optionnel)
    current_hour_utc: Optional[int] = None
    weekday_utc: Optional[int] = None
    session_duration_sec: Optional[float] = None
    velocity_count: Optional[int] = None
    signature_failure_count: Optional[int] = None
    device_churn_distinct_24h: Optional[int] = None
    session_is_new: Optional[bool] = None
    login_failures_recent: Optional[int] = None
    refresh_failures_recent: Optional[int] = None
    last_ip: Optional[str] = None
    current_ip: Optional[str] = None
    last_country: Optional[str] = None
    attestation_absent: Optional[bool] = None
    attestation_stale: Optional[bool] = None
    profile_override: Optional[ProfileOverrideIn] = None
    """Dernière empreinte pays/IP + churn (isolé uniquement)."""
    now_utc: Optional[str] = None
    """ISO8601 (ex. 2026-01-01T12:00:00Z) — fixe heure/jour UTC pour reproductibilité."""
    simulation_seed: Optional[int] = None
    """Réservé reproductibilité future (stocké dans explain)."""
    deterministic: Optional[bool] = None
    """Si true : pas d’horodatage implicite (utiliser now_utc ou défauts fixes)."""


class SimulateResponse(BaseModel):
    would_trigger: Optional[str] = None
    would_action: Optional[str] = None
    matched_conditions: List[str] = Field(default_factory=list)
    raw_conditions: Optional[Dict[str, Any]] = None
    rule_name: Optional[str] = None
    explain: Optional[Dict[str, Any]] = None
    estimated_score_note: Optional[str] = None
    risk_reason: List[str] = Field(default_factory=list)
    simulate_mode: Optional[str] = None
    decision: Optional[str] = None
    risk_score: Optional[int] = None
    rule_triggered: Optional[str] = None
    rule_conditions: Optional[Dict[str, Any]] = None
    used_baseline: Optional[bool] = None
    used_cache: Optional[bool] = None
    used_runtime_state: Optional[bool] = None
    used_profile_override: Optional[bool] = None
    dry_run_result: Optional[Dict[str, Any]] = None


class RiskSettingsOut(BaseModel):
    dry_run: bool
    dry_run_source: str  # "env" | "redis"
    device_risk_rules_ruleset: str
    redis_override_available: bool


def _row_to_out(row: AuthRiskRule) -> RiskRuleOut:
    return RiskRuleOut(
        id=str(row.id),
        name=row.name,
        priority=int(row.priority or 100),
        conditions=row.conditions if isinstance(row.conditions, dict) else {},
        action=(row.action or "").strip(),
        enabled=bool(row.enabled),
        is_active=bool(getattr(row, "is_active", True)),
        ruleset=str(getattr(row, "ruleset", None) or "default"),
        version=int(getattr(row, "version", None) or 1),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("/rules", response_model=List[RiskRuleOut])
def list_risk_rules(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
    ruleset: Optional[str] = Query(None, description="Filtre exact ruleset"),
    sort: str = Query("priority", pattern="^(priority|updated_at)$"),
) -> List[RiskRuleOut]:
    _ = current_user
    q = db.query(AuthRiskRule)
    if ruleset:
        q = q.filter(AuthRiskRule.ruleset == ruleset.strip())
    if sort == "priority":
        q = q.order_by(AuthRiskRule.priority.asc(), AuthRiskRule.id.asc())
    else:
        q = q.order_by(AuthRiskRule.updated_at.desc(), AuthRiskRule.id.asc())
    return [_row_to_out(r) for r in q.all()]


@router.get("/rules/{rule_id}", response_model=RiskRuleOut)
def get_risk_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
) -> RiskRuleOut:
    _ = current_user
    try:
        rid = uuid.UUID(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid rule id") from exc
    row = db.query(AuthRiskRule).filter(AuthRiskRule.id == rid).first()
    if row is None:
        raise HTTPException(status_code=404, detail="rule not found")
    return _row_to_out(row)


@router.patch("/rules/{rule_id}", response_model=RiskRuleOut)
def patch_risk_rule(
    rule_id: str,
    body: RiskRuleUpdate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
) -> RiskRuleOut:
    _ = current_user
    try:
        rid = uuid.UUID(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid rule id") from exc
    row = db.query(AuthRiskRule).filter(AuthRiskRule.id == rid).first()
    if row is None:
        raise HTTPException(status_code=404, detail="rule not found")
    data = body.model_dump(exclude_unset=True)
    if "conditions" in data and data["conditions"] is not None:
        if not validate_risk_rule_conditions(data["conditions"]):
            raise HTTPException(status_code=400, detail="conditions DSL invalid")
    for k, v in data.items():
        setattr(row, k, v)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_out(row)


@router.post("/rules", response_model=RiskRuleOut)
def create_risk_rule(
    body: RiskRuleCreate,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
) -> RiskRuleOut:
    _ = current_user
    if not validate_risk_rule_conditions(body.conditions):
        raise HTTPException(status_code=400, detail="conditions DSL invalid")
    act = body.action.strip().upper()
    if act not in ("ALLOW", "STEP_UP", "BLOCK"):
        raise HTTPException(status_code=400, detail="action must be ALLOW, STEP_UP or BLOCK")
    row = AuthRiskRule(
        id=uuid.uuid4(),
        name=body.name[:128],
        priority=body.priority,
        conditions=body.conditions,
        action=act,
        enabled=body.enabled,
        is_active=body.is_active,
        ruleset=body.ruleset[:64],
        version=1,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _row_to_out(row)


@router.post("/rules/validate", response_model=ValidateResponse)
def validate_rule_dsl(
    body: ValidateBody,
    current_user: AdminUser = Depends(get_current_user),
) -> ValidateResponse:
    _ = current_user
    ok = validate_risk_rule_conditions(body.conditions)
    if ok:
        return ValidateResponse(valid=True, error=None)
    return ValidateResponse(valid=False, error="DSL invalide (structure / clés / types)")


@router.post("/rules/simulate", response_model=SimulateResponse)
def simulate_rule(
    body: SimulateBody,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
) -> SimulateResponse:
    _ = current_user
    row: Optional[AuthRiskRule] = None
    if body.rule_id:
        try:
            rid = uuid.UUID(body.rule_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid rule_id") from exc
        row = db.query(AuthRiskRule).filter(AuthRiskRule.id == rid).first()
        if row is None:
            raise HTTPException(status_code=404, detail="rule not found")
    if body.conditions is not None:
        cond = body.conditions
        rule_name = ((row.name or "").strip() or str(row.id) if row else "(brouillon)")
        act_upper = ((row.action or "BLOCK").strip().upper() if row else "BLOCK")
    elif row is not None:
        cond = row.conditions if isinstance(row.conditions, dict) else {}
        rule_name = (row.name or "").strip() or str(row.id)
        act_upper = (row.action or "").strip().upper()
    else:
        raise HTTPException(status_code=400, detail="rule_id ou conditions requis")

    if not cond or not validate_risk_rule_conditions(cond):
        return SimulateResponse(
            explain={"error": "conditions invalides"},
            estimated_score_note="Règle non évaluable (DSL)",
            simulate_mode=body.simulate_mode or "runtime",
        )

    mode = body.simulate_mode or "runtime"
    if mode == "isolated":
        from services.auth.risk_runtime_settings import get_dry_run_effective
        from services.auth.risk_simulation_isolated import evaluate_risk_simulation_isolated

        dry, dry_src = get_dry_run_effective()
        payload = evaluate_risk_simulation_isolated(
            cond=cond,
            rule_name=rule_name,
            act_upper=act_upper,
            body=body,
            baseline_override=body.baseline_override,
        )
        payload["dry_run_result"] = {"enabled": dry, "source": dry_src}
        return SimulateResponse(**payload)

    did = normalize_device_id(body.device_id or "unknown-device")
    dh = _device_hash_synthetic(body.user_id, did)
    prof = resolve_user_device_profile(db, body.user_id, dh)

    cc = (body.country or "").strip().upper()[:8] or None
    ctx = RiskEvaluationContext(
        device_trust_level=(body.device_trust_level or "HIGH").strip().upper(),
        attestation_absent=False,
        attestation_stale=False,
        last_ip="127.0.0.1",
        current_ip="127.0.0.1",
        last_country=cc,
        current_country=cc,
        velocity_count=0,
        signature_failure_count=0,
        device_churn_distinct_24h=0,
        session_is_new=False,
        login_failures_recent=0,
        refresh_failures_recent=0,
        current_hour_utc=datetime.now(timezone.utc).hour,
        weekday_utc=datetime.now(timezone.utc).weekday(),
        session_duration_sec=120.0,
        action_type=(body.action_type or "unknown").strip(),
        amount_eur=body.amount_eur,
    )
    signals = combination_rule_signals(ctx=ctx, profile=prof)
    matched, trace = evaluate_condition_node_with_trace(cond, signals, ctx)
    explain: Dict[str, Any] = {
        "rule_name": rule_name,
        "matched": matched,
        "matched_conditions": trace,
        "raw_conditions": cond,
        "route": body.route,
        "simulate_mode": "runtime",
    }
    meta = {
        "simulate_mode": "runtime",
        "used_baseline": False,
        "used_cache": False,
        "used_runtime_state": True,
    }
    if not matched:
        return SimulateResponse(
            matched_conditions=trace,
            raw_conditions=cond,
            rule_name=rule_name,
            explain=explain,
            estimated_score_note="Conditions non satisfaites — pas de déclenchement",
            risk_reason=["rule_conditions_not_matched"],
            **meta,
        )

    return SimulateResponse(
        would_trigger=rule_name,
        would_action=act_upper,
        matched_conditions=trace,
        raw_conditions=cond,
        rule_name=rule_name,
        explain=explain,
        estimated_score_note="Conditions satisfaites — la règle s’appliquerait (hors dry-run global)",
        risk_reason=[f"dynamic_rule_would:{act_upper}"],
        **meta,
    )


@router.get("/logs")
def list_risk_logs(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
    rule: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    from_ts: Optional[datetime] = Query(None, alias="from"),
    to_ts: Optional[datetime] = Query(None, alias="to"),
    limit: int = Query(100, ge=1, le=500),
) -> Dict[str, Any]:
    """Événements liés au risque issus de ``auth_security_events`` (méta SIEM)."""
    _ = current_user
    q = db.query(AuthSecurityEvent).filter(
        or_(
            AuthSecurityEvent.event_type.ilike("%risk%"),
            AuthSecurityEvent.event_type.ilike("%device_risk%"),
        )
    )
    if from_ts:
        q = q.filter(AuthSecurityEvent.created_at >= from_ts)
    if to_ts:
        q = q.filter(AuthSecurityEvent.created_at <= to_ts)
    rows = q.order_by(AuthSecurityEvent.created_at.desc()).limit(limit * 5).all()
    items: List[Dict[str, Any]] = []
    for ev in rows:
        meta = ev.metadata_payload if isinstance(ev.metadata_payload, dict) else {}
        evname = meta.get("event") or ""
        rname = meta.get("rule_name") or meta.get("rule") or ""
        if rule and rname and rule.lower() not in (rname or "").lower():
            continue
        act = meta.get("action") or ev.event_type
        if action and action.lower() not in (act or "").lower():
            continue
        items.append(
            {
                "timestamp": ev.created_at.isoformat() if ev.created_at else None,
                "user_id": ev.user_id,
                "rule_name": rname or None,
                "action": act,
                "route": meta.get("route"),
                "risk_score": meta.get("risk_score") or meta.get("score"),
                "event_type": ev.event_type,
                "metadata": meta,
            }
        )
        if len(items) >= limit:
            break
    return {
        "items": items,
        "note": "Source: auth_security_events (filtre risk). Les logs détaillés device_risk_* restent aussi dans les logs applicatifs.",
    }


@router.get("/settings", response_model=RiskSettingsOut)
def get_risk_settings(
    current_user: AdminUser = Depends(get_current_user),
) -> RiskSettingsOut:
    _ = current_user
    from services.auth.risk_runtime_settings import get_dry_run_effective, redis_dry_run_override_available

    dry, src = get_dry_run_effective()
    try:
        redis_ok = redis_dry_run_override_available()
    except Exception:
        redis_ok = False
    return RiskSettingsOut(
        dry_run=dry,
        dry_run_source=src,
        device_risk_rules_ruleset=device_risk_rules_ruleset(),
        redis_override_available=redis_ok,
    )


@router.put("/settings/dry-run")
def put_dry_run(
    body: Dict[str, Any],
    current_user: AdminUser = Depends(get_current_user),
) -> Dict[str, Any]:
    """Active/désactive le dry-run runtime (Redis) si disponible."""
    _ = current_user
    val = body.get("enabled")
    if not isinstance(val, bool):
        raise HTTPException(status_code=400, detail="body.enabled bool requis")
    try:
        from services.auth.risk_runtime_settings import get_dry_run_effective, set_dry_run_override

        set_dry_run_override(val)
    except RuntimeError as e:
        raise HTTPException(status_code=501, detail=str(e)) from e
    dry, src = get_dry_run_effective()
    return {"dry_run": dry, "dry_run_source": src}


@router.post("/rules/{rule_id}/duplicate", response_model=RiskRuleOut)
def duplicate_rule(
    rule_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
) -> RiskRuleOut:
    _ = current_user
    try:
        rid = uuid.UUID(rule_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid rule id") from exc
    src = db.query(AuthRiskRule).filter(AuthRiskRule.id == rid).first()
    if src is None:
        raise HTTPException(status_code=404, detail="rule not found")
    ver = int(getattr(src, "version", 1) or 1) + 1
    nm = f"{(src.name or 'rule')[:100]} (copy)"
    dup = AuthRiskRule(
        id=uuid.uuid4(),
        name=nm,
        priority=int(src.priority or 100),
        conditions=dict(src.conditions) if isinstance(src.conditions, dict) else {},
        action=(src.action or "ALLOW").strip().upper(),
        enabled=bool(src.enabled),
        is_active=False,
        ruleset=str(getattr(src, "ruleset", None) or "default")[:64],
        version=ver,
    )
    db.add(dup)
    db.commit()
    db.refresh(dup)
    return _row_to_out(dup)


@router.post("/rules/disable-all")
def disable_all_rules(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
    ruleset: Optional[str] = Query(None),
) -> Dict[str, Any]:
    _ = current_user
    q = db.query(AuthRiskRule)
    if ruleset:
        q = q.filter(AuthRiskRule.ruleset == ruleset.strip())
    n = q.update({AuthRiskRule.is_active: False}, synchronize_session=False)
    db.commit()
    return {"updated": n, "ruleset": ruleset or "*"}
