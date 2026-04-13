"""PR D4 — skew serré, binding JWT, scope nonce par route, risque minimal."""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

from auth import create_access_token
from services.auth.device_pr_d4_policy import (
    compute_device_binding_hash,
    device_binding_hashes_equal,
    enforce_jwt_device_binding_if_configured,
    sensitive_signature_clock_skew_sec,
)
from services.auth.device_signature_normalization import (
    normalize_signature_path,
    resolve_body_sha256_for_sensitive_signature,
)
from services.auth.device_request_signature import verify_sensitive_device_signature
from services.auth.jwt_user_claims import build_user_jwt_access_base_claims


def test_sensitive_skew_tighter_when_level_3(monkeypatch):
    monkeypatch.setenv("DEVICE_SECURITY_LEVEL", "3")
    assert sensitive_signature_clock_skew_sec() == 30


def test_sensitive_skew_wide_when_level_2(monkeypatch):
    monkeypatch.setenv("DEVICE_SECURITY_LEVEL", "2")
    monkeypatch.delenv("DEVICE_SIGNATURE_SENSITIVE_CLOCK_SKEW_SEC", raising=False)
    monkeypatch.setenv("DEVICE_SIGNATURE_CLOCK_SKEW_SEC", "120")
    assert sensitive_signature_clock_skew_sec() == 120


def test_device_binding_hash_stable():
    a = compute_device_binding_hash("device-abc")
    b = compute_device_binding_hash("device-abc")
    assert len(a) == 32
    assert a == b
    assert a != compute_device_binding_hash("device-abz")


def test_device_binding_legacy_prefix_matches():
    full = compute_device_binding_hash("same-device")
    assert device_binding_hashes_equal(full[:16], full)
    assert device_binding_hashes_equal(full, full)


def test_normalize_signature_path_slash():
    assert normalize_signature_path("/foo/bar/") == "/foo/bar"
    assert normalize_signature_path("/") == "/"
    assert normalize_signature_path("/a//b") == "/a/b"


def test_body_hash_accepts_raw_or_canonical_json():
    import hashlib
    import json

    raw = b'{"b":2,"a":1}'
    raw_h = hashlib.sha256(raw).hexdigest()
    obj = json.loads(raw.decode("utf-8"))
    canon = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    canon_h = hashlib.sha256(canon).hexdigest()
    assert (
        resolve_body_sha256_for_sensitive_signature(
            raw_body=raw,
            content_type="application/json",
            header_sha256_hex=raw_h,
        )
        == raw_h
    )
    assert (
        resolve_body_sha256_for_sensitive_signature(
            raw_body=raw,
            content_type="application/json",
            header_sha256_hex=canon_h,
        )
        == canon_h
    )


def test_enforce_jwt_binding_rejects_mismatch(monkeypatch, db):
    from database import AdminUser

    monkeypatch.setenv("DEVICE_SECURITY_LEVEL", "3")
    u = db.query(AdminUser).first()
    assert u is not None
    claims = build_user_jwt_access_base_claims(u)
    tok = create_access_token(
        {**claims},
        device_binding_hash=compute_device_binding_hash("good-device"),
    )
    with pytest.raises(HTTPException) as ei:
        enforce_jwt_device_binding_if_configured(token=tok, x_device_id="wrong-device")
    assert ei.value.status_code == 403
    assert ei.value.detail["code"] == "device_jwt_binding_mismatch"


def test_enforce_jwt_binding_accepts_matching_header(monkeypatch, db):
    from database import AdminUser

    monkeypatch.setenv("DEVICE_SECURITY_LEVEL", "3")
    u = db.query(AdminUser).first()
    assert u is not None
    claims = build_user_jwt_access_base_claims(u)
    did = "my-physical-device"
    tok = create_access_token({**claims}, device_binding_hash=compute_device_binding_hash(did))
    enforce_jwt_device_binding_if_configured(token=tok, x_device_id=did)


def test_verify_sensitive_rejects_stale_ts_under_pr_d4(monkeypatch):
    monkeypatch.setenv("DEVICE_SECURITY_LEVEL", "3")
    priv = ec.generate_private_key(ec.SECP256R1(), default_backend())
    der = priv.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    spki_b64 = base64.b64encode(der).decode("ascii")
    old_ts = int((datetime.now(timezone.utc) - timedelta(seconds=90)).timestamp())
    from services.auth.device_request_signature import build_sensitive_signing_message

    msg = build_sensitive_signing_message("n", old_ts, "POST", "/x", "a" * 64)
    sig_b64 = base64.b64encode(priv.sign(msg, ec.ECDSA(hashes.SHA256()))).decode("ascii")
    assert not verify_sensitive_device_signature(
        public_key_spki_b64=spki_b64,
        nonce="n",
        unix_ts=old_ts,
        method="POST",
        path="/x",
        body_sha256_hex="a" * 64,
        signature_b64=sig_b64,
    )
