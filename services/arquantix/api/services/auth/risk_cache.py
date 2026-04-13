"""PR G — cache distribué des résultats PR F (court TTL, cohérence multi-instance)."""
from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional, TYPE_CHECKING

from services.auth.redis_client import get_redis_client
from services.auth.redis_metrics import bump_redis_error, bump_redis_hit, bump_redis_miss
from services.security.security_env import (
    device_risk_cache_rules_version,
    device_risk_cache_ttl_sec,
    is_redis_cache_enabled,
)

if TYPE_CHECKING:
    from services.auth.device_risk_engine_pr_f import RiskEvaluationResult

logger = logging.getLogger("arquantix.auth.risk_cache")


def _risk_key(user_id: int, device_id: str) -> str:
    rv = device_risk_cache_rules_version()
    suffix = f":{rv}" if rv else ""
    # device_id déjà normalisé côté appelant
    safe_dev = device_id.replace(":", "_")[:200]
    return f"risk{suffix}:{user_id}:{safe_dev}"


def risk_evaluation_result_to_payload(r: "RiskEvaluationResult") -> Dict[str, Any]:
    return {
        "score": r.score,
        "decision": r.decision,
        "risk_reasons": list(r.risk_reasons),
        "dry_run_result": r.dry_run_result,
        "triggered_rule_name": r.triggered_rule_name,
        "triggered_rule_conditions": r.triggered_rule_conditions,
    }


def risk_evaluation_result_from_payload(
    payload: Dict[str, Any],
    ctx: Any,
) -> "RiskEvaluationResult":
    from services.auth.device_risk_engine_pr_f import RiskEvaluationResult

    return RiskEvaluationResult(
        score=int(payload["score"]),
        decision=payload["decision"],  # type: ignore[arg-type]
        context=ctx,
        risk_reasons=list(payload.get("risk_reasons") or []),
        dry_run_result=payload.get("dry_run_result"),
        triggered_rule_name=payload.get("triggered_rule_name"),
        triggered_rule_conditions=payload.get("triggered_rule_conditions"),
    )


def get_risk_cache_payload(user_id: int, device_id: str) -> Optional[Dict[str, Any]]:
    """Retourne le JSON déserialisé ou ``None``."""
    if not is_redis_cache_enabled() or device_risk_cache_ttl_sec() <= 0:
        return None
    r = get_redis_client()
    if r is None:
        return None
    key = _risk_key(user_id, device_id)
    try:
        raw = r.get(key)
        if not raw:
            bump_redis_miss()
            logger.info(
                "redis_cache_miss",
                extra={"event": "redis_cache_miss", "layer": "risk", "key": key[:80]},
            )
            return None
        bump_redis_hit()
        logger.info(
            "redis_cache_hit",
            extra={"event": "redis_cache_hit", "layer": "risk", "key": key[:80]},
        )
        return json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        bump_redis_error()
        logger.warning("redis_cache_error layer=risk op=get err=%s", exc)
        return None


def set_risk_cache_payload(user_id: int, device_id: str, payload: Dict[str, Any]) -> None:
    if not is_redis_cache_enabled() or device_risk_cache_ttl_sec() <= 0:
        return
    r = get_redis_client()
    if r is None:
        return
    ttl = device_risk_cache_ttl_sec()
    key = _risk_key(user_id, device_id)
    body = dict(payload)
    body["ts"] = int(time.time())
    try:
        r.setex(key, ttl, json.dumps(body, separators=(",", ":"), default=str))
    except Exception as exc:  # noqa: BLE001
        bump_redis_error()
        logger.warning("redis_cache_error layer=risk op=setex err=%s", exc)


def maybe_cache_risk_evaluation_result(
    user_id: int,
    device_id: str,
    result: "RiskEvaluationResult",
    *,
    allow: bool,
) -> None:
    if not allow or result.dry_run_result is not None:
        return
    set_risk_cache_payload(user_id, device_id, risk_evaluation_result_to_payload(result))
