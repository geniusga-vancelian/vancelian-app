"""PR F.4 — moteur de règles dynamiques (conditions JSON + priorité). PR F.4.1 hardening."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from fastapi import Request
from sqlalchemy.orm import Session

from database import AuthRiskRule, AuthUserDeviceProfile
from services.auth.device_risk_engine_pr_f import RiskEvaluationContext
from services.auth.device_risk_engine_pr_f2 import CombinationRuleOutcome, combination_rule_signals
from services.security.security_env import (
    device_risk_rules_ruleset,
    is_device_risk_dynamic_rules_enabled,
    is_device_risk_rules_dry_run,
)

logger = logging.getLogger("arquantix.auth.device_risk_dynamic_rules")

ConditionNode = Union[str, Dict[str, Any]]

_STRUCT_KEYS = frozenset({"all", "any", "not"})
_BUSINESS_KEYS = frozenset(
    {"amount_gt", "amount_lt", "action_type_eq", "country_in", "country_not_in"}
)
_ALLOWED_TOP_KEYS = _STRUCT_KEYS | _BUSINESS_KEYS

# Alias → libellé canonique aligné sur ``infer_risk_action_type`` (évite échecs silencieux
# ex. règle ``withdraw`` vs contexte ``withdrawal``).
ACTION_TYPE_NORMALIZATION: Dict[str, str] = {
    "withdraw": "withdrawal",
}


def _normalize_risk_action_type_label(raw: str) -> str:
    x = (raw or "").strip().lower()
    if not x:
        return "unknown"
    return ACTION_TYPE_NORMALIZATION.get(x, x)


def validate_risk_rule_conditions(conditions: Any) -> bool:
    """
    Vérifie que le DSL est utilisable (all/any/not + prédicats métier autorisés).

    Retourne ``False`` si la structure ou les types sont invalides (fail-safe : ignorer la règle).
    """

    def _walk(node: Any) -> bool:
        if isinstance(node, str):
            return bool((node or "").strip())
        if not isinstance(node, dict) or not node:
            return False
        keys = set(node.keys())
        if keys <= _STRUCT_KEYS:
            if "all" in node:
                parts = node.get("all")
                if not isinstance(parts, list):
                    return False
                return all(_walk(p) for p in parts)
            if "any" in node:
                parts = node.get("any")
                if not isinstance(parts, list):
                    return False
                return all(_walk(p) for p in parts)
            if "not" in node:
                return _walk(node.get("not"))
            return False
        if len(keys) != 1:
            return False
        k = next(iter(keys))
        if k not in _BUSINESS_KEYS:
            return False
        v = node[k]
        if k in ("amount_gt", "amount_lt"):
            if isinstance(v, bool):
                return False
            try:
                float(v)
            except (TypeError, ValueError):
                return False
            return True
        if k == "action_type_eq":
            return isinstance(v, str) and bool(v.strip())
        if k in ("country_in", "country_not_in"):
            if not isinstance(v, list) or not v:
                return False
            return all(isinstance(x, str) and x.strip() for x in v)
        return False

    return _walk(conditions)


def _eval_business_leaf(
    key: str, val: Any, ctx: Optional[RiskEvaluationContext]
) -> Tuple[bool, List[str]]:
    if ctx is None:
        return False, []
    if key == "amount_gt":
        if ctx.amount_eur is None:
            return False, []
        try:
            bound = float(val)
        except (TypeError, ValueError):
            return False, []
        ok = float(ctx.amount_eur) > bound
        return ok, ([f"amount_gt>{bound}"] if ok else [])
    if key == "amount_lt":
        if ctx.amount_eur is None:
            return False, []
        try:
            bound = float(val)
        except (TypeError, ValueError):
            return False, []
        ok = float(ctx.amount_eur) < bound
        return ok, ([f"amount_lt<{bound}"] if ok else [])
    if key == "action_type_eq":
        want = _normalize_risk_action_type_label(str(val))
        got = _normalize_risk_action_type_label(ctx.action_type or "unknown")
        ok = got == want
        return ok, ([f"action_type_eq:{got}"] if ok else [])
    if key == "country_in":
        cc = (ctx.current_country or "").strip().upper()
        if not cc:
            return False, []
        allowed: Set[str] = {str(x).strip().upper() for x in val if isinstance(x, str)}
        ok = cc in allowed
        return ok, ([f"country_in:{cc}"] if ok else [])
    if key == "country_not_in":
        cc = (ctx.current_country or "").strip().upper()
        if not cc:
            return False, []
        forbidden = {str(x).strip().upper() for x in val if isinstance(x, str)}
        ok = cc not in forbidden
        return ok, ([f"country_not_in:{cc}"] if ok else [])
    return False, []


def evaluate_condition_node_with_trace(
    node: ConditionNode,
    signals: Dict[str, bool],
    ctx: Optional[RiskEvaluationContext] = None,
) -> Tuple[bool, List[str]]:
    """Évalue une condition et renvoie la liste des atomes satisfaits (explainability)."""
    if isinstance(node, str):
        v = bool(signals.get(node, False))
        return v, ([f"signal:{node}"] if v else [])
    if not isinstance(node, dict):
        return False, []
    if "all" in node:
        parts = node.get("all") or []
        traces: List[str] = []
        for p in parts:
            ok, tr = evaluate_condition_node_with_trace(p, signals, ctx)
            if not ok:
                return False, []
            traces.extend(tr)
        return True, traces
    if "any" in node:
        parts = node.get("any") or []
        traces = []
        any_ok = False
        for p in parts:
            ok, tr = evaluate_condition_node_with_trace(p, signals, ctx)
            if ok:
                any_ok = True
                traces.extend(tr)
        return any_ok, traces
    if "not" in node:
        ok, tr = evaluate_condition_node_with_trace(node["not"], signals, ctx)
        inv = not ok
        return inv, ([f"not({','.join(tr)})"] if inv else [])
    if len(node) == 1:
        k = next(iter(node))
        if k in _BUSINESS_KEYS:
            return _eval_business_leaf(k, node[k], ctx)
    return False, []


def evaluate_condition_node(
    node: ConditionNode,
    signals: Dict[str, bool],
    ctx: Optional[RiskEvaluationContext] = None,
) -> bool:
    ok, _ = evaluate_condition_node_with_trace(node, signals, ctx)
    return ok


@dataclass
class DynamicRulesEvaluationResult:
    """Résultat PR F.4 / F.4.1 : outcome + métadonnées dry-run / explain."""

    outcome: CombinationRuleOutcome
    explain: Optional[Dict[str, Any]] = None
    dry_run: Optional[Dict[str, Any]] = None

    @property
    def triggered(self) -> bool:
        return self.outcome.triggered

    @property
    def decision(self):
        return self.outcome.decision

    @property
    def forced_score(self):
        return self.outcome.forced_score

    @property
    def reasons(self):
        return self.outcome.reasons


def _log_rule_event(
    event: str,
    *,
    user_id: Optional[int],
    rule_name: str,
    action: str,
    route: str,
    score: Optional[int],
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    payload: Dict[str, Any] = {
        "event": event,
        "user_id": user_id,
        "rule_name": rule_name,
        "action": action,
        "route": route,
        "score": score,
    }
    if extra:
        payload.update(extra)
    logger.info(event, extra=payload)


def evaluate_dynamic_rules(
    db: Session,
    *,
    ctx: RiskEvaluationContext,
    profile: Optional[AuthUserDeviceProfile],
    request: Optional[Request] = None,
    user_id: Optional[int] = None,
) -> DynamicRulesEvaluationResult:
    """
    Première règle activée dont les conditions matchent (ordre ``priority`` croissant).

    PR F.4.1 : uniquement ``is_active`` + ``ruleset`` ; dry-run ; validation DSL ; fail-safe.
    """
    if not is_device_risk_dynamic_rules_enabled():
        return DynamicRulesEvaluationResult(CombinationRuleOutcome(triggered=False))

    route = ""
    if request is not None:
        route = (request.url.path or "")[:512]

    ruleset_name = device_risk_rules_ruleset()
    dry_run_mode = is_device_risk_rules_dry_run()

    try:
        rows = (
            db.query(AuthRiskRule)
            .filter(
                AuthRiskRule.is_active.is_(True),
                AuthRiskRule.enabled.is_(True),
                AuthRiskRule.ruleset == ruleset_name,
            )
            .order_by(AuthRiskRule.priority.asc(), AuthRiskRule.id.asc())
            .all()
        )
    except Exception as exc:  # noqa: BLE001
        _log_rule_event(
            "device_risk_rule_error",
            user_id=user_id,
            rule_name="",
            action="",
            route=route,
            score=None,
            extra={"error": str(exc)[:500]},
        )
        logger.exception("device_risk_rule_error query auth_risk_rules: %s", exc)
        return DynamicRulesEvaluationResult(CombinationRuleOutcome(triggered=False))

    if not rows:
        return DynamicRulesEvaluationResult(CombinationRuleOutcome(triggered=False))

    signals = combination_rule_signals(ctx=ctx, profile=profile)

    try:
        for row in rows:
            cond = row.conditions
            if cond is None or (isinstance(cond, dict) and not cond):
                continue

            if not validate_risk_rule_conditions(cond):
                rname = (row.name or "").strip() or str(row.id)
                _log_rule_event(
                    "device_risk_rule_skipped_invalid",
                    user_id=user_id,
                    rule_name=rname,
                    action=str(row.action or ""),
                    route=route,
                    score=None,
                    extra={"rule_id": str(row.id)},
                )
                logger.error(
                    "device_risk_rule_skipped_invalid id=%s name=%s",
                    row.id,
                    rname,
                )
                continue

            try:
                matched, trace = evaluate_condition_node_with_trace(cond, signals, ctx)  # type: ignore[arg-type]
                if not matched:
                    continue
            except Exception as exc:  # noqa: BLE001
                _log_rule_event(
                    "device_risk_rule_error",
                    user_id=user_id,
                    rule_name=(row.name or "").strip() or str(row.id),
                    action=str(row.action or ""),
                    route=route,
                    score=None,
                    extra={"error": str(exc)[:500], "rule_id": str(row.id)},
                )
                logger.warning("device_risk_rule_eval_failed id=%s err=%s", row.id, exc)
                continue

            act = (row.action or "").strip().upper()
            rid = str(row.id)
            rname = (row.name or "").strip() or rid
            raw_conds = cond if isinstance(cond, dict) else {}
            explain: Dict[str, Any] = {
                "rule_name": rname,
                "rule_action": act,
                "matched_conditions": trace,
                "raw_conditions": raw_conds,
            }

            if act == "ALLOW":
                return DynamicRulesEvaluationResult(CombinationRuleOutcome(triggered=False), explain=explain)

            if dry_run_mode:
                dry_payload = {"would_trigger": rname, "would_action": act}
                _log_rule_event(
                    "device_risk_rule_dry_run",
                    user_id=user_id,
                    rule_name=rname,
                    action=act,
                    route=route,
                    score=None,
                    extra={"would_action": act},
                )
                return DynamicRulesEvaluationResult(
                    CombinationRuleOutcome(triggered=False),
                    explain=explain,
                    dry_run=dry_payload,
                )

            if act == "BLOCK":
                _log_rule_event(
                    "device_risk_rule_triggered",
                    user_id=user_id,
                    rule_name=rname,
                    action=act,
                    route=route,
                    score=100,
                )
                return DynamicRulesEvaluationResult(
                    CombinationRuleOutcome(
                        triggered=True,
                        decision="block",
                        forced_score=100,
                        reasons=(f"dynamic_rule:{rname}",),
                    ),
                    explain=explain,
                )
            if act == "STEP_UP":
                _log_rule_event(
                    "device_risk_rule_triggered",
                    user_id=user_id,
                    rule_name=rname,
                    action=act,
                    route=route,
                    score=None,
                )
                return DynamicRulesEvaluationResult(
                    CombinationRuleOutcome(
                        triggered=True,
                        decision="step_up",
                        forced_score=None,
                        reasons=(f"dynamic_rule:{rname}",),
                    ),
                    explain=explain,
                )

            logger.warning("dynamic_risk_rule_unknown_action id=%s action=%s", row.id, act)

        return DynamicRulesEvaluationResult(CombinationRuleOutcome(triggered=False))
    except Exception as exc:  # noqa: BLE001
        _log_rule_event(
            "device_risk_rule_error",
            user_id=user_id,
            rule_name="",
            action="",
            route=route,
            score=None,
            extra={"error": str(exc)[:500]},
        )
        logger.exception("device_risk_rule_error evaluate_dynamic_rules: %s", exc)
        return DynamicRulesEvaluationResult(CombinationRuleOutcome(triggered=False))
