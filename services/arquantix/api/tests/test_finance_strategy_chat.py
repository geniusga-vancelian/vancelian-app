import pytest
from fastapi.testclient import TestClient

from main import app
from services.finance_strategy_chat.store import InMemoryTTLStore
from services.finance_strategy_chat import store as store_module


client = TestClient(app)


def test_start_returns_session_and_first_step(monkeypatch):
    store_module.STORE = InMemoryTTLStore()

    response = client.post("/api/finance/strategy-chat/start", json={"locale": "fr"})
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert data["progress"]["phase"] >= 0
    assert data["ui"]["type"] in ("quick_replies", "free_text")
    assert data["messages"]
    assert "profile" in data["state"]


def test_step_routes_target_amount_and_ack(monkeypatch):
    store_module.STORE = InMemoryTTLStore()

    start = client.post("/api/finance/strategy-chat/start", json={})
    session_id = start.json()["session_id"]

    step1 = client.post(
        "/api/finance/strategy-chat/step",
        json={"session_id": session_id, "user_input": {"type": "free_text", "value": "Voyage"}},
    )
    assert step1.status_code == 200

    step2 = client.post(
        "/api/finance/strategy-chat/step",
        json={"session_id": session_id, "user_input": {"type": "free_text", "value": "4500 euro"}},
    )
    assert step2.status_code == 200
    data = step2.json()
    profile = data["state"]["profile"]
    assert profile.get("target_amount") == 4500.0
    messages = [m["content"] for m in data["messages"]]
    assert any("objectif" in m.lower() for m in messages)


def test_state_returns_profile(monkeypatch):
    store_module.STORE = InMemoryTTLStore()

    start = client.post("/api/finance/strategy-chat/start", json={})
    session_id = start.json()["session_id"]

    state = client.get(f"/api/finance/strategy-chat/state?session_id={session_id}")
    assert state.status_code == 200
    data = state.json()
    assert data["state"].get("profile") is not None


def test_ttl_store_expires_sessions(monkeypatch):
    store = InMemoryTTLStore()
    now = [1000.0]

    def fake_time():
        return now[0]

    monkeypatch.setattr(store_module.time, "time", fake_time)

    store.set("sess-1", {"phase": 1}, ttl_seconds=10)
    assert store.get("sess-1") == {"phase": 1}

    now[0] = 1009.0
    assert store.get("sess-1") == {"phase": 1}

    now[0] = 1011.0
    assert store.get("sess-1") is None
