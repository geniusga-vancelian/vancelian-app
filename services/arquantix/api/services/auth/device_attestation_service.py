"""
Vérification d’attestation matérielle (App Attest, DeviceCheck, Play Integrity).

Tier-1 : en strict Apple, chaîne x5c jusqu’à l’ancre PEM configurée, ECDSA sur
l’assertion, et alignement nonce ↔ challenge ``clientDataJSON``. Hors dev,
Play Integrity exige l’API Google si ``PLAY_INTEGRITY_REQUIRE_API_OUTSIDE_DEV`` (défaut).
"""
from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete
from sqlalchemy.orm import Session

logger = logging.getLogger("arquantix.auth.device_attestation")


# Niveau issu de l’analyse cryptographique / verdict (pas le trust stocké session)
TRUST_HIGH = "HIGH"
TRUST_MEDIUM = "MEDIUM"
TRUST_LOW = "LOW"
TRUST_BLOCKED = "BLOCKED"

# Modèle session / JWT
DEVICE_TRUST_TRUSTED = "TRUSTED"
DEVICE_TRUST_UNKNOWN = "UNKNOWN"
DEVICE_TRUST_SUSPICIOUS = "SUSPICIOUS"
DEVICE_TRUST_BLOCKED = "BLOCKED"


@dataclass
class AttestationResult:
    is_valid: bool
    trust_level: str
    risk_flags: List[str] = field(default_factory=list)
    attestation_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


def is_device_attestation_enabled() -> bool:
    v = (os.getenv("DEVICE_ATTESTATION_ENABLED") or "false").strip().lower()
    return v in ("1", "true", "yes", "on")


def is_strict_mode() -> bool:
    return (os.getenv("DEVICE_ATTESTATION_STRICT") or "false").strip().lower() in ("1", "true", "yes")


def fail_blocks_login() -> bool:
    return (os.getenv("DEVICE_ATTESTATION_FAIL_BLOCKS_LOGIN") or "false").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def step_up_on_fail() -> bool:
    return (os.getenv("DEVICE_ATTESTATION_STEP_UP_ON_FAIL") or "true").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def header_required_for_mobile() -> bool:
    """Si true, clients qui envoient X-Device-ID autre que legacy-unknown doivent fournir l’attestation."""
    return (os.getenv("DEVICE_ATTESTATION_HEADER_REQUIRED") or "false").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def map_verdict_to_device_trust(result: AttestationResult) -> str:
    if not result.is_valid:
        return DEVICE_TRUST_SUSPICIOUS
    if result.trust_level == TRUST_HIGH:
        return DEVICE_TRUST_TRUSTED
    if result.trust_level == TRUST_MEDIUM:
        return DEVICE_TRUST_UNKNOWN
    if result.trust_level == TRUST_LOW:
        return DEVICE_TRUST_SUSPICIOUS
    return DEVICE_TRUST_BLOCKED


def parse_x_device_attestation_header(raw: Optional[str]) -> Optional[Dict[str, Any]]:
    if raw is None or not str(raw).strip():
        return None
    s = str(raw).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    try:
        pad = "=" * (-len(s) % 4)
        dec = base64.urlsafe_b64decode(s + pad)
        return json.loads(dec.decode("utf-8"))
    except Exception:  # noqa: BLE001
        logger.debug("X-Device-Attestation parse failed")
        return None


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def mint_attestation_nonce(*, db: Session, platform: str, device_id: str) -> tuple[str, datetime]:
    """Crée un nonce serveur (anti-rejeu côté assertion)."""
    from database import AuthDeviceAttestNonce

    raw = secrets.token_urlsafe(32)
    digest = _sha256_hex(raw.encode("utf-8"))
    ttl = max(60, min(900, int(os.getenv("DEVICE_ATTEST_NONCE_TTL_SEC", "300"))))
    exp = datetime.now(timezone.utc) + timedelta(seconds=ttl)
    row = AuthDeviceAttestNonce(
        nonce_hash=digest,
        platform=(platform or "")[:32],
        device_id_prefix=(device_id or "")[:16],
        expires_at=exp,
    )
    db.add(row)
    db.commit()
    return raw, exp


