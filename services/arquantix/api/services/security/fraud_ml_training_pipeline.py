"""
Entraînement batch à partir de ``auth_security_events`` + labels heuristiques.

Labels : fraude = 1 si ``assess_user_risk`` est HIGH/CRITICAL pour l’utilisateur.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from database import AuthSecurityEvent
from services.security.ml.fraud_feature_store import build_feature_vector
from services.security.ml.fraud_ml_model import FEATURE_KEYS, clear_model_cache, train_model
from services.security.ml.model_storage import ModelManifest, save_artifact_bundle, utc_now_iso
from services.security.security_correlation_engine import assess_user_risk

logger = logging.getLogger("arquantix.security.ml.training")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def build_training_dataset(
    db: Session,
    *,
    since_days: int = 30,
    min_events_per_user: int = 3,
) -> List[Tuple[Dict[str, float], int]]:
    """Construit (features, label) pour chaque utilisateur ayant assez d’événements."""
    since = _utcnow() - timedelta(days=max(7, since_days))
    uids = (
        db.execute(
            select(AuthSecurityEvent.user_id)
            .where(
                AuthSecurityEvent.user_id.isnot(None),
                AuthSecurityEvent.created_at >= since,
            )
            .distinct()
        )
        .scalars()
        .all()
    )
    out: List[Tuple[Dict[str, float], int]] = []
    for uid in uids:
        if uid is None:
            continue
        uid_int = int(uid)
        n_ev = int(
            db.execute(
                select(func.count())
                .select_from(AuthSecurityEvent)
                .where(
                    AuthSecurityEvent.user_id == uid_int,
                    AuthSecurityEvent.created_at >= since,
                )
            ).scalar_one()
            or 0
        )
        if n_ev < min_events_per_user:
            continue
        fv = build_feature_vector(db, uid_int)
        ass = assess_user_risk(db, uid_int)
        label = 1 if ass.risk_level in ("HIGH", "CRITICAL") else 0
        out.append((fv, label))
    return out


def run_batch_retraining(
    db: Session,
    *,
    since_days: int = 30,
    kind: str | None = None,
) -> Dict[str, Any]:
    """
    Entraîne, versionne et persiste le modèle. Lève ``ValueError`` si trop peu de données.
    """
    min_samples = int(os.getenv("FRAUD_ML_MIN_SAMPLES", "20"))
    dataset = build_training_dataset(db, since_days=since_days)
    if len(dataset) < min_samples:
        raise ValueError(f"too_few_samples: {len(dataset)} < {min_samples}")

    joblib_bytes, version, extra = train_model(dataset, kind=kind)
    mk = str(extra.get("model_kind", "random_forest"))
    manifest = ModelManifest(
        version=version,
        kind=mk,
        feature_keys=list(FEATURE_KEYS),
        trained_at_utc=utc_now_iso(),
        extra={k: v for k, v in extra.items() if k != "model_kind"},
    )
    saved_ver = save_artifact_bundle(version=version, manifest=manifest, joblib_bytes=joblib_bytes)
    clear_model_cache()
    logger.info("fraud_ml training done version=%s samples=%s", saved_ver, len(dataset))
    return {
        "version": saved_ver,
        "n_samples": len(dataset),
        "model_kind": mk,
        "manifest": manifest.to_dict(),
    }
