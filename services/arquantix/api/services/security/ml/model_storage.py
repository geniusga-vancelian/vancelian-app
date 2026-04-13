"""
Stockage versionné des artefacts ML (local, S3 optionnel).

Manifest obligatoire : version, kind, feature_keys, trained_at_utc.
"""
from __future__ import annotations

import io
import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("arquantix.security.ml.storage")

_MANIFEST = "manifest.json"
_MODEL_FILE = "model.joblib"


def _safe_version(v: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._-]", "_", v)[:128]


@dataclass
class ModelManifest:
    version: str
    kind: str
    feature_keys: List[str]
    trained_at_utc: str
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "kind": self.kind,
            "feature_keys": self.feature_keys,
            "trained_at_utc": self.trained_at_utc,
            **(self.extra or {}),
        }


def base_model_dir() -> Path:
    raw = (os.getenv("FRAUD_ML_MODEL_DIR") or "data/fraud_ml_models").strip()
    p = Path(raw)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[3] / p
    return p


def manifest_path(version: str) -> Path:
    return base_model_dir() / _safe_version(version) / _MANIFEST


def model_joblib_path(version: str) -> Path:
    return base_model_dir() / _safe_version(version) / _MODEL_FILE


def save_bytes_to_s3(*, bucket: str, key: str, body: bytes) -> None:
    import boto3

    boto3.client("s3").put_object(Bucket=bucket, Key=key, Body=body)


def load_bytes_from_s3(*, bucket: str, key: str) -> bytes:
    import boto3

    obj = boto3.client("s3").get_object(Bucket=bucket, Key=key)
    return obj["Body"].read()


def save_artifact_bundle(
    *,
    version: str,
    manifest: ModelManifest,
    joblib_bytes: bytes,
) -> str:
    """Écrit localement ; optionnellement synchronise vers S3."""
    ver = _safe_version(version)
    d = base_model_dir() / ver
    d.mkdir(parents=True, exist_ok=True)
    mp = d / _MANIFEST
    jp = d / _MODEL_FILE
    mp.write_text(json.dumps(manifest.to_dict(), indent=2), encoding="utf-8")
    jp.write_bytes(joblib_bytes)
    (base_model_dir() / "LATEST").write_text(ver, encoding="utf-8")

    bucket = (os.getenv("FRAUD_ML_S3_BUCKET") or "").strip()
    prefix = (os.getenv("FRAUD_ML_S3_PREFIX") or "fraud_ml_models").strip().strip("/")
    if bucket:
        try:
            save_bytes_to_s3(bucket=bucket, key=f"{prefix}/{ver}/{_MANIFEST}", body=mp.read_bytes())
            save_bytes_to_s3(bucket=bucket, key=f"{prefix}/{ver}/{_MODEL_FILE}", body=joblib_bytes)
            save_bytes_to_s3(bucket=bucket, key=f"{prefix}/LATEST", body=ver.encode("utf-8"))
        except Exception as exc:  # noqa: BLE001
            logger.warning("fraud_ml S3 upload failed: %s", exc)

    return ver


def read_latest_version_local() -> Optional[str]:
    latest = base_model_dir() / "LATEST"
    if not latest.is_file():
        return None
    return latest.read_text(encoding="utf-8").strip() or None


def load_manifest(version: Optional[str] = None) -> Optional[ModelManifest]:
    ver = version or read_latest_version_local()
    if not ver:
        return None
    mp = manifest_path(ver)
    if not mp.is_file():
        return None
    data = json.loads(mp.read_text(encoding="utf-8"))
    return ModelManifest(
        version=str(data.get("version", ver)),
        kind=str(data.get("kind", "random_forest")),
        feature_keys=list(data.get("feature_keys") or []),
        trained_at_utc=str(data.get("trained_at_utc", "")),
        extra={k: v for k, v in data.items() if k not in ("version", "kind", "feature_keys", "trained_at_utc")},
    )


def load_joblib_bytes(version: Optional[str] = None) -> Optional[bytes]:
    ver = version or read_latest_version_local()
    if not ver:
        return None
    jp = model_joblib_path(ver)
    if jp.is_file():
        return jp.read_bytes()
    bucket = (os.getenv("FRAUD_ML_S3_BUCKET") or "").strip()
    prefix = (os.getenv("FRAUD_ML_S3_PREFIX") or "fraud_ml_models").strip().strip("/")
    if bucket:
        try:
            return load_bytes_from_s3(bucket=bucket, key=f"{prefix}/{_safe_version(ver)}/{_MODEL_FILE}")
        except Exception as exc:  # noqa: BLE001
            logger.warning("fraud_ml S3 load failed: %s", exc)
    return None


def latest_manifest_for_api() -> Dict[str, Any]:
    m = load_manifest()
    if not m:
        return {"loaded": False, "model_version": None, "model_kind": None, "trained_at_utc": None}
    return {
        "loaded": True,
        "model_version": m.version,
        "model_kind": m.kind,
        "trained_at_utc": m.trained_at_utc,
        "feature_keys": m.feature_keys,
        "storage_path": str(base_model_dir() / _safe_version(m.version)),
    }


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