def attestation_nonce_is_valid(*, db: Session, nonce: str) -> bool:
    """True si le nonce existe, n’est pas expiré et n’a pas encore été consommé."""
    from database import AuthDeviceAttestNonce

    if not nonce or not str(nonce).strip():
        return False
    digest = _sha256_hex(str(nonce).strip().encode("utf-8"))
    now = datetime.now(timezone.utc)
    row = (
        db.query(AuthDeviceAttestNonce)
        .filter(
            AuthDeviceAttestNonce.nonce_hash == digest,
            AuthDeviceAttestNonce.expires_at > now,
            AuthDeviceAttestNonce.consumed_at.is_(None),
        )
        .first()
    )
    return row is not None


def consume_attestation_nonce(*, db: Session, nonce: str) -> bool:
    """Marque le nonce comme consommé après auth réussie."""
    from database import AuthDeviceAttestNonce

    if not nonce or not str(nonce).strip():
        return False
    digest = _sha256_hex(str(nonce).strip().encode("utf-8"))
    now = datetime.now(timezone.utc)
    row = (
        db.query(AuthDeviceAttestNonce)
        .filter(
            AuthDeviceAttestNonce.nonce_hash == digest,
            AuthDeviceAttestNonce.expires_at > now,
            AuthDeviceAttestNonce.consumed_at.is_(None),
        )
        .first()
    )
    if row is None:
        return False
    row.consumed_at = now
    return True


def _artifact_digest(assertion_blob: str, nonce: str) -> str:
    return _sha256_hex(f"{nonce}|{assertion_blob}".encode("utf-8"))


def artifact_replay_seen(*, db: Session, digest: str) -> bool:
    """True si ce digest a déjà été enregistré (rejeu)."""
    from database import AuthDeviceAttestArtifact

    row = db.query(AuthDeviceAttestArtifact).filter(AuthDeviceAttestArtifact.digest == digest).first()
    return row is not None


def register_artifact_replay_guard(*, db: Session, digest: str) -> bool:
    """Enregistre le digest après succès auth. False si conflit (concurrent replay)."""
    from database import AuthDeviceAttestArtifact

    now = datetime.now(timezone.utc)
    db.execute(delete(AuthDeviceAttestArtifact).where(AuthDeviceAttestArtifact.expires_at < now))
    if db.query(AuthDeviceAttestArtifact).filter(AuthDeviceAttestArtifact.digest == digest).first():
        return False
    ttl = max(60, min(3600, int(os.getenv("DEVICE_ATTEST_ARTIFACT_TTL_SEC", "600"))))
    db.add(
        AuthDeviceAttestArtifact(
            digest=digest,
            expires_at=now + timedelta(seconds=ttl),
        )
    )
    return True


def _verify_nonce_optional(db: Optional[Session], nonce: Optional[str]) -> tuple[bool, List[str]]:
    flags: List[str] = []
    if not nonce:
        flags.append("missing_nonce")
        return False, flags
    if db is None:
        return not is_strict_mode(), flags + ([] if not is_strict_mode() else ["no_db_for_nonce"])
    ok = attestation_nonce_is_valid(db=db, nonce=str(nonce))
    if not ok:
        flags.append("nonce_invalid_or_reused_or_expired")
    return ok, flags


def _decode_apple_assertion_cbor(assertion_b64: str) -> tuple[Optional[Dict[str, Any]], List[str]]:
    flags: List[str] = []
    try:
        raw = base64.b64decode(assertion_b64, validate=True)
    except Exception:  # noqa: BLE001
        return None, ["apple_assertion_base64_invalid"]
    try:
        import cbor2

        obj = cbor2.loads(raw)
    except Exception as exc:  # noqa: BLE001
        logger.debug("cbor2.loads assertion failed: %s", exc)
        return None, ["apple_assertion_cbor_invalid"]
    if not isinstance(obj, dict):
        return None, ["apple_assertion_not_map"]
    return obj, flags


def _apple_authenticator_data_ok(auth_data: bytes) -> tuple[bool, List[str]]:
    flags: List[str] = []
    if len(auth_data) < 37:
        return False, ["apple_auth_data_short"]
    # RP / App ID hash : en strict, comparer au hash configuré
    app_id = (os.getenv("IOS_ATTEST_APP_ID") or "").strip()
    if app_id and is_strict_mode():
        expected = hashlib.sha256(app_id.encode("utf-8")).digest()[:32]
        if auth_data[:32] != expected:
            flags.append("apple_app_id_hash_mismatch")
            return False, flags
    return True, flags


