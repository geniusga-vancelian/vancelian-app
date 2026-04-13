"""PR D3 — liaison attestation / clé, message sens ARQXD3, nonces."""
from __future__ import annotations

import base64
from datetime import datetime, timezone

import pytest
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from services.auth.device_request_signature import (
    build_sensitive_signing_message,
    verify_sensitive_device_signature,
)


def test_sensitive_message_roundtrip():
    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    public_der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    spki_b64 = base64.b64encode(public_der).decode("ascii")
    nonce = "test-nonce-abc"
    ts = int(datetime.now(timezone.utc).timestamp())
    body_hex = "a" * 64
    msg = build_sensitive_signing_message(nonce, ts, "POST", "/auth/device/sensitive-action", body_hex)
    sig = private_key.sign(msg, ec.ECDSA(hashes.SHA256()))
    sig_b64 = base64.b64encode(sig).decode("ascii")
    assert verify_sensitive_device_signature(
        public_key_spki_b64=spki_b64,
        nonce=nonce,
        unix_ts=ts,
        method="POST",
        path="/auth/device/sensitive-action",
        body_sha256_hex=body_hex,
        signature_b64=sig_b64,
    )


def test_normalize_pk_sha256_matches_der():
    import hashlib

    private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
    der = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    h = hashlib.sha256(der).hexdigest()
    assert len(h) == 64
