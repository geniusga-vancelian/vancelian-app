"""
Modèles baseline : RandomForestClassifier (supervisé), IsolationForest (anomalie).

``predict`` retourne ml_score 0–100, confidence, model_version.
"""
from __future__ import annotations

import io
import logging
import os
import threading
import uuid
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np

logger = logging.getLogger("arquantix.security.ml.model")

FEATURE_KEYS = [
    "login_count_24h",
    "login_count_7d",
    "unique_ip_count_24h",
    "unique_device_count_7d",
    "avg_session_duration",
    "refresh_rate_per_hour",
    "failed_login_ratio",
    "geo_distance_variance",
    "time_of_day_entropy",
    "device_trust_distribution",
    "historical_risk_score_avg",
    "historical_risk_score_max",
]

_lock = threading.Lock()
_cached: Optional[Dict[str, Any]] = None


def default_feature_vector() -> Dict[str, float]:
    return {k: 0.0 for k in FEATURE_KEYS}


def _vector_array(feature_vector: Dict[str, float], keys: List[str]) -> np.ndarray:
    return np.array([[float(feature_vector.get(k, 0.0)) for k in keys]], dtype=np.float64)


def train_model(
    dataset: List[Tuple[Dict[str, float], int]],
    *,
    kind: Optional[str] = None,
) -> Tuple[bytes, str, Dict[str, Any]]:
    """
    Entraîne un modèle. Retourne (joblib_bytes, version, manifest_extra).

    ``dataset`` : liste de (feature_dict, label 0/1).
    """
    from sklearn.ensemble import IsolationForest, RandomForestClassifier
    from sklearn.preprocessing import StandardScaler

    kind = (kind or os.getenv("FRAUD_ML_MODEL_KIND", "random_forest")).strip().lower()
    if kind not in ("random_forest", "isolation_forest"):
        kind = "random_forest"

    if not dataset:
        raise ValueError("empty_dataset")

    X = np.array([[float(row[0].get(k, 0.0)) for k in FEATURE_KEYS] for row in dataset], dtype=np.float64)
    y = np.array([int(row[1]) for row in dataset], dtype=np.int32)

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    model: Any
    if kind == "isolation_forest":
        contamination = float(os.getenv("FRAUD_ML_IF_CONTAMINATION", "0.1"))
        contamination = max(0.01, min(0.45, contamination))
        model = IsolationForest(
            n_estimators=int(os.getenv("FRAUD_ML_IF_ESTIMATORS", "200")),
            contamination=contamination,
            random_state=42,
        )
        model.fit(Xs)
    else:
        if len(np.unique(y)) < 2:
            logger.warning("fraud_ml: single class in labels — falling back to IsolationForest")
            kind = "isolation_forest"
            model = IsolationForest(n_estimators=200, contamination=0.1, random_state=42)
            model.fit(Xs)
        else:
            model = RandomForestClassifier(
                n_estimators=int(os.getenv("FRAUD_ML_RF_ESTIMATORS", "200")),
                max_depth=int(os.getenv("FRAUD_ML_RF_MAX_DEPTH", "12")),
                random_state=42,
                class_weight="balanced_subsample",
            )
            model.fit(Xs, y)

    version = str(os.getenv("FRAUD_ML_TRAIN_VERSION") or "").strip() or uuid.uuid4().hex[:16]
    bundle = {
        "model": model,
        "scaler": scaler,
        "kind": kind,
        "feature_keys": list(FEATURE_KEYS),
        "version": version,
    }
    buf = io.BytesIO()
    joblib.dump(bundle, buf)
    extra = {
        "n_samples": len(dataset),
        "positive_rate": float(y.mean()) if len(y) else 0.0,
        "model_kind": kind,
    }
    return buf.getvalue(), version, extra


def predict(
    feature_vector: Dict[str, float],
    *,
    bundle: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Inférence : ``ml_score`` 0–100, ``confidence`` 0–1, ``model_version``.
    """
    b = bundle or _load_bundle_cached()
    if b is None:
        return {
            "ml_score": 0.0,
            "confidence": 0.0,
            "model_version": "",
            "ok": False,
            "reason": "no_model",
        }

    keys: List[str] = list(b.get("feature_keys") or FEATURE_KEYS)
    model = b["model"]
    scaler = b["scaler"]
    kind = str(b.get("kind", "random_forest"))
    version = str(b.get("version", ""))

    X = _vector_array(feature_vector, keys)
    Xs = scaler.transform(X)

    if kind == "isolation_forest":
        raw = model.decision_function(Xs)[0]
        pred = int(model.predict(Xs)[0])
        # anomalie (–1) ou score bas => risque élevé
        ml_score = float(np.clip(50.0 - 55.0 * float(raw), 0.0, 100.0))
        if pred == -1:
            ml_score = float(min(100.0, ml_score + 15.0))
        confidence = float(np.clip(0.35 + abs(float(raw)) * 1.2, 0.0, 1.0))
    else:
        proba = model.predict_proba(Xs)[0]
        # classe 1 = fraude si présente, sinon dernière colonne
        if proba.shape[0] > 1:
            fraud_p = float(proba[1])
        else:
            fraud_p = float(proba[0])
        ml_score = float(np.clip(fraud_p * 100.0, 0.0, 100.0))
        confidence = float(np.clip(max(proba), 0.0, 1.0))

    return {
        "ml_score": ml_score,
        "confidence": confidence,
        "model_version": version,
        "ok": True,
        "reason": "",
    }


def _load_bundle_cached() -> Optional[Dict[str, Any]]:
    global _cached
    with _lock:
        if _cached is not None:
            return _cached
        from services.security.ml import model_storage

        raw = model_storage.load_joblib_bytes()
        if not raw:
            return None
        try:
            bundle = joblib.load(io.BytesIO(raw))
        except Exception as exc:  # noqa: BLE001
            logger.warning("fraud_ml joblib load failed: %s", exc)
            return None
        man = model_storage.load_manifest()
        if man:
            bundle["version"] = man.version
            bundle.setdefault("kind", man.kind)
            bundle.setdefault("feature_keys", man.feature_keys)
        else:
            bundle.setdefault("version", "unknown")
        _cached = bundle
        return _cached


def clear_model_cache() -> None:
    global _cached
    with _lock:
        _cached = None