def _nonce_matches_apple_challenge(nonce: str, challenge: Any) -> bool:
    if challenge is None:
        return False
    ch = str(challenge).strip()
    if ch == str(nonce).strip():
        return True
    pad = "=" * (-len(ch) % 4)
    for dec in (
        lambda x: base64.urlsafe_b64decode(x + pad),
        lambda x: base64.b64decode(x + pad, validate=False),
    ):
        try:
            raw = dec(ch)
        except Exception:  # noqa: BLE001
            continue
        if raw == str(nonce).encode("utf-8"):
            return True
        if raw == hashlib.sha256(str(nonce).encode("utf-8")).digest():
            return True
    return False


def _apple_client_data_challenge_ok(decoded: Dict[str, Any], nonce: Optional[str]) -> tuple[bool, List[str]]:
    flags: List[str] = []
    if not nonce:
        return True, flags
    cdj = decoded.get("clientDataJSON")
    if cdj is None:
        return False, ["missing_client_data_json"]
    if isinstance(cdj, bytes):
        try:
            cdo = json.loads(cdj.decode("utf-8"))
        except Exception:  # noqa: BLE001
            return False, ["client_data_json_invalid"]
    elif isinstance(cdj, str):
        try:
            cdo = json.loads(cdj)
        except Exception:  # noqa: BLE001
            return False, ["client_data_json_invalid"]
    else:
        return False, ["client_data_json_bad_type"]
    ch = cdo.get("challenge")
    if not ch:
        return False, ["missing_challenge_in_client_data"]
    if not _nonce_matches_apple_challenge(str(nonce), ch):
        return False, ["apple_challenge_nonce_mismatch"]
    return True, flags


def _find_x5c_in_cbor(obj: Any) -> Optional[List[bytes]]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "x5c" and isinstance(v, list) and v and isinstance(v[0], bytes):
                return v
            r = _find_x5c_in_cbor(v)
            if r:
                return r
    elif isinstance(obj, list):
        for x in obj:
            r = _find_x5c_in_cbor(x)
            if r:
                return r
    return None


def _load_apple_trust_anchor() -> Optional[Any]:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    path = (os.getenv("APPLE_APP_ATTEST_ROOT_PEM_PATH") or "").strip()
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, "rb") as f:
            pem = f.read()
        return x509.load_pem_x509_certificate(pem, default_backend())
    except Exception:  # noqa: BLE001
        return None


def _verify_child_signed_by_issuer(child: Any, issuer_pk: Any) -> None:
    from cryptography.hazmat.primitives.asymmetric import ec, rsa, padding

    if isinstance(issuer_pk, ec.EllipticCurvePublicKey):
        issuer_pk.verify(
            child.signature,
            child.tbs_certificate_bytes,
            ec.ECDSA(child.signature_hash_algorithm),
        )
    elif isinstance(issuer_pk, rsa.RSAPublicKey):
        issuer_pk.verify(
            child.signature,
            child.tbs_certificate_bytes,
            padding.PKCS1v15(),
            child.signature_hash_algorithm,
        )
    else:
        raise ValueError("unsupported_issuer_key_type")


def _verify_apple_x5c_chain(x5c_der: List[bytes], anchor: Any) -> tuple[bool, List[str]]:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    flags: List[str] = []
    be = default_backend()
    try:
        certs = [x509.load_der_x509_certificate(d, be) for d in x5c_der]
    except Exception:  # noqa: BLE001
        return False, ["x5c_parse_failed"]
    if not certs:
        return False, ["x5c_empty"]
    for i in range(len(certs) - 1):
        try:
            _verify_child_signed_by_issuer(certs[i], certs[i + 1].public_key())
        except Exception:  # noqa: BLE001
            return False, [f"x5c_chain_break_at_{i}"]
    try:
        _verify_child_signed_by_issuer(certs[-1], anchor.public_key())
    except Exception:  # noqa: BLE001
        flags.append("x5c_root_signature_mismatch")
        return False, flags
    return True, flags


