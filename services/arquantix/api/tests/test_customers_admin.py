"""Tests Customer 360 admin API."""
import uuid

import pytest
from fastapi.testclient import TestClient

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-admin@example.com",
    "X-Actor-Roles": "admin",
}

CLIENT_HEADERS = {
    "X-Actor-Type": "client",
    "X-Actor-Id": "c1",
    "X-Actor-Roles": "client",
}


def test_customers_list_forbidden_for_client(client: TestClient):
    res = client.get("/api/admin/customers", headers=CLIENT_HEADERS)
    assert res.status_code == 403


def test_customers_list_ok_for_admin(client: TestClient):
    res = client.get("/api/admin/customers?page=1&page_size=5", headers=ADMIN_HEADERS)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert isinstance(data["items"], list)


def test_customers_detail_not_found(client: TestClient):
    rid = uuid.uuid4()
    res = client.get(f"/api/admin/customers/{rid}", headers=ADMIN_HEADERS)
    assert res.status_code == 404


def test_customers_sort_invalid(client: TestClient):
    res = client.get("/api/admin/customers?sort=invalid", headers=ADMIN_HEADERS)
    assert res.status_code == 400


def test_customers_search_ok(client: TestClient):
    res = client.get("/api/admin/customers/search?q=te&limit=5", headers=ADMIN_HEADERS)
    assert res.status_code == 200, res.text
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)


def test_customers_search_short_query_empty(client: TestClient):
    res = client.get("/api/admin/customers/search?q=a", headers=ADMIN_HEADERS)
    assert res.status_code == 200
    assert res.json()["items"] == []
