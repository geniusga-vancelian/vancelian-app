"""PR D2 — vérification ECDSA P-256 (SHA-256) des en-têtes ``X-Device-Signature`` sur refresh.

Message canonique (UTF-8) ::
    ARQXD2|v1|{unix_ts}|{sha256_hex(refresh_token)}

En-têtes attendus :
    X-Device-Signature: base64 standard (signature DER ECDSA)
    X-Device-Signature-Timestamp: secondes Unix (même fenêtre que le message)
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

logger = logging.getLogger("arquantix.auth.device_signature")

SIGNATURE_PREFIX = "ARQXD2|v1"
SIGNATURE_SENSITIVE_PREFIX = "ARQXD3|v1"
# Tolérance horloge (secondes)
DEFAULT_CLOCK_SKEW_SEC = 120


def _sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def build_refresh_signing_message(unix_ts: int, refresh_token: str) -> bytes:
    inner = f"{SIGNATURE_PREFIX}|{unix_ts}|{_sha256_hex(refresh_token)}"
    return inner.encode("utf-8")


def build_sensitive_signing_message(
    nonce: str,
    unix_ts: int,
    method: str,
    path: str,
    body_sha256_hex: str,
) -> bytes:
    """PR D3 — corps signé pour routes sensibles (nonce + horodatage + méthode + chemin + hash corps)."""
    inner = (
        f"{SIGNATURE_SENSITIVE_PREFIX}|{nonce}|{unix_ts}|{method.upper()}|{path}|{body_sha256_hex.lower()}"
    )
    return inner.encode("utf-8")


def verify_sensitive_device_signature(
    *,
    public_key_spki_b64: str,
    nonce: str,
    unix_ts: int,
    method: str,
    path: str,
    body_sha256_hex: str,
    signature_b64: Optional[str],
) -> bool:
    if not signature_b64 or not str(signature_b64).strip():
        return False
    try:
        ts = int(str(unix_ts).strip())
    except (TypeError, ValueError):
        return False
    now = int(datetime.now(timezone.utc).timestamp())
    from services.auth.device_pr_d4_policy import sensitive_signature_clock_skew_sec

    skew = sensitive_signature_clock_skew_sec()
    if abs(now - ts) > skew:
        return False
    try:
        der = base64.b64decode(public_key_spki_b64.strip(), validate=True)
    except Exception:
        return False
    msg = build_sensitive_signing_message(
        str(nonce).strip(),
        ts,
        method,
        path,
        body_sha256_hex,
    )
    return verify_p256_signature(public_key_spki_der=der, message=msg, signature_b64=signature_b64)


def verify_p256_signature(
    *,
    public_key_spki_der: bytes,
    message: bytes,
    signature_b64: str,
) -> bool:
    try:
        raw_sig = base64.b64decode(signature_b64.strip(), validate=True)
    except Exception:
        return False
    try:
        pub = serialization.load_der_public_key(public_key_spki_der)
    except Exception:
        return False
    if not isinstance(pub, ec.EllipticCurvePublicKey):
        return False

    def _try_verify(sig_bytes: bytes) -> bool:
        try:
            pub.verify(sig_bytes, message, ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False

    if _try_verify(raw_sig):
        return True
    if len(raw_sig) == 64:
        try:
            r = int.from_bytes(raw_sig[:32], "big")
            s = int.from_bytes(raw_sig[32:], "big")
            sig_der = utils.encode_dss_signature(r, s)
            return _try_verify(sig_der)
        except Exception:
            return False
    return False


def verify_refresh_device_signature(
    *,
    public_key_spki_b64: str,
    refresh_token: str,
    signature_b64: Optional[str],
    timestamp_raw: Optional[str],
) -> bool:
    if not signature_b64 or not str(signature_b64).strip():
        return False
    if not timestamp_raw or not str(timestamp_raw).strip():
        return False
    try:
        ts = int(str(timestamp_raw).strip())
    except ValueError:
        return False
    now = int(datetime.now(timezone.utc).timestamp())
    skew = int(os.getenv("DEVICE_SIGNATURE_CLOCK_SKEW_SEC", str(DEFAULT_CLOCK_SKEW_SEC)))
    if abs(now - ts) > skew:
        logger.info("device_signature clock skew reject ts=%s now=%s", ts, now)
        return False
    try:
        der = base64.b64decode(public_key_spki_b64.strip(), validate=True)
    except Exception:
        return False
    msg = build_refresh_signing_message(ts, refresh_token)
    return verify_p256_signature(public_key_spki_der=der, message=msg, signature_b64=signature_b64)


def decode_spki_b64_to_der(b64: str) -> Optional[bytes]:
    try:
        return base64.b64decode(b64.strip(), validate=True)
    except Exception:
        return None


def normalize_public_key_b64_to_spki_der(b64: str) -> Optional[bytes]:
    """Accepte SPKI DER base64 ou point SEC1 non compressé 65 octets (0x04||x||y)."""
    try:
        raw = base64.b64decode(b64.strip(), validate=True)
    except Exception:
        return None
    if not raw:
        return None
    if raw[0] == 0x30:
        try:
            serialization.load_der_public_key(raw)
            return raw
        except Exception:
            return None
    if len(raw) == 65 and raw[0] == 0x04:
        from cryptography.hazmat.backends import default_backend

        nums = ec.EllipticCurvePublicNumbers(
            int.from_bytes(raw[1:33], "big"),
            int.from_bytes(raw[33:65], "big"),
            ec.SECP256R1(),
        )
        pub = nums.public_key(default_backend())
        return pub.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    return None
