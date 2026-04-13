"""Endpoints admin — métadonnées modèle fraude ML et prédiction diagnostic."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth import get_current_user
from database import AdminUser, get_db
from schemas import FraudMLModelInfoResponse, FraudMLPredictResponse
from services.security.ml import model_storage
from services.security.ml.fraud_feature_store import build_feature_vector
from services.security.security_response_engine import compute_global_risk_score_with_detail

router = APIRouter(prefix="/admin/security/ml", tags=["admin-security-ml"])


@router.get("/model", response_model=FraudMLModelInfoResponse)
def get_fraud_ml_model(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    _ = db
    _ = current_user
    data = model_storage.latest_manifest_for_api()
    return FraudMLModelInfoResponse(
        loaded=bool(data.get("loaded")),
        model_version=data.get("model_version"),
        model_kind=data.get("model_kind"),
        trained_at_utc=data.get("trained_at_utc"),
        feature_keys=list(data.get("feature_keys") or []),
        storage_path=data.get("storage_path"),
    )


@router.get("/predict/{user_id}", response_model=FraudMLPredictResponse)
def get_fraud_ml_predict(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    _ = current_user
    _, level, detail = compute_global_risk_score_with_detail(db, user_id)
    fv = build_feature_vector(db, user_id)
    return FraudMLPredictResponse(
        user_id=user_id,
        heuristic_score=int(detail["heuristic_score"]),
        hybrid_score=int(detail["hybrid_score"]),
        enforcement_score=int(detail["enforcement_score"]),
        risk_level=level,
        ml_available=bool(detail.get("ml_ok")),
        ml_score=detail.get("ml_score"),
        ml_confidence=detail.get("ml_confidence"),
        model_version=detail.get("model_version"),
        ml_weight=float(detail.get("ml_weight", 0.4)),
        ml_enforce_gate=int(detail.get("ml_enforce_gate", 45)),
        feature_vector=fv,
    )
