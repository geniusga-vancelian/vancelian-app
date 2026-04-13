"""PR D2 — signature refresh ECDSA P-256 + politique device_security."""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from services.auth.device_request_signature import (
    build_refresh_signing_message,
    normalize_public_key_b64_to_spki_der,
    verify_refresh_device_signature,
)
from services.auth.device_security_pr_d2 import (
    attestation_session_max_age_sec,
    check_attestation_freshness_or_raise,
    device_security_level,
)


def test_build_message_and_verify_roundtrip():
    from cryptography.hazmat.backends import default_backend

    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    spki_b64 = base64.b64encode(public_der).decode("ascii")
    rt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.signature"
    ts = int(datetime.now(timezone.utc).timestamp())
    msg = build_refresh_signing_message(ts, rt)
    sig = private_key.sign(msg, ec.ECDSA(hashes.SHA256()))
    sig_b64 = base64.b64encode(sig).decode("ascii")
    assert verify_refresh_device_signature(
        public_key_spki_b64=spki_b64,
        refresh_token=rt,
        signature_b64=sig_b64,
        timestamp_raw=str(ts),
    )


def test_normalize_sec1_uncompressed_to_spki():
    from cryptography.hazmat.backends import default_backend

    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    pub = private_key.public_key()
    nums = pub.public_numbers()
    x = nums.x.to_bytes(32, "big")
    y = nums.y.to_bytes(32, "big")
    sec1 = b"\x04" + x + y
    b64 = base64.b64encode(sec1).decode("ascii")
    der = normalize_public_key_b64_to_spki_der(b64)
    assert der is not None and der[0] == 0x30


def test_attestation_freshness_raises_when_stale(monkeypatch):
    from fastapi import HTTPException

    monkeypatch.setenv("ATTESTATION_SESSION_MAX_AGE_SEC", "300")
    assert attestation_session_max_age_sec() == 300
    s = type(
        "S",
        (),
        {
            "attestation_verified_at": datetime.now(timezone.utc) - timedelta(seconds=400),
        },
    )()
    with pytest.raises(HTTPException) as ei:
        check_attestation_freshness_or_raise(session=s)
    assert ei.value.status_code == 403


def test_device_security_level_default_zero(monkeypatch):
    monkeypatch.delenv("DEVICE_SECURITY_LEVEL", raising=False)
    assert device_security_level() == 0
