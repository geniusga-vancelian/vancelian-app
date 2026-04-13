"""
Évaluation hybride fraude au login / refresh : ML baseline + règles vélocité explicites.

Garde-fous : le score ML ne peut pas à lui seul imposer un blocage si l’heuristique globale
est sous le gate (aligné sur ``FRAUD_ML_ENFORCE_MIN_HEURISTIC``).
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from services.security.fraud_ml_inference_service import is_fraud_ml_inference_enabled, predict_user_risk_ml
from services.security.ml.login_fraud_features import build_login_feature_vector
from services.security.security_env import (
    fraud_ml_enforce_min_heuristic,
    is_login_fraud_ml_evaluation_enabled,
    login_fraud_pattern_weight,
)

logger = logging.getLogger("arquantix.security.ml.login_fraud_eval")


def is_login_fraud_evaluation_enabled() -> bool:
    return is_login_fraud_ml_evaluation_enabled()


def _ml_enforce_gate() -> int:
    return fraud_ml_enforce_min_heuristic()


def _pattern_weight() -> float:
    return login_fraud_pattern_weight()


def _heuristic_snapshot(db: Session, user_id: int) -> Dict[str, Any]:
    from services.security.security_response_engine import compute_global_risk_score_with_detail

    _enf, _lvl, detail = compute_global_risk_score_with_detail(db, user_id)
    return detail


def evaluate_pattern_rules(features: Dict[str, float]) -> List[Dict[str, Any]]:
    """
    Règles vélocité / schémas — visibles dans ``login_fraud_signals`` (SIEM / audit).
    """
    signals: List[Dict[str, Any]] = []

    if features.get("login_count_1h", 0) >= 8:
        signals.append(
            {
                "code": "high_login_velocity_1h",
                "severity": "HIGH",
                "detail": f"login_count_1h={int(features['login_count_1h'])}",
                "source": "heuristic_pattern",
            }
        )
    elif features.get("login_count_1h", 0) >= 5:
        signals.append(
            {
                "code": "elevated_login_velocity_1h",
                "severity": "MEDIUM",
                "detail": f"login_count_1h={int(features['login_count_1h'])}",
                "source": "heuristic_pattern",
            }
        )

    if features.get("new_device_recently", 0) >= 1 and features.get("unique_country_count_24h", 0) >= 2:
        signals.append(
            {
                "code": "new_device_multi_country_24h",
                "severity": "HIGH",
                "detail": "new_device_recently=1 and unique_country_count_24h>=2",
                "source": "heuristic_pattern",
            }
        )

    if features.get("unique_device_count_24h", 0) >= 4:
        signals.append(
            {
                "code": "multi_device_short_window_24h",
                "severity": "HIGH",
                "detail": f"unique_device_count_24h={int(features['unique_device_count_24h'])}",
                "source": "heuristic_pattern",
            }
        )

    if features.get("refresh_velocity", 0) >= 25:
        signals.append(
            {
                "code": "refresh_burst_1h",
                "severity": "HIGH",
                "detail": f"refresh_velocity={int(features['refresh_velocity'])}",
                "source": "heuristic_pattern",
            }
        )
    elif features.get("refresh_velocity", 0) >= 15:
        signals.append(
            {
                "code": "elevated_refresh_rate_1h",
                "severity": "MEDIUM",
                "detail": f"refresh_velocity={int(features['refresh_velocity'])}",
                "source": "heuristic_pattern",
            }
        )

    if features.get("otp_fail_then_success_new_device", 0) >= 1:
        signals.append(
            {
                "code": "otp_fail_then_success_different_device_1h",
                "severity": "HIGH",
                "detail": "OTP échecs puis succès sur autre device (fenêtre 1h)",
                "source": "heuristic_pattern",
            }
        )

    if features.get("failed_login_count_1h", 0) >= 6:
        signals.append(
            {
                "code": "failed_login_spike_1h",
                "severity": "MEDIUM",
                "detail": f"failed_login_count_1h={int(features['failed_login_count_1h'])}",
                "source": "heuristic_pattern",
            }
        )

    return signals


def _pattern_risk_score(signals: List[Dict[str, Any]]) -> float:
    pts = 0.0
    for s in signals:
        sev = str(s.get("severity") or "").upper()
        if sev == "CRITICAL":
            pts += 40
        elif sev == "HIGH":
            pts += 28
        elif sev == "MEDIUM":
            pts += 15
        else:
            pts += 6
    return float(min(100.0, pts))


def _top_features_for_explain(features: Dict[str, float], *, k: int = 5) -> List[Dict[str, Any]]:
    ranked = sorted(features.items(), key=lambda kv: abs(kv[1]), reverse=True)
    out: List[Dict[str, Any]] = []
    for name, value in ranked[:k]:
        out.append(
            {
                "name": name,
                "value": float(value),
                "contribution_hint": "magnitude",
            }
        )
    return out


def _recommendation_from_scores(
    *,
    hybrid: float,
    pattern_risk: float,
    heuristic_score: int,
    ml_score: float,
    ml_ok: bool,
    gate: int,
    signals: List[Dict[str, Any]],
) -> str:
    """allow | step_up | review | block — ``block`` réservé aux cas alignés garde-fous."""
    sev_high = sum(1 for s in signals if str(s.get("severity")).upper() == "HIGH")
    sev_crit = sum(1 for s in signals if str(s.get("severity")).upper() == "CRITICAL")

    # Blocage : uniquement si patterns forts ET heuristique déjà significative (pas le ML seul).
    if sev_crit >= 1 and heuristic_score >= max(30, gate - 15):
        return "block"
    if sev_high >= 2 and pattern_risk >= 55 and heuristic_score >= gate:
        return "block"

    if hybrid >= 72 or (sev_high >= 1 and pattern_risk >= 50):
        return "step_up"
    if hybrid >= 48 or pattern_risk >= 35 or (ml_ok and ml_score >= 60 and heuristic_score >= gate):
        return "review"
    return "allow"


def _blend_hybrid(*, ml_score: float, pattern_risk: float, ml_ok: bool) -> float:
    pw = _pattern_weight()
    if not ml_ok:
        return float(min(100.0, pattern_risk))
    return float(min(100.0, (1.0 - pw) * ml_score + pw * pattern_risk))


def evaluate_login_fraud_risk(
    db: Session,
    user_id: int,
    *,
    device_hash: Optional[str] = None,
    ip: Optional[str] = None,
    session_id: Optional[Any] = None,
) -> Dict[str, Any]:
    return _evaluate_fraud_risk(
        db,
        user_id,
        flow="login",
        device_hash=device_hash,
        ip=ip,
        session_id=session_id,
    )


def evaluate_refresh_fraud_risk(
    db: Session,
    user_id: int,
    *,
    device_hash: Optional[str] = None,
    ip: Optional[str] = None,
    session_id: Optional[Any] = None,
) -> Dict[str, Any]:
    return _evaluate_fraud_risk(
        db,
        user_id,
        flow="refresh",
        device_hash=device_hash,
        ip=ip,
        session_id=session_id,
    )


def _evaluate_fraud_risk(
    db: Session,
    user_id: int,
    *,
    flow: str,
    device_hash: Optional[str],
    ip: Optional[str],
    session_id: Optional[Any],
) -> Dict[str, Any]:
    gate = _ml_enforce_gate()
    empty: Dict[str, Any] = {
        "ml_score": 0.0,
        "confidence": 0.0,
        "top_features": [],
        "hybrid_score": 0.0,
        "recommendation": "allow",
        "pattern_signals": [],
        "pattern_risk": 0.0,
        "heuristic_score": 0,
        "enforcement_score": 0,
        "ml_ok": False,
        "flow": flow,
        "model_version": "",
        "deterministic_block_eligible": False,
    }

    if not is_login_fraud_evaluation_enabled():
        empty["reason"] = "login_fraud_evaluation_disabled"
        return empty

    detail = _heuristic_snapshot(db, user_id)
    heuristic_score = int(detail.get("heuristic_score") or 0)
    enforcement_score = int(detail.get("enforcement_score") or heuristic_score)

    feats = build_login_feature_vector(
        db,
        user_id,
        session_id=session_id,
        device_hash=device_hash,
        ip=ip,
    )
    signals = evaluate_pattern_rules(feats)
    pattern_risk = _pattern_risk_score(signals)

    ml_score = 0.0
    confidence = 0.0
    model_version = ""
    ml_ok = False

    if is_fraud_ml_inference_enabled():
        pred = predict_user_risk_ml(db, user_id)
        ml_ok = bool(pred.get("ok"))
        ml_score = float(pred.get("ml_score") or 0.0)
        confidence = float(pred.get("confidence") or 0.0)
        model_version = str(pred.get("model_version") or "")
    else:
        ml_ok = False

    hybrid = _blend_hybrid(ml_score=ml_score, pattern_risk=pattern_risk, ml_ok=ml_ok)
    if heuristic_score < gate and ml_ok:
        # N’amplifie pas artificiellement l’hybride si le gate ML n’est pas franchi côté heuristique.
        hybrid = float(min(hybrid, max(hybrid * 0.85, float(heuristic_score))))

    rec = _recommendation_from_scores(
        hybrid=hybrid,
        pattern_risk=pattern_risk,
        heuristic_score=heuristic_score,
        ml_score=ml_score,
        ml_ok=ml_ok,
        gate=gate,
        signals=signals,
    )

    det_block = rec == "block" and (
        any(str(s.get("severity")).upper() in ("HIGH", "CRITICAL") for s in signals)
        and heuristic_score >= max(30, gate - 15)
    )

    out: Dict[str, Any] = {
        "ml_score": round(ml_score, 4),
        "confidence": round(confidence, 4),
        "top_features": _top_features_for_explain(feats),
        "hybrid_score": round(hybrid, 4),
        "recommendation": rec,
        "pattern_signals": signals,
        "pattern_risk": round(pattern_risk, 4),
        "heuristic_score": heuristic_score,
        "enforcement_score": enforcement_score,
        "ml_ok": ml_ok,
        "ml_enforce_gate": gate,
        "flow": flow,
        "model_version": model_version,
        "deterministic_block_eligible": det_block,
    }

    logger.info(
        "login_fraud_eval user_id=%s flow=%s recommendation=%s hybrid=%.2f ml_ok=%s heuristic=%s signals=%s",
        user_id,
        flow,
        rec,
        hybrid,
        ml_ok,
        heuristic_score,
        [s.get("code") for s in signals],
    )
    return out


def merge_step_up_from_login_fraud(
    current_step_up: bool,
    evaluation: Dict[str, Any],
) -> bool:
    """N’ajoute du step-up que si la reco l’exige et que les garde-fous sont cohérents."""
    if not evaluation:
        return current_step_up
    rec = str(evaluation.get("recommendation") or "")
    h = int(evaluation.get("heuristic_score") or 0)
    gate = int(evaluation.get("ml_enforce_gate") or _ml_enforce_gate())
    hybrid = float(evaluation.get("hybrid_score") or 0)
    if rec == "step_up" and hybrid >= 50 and h >= min(35, gate):
        return True
    if rec == "review" and hybrid >= 68 and h >= gate:
        return True
    return current_step_up


def metadata_for_security_event(evaluation: Dict[str, Any]) -> Dict[str, Any]:
    """Champs normalisés pour ``auth_security_events`` + SIEM."""
    if not evaluation:
        return {}
    signals = evaluation.get("pattern_signals") or []
    return {
        "login_ml_score": evaluation.get("ml_score"),
        "login_ml_confidence": evaluation.get("confidence"),
        "login_hybrid_score": evaluation.get("hybrid_score"),
        "login_fraud_signals": signals,
        "login_fraud_recommendation": evaluation.get("recommendation"),
        "login_fraud_flow": evaluation.get("flow"),
        "login_fraud_ml_ok": evaluation.get("ml_ok"),
        "login_fraud_model_version": evaluation.get("model_version"),
    }