def _verify_apple_ecdsa_assertion(
    leaf_pubkey: Any,
    auth_data: bytes,
    client_data_json_bytes: bytes,
    signature: bytes,
) -> tuple[bool, List[str]]:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import ec, utils

    msg = auth_data + hashlib.sha256(client_data_json_bytes).digest()
    if not isinstance(leaf_pubkey, ec.EllipticCurvePublicKey):
        return False, ["apple_leaf_not_ec_key"]
    try:
        leaf_pubkey.verify(signature, msg, ec.ECDSA(hashes.SHA256()))
        return True, []
    except Exception:  # noqa: BLE001
        if len(signature) == 64:
            try:
                r = int.from_bytes(signature[:32], "big")
                s = int.from_bytes(signature[32:], "big")
                der = utils.encode_dss_signature(r, s)
                leaf_pubkey.verify(der, msg, ec.ECDSA(hashes.SHA256()))
                return True, []
            except Exception as exc:  # noqa: BLE001
                return False, [f"apple_ecdsa_verify_failed:{type(exc).__name__}"]
        return False, ["apple_ecdsa_verify_failed"]


def _verify_apple_strict_attestation_and_signature(
    payload: Dict[str, Any],
    decoded_assertion: Dict[str, Any],
    *,
    auth_data: bytes,
    client_data_json_bytes: bytes,
    signature: bytes,
) -> tuple[bool, List[str]]:
    risk: List[str] = []
    ao_b64 = payload.get("attestation_object_b64")
    if not ao_b64:
        risk.append("strict_requires_attestation_object")
        return False, risk
    try:
        import cbor2

        raw = base64.b64decode(str(ao_b64), validate=True)
        ao = cbor2.loads(raw)
    except Exception:  # noqa: BLE001
        return False, risk + ["attestation_object_cbor_invalid"]
    x5c = _find_x5c_in_cbor(ao)
    if not x5c:
        return False, risk + ["attestation_x5c_missing"]
    anchor = _load_apple_trust_anchor()
    if anchor is None:
        return False, risk + ["apple_trust_anchor_not_configured"]
    ok, fl = _verify_apple_x5c_chain(x5c, anchor)
    risk.extend(fl)
    if not ok:
        return False, risk
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend

    leaf = x509.load_der_x509_certificate(x5c[0], default_backend())
    pk = leaf.public_key()
    s_ok, s_flags = _verify_apple_ecdsa_assertion(pk, auth_data, client_data_json_bytes, signature)
    risk.extend(s_flags)
    return s_ok, risk


def _verify_apple_app_attest(
    payload: Dict[str, Any],
    device_id: str,
    db: Optional[Session],
) -> AttestationResult:
    risk: List[str] = []
    assertion_b64 = payload.get("assertion") or payload.get("assertion_b64")
    key_id = payload.get("key_id") or payload.get("keyId")
    nonce = payload.get("nonce")
    if not assertion_b64:
        return AttestationResult(False, TRUST_LOW, ["missing_apple_assertion"], "apple_app_attest", {})

    n_ok, n_flags = _verify_nonce_optional(db, nonce)
    risk.extend(n_flags)
    if not n_ok:
        return AttestationResult(False, TRUST_BLOCKED, risk, "apple_app_attest", {"stage": "nonce"})

    if db is not None and artifact_replay_seen(db=db, digest=_artifact_digest(str(assertion_b64), str(nonce))):
        return AttestationResult(False, TRUST_BLOCKED, risk + ["replay_assertion"], "apple_app_attest", {})

    decoded, d_flags = _decode_apple_assertion_cbor(str(assertion_b64))
    risk.extend(d_flags)
    if decoded is None:
        return AttestationResult(False, TRUST_LOW, risk, "apple_app_attest", {})

    cd_ok, cd_flags = _apple_client_data_challenge_ok(decoded, str(nonce) if nonce else None)
    risk.extend(cd_flags)
    if not cd_ok:
        return AttestationResult(False, TRUST_BLOCKED, risk, "apple_app_attest", {"stage": "client_data_challenge"})

    auth_data = decoded.get("authenticatorData")
    if isinstance(auth_data, bytes):
        ok, f2 = _apple_authenticator_data_ok(auth_data)
        risk.extend(f2)
        if not ok:
            return AttestationResult(False, TRUST_LOW, risk, "apple_app_attest", {})

    signature = decoded.get("signature")
    cdj_raw = decoded.get("clientDataJSON")
    client_data_json_bytes = cdj_raw if isinstance(cdj_raw, bytes) else (
        str(cdj_raw).encode("utf-8") if cdj_raw is not None else b""
    )

    if is_strict_mode():
        if not isinstance(auth_data, bytes) or not isinstance(signature, bytes) or not client_data_json_bytes:
            risk.append("strict_missing_auth_fields")
            return AttestationResult(False, TRUST_BLOCKED, risk, "apple_app_attest", {"key_id": key_id})
        st_ok, st_risk = _verify_apple_strict_attestation_and_signature(
            payload,
            decoded,
            auth_data=auth_data,
            client_data_json_bytes=client_data_json_bytes,
            signature=signature,
        )
        risk.extend(st_risk)
        if not st_ok:
            return AttestationResult(False, TRUST_BLOCKED, risk, "apple_app_attest", {"key_id": key_id})

    trust = TRUST_HIGH if not risk else TRUST_MEDIUM
    return AttestationResult(True, trust, risk, "apple_app_attest", {"key_id_present": bool(key_id)})


