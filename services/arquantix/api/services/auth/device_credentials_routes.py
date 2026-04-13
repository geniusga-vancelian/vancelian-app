"""PR D2 / PR D3 — credentials device, enregistrement clé, cycle de vie, nonces, action signée."""
from __future__ import annotations

import base64
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from auth import get_current_user
from database import AdminUser, AuthDeviceCredential, get_db
from services.auth.device_attestation_service import (
    evaluate_header_for_auth,
    extract_pk_sha256_from_attestation_header,
    parse_x_device_attestation_header,
)
from services.auth.device_pr_d3_policy import (
    device_signature_nonce_ttl_sec,
    register_key_pk_attestation_binding_required,
)
from services.auth.device_pr_d4_policy import nonce_route_scoping_enabled
from services.auth.device_request_signature import normalize_public_key_b64_to_spki_der
from services.auth.device_sensitive_signature import default_nonce_ttl_sec, require_sensitive_device_signature
from services.auth.device_signature_failure_rl import check_and_record_signature_failure
from services.auth.device_signature_normalization import normalize_signature_path
from services.auth.device_signature_nonce_service import mint_device_signature_nonce
from services.auth.refresh_session import LEGACY_UNKNOWN_DEVICE, normalize_device_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/device", tags=["auth-device-pr-d2"])


class RegisterDeviceKeyRequest(BaseModel):
    public_key_spki_b64: str = Field(..., min_length=32, max_length=8192)
    attestation_level: Optional[str] = Field(default=None, max_length=32)
    device_label: Optional[str] = Field(default=None, max_length=128)


class RegisterDeviceKeyResponse(BaseModel):
    ok: bool
    device_id: str


class DeviceCredentialItem(BaseModel):
    device_id: str
    device_label: Optional[str]
    created_at: datetime
    last_used_at: Optional[datetime]
    revoked_at: Optional[datetime]
    public_key_sha256_hex: Optional[str]
    attestation_bound_at: Optional[datetime]


class DeviceListResponse(BaseModel):
    devices: List[DeviceCredentialItem]


class SignatureNonceResponse(BaseModel):
    nonce: str
    expires_at: datetime
    ttl_seconds: int


@router.post("/register-key", response_model=RegisterDeviceKeyResponse)
def register_device_public_key(
    body: RegisterDeviceKeyRequest,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    x_device_attestation: Optional[str] = Header(None, alias="X-Device-Attestation"),
):
    """Enregistre la clé publique P-256 ; PR D3 optionnel : liaison attestation ↔ hash clé."""
    if x_device_id is None or not str(x_device_id).strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Device-ID header required",
        )
    did = normalize_device_id(x_device_id)
    if did == "legacy-unknown":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Device-ID must be a real device identifier",
        )

    der = normalize_public_key_b64_to_spki_der(body.public_key_spki_b64)
    if der is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid public key (SPKI DER or SEC1 uncompressed)",
        )
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric import ec

        pub = serialization.load_der_public_key(der)
        if not isinstance(pub, ec.EllipticCurvePublicKey):
            raise ValueError("not ec")
        if pub.curve.name != "secp256r1":
            raise ValueError("curve")
    except Exception as exc:
        logger.info("register_device_public_key reject key parse: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="public_key must be ECDSA P-256 (SPKI DER)",
        ) from exc

    spki_b64_stored = base64.b64encode(der).decode("ascii")
    pk_hex = hashlib.sha256(der).hexdigest()
    now = datetime.now(timezone.utc)

    binding = register_key_pk_attestation_binding_required()
    if binding:
        if not x_device_attestation or not str(x_device_attestation).strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="X-Device-Attestation required (REGISTER_KEY_PK_ATTESTATION_BINDING)",
            )
        parsed = parse_x_device_attestation_header(x_device_attestation)
        att_res, _trust, _step = evaluate_header_for_auth(
            db=db,
            request_device_id=did,
            attestation_header_raw=x_device_attestation,
            legacy_unknown_label=LEGACY_UNKNOWN_DEVICE,
        )
        if att_res is None or not att_res.is_valid:
            check_and_record_signature_failure(f"attest:{current_user.id}:{did}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "device_attestation_invalid", "message": "Attestation required for key binding."},
            )
        claim = extract_pk_sha256_from_attestation_header(parsed or {})
        if not claim or claim != pk_hex:
            check_and_record_signature_failure(f"attest:{current_user.id}:{did}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "attestation_pk_mismatch",
                    "message": "pk_sha256 in attestation must match registered public key.",
                },
            )

    row = (
        db.query(AuthDeviceCredential)
        .filter(
            AuthDeviceCredential.user_id == current_user.id,
            AuthDeviceCredential.device_id == did,
        )
        .first()
    )
    if row is not None and row.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Device credential revoked — register a new key after rotation.",
        )

    att_bound = now if binding else None
    if row is None:
        row = AuthDeviceCredential(
            user_id=current_user.id,
            device_id=did,
            public_key_spki_b64=spki_b64_stored,
            attestation_level=(body.attestation_level or None),
            last_used_at=now,
            device_label=(body.device_label or None),
            public_key_sha256_hex=pk_hex,
            attestation_bound_at=att_bound,
        )
        db.add(row)
    else:
        row.public_key_spki_b64 = spki_b64_stored
        row.attestation_level = body.attestation_level or row.attestation_level
        row.last_used_at = now
        row.device_label = body.device_label if body.device_label is not None else row.device_label
        row.public_key_sha256_hex = pk_hex
        if att_bound is not None:
            row.attestation_bound_at = att_bound
    db.commit()
    return RegisterDeviceKeyResponse(ok=True, device_id=did)


