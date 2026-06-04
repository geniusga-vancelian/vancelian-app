"""Tests quote freshness LI.FI portal (compare + confirm-execute)."""
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
from services.lifi.routes import _confirm_svc, _quote_svc
from services.lifi.swap_quote_freshness import compare_receive_against_review
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
PRIVY_USER = "did:privy:testfreshness001"


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
        external_email="freshness@test.local",
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


def _mock_lifi_quote(*, to_amount: str = "450000000000000000"):
    return {
        "id": "quote-test-1",
        "tool": "stargateV2",
        "action": {"fromChainId": 8453, "toChainId": 8453},
        "estimate": {
            "toAmount": to_amount,
            "toAmountMin": to_amount,
            "executionDuration": 120,
            "feeCosts": [],
        },
        "transactionRequest": {
            "to": "0x1234567890123456789012345678901234567890",
            "data": "0xdeadbeef",
            "value": "0",
            "chainId": 8453,
        },
    }


class TestCompareReceiveAgainstReview:
    def test_acceptable_within_slippage(self):
        r = compare_receive_against_review(
            review_estimated_receive="1.0",
            fresh_estimated_receive="0.996",
            slippage_bps=50,
        )
        assert r.acceptable is True
        assert r.delta_bps == 40

    def test_rejected_beyond_slippage(self):
        r = compare_receive_against_review(
            review_estimated_receive="1.0",
            fresh_estimated_receive="0.99",
            slippage_bps=50,
        )
        assert r.acceptable is False
        assert r.delta_bps == 100

    def test_fresh_higher_is_ok(self):
        r = compare_receive_against_review(
            review_estimated_receive="1.0",
            fresh_estimated_receive="1.05",
            slippage_bps=50,
        )
        assert r.acceptable is True
        assert r.delta_bps == 0


def test_confirm_execute_refreshes_and_prepares(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)

    mock_client = MagicMock(spec=LifiClient)
    mock_client.get_quote.return_value = _mock_lifi_quote()
    _quote_svc._lifi = mock_client
    _confirm_svc._quote._lifi = mock_client
    monkeypatch.setenv("LIFI_API_KEY", "test-key")

    quote_res = client.post(
        "/api/swaps/quote",
        headers=_auth_headers(db, pe),
        json={
            "from_asset": "USDC",
            "to_asset": "ETH",
            "amount": "1000",
            "from_chain": "base",
            "to_chain": "base",
        },
    )
    assert quote_res.status_code == 200, quote_res.text
    body = quote_res.json()
    swap_id = body["swap_id"]
    review_receive = body["estimated_receive"]

    mock_client.get_quote.return_value = _mock_lifi_quote(to_amount="450000000000000000")
    confirm_res = client.post(
        "/api/swaps/confirm-execute",
        headers=_auth_headers(db, pe),
        json={
            "swap_id": swap_id,
            "review_estimated_receive": review_receive,
            "review_amount_in": body["amount_in"],
        },
    )
    assert confirm_res.status_code == 200, confirm_res.text
    payload = confirm_res.json()
    assert payload["execute"]["status"] == "AWAITING_SIGNATURE"
    assert payload["quote"]["swap_id"] == swap_id
    assert mock_client.get_quote.call_count >= 2


def test_confirm_execute_price_changed_409(client: TestClient, db: Session, monkeypatch):
    pe = make_linked_client(db)
    _seed_wallet(db, pe)

    mock_client = MagicMock(spec=LifiClient)
    mock_client.get_quote.return_value = _mock_lifi_quote(to_amount="450000000000000000")
    _quote_svc._lifi = mock_client
    _confirm_svc._quote._lifi = mock_client
    monkeypatch.setenv("LIFI_API_KEY", "test-key")

    quote_res = client.post(
        "/api/swaps/quote",
        headers=_auth_headers(db, pe),
        json={
            "from_asset": "USDC",
            "to_asset": "ETH",
            "amount": "1000",
            "from_chain": "base",
            "to_chain": "base",
        },
    )
    body = quote_res.json()
    swap_id = body["swap_id"]

    mock_client.get_quote.return_value = _mock_lifi_quote(to_amount="400000000000000000")
    confirm_res = client.post(
        "/api/swaps/confirm-execute",
        headers=_auth_headers(db, pe),
        json={
            "swap_id": swap_id,
            "review_estimated_receive": body["estimated_receive"],
        },
    )
    assert confirm_res.status_code == 409, confirm_res.text
    detail = confirm_res.json()["detail"]
    assert detail["code"] == "swap.price_changed"
    assert detail["quote"]["swap_id"] == swap_id
    assert Decimal(detail["quote"]["estimated_receive"]) < Decimal(body["estimated_receive"])