def _verify_apple_devicecheck(payload: Dict[str, Any], device_id: str, db: Optional[Session]) -> AttestationResult:
    """Fallback léger : jeton DeviceCheck / query — validation serveur Apple requise en prod."""
    token = payload.get("device_token") or payload.get("device_check_token")
    nonce = payload.get("nonce")
    if not token:
        return AttestationResult(False, TRUST_LOW, ["missing_devicecheck_token"], "apple_devicecheck", {})
    n_ok, n_flags = _verify_nonce_optional(db, nonce)
    if not n_ok:
        return AttestationResult(False, TRUST_BLOCKED, n_flags, "apple_devicecheck", {})
    if is_strict_mode():
        return AttestationResult(
            False,
            TRUST_LOW,
            n_flags + ["devicecheck_strict_not_configured"],
            "apple_devicecheck",
            {},
        )
    return AttestationResult(True, TRUST_MEDIUM, n_flags, "apple_devicecheck", {"bound_device": device_id[:8]})


def _verify_play_integrity(
    payload: Dict[str, Any],
    device_id: str,
    db: Optional[Session],
) -> AttestationResult:
    risk: List[str] = []
    token = payload.get("integrity_token") or payload.get("token")
    nonce = payload.get("nonce")
    if not token:
        return AttestationResult(False, TRUST_LOW, ["missing_integrity_token"], "play_integrity", {})

    n_ok, n_flags = _verify_nonce_optional(db, nonce)
    risk.extend(n_flags)
    if not n_ok:
        return AttestationResult(False, TRUST_BLOCKED, risk, "play_integrity", {"stage": "nonce"})

    if db is not None and artifact_replay_seen(
        db=db, digest=_artifact_digest(str(token)[:2000], str(nonce))
    ):
        return AttestationResult(False, TRUST_BLOCKED, risk + ["replay_integrity_token"], "play_integrity", {})

    from core.env import is_dev_mode

    use_api = (os.getenv("PLAY_INTEGRITY_USE_GOOGLE_API") or "false").strip().lower() in ("1", "true", "yes")
    require_api_prod = (not is_dev_mode()) and (
        os.getenv("PLAY_INTEGRITY_REQUIRE_API_OUTSIDE_DEV", "true").strip().lower() in ("1", "true", "yes")
    )
    if require_api_prod and not use_api:
        return AttestationResult(
            False,
            TRUST_BLOCKED,
            risk + ["play_integrity_api_required_production"],
            "play_integrity",
            {"stage": "require_api_prod"},
        )

    if use_api:
        verdict = _call_play_integrity_api(str(token))
        if not verdict.get("ok"):
            return AttestationResult(
                False,
                TRUST_LOW,
                risk + ["google_api_rejected"],
                "play_integrity",
                verdict,
            )
        return AttestationResult(True, verdict.get("trust_level", TRUST_HIGH), risk, "play_integrity", verdict)

    # Mode non-API : interpréter un verdict JSON optionnel côté client (JWS non vérifié — jamais en strict seul)
    verdict = payload.get("verdict") or {}
    if isinstance(verdict, dict):
        device_ok = verdict.get("deviceIntegrity")
        basic = verdict.get("basicIntegrity")
        strong = verdict.get("strongIntegrity")
        meta = {"deviceIntegrity": device_ok, "basicIntegrity": basic, "strongIntegrity": strong}
        if strong is True or device_ok == "MEETS_STRONG_INTEGRITY":
            return AttestationResult(True, TRUST_HIGH, risk, "play_integrity", meta)
        if basic is True or device_ok in ("MEETS_BASIC_INTEGRITY", "MEETS_DEVICE_INTEGRITY"):
            return AttestationResult(True, TRUST_MEDIUM, risk, "play_integrity", meta)
        if is_strict_mode():
            return AttestationResult(False, TRUST_LOW, risk + ["play_integrity_strict_no_api"], "play_integrity", meta)
        return AttestationResult(True, TRUST_LOW, risk + ["play_integrity_lenient"], "play_integrity", meta)

    if is_strict_mode():
        return AttestationResult(False, TRUST_LOW, risk + ["play_integrity_no_verdict"], "play_integrity", {})
    return AttestationResult(True, TRUST_MEDIUM, risk + ["play_integrity_assumed_medium"], "play_integrity", {})


