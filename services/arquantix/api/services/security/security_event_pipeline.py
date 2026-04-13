"""
Pipeline unifié d’événements sécurité (DB + normalisation + anonymisation SIEM + sinks).

Point d’entrée : ``emit_security_event`` (compatible fintech / corrélation ``risk_level``).
La persistance réutilise ``persist_auth_security_event`` (table ``auth_security_events``).
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from services.auth.security_event_anonymize import anonymize_security_payload_for_sink
from services.auth.security_events_service import is_security_events_enabled, persist_auth_security_event
from services.security.security_env import (
    is_security_correlation_on_emit_enabled,
    is_security_response_engine_on_emit_enabled,
    security_events_sink_name,
)
from services.security.security_event_sink import get_security_event_sink

logger = logging.getLogger("arquantix.security.siem.pipeline")


def _coerce_user_id(user_id: Optional[str]) -> Optional[int]:
    if user_id is None:
        return None
    s = str(user_id).strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _extract_email_for_hash(metadata: Dict[str, Any]) -> Optional[str]:
    for k in ("email", "mail", "user_email", "identifier"):
        v = metadata.get(k)
        if isinstance(v, str) and "@" in v:
            return v.strip().lower()
    return None


def _email_fingerprint(email: str) -> str:
    return hashlib.sha256(email.encode("utf-8")).hexdigest()


def normalize_security_metadata(
    metadata: Optional[Dict[str, Any]],
    *,
    risk_level: str,
    user_id_raw: Optional[str],
) -> Dict[str, Any]:
    """JSON sérialisable, enrichi (risk_level, user_id_external, email_sha256 si présent)."""
    base: Dict[str, Any] = dict(metadata or {})
    base["risk_level"] = (risk_level or "LOW").strip().upper()[:32]
    if "global_risk_score" in base and base["global_risk_score"] is not None:
        try:
            base["global_risk_score"] = int(base["global_risk_score"])
        except (TypeError, ValueError):
            base["global_risk_score"] = None
    if "action_taken" in base and base["action_taken"] is not None:
        base["action_taken"] = str(base["action_taken"])[:128]
    if "device_reputation_score" in base and base["device_reputation_score"] is not None:
        try:
            base["device_reputation_score"] = int(base["device_reputation_score"])
        except (TypeError, ValueError):
            base["device_reputation_score"] = None
    if "device_reputation_level" in base and base["device_reputation_level"] is not None:
        base["device_reputation_level"] = str(base["device_reputation_level"])[:16]
    for lk in ("login_ml_score", "login_hybrid_score"):
        if lk in base and base[lk] is not None:
            try:
                base[lk] = float(base[lk])
            except (TypeError, ValueError):
                base[lk] = None
    if "login_ml_confidence" in base and base["login_ml_confidence"] is not None:
        try:
            base["login_ml_confidence"] = float(base["login_ml_confidence"])
        except (TypeError, ValueError):
            base["login_ml_confidence"] = None
    if "login_fraud_signals" in base and base["login_fraud_signals"] is not None:
        if not isinstance(base["login_fraud_signals"], list):
            base["login_fraud_signals"] = []
    if user_id_raw is not None and str(user_id_raw).strip() != "":
        coerced = _coerce_user_id(user_id_raw)
        if coerced is None:
            base.setdefault("user_id_external", str(user_id_raw).strip()[:128])
    em = _extract_email_for_hash(base)
    if em:
        base["email_sha256"] = _email_fingerprint(em)
    return base


def build_sink_payload(
    *,
    event_id: str,
    event_type: str,
    user_id_db: Optional[int],
    device_id: str,
    ip_address: Optional[str],
    user_agent: Optional[str],
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    anon = anonymize_security_payload_for_sink(
        user_id=user_id_db,
        device_id=device_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=metadata,
    )
    meta_out = dict(anon.get("metadata") or {})
    if metadata.get("email_sha256"):
        meta_out["email_sha256"] = metadata["email_sha256"]
    return {
        "@timestamp": ts,
        "event_id": event_id,
        "event_type": event_type,
        "user_id": user_id_db,
        **{k: v for k, v in anon.items() if k != "metadata"},
        "metadata": meta_out,
        "schema": "arquantix.security.event.v2",
        "risk_level": metadata.get("risk_level", "LOW"),
        "global_risk_score": metadata.get("global_risk_score"),
        "action_taken": metadata.get("action_taken"),
        "device_reputation_score": metadata.get("device_reputation_score"),
        "device_reputation_level": metadata.get("device_reputation_level"),
        "login_ml_score": metadata.get("login_ml_score"),
        "login_ml_confidence": metadata.get("login_ml_confidence"),
        "login_hybrid_score": metadata.get("login_hybrid_score"),
        "login_fraud_signals": metadata.get("login_fraud_signals"),
    }


def forward_after_persist(
    *,
    event_id: str,
    event_type: str,
    user_id: Optional[int],
    device_id: str,
    ip_address: Optional[str],
    user_agent: Optional[str],
    metadata: Optional[Dict[str, Any]],
    db: Optional[Session],
) -> None:
    """Après flush/commit DB : export SIEM + corrélation rapide optionnelle."""
    meta = metadata if isinstance(metadata, dict) else {}
    payload = build_sink_payload(
        event_id=event_id,
        event_type=event_type,
        user_id_db=user_id,
        device_id=device_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata=meta,
    )
    sink = get_security_event_sink()
    try:
        ok = sink.push(payload)
        if not ok:
            logger.debug("siem_sink not delivered for %s", event_type)
    except Exception as exc:  # noqa: BLE001
        logger.warning("siem_sink push failed: %s", exc)

    if is_security_correlation_on_emit_enabled():
        try:
            from services.auth.security_correlation_service import quick_check_after_event

            quick_check_after_event(db, event_type=event_type, user_id=user_id, ip_address=ip_address)
        except Exception as exc:  # noqa: BLE001
            logger.warning("quick_correlation failed: %s", exc)

    if (
        user_id is not None
        and not str(event_type).startswith("auth.security.action.")
        and not meta.get("skip_security_response_engine")
        and is_security_response_engine_on_emit_enabled()
    ):
        try:
            from services.security.security_response_engine import recompute_user_risk_and_enforce

            recompute_user_risk_and_enforce(db, int(user_id))
        except Exception as exc:  # noqa: BLE001
            logger.warning("security_response_engine recompute failed: %s", exc)


def emit_security_event(
    event_type: str,
    user_id: Optional[str],
    device_id: Optional[str],
    ip: Optional[str],
    metadata: Optional[dict] = None,
    risk_level: str = "LOW",
    *,
    user_agent: Optional[str] = None,
    db: Optional[Session] = None,
) -> None:
    """
    Émet un événement : persistance + forward SIEM (via hook persist).

    ``user_id`` peut être un identifiant numérique admin ; sinon stocké dans metadata ``user_id_external``.
    """
    if not is_security_events_enabled():
        return
    uid_int = _coerce_user_id(user_id)
    meta = normalize_security_metadata(metadata or {}, risk_level=risk_level, user_id_raw=user_id)
    try:
        meta_json = json.loads(json.dumps(meta, default=str))
    except Exception:  # noqa: BLE001
        meta_json = {"_normalize_error": True, "risk_level": risk_level}

    persist_auth_security_event(
        user_id=uid_int,
        device_id=(device_id or "")[:128] if device_id else "",
        event_type=event_type[:128],
        ip_address=ip,
        user_agent=user_agent,
        metadata=meta_json,
        db=db,
    )


def build_structured_preview(
    *,
    event_type: str,
    user_id: Optional[str],
    device_id: Optional[str],
    ip: Optional[str],
    user_agent: Optional[str],
    metadata: Optional[Dict[str, Any]],
    risk_level: str = "LOW",
) -> Dict[str, Any]:
    uid_int = _coerce_user_id(user_id)
    meta = normalize_security_metadata(metadata or {}, risk_level=risk_level, user_id_raw=user_id)
    return build_sink_payload(
        event_id=str(uuid.uuid4()),
        event_type=event_type,
        user_id_db=uid_int,
        device_id=device_id or "",
        ip_address=ip,
        user_agent=user_agent,
        metadata=meta,
    )