@router.get("/list", response_model=DeviceListResponse)
def list_device_credentials(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    rows = (
        db.query(AuthDeviceCredential)
        .filter(AuthDeviceCredential.user_id == current_user.id)
        .order_by(AuthDeviceCredential.created_at.desc())
        .all()
    )
    items: List[DeviceCredentialItem] = []
    for r in rows:
        items.append(
            DeviceCredentialItem(
                device_id=r.device_id,
                device_label=r.device_label,
                created_at=r.created_at,
                last_used_at=r.last_used_at,
                revoked_at=r.revoked_at,
                public_key_sha256_hex=r.public_key_sha256_hex,
                attestation_bound_at=r.attestation_bound_at,
            )
        )
    return DeviceListResponse(devices=items)


@router.post("/{device_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_device_credential(
    device_id: str,
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
):
    did = normalize_device_id(device_id)
    row = (
        db.query(AuthDeviceCredential)
        .filter(
            AuthDeviceCredential.user_id == current_user.id,
            AuthDeviceCredential.device_id == did,
        )
        .first()
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unknown device")
    row.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return None


@router.post("/signature-nonce", response_model=SignatureNonceResponse)
def issue_signature_nonce(
    db: Session = Depends(get_db),
    current_user: AdminUser = Depends(get_current_user),
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    route: Optional[str] = Query(
        None,
        description="PR D4 : chemin exact de la requête signée (ex. /auth/device/sensitive-action).",
    ),
):
    """Nonce pour signature PR D3 (routes sensibles) — TTL court. PR D4 : paramètre ``route`` obligatoire."""
    if not x_device_id or not str(x_device_id).strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Device-ID required")
    did = normalize_device_id(x_device_id)
    ttl = default_nonce_ttl_sec()
    route_path: Optional[str] = None
    if nonce_route_scoping_enabled():
        rp = (route or "").strip()
        if not rp.startswith("/"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="route query required for PR D4 (e.g. ?route=/auth/device/sensitive-action)",
            )
        route_path = normalize_signature_path(rp)
    raw, exp = mint_device_signature_nonce(
        db=db,
        user_id=current_user.id,
        device_id=did,
        purpose="sensitive",
        ttl_sec=ttl,
        route_path=route_path,
    )
    return SignatureNonceResponse(nonce=raw, expires_at=exp, ttl_seconds=ttl)


@router.post("/sensitive-action", response_model=dict[str, Any])
def sensitive_action_demo(
    current_user: AdminUser = Depends(require_sensitive_device_signature),
):
    """Exemple d’endpoint exigeant signature + nonce lorsque ``DEVICE_SECURITY_LEVEL>=2``."""
    return {"ok": True, "user_id": current_user.id}


@router.get("/policy")
def device_security_policy_public() -> dict[str, Any]:
    """Métadonnées non sensibles pour clients (TTL nonce, flags effectifs)."""
    from services.auth.device_pr_d3_policy import sensitive_routes_device_signature_enabled
    from services.auth.device_attestation_pr_e_policy import (
        device_attestation_required_login,
        device_attestation_required_refresh,
        device_attestation_required_sensitive,
        device_trust_required_level,
    )
    from services.auth.device_pr_d4_policy import (
        device_access_jwt_binding_enabled,
        device_pr_d4_enabled,
        device_risk_revoke_all_sessions_threshold,
        nonce_route_scoping_enabled,
        sensitive_signature_clock_skew_sec,
    )
    from services.auth.device_security_pr_d2 import device_security_level

    return {
        "device_security_level": device_security_level(),
        "sensitive_signature_required": sensitive_routes_device_signature_enabled(),
        "nonce_ttl_seconds": device_signature_nonce_ttl_sec(),
        "register_key_pk_attestation_binding": register_key_pk_attestation_binding_required(),
        "pr_d4_enabled": device_pr_d4_enabled(),
        "nonce_route_scoping": nonce_route_scoping_enabled(),
        "jwt_device_binding": device_access_jwt_binding_enabled(),
        "sensitive_signature_clock_skew_sec": sensitive_signature_clock_skew_sec(),
        "signature_path_normalization": True,
        "body_hash_accepts_json_canonical": True,
        "device_binding_hash_hex_chars": 32,
        "risk_revoke_all_sessions_threshold": device_risk_revoke_all_sessions_threshold(),
        "device_attestation_required_login": device_attestation_required_login(),
        "device_attestation_required_refresh": device_attestation_required_refresh(),
        "device_attestation_required_sensitive": device_attestation_required_sensitive(),
        "device_trust_required_level": device_trust_required_level(),
    }
