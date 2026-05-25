"""Tests routes swap LI.FI (quote/execute) avec client mocké."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from auth import create_access_token
from services.auth.jwt_user_claims import build_user_jwt_access_base_claims
from services.auth.person_identity_bridge import PROVIDER_PRIVY, link_external_identity_to_person, upsert_person_crypto_wallet
from services.lifi.lifi_client import LifiClient
from services.lifi.routes import _quote_svc
from tests.conftest import ensure_admin_for_linked_client, make_linked_client


def _migration_159_applied() -> bool:
    try:
        from sqlalchemy import inspect

        from database import engine

        return inspect(engine).has_table("person_wallet_swaps")
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _migration_159_applied(),
    reason="Appliquer `alembic upgrade head` (159) pour les tests swap LI.FI.",
)


EVM_ADDR = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
EXTERNAL_ADDR = "0x1234567890123456789012345678901234567890"
PRIVY_USER = "did:privy:testswaplifi001"


def _auth_headers(db: Session, client_id):
    user = ensure_admin_for_linked_client(db, client_id)
    token = create_access_token(build_user_jwt_access_base_claims(user))
    return {"Authorization": f"Bearer {token}"}


def _seed_wallet(db: Session, pe):
    link_external_identity_to_person(
        db,
        person_id=pe.person_id,
        provider=PROVIDER_PRIVY,
        external_subject=PRIVY_USER,
        external_email="swap-lifi@test.local",
    )
    upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider=PROVIDER_PRIVY,
        wallet_type="embedded",
        chain_type="ethereum",
        address=EVM_ADDR,
        metadata_json={"privy_wallet_id": "w1"},
    )
    db.commit()


def _seed_external_wallet(db: Session, pe, address: str = EXTERNAL_ADDR):
    upsert_person_crypto_wallet(
        db,
        person_id=pe.person_id,
        pe_client_id=pe.id,
        provider="external",
        wallet_type="external",
        chain_type="evm",
        address=address,
        metadata_json={"is_verified": True, "wallet_provider": "metamask"},
    )
    db.commit()


def _mock_lifi_quote():
    return {
        "id": "quote-test-1",
        "tool": "stargateV2",
        "action": {"fromChainId": 1, "toChainId": 1},
        "estimate": {
            "toAmount": "450000000000000000",
            "toAmountMin": "445000000000000000",
            "executionDuration": 120,
            "feeCosts": [],
        },
        "transactionRequest": {
            "to": "0x1234567890123456789012345678901234567890",
            "data": "0xdeadbeef",
            "value": "0",
            "chainId": 1,
        },
    }


def test_supported_assets_public(client: TestClient):
    res = client.get("/api/swaps/supported-assets")
    assert res.status_code == 200
    body = res.json()
    assert body["swap_fee_bps"] == 0
    symbols = {a["symbol"] for a in body["assets"]}
    assert symbols == {"USDC", "USDT", "ETH"}
    assert {a["symbol"] for a in body["destination_assets"]} == {"USDC", "USDT", "ETH"}


def test_quote_requires_auth(client: TestClient):
    res = client.post(
        "/api/swaps/quote",
        json={
            "from_asset": "USDC",
            "to_asset": "ETH",
            "amount": "100",
            "from_chain": "base",
            "to_chain": "ethereum",
        },
    )
    assert res.status_code == 401


def test_quote_success(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)

    mock_client = MagicMock(spec=LifiClient)
    mock_client.get_quote.return_value = _mock_lifi_quote()
    _quote_svc._lifi = mock_client
    monkeypatch.setenv("LIFI_API_KEY", "test-key")

    res = client.post(
        "/api/swaps/quote",
        headers=_auth_headers(db, pe),
        json={
            "from_asset": "USDC",
            "to_asset": "ETH",
            "amount": "1000",
            "from_chain": "base",
            "to_chain": "ethereum",
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["from_asset"] == "USDC"
    assert body["to_asset"] == "ETH"
    assert Decimal(body["estimated_receive"]) > 0
    assert body["route_steps"]


def test_quote_external_wallet_uses_metamask_address(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)
    _seed_external_wallet(db, pe)

    mock_client = MagicMock(spec=LifiClient)
    mock_client.get_quote.return_value = _mock_lifi_quote()
    _quote_svc._lifi = mock_client
    monkeypatch.setenv("LIFI_API_KEY", "test-key")

    res = client.post(
        "/api/swaps/quote",
        headers=_auth_headers(db, pe),
        json={
            "from_asset": "USDT",
            "to_asset": "ETH",
            "amount": "100",
            "from_chain": "ethereum",
            "to_chain": "ethereum",
            "signing_wallet_mode": "external_evm",
            "signing_wallet_address": EXTERNAL_ADDR,
        },
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["signing_wallet_mode"] == "external_evm"
    assert body["signing_wallet_address"].lower() == EXTERNAL_ADDR.lower()

    mock_client.get_quote.assert_called_once()
    call_kwargs = mock_client.get_quote.call_args.kwargs
    assert call_kwargs["from_address"].lower() == EXTERNAL_ADDR.lower()
    assert call_kwargs["to_address"].lower() == EXTERNAL_ADDR.lower()


def test_execute_after_quote(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)

    mock_client = MagicMock(spec=LifiClient)
    mock_client.get_quote.return_value = _mock_lifi_quote()
    _quote_svc._lifi = mock_client
    monkeypatch.setenv("LIFI_API_KEY", "test-key")

    quote_res = client.post(
        "/api/swaps/quote",
        headers=_auth_headers(db, pe),
        json={
            "from_asset": "USDC",
            "to_asset": "ETH",
            "amount": "1000",
            "from_chain": "base",
            "to_chain": "ethereum",
        },
    )
    swap_id = quote_res.json()["swap_id"]

    exec_res = client.post(
        "/api/swaps/execute",
        headers=_auth_headers(db, pe),
        json={"swap_id": swap_id},
    )
    assert exec_res.status_code == 200, exec_res.text
    body = exec_res.json()
    assert body["status"] == "AWAITING_SIGNATURE"
    assert body["transaction"]["to"].startswith("0x")
