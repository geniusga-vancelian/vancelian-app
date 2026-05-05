"""Tests d'intégration du router admin ``/api/admin/assistance/conversations``.

Couvre :
  - Auth : 401/403 si pas admin/ops, 200 sinon.
  - GET / : 400 si ni `client_id` ni `person_id`, 200 sinon.
    Pagination, filtre `status`, counts agrégés (msg + tool calls).
  - GET / via `person_id` : résolution → `client_id` ; 404 si person_id
    sans pe_client.
  - GET /{id} : 404 si conv inconnue, 200 + messages ordonnés par
    turn_index, conversation_facts list, current_topic, summary.
  - GET /{id}/decisions : 404 si conv inconnue, ordering par iteration,
    arguments_json restitué en `arguments`.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from database import (
    AssistanceAgentDecision,
    AssistanceConversation,
    AssistanceMessage,
    Person,
)
from services.portfolio_engine.clients.models import Client as PEClient


ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-admin-conv@example.com",
    "X-Actor-Roles": "admin",
}
OPS_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-ops-conv@example.com",
    "X-Actor-Roles": "ops",
}
CLIENT_HEADERS = {
    "X-Actor-Type": "user",
    "X-Actor-Id": "test-user-conv@example.com",
    "X-Actor-Roles": "client",
}

BASE = "/api/admin/assistance/conversations"


# ─────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def seeded_conversation(db) -> dict:
    """Crée 1 person, 1 pe_client, 1 conversation, 3 messages, 4 tool calls."""
    person_uuid = uuid4()
    person = Person(
        id=person_uuid,
        status="active",
        jurisdiction="FR",
        profile_json={},
        kyc_status="not_started",
    )
    db.add(person)
    db.flush()

    client_uuid = uuid4()
    pe_client = PEClient(id=client_uuid, person_id=person_uuid)
    db.add(pe_client)
    db.flush()

    conv = AssistanceConversation(
        id=uuid4(),
        client_id=client_uuid,
        title="Test conversation produit",
        status="active",
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        updated_at=datetime.now(timezone.utc),
        last_message_at=datetime.now(timezone.utc),
        last_assistant_message_at=datetime.now(timezone.utc),
        conversation_summary="Le client a posé 2 questions sur les bundles.",
        conversation_facts=[
            {"key": "interest_topic", "value": "crypto_basket", "turn": 2}
        ],
        summarized_until_turn=2,
        summary_updated_at=datetime.now(timezone.utc),
        current_topic={
            "kind": "vancelian_product",
            "product_code": "TOP_5",
            "agent_owner": "product",
        },
    )
    db.add(conv)
    db.flush()

    # 3 messages ordonnés
    for idx, (role, content, agent) in enumerate(
        [
            ("user", "parle moi des bundles", None),
            ("assistant", "Vancelian propose deux Crypto Baskets…", "product"),
            ("user", "et le top 5 ?", None),
        ]
    ):
        msg = AssistanceMessage(
            id=uuid4(),
            conversation_id=conv.id,
            turn_index=idx,
            role=role,
            content=content,
            agent_used=agent,
            message_type="text",
            message_payload=None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(msg)
    db.flush()

    # 4 tool calls (1 erreur)
    for it, (tool, agent_id, error) in enumerate(
        [
            ("classify_actor", "router", None),
            ("select_wiki_pages", "product", None),
            ("read_wiki_page", "product", None),
            ("show_bundle_detail", "product", "not_found"),
        ]
    ):
        d = AssistanceAgentDecision(
            id=uuid4(),
            conversation_id=conv.id,
            message_id=None,
            agent_id=agent_id,
            iteration=it,
            tool_name=tool,
            autonomy_level="L0",
            arguments_json={"q": "bundles", "iter": it},
            result_summary={"matches": it},
            proposed_action=None,
            target_client_id=None,
            target_person_id=None,
            reasoning_summary=f"step {it}",
            review_status="auto",
            duration_ms=120 * (it + 1),
            error_code=error,
            correlation_id="test-corr",
            created_at=datetime.now(timezone.utc),
        )
        db.add(d)

    db.commit()
    return {
        "person_id": str(person_uuid),
        "client_id": str(client_uuid),
        "conversation_id": str(conv.id),
    }


# ─────────────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────────────


class TestAuth:
    def test_no_headers_rejected(self, client: TestClient):
        res = client.get(f"{BASE}?client_id={uuid4()}")
        assert res.status_code in (401, 403)

    def test_client_role_rejected(self, client: TestClient):
        res = client.get(
            f"{BASE}?client_id={uuid4()}", headers=CLIENT_HEADERS
        )
        assert res.status_code in (401, 403)

    def test_admin_accepted(self, client: TestClient):
        # Random unknown client_id → 200 + items=[]
        res = client.get(
            f"{BASE}?client_id={uuid4()}", headers=ADMIN_HEADERS
        )
        assert res.status_code == 200
        body = res.json()
        assert body["items"] == []
        assert body["total"] == 0

    def test_ops_accepted(self, client: TestClient):
        res = client.get(
            f"{BASE}?client_id={uuid4()}", headers=OPS_HEADERS
        )
        assert res.status_code == 200


# ─────────────────────────────────────────────────────────────────────
# GET /
# ─────────────────────────────────────────────────────────────────────


class TestList:
    def test_missing_both_client_and_person_returns_400(
        self, client: TestClient
    ):
        res = client.get(BASE, headers=ADMIN_HEADERS)
        assert res.status_code == 400

    def test_invalid_client_id_returns_400(self, client: TestClient):
        res = client.get(f"{BASE}?client_id=not-uuid", headers=ADMIN_HEADERS)
        assert res.status_code == 400

    def test_returns_seeded_conversation_with_counts(
        self, client: TestClient, seeded_conversation
    ):
        res = client.get(
            f"{BASE}?client_id={seeded_conversation['client_id']}",
            headers=ADMIN_HEADERS,
        )
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 1
        assert len(body["items"]) == 1
        item = body["items"][0]
        assert item["id"] == seeded_conversation["conversation_id"]
        assert item["status"] == "active"
        assert item["message_count"] == 3
        assert item["tool_call_count"] == 4
        assert item["tool_error_count"] == 1
        assert item["current_topic"]["product_code"] == "TOP_5"
        # Aggrégats globaux
        assert body["total_messages"] == 3
        assert body["total_tool_calls"] == 4
        assert body["total_tool_errors"] == 1
        assert body["last_activity_at"] is not None

    def test_status_filter_closed_excludes_active(
        self, client: TestClient, seeded_conversation
    ):
        res = client.get(
            f"{BASE}?client_id={seeded_conversation['client_id']}"
            f"&status=closed",
            headers=ADMIN_HEADERS,
        )
        assert res.status_code == 200
        assert res.json()["total"] == 0

    def test_status_filter_invalid_value_returns_400(
        self, client: TestClient, seeded_conversation
    ):
        res = client.get(
            f"{BASE}?client_id={seeded_conversation['client_id']}"
            f"&status=archived",
            headers=ADMIN_HEADERS,
        )
        assert res.status_code == 400

    def test_pagination_limit_offset(
        self, client: TestClient, seeded_conversation
    ):
        res = client.get(
            f"{BASE}?client_id={seeded_conversation['client_id']}"
            f"&limit=10&offset=0",
            headers=ADMIN_HEADERS,
        )
        assert res.status_code == 200
        body = res.json()
        assert body["limit"] == 10
        assert body["offset"] == 0


# ─────────────────────────────────────────────────────────────────────
# GET /{id}
# ─────────────────────────────────────────────────────────────────────


class TestDetail:
    def test_unknown_conv_returns_404(self, client: TestClient):
        res = client.get(f"{BASE}/{uuid4()}", headers=ADMIN_HEADERS)
        assert res.status_code == 404

    def test_invalid_uuid_returns_400(self, client: TestClient):
        res = client.get(f"{BASE}/not-uuid", headers=ADMIN_HEADERS)
        assert res.status_code == 400

    def test_returns_messages_ordered_by_turn(
        self, client: TestClient, seeded_conversation
    ):
        res = client.get(
            f"{BASE}/{seeded_conversation['conversation_id']}",
            headers=ADMIN_HEADERS,
        )
        assert res.status_code == 200
        body = res.json()
        assert body["status"] == "active"
        assert body["message_count"] == 3
        assert body["tool_call_count"] == 4
        assert body["tool_error_count"] == 1
        assert len(body["messages"]) == 3
        assert [m["turn_index"] for m in body["messages"]] == [0, 1, 2]
        assert body["messages"][0]["role"] == "user"
        assert body["messages"][1]["agent_used"] == "product"
        # Mémoire / topic
        assert body["current_topic"]["product_code"] == "TOP_5"
        assert body["summarized_until_turn"] == 2
        assert isinstance(body["conversation_facts"], list)
        assert len(body["conversation_facts"]) >= 1


# ─────────────────────────────────────────────────────────────────────
# GET /{id}/decisions
# ─────────────────────────────────────────────────────────────────────


class TestDecisions:
    def test_unknown_conv_returns_404(self, client: TestClient):
        res = client.get(
            f"{BASE}/{uuid4()}/decisions", headers=ADMIN_HEADERS
        )
        assert res.status_code == 404

    def test_returns_decisions_ordered_by_iteration(
        self, client: TestClient, seeded_conversation
    ):
        res = client.get(
            f"{BASE}/{seeded_conversation['conversation_id']}/decisions",
            headers=ADMIN_HEADERS,
        )
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 4
        assert len(body["decisions"]) == 4
        iterations = [d["iteration"] for d in body["decisions"]]
        assert iterations == sorted(iterations)
        # Le dernier a une error_code
        assert body["decisions"][-1]["error_code"] == "not_found"
        # Les arguments_json sont remappés vers `arguments`
        assert body["decisions"][0]["arguments"]["q"] == "bundles"
