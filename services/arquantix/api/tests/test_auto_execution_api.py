"""Tests for the trigger orders REST API endpoints (JWT)."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from conftest import make_linked_client, mobile_auth_headers


@pytest.fixture
def mobile_headers(client: TestClient, db: Session):
    pe = make_linked_client(db, email=f"auto-exec-{uuid.uuid4().hex[:8]}@example.com")
    return mobile_auth_headers(db, pe)


class TestCreateOrder:

    def test_create_buy_limit_valid(self, client, db, mobile_headers):
        resp = client.post(
            "/api/app/orders",
            json={
                "asset": "BTC", "side": "buy", "order_type": "limit",
                "trigger_price": 65000.0, "amount": 100.0,
            },
            headers=mobile_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["side"] == "buy"
        assert data["order_type"] == "limit"
        assert data["direction"] == "down"
        assert data["price_source"] == "ask"
        assert data["status"] == "active"

    def test_create_sell_stop_valid(self, client, db, mobile_headers):
        resp = client.post(
            "/api/app/orders",
            json={
                "asset": "BTC", "side": "sell", "order_type": "stop",
                "trigger_price": 80000.0, "amount": 0.5,
            },
            headers=mobile_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["direction"] == "down"
        assert data["price_source"] == "bid"

    def test_create_with_slippage(self, client, db, mobile_headers):
        resp = client.post(
            "/api/app/orders",
            json={
                "asset": "ETH", "side": "buy", "order_type": "stop",
                "trigger_price": 4000.0, "amount": 50.0, "slippage_bps": 100,
            },
            headers=mobile_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["slippage_bps"] == 100

    def test_create_invalid_side_rejected(self, client, db, mobile_headers):
        resp = client.post(
            "/api/app/orders",
            json={
                "asset": "BTC", "side": "short", "order_type": "limit",
                "trigger_price": 65000.0, "amount": 100.0,
            },
            headers=mobile_headers,
        )
        assert resp.status_code == 422

    def test_create_invalid_order_type_rejected(self, client, db, mobile_headers):
        resp = client.post(
            "/api/app/orders",
            json={
                "asset": "BTC", "side": "buy", "order_type": "market",
                "trigger_price": 65000.0, "amount": 100.0,
            },
            headers=mobile_headers,
        )
        assert resp.status_code == 422

    def test_create_zero_amount_rejected(self, client, db, mobile_headers):
        resp = client.post(
            "/api/app/orders",
            json={
                "asset": "BTC", "side": "buy", "order_type": "limit",
                "trigger_price": 65000.0, "amount": 0,
            },
            headers=mobile_headers,
        )
        assert resp.status_code == 422


class TestListOrders:

    def test_list_returns_200(self, client, db, mobile_headers):
        resp = client.get("/api/app/orders", headers=mobile_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_filters_by_asset(self, client, db, mobile_headers):
        baseline_btc = len(client.get("/api/app/orders?asset=BTC", headers=mobile_headers).json())
        baseline_eth = len(client.get("/api/app/orders?asset=ETH", headers=mobile_headers).json())
        client.post(
            "/api/app/orders",
            json={
                "asset": "BTC", "side": "buy", "order_type": "limit",
                "trigger_price": 65000.0, "amount": 100.0,
            },
            headers=mobile_headers,
        )
        client.post(
            "/api/app/orders",
            json={
                "asset": "ETH", "side": "sell", "order_type": "stop",
                "trigger_price": 3000.0, "amount": 1.0,
            },
            headers=mobile_headers,
        )
        resp_btc = client.get("/api/app/orders?asset=BTC", headers=mobile_headers)
        resp_eth = client.get("/api/app/orders?asset=ETH", headers=mobile_headers)
        assert resp_btc.status_code == 200
        assert resp_eth.status_code == 200
        assert len(resp_btc.json()) == baseline_btc + 1
        assert len(resp_eth.json()) == baseline_eth + 1
        assert all(o["asset"] == "BTC" for o in resp_btc.json())
        assert all(o["asset"] == "ETH" for o in resp_eth.json())


class TestDeleteOrder:

    def test_cancel_active_order(self, client, db, mobile_headers):
        create = client.post(
            "/api/app/orders",
            json={
                "asset": "BTC", "side": "buy", "order_type": "limit",
                "trigger_price": 65000.0, "amount": 100.0,
            },
            headers=mobile_headers,
        )
        order_id = create.json()["id"]
        resp = client.delete(f"/api/app/orders/{order_id}", headers=mobile_headers)
        assert resp.status_code == 204

    def test_delete_nonexistent_returns_404(self, client, db, mobile_headers):
        resp = client.delete(
            "/api/app/orders/00000000-0000-0000-0000-000000000000",
            headers=mobile_headers,
        )
        assert resp.status_code == 404
