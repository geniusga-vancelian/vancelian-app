"""Tests unitaires — signature serveur déléguée Privy (P-256) et parité du payload RPC."""
from __future__ import annotations

import base64
import json

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from services.privy_wallet.delegated_signer import (
    build_authorization_signature_input,
    build_eth_send_transaction_rpc_body,
    build_wallet_rpc_url,
    canonicalize_payload,
    generate_authorization_signature,
    privy_delegated_signing_configured,
)
from services.privy_wallet.privy_api_client import PrivyApiError


def _generate_authorization_key_b64() -> tuple[str, ec.EllipticCurvePublicKey]:
    private_key = ec.generate_private_key(ec.SECP256R1())
    der = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return base64.b64encode(der).decode("ascii"), private_key.public_key()


def test_rpc_body_mirrors_browser_format():
    body = build_eth_send_transaction_rpc_body(
        chain_id=8453,
        to="0xAbCdEf0000000000000000000000000000000001",
        data="0xDEADBEEF",
        value=None,
        gas_limit=21000,
    )
    assert body["method"] == "eth_sendTransaction"
    assert body["caip2"] == "eip155:8453"
    assert body["chain_type"] == "ethereum"
    assert body["sponsor"] is True
    tx = body["params"]["transaction"]
    assert tx["to"] == "0xabcdef0000000000000000000000000000000001"  # lowercased
    assert tx["data"] == "0xdeadbeef"
    assert tx["value"] == "0x0"
    assert tx["gas_limit"] == "0x5208"  # 21000 en hex


def test_rpc_body_omits_gas_limit_when_absent():
    body = build_eth_send_transaction_rpc_body(
        chain_id=8453, to="0x" + "11" * 20, data="0x", value="1000"
    )
    assert "gas_limit" not in body["params"]["transaction"]
    assert body["params"]["transaction"]["value"] == "0x3e8"  # 1000 décimal -> hex


def test_canonicalization_is_sorted_and_compact():
    payload = {"b": 2, "a": {"y": 1, "x": 2}}
    assert canonicalize_payload(payload) == b'{"a":{"x":2,"y":1},"b":2}'


def test_authorization_signature_input_shape():
    rpc_url = build_wallet_rpc_url("wallet-123")
    body = build_eth_send_transaction_rpc_body(chain_id=8453, to="0x" + "0" * 40, data="0x")
    sig_input = build_authorization_signature_input(app_id="app-xyz", rpc_url=rpc_url, rpc_body=body)
    assert sig_input["version"] == 1
    assert sig_input["method"] == "POST"
    assert sig_input["url"].endswith("/v1/wallets/wallet-123/rpc")
    assert sig_input["headers"] == {"privy-app-id": "app-xyz"}
    assert sig_input["body"] == body


def test_signature_verifies_with_public_key(monkeypatch):
    key_b64, public_key = _generate_authorization_key_b64()
    monkeypatch.setenv("PRIVY_AUTHORIZATION_KEY", key_b64)

    sig_input = {"version": 1, "method": "POST", "url": "u", "body": {"z": 1}, "headers": {}}
    signature_b64 = generate_authorization_signature(sig_input)

    serialized = canonicalize_payload(sig_input)
    # Ne lève pas si la signature est valide.
    public_key.verify(base64.b64decode(signature_b64), serialized, ec.ECDSA(hashes.SHA256()))


def test_signature_accepts_wallet_auth_prefix(monkeypatch):
    key_b64, public_key = _generate_authorization_key_b64()
    monkeypatch.setenv("PRIVY_AUTHORIZATION_KEY", f"wallet-auth:{key_b64}")

    sig_input = {"version": 1, "method": "POST", "url": "u", "body": {}, "headers": {}}
    signature_b64 = generate_authorization_signature(sig_input)
    public_key.verify(
        base64.b64decode(signature_b64), canonicalize_payload(sig_input), ec.ECDSA(hashes.SHA256())
    )


def test_invalid_authorization_key_raises(monkeypatch):
    monkeypatch.setenv("PRIVY_AUTHORIZATION_KEY", "not-a-real-key")
    with pytest.raises(PrivyApiError) as exc:
        generate_authorization_signature({"version": 1})
    assert exc.value.code == "privy.authorization_key_invalid"


def test_configured_flag_requires_all_env(monkeypatch):
    monkeypatch.setenv("PRIVY_APP_ID", "app")
    monkeypatch.setenv("PRIVY_APP_SECRET", "secret")
    monkeypatch.delenv("PRIVY_AUTHORIZATION_KEY", raising=False)
    assert privy_delegated_signing_configured() is False

    monkeypatch.setenv("PRIVY_AUTHORIZATION_KEY", "wallet-auth:abc")
    assert privy_delegated_signing_configured() is True

    monkeypatch.delenv("PRIVY_APP_SECRET", raising=False)
    assert privy_delegated_signing_configured() is False


def test_build_wallet_rpc_url_rejects_empty():
    with pytest.raises(PrivyApiError) as exc:
        build_wallet_rpc_url("  ")
    assert exc.value.code == "privy.wallet_id_required"
