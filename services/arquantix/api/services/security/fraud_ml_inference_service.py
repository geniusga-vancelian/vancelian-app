"""
Pipeline d’inférence fraude ML : feature vector → modèle → score.

Ne remplace pas les heuristiques seules pour les actions automatiques (voir Risk Engine).
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from services.security.security_env import is_fraud_ml_inference_enabled

logger = logging.getLogger("arquantix.security.ml.inference")


def predict_user_risk_ml(db: Session, user_id: int) -> Dict[str, Any]:
    """
    Retourne au minimum : ok, ml_score, confidence, model_version, reason.

    En cas d’erreur ou de modèle absent : ``ok=False`` (fallback heuristique côté Risk Engine).
    """
    if not is_fraud_ml_inference_enabled():
        return {
            "ok": False,
            "ml_score": 0.0,
            "confidence": 0.0,
            "model_version": "",
            "reason": "inference_disabled",
        }
    try:
        from services.security.ml.fraud_feature_store import build_feature_vector
        from services.security.ml.fraud_ml_model import predict as ml_predict

        fv = build_feature_vector(db, user_id)
        out = ml_predict(fv)
        return dict(out)
    except Exception as exc:  # noqa: BLE001
        logger.warning("fraud_ml inference failed user=%s: %s", user_id, exc)
        return {
            "ok": False,
            "ml_score": 0.0,
            "confidence": 0.0,
            "model_version": "",
            "reason": "inference_error",
        }