def _call_play_integrity_api(token: str) -> Dict[str, Any]:
    """Appel Google Play Integrity (nécessite ADC / JSON service account + package name)."""
    import httpx

    pkg = (os.getenv("ANDROID_PACKAGE_NAME") or "").strip()
    if not pkg:
        return {"ok": False, "error": "missing_ANDROID_PACKAGE_NAME"}
    try:
        from google.oauth2 import service_account  # type: ignore[import-untyped]
        from google.auth.transport.requests import Request as GARequest  # type: ignore[import-untyped]
    except ImportError:
        logger.warning("google-auth not installed; Play Integrity API skipped")
        return {"ok": False, "error": "google_auth_missing"}

    sa_path = (os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or "").strip()
    if not sa_path or not os.path.isfile(sa_path):
        return {"ok": False, "error": "missing_service_account_file"}

    try:
        creds = service_account.Credentials.from_service_account_file(
            sa_path,
            scopes=["https://www.googleapis.com/auth/playintegrity"],
        )
        creds.refresh(GARequest())  # type: ignore[misc]
        url = f"https://playintegrity.googleapis.com/v1/{pkg}:decodeIntegrityToken"
        body = {"integrity_token": token}
        r = httpx.post(
            url,
            headers={"Authorization": f"Bearer {creds.token}", "Content-Type": "application/json"},
            json=body,
            timeout=15.0,
        )
        if r.status_code != 200:
            return {"ok": False, "status": r.status_code, "body": r.text[:500]}
        data = r.json()
        token_payload = (data.get("tokenPayloadExternal") or {})
        device_integrity = (token_payload.get("deviceIntegrity") or {})
        di = device_integrity.get("deviceRecognitionVerdict") or []
        trust_level = TRUST_LOW
        if "MEETS_STRONG_INTEGRITY" in di:
            trust_level = TRUST_HIGH
        elif "MEETS_DEVICE_INTEGRITY" in di or "MEETS_BASIC_INTEGRITY" in di:
            trust_level = TRUST_MEDIUM
        return {
            "ok": True,
            "trust_level": trust_level,
            "deviceRecognitionVerdict": di,
            "tokenPayloadExternal": token_payload,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Play Integrity API error: %s", exc)
        return {"ok": False, "error": str(exc)}


def verify_device_attestation(
    platform: str,
    attestation_payload: Dict[str, Any],
    device_id: str,
    *,
    db: Optional[Session] = None,
) -> AttestationResult:
    """
    Point d’entrée : ``attestation_payload`` = corps JSON parsé depuis ``X-Device-Attestation``.
    """
    fmt = (attestation_payload.get("format") or platform or "").strip().lower()
    if fmt in ("apple_app_attest", "ios_app_attest", "app_attest"):
        return _verify_apple_app_attest(attestation_payload, device_id, db)
    if fmt in ("apple_devicecheck", "devicecheck"):
        return _verify_apple_devicecheck(attestation_payload, device_id, db)
    if fmt in ("play_integrity", "android_play_integrity", "android"):
        return _verify_play_integrity(attestation_payload, device_id, db)
    return AttestationResult(
        False,
        TRUST_LOW,
        [f"unknown_attestation_format:{fmt or '?'}"] if fmt else ["missing_format"],
        None,
        {},
    )


def finalize_successful_attestation(db: Session, parsed: Optional[Dict[str, Any]]) -> None:
    """Après authentification réussie : consomme le nonce et enregistre l’anti-rejeu."""
    if not parsed:
        return
    nonce = parsed.get("nonce")
    if nonce:
        if not consume_attestation_nonce(db=db, nonce=str(nonce)):
            logger.warning("device_attest: nonce finalize consume failed")
    fmt = (parsed.get("format") or "").lower()
    try:
        if fmt in ("apple_app_attest", "ios_app_attest", "app_attest"):
            assertion_b64 = parsed.get("assertion") or parsed.get("assertion_b64")
            if assertion_b64 and nonce:
                register_artifact_replay_guard(
                    db=db, digest=_artifact_digest(str(assertion_b64), str(nonce))
                )
        elif fmt in ("play_integrity", "android_play_integrity", "android"):
            token = parsed.get("integrity_token") or parsed.get("token")
            if token and nonce:
                register_artifact_replay_guard(
                    db=db, digest=_artifact_digest(str(token)[:2000], str(nonce))
                )
    except Exception as exc:  # noqa: BLE001
        logger.warning("device_attest finalize artifact: %s", exc)


def evaluate_header_for_auth(
    *,
    db: Session,
    request_device_id: str,
    attestation_header_raw: Optional[str],
    legacy_unknown_label: str,
) -> tuple[Optional[AttestationResult], str, bool]:
    """
    Retourne (result|None, device_trust_level, step_up_otp_required).

    Si pas d’en-tête : UNKNOWN, pas de step-up (sauf politique future).
    """
    from services.auth.refresh_session import LEGACY_UNKNOWN_DEVICE

    parsed = parse_x_device_attestation_header(attestation_header_raw)
    if parsed is None:
        if header_required_for_mobile() and request_device_id != legacy_unknown_label:
            return (
                AttestationResult(False, TRUST_LOW, ["missing_attestation_header"], None, {}),
                DEVICE_TRUST_SUSPICIOUS,
                step_up_on_fail(),
            )
        return None, DEVICE_TRUST_UNKNOWN, False

    plat = (parsed.get("platform") or parsed.get("os") or "").strip().lower()
    if not plat:
        if "format" in parsed:
            plat = str(parsed.get("format")).split("_")[0]
    res = verify_device_attestation(plat, parsed, request_device_id, db=db)
    trust = map_verdict_to_device_trust(res)
    step = (not res.is_valid) and step_up_on_fail()
    return res, trust, step


def extract_pk_sha256_from_attestation_header(parsed: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    PR D3 — hash SHA-256 hex (64 car.) de la clé publique SPKI attendu dans l’attestation.

    Cherche ``pk_sha256`` / ``public_key_sha256`` au niveau racine du JSON, puis dans
    ``clientDataJSON`` décodé (assertion App Attest).
    """
    if not parsed:
        return None

    def _norm_hex(s: str) -> Optional[str]:
        t = str(s).strip().lower()
        if len(t) == 64 and all(c in "0123456789abcdef" for c in t):
            return t
        return None

    for k in ("pk_sha256", "public_key_sha256"):
        v = parsed.get(k)
        if v:
            h = _norm_hex(str(v))
            if h:
                return h

    assertion_b64 = parsed.get("assertion") or parsed.get("assertion_b64")
    if not assertion_b64:
        return None
    decoded, _ = _decode_apple_assertion_cbor(str(assertion_b64))
    if not isinstance(decoded, dict):
        return None
    cdj = decoded.get("clientDataJSON")
    if cdj is None:
        return None
    try:
        if isinstance(cdj, bytes):
            cdo = json.loads(cdj.decode("utf-8"))
        elif isinstance(cdj, str):
            cdo = json.loads(cdj)
        else:
            return None
    except Exception:  # noqa: BLE001
        return None
    if not isinstance(cdo, dict):
        return None
    for k in ("pk_sha256", "public_key_sha256"):
        v = cdo.get(k)
        if v:
            h = _norm_hex(str(v))
            if h:
                return h
    return None
