"""Tests d'intégration du router admin
``/api/admin/assistance/observability`` (PR 4B).

Couvre auth, bornes ``period_days``, agrégats summary / gaps / tool-usage.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from database import (
    AssistanceAgentDecision,
    AssistanceConversation,
    Person,
)
from services.portfolio_engine.clients.models import Client as PEClient

ADMIN_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-admin-obs@example.com",
    "X-Actor-Roles": "admin",
}
OPS_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-ops-obs@example.com",
    "X-Actor-Roles": "ops",
}
CLIENT_HEADERS = {
    "X-Actor-Type": "user",
    "X-Actor-Id": "test-user-obs@example.com",
    "X-Actor-Roles": "client",
}

BASE = "/api/admin/assistance/observability"


def _make_router_decision(
    *,
    conversation_id,
    iteration: int,
    agent_id: str,
    created_at: datetime,
    orchestration: dict | None = None,
) -> AssistanceAgentDecision:
    args: dict = {
        "decision_kind": "route_to",
        "agent_id": agent_id,
        "confidence": 0.85,
    }
    if orchestration is not None:
        args["orchestration"] = orchestration
    return AssistanceAgentDecision(
        id=uuid4(),
        conversation_id=conversation_id,
        message_id=None,
        agent_id="router",
        iteration=iteration,
        tool_name="router_classify",
        autonomy_level="L0",
        arguments_json=args,
        result_summary=None,
        proposed_action=None,
        target_client_id=None,
        target_person_id=None,
        reasoning_summary="reasoning",
        review_status="auto",
        duration_ms=12,
        error_code=None,
        correlation_id="test-obs",
        created_at=created_at,
    )


def _make_policy_gap(
    *,
    conversation_id,
    iteration: int,
    agent_id: str,
    created_at: datetime,
) -> AssistanceAgentDecision:
    return AssistanceAgentDecision(
        id=uuid4(),
        conversation_id=conversation_id,
        message_id=None,
        agent_id=agent_id,
        iteration=iteration,
        tool_name="policy_data_need_reads",
        autonomy_level="L0",
        arguments_json={
            "data_need": "account_data",
            "tools_called_this_tour": [],
            "expected_read_tools": [
                "read_compliance_state",
                "read_documents",
            ],
            "policy_version": 1,
        },
        result_summary={"status": "warn"},
        proposed_action=None,
        target_client_id=None,
        target_person_id=None,
        reasoning_summary=None,
        review_status="auto",
        duration_ms=5,
        error_code="policy_soft_warn",
        correlation_id="test-obs-gap",
        created_at=created_at,
    )


def _make_tool_call(
    *,
    conversation_id,
    iteration: int,
    tool_name: str,
    created_at: datetime,
) -> AssistanceAgentDecision:
    return AssistanceAgentDecision(
        id=uuid4(),
        conversation_id=conversation_id,
        message_id=None,
        agent_id="advisor",
        iteration=iteration,
        tool_name=tool_name,
        autonomy_level="L0",
        arguments_json={},
        result_summary=None,
        proposed_action=None,
        target_client_id=None,
        target_person_id=None,
        reasoning_summary=None,
        review_status="auto",
        duration_ms=8,
        error_code=None,
        correlation_id="test-obs-tool",
        created_at=created_at,
    )


@pytest.fixture
def seeded_observability(db) -> dict:
    person_uuid = uuid4()
    db.add(
        Person(
            id=person_uuid,
            status="active",
            jurisdiction="FR",
            profile_json={},
            kyc_status="not_started",
        )
    )
    db.flush()

    client_uuid = uuid4()
    db.add(PEClient(id=client_uuid, person_id=person_uuid))
    db.flush()

    conv = AssistanceConversation(
        id=uuid4(),
        client_id=client_uuid,
        title="Obs test",
        status="active",
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(conv)
    db.flush()

    now = datetime.now(timezone.utc)

    db.add(
        _make_router_decision(
            conversation_id=conv.id,
            iteration=1,
            agent_id="advisor",
            created_at=now - timedelta(minutes=5),
            orchestration={"data_need": "account_data", "memory_mode": "default"},
        )
    )
    db.add(
        _make_router_decision(
            conversation_id=conv.id,
            iteration=2,
            agent_id="trust",
            created_at=now - timedelta(minutes=4),
            orchestration={"data_need": "kyc_data"},
        )
    )
    db.add(
        _make_router_decision(
            conversation_id=conv.id,
            iteration=3,
            agent_id="product",
            created_at=now - timedelta(minutes=3),
            orchestration=None,
        )
    )
    db.add(
        _make_policy_gap(
            conversation_id=conv.id,
            iteration=4,
            agent_id="advisor",
            created_at=now - timedelta(minutes=2),
        )
    )
    db.add(
        _make_tool_call(
            conversation_id=conv.id,
            iteration=5,
            tool_name="read_compliance_state",
            created_at=now - timedelta(minutes=1),
        )
    )

    db.commit()
    return {"conversation_id": str(conv.id)}


class TestAuth:
    def test_no_headers_rejected(self, client: TestClient):
        res = client.get(f"{BASE}/summary")
        assert res.status_code in (401, 403)

    def test_client_role_rejected(self, client: TestClient):
        res = client.get(f"{BASE}/summary", headers=CLIENT_HEADERS)
        assert res.status_code in (401, 403)

    def test_admin_accepted_summary(self, client: TestClient):
        res = client.get(f"{BASE}/summary", headers=ADMIN_HEADERS)
        assert res.status_code == 200

    def test_ops_accepted_gaps(self, client: TestClient):
        res = client.get(f"{BASE}/data-need-gaps", headers=OPS_HEADERS)
        assert res.status_code == 200


class TestQueryBounds:
    def test_period_days_too_low_rejected(self, client: TestClient):
        res = client.get(
            f"{BASE}/summary?period_days=0", headers=ADMIN_HEADERS
        )
        assert res.status_code == 422

    def test_period_days_too_high_rejected(self, client: TestClient):
        res = client.get(
            f"{BASE}/summary?period_days=91", headers=ADMIN_HEADERS
        )
        assert res.status_code == 422


class TestObservabilityAggregates:
    def test_summary_includes_seed_and_rate_matches_components(
        self, client: TestClient, seeded_observability
    ):
        res = client.get(
            f"{BASE}/summary?period_days=1", headers=ADMIN_HEADERS
        )
        assert res.status_code == 200
        body = res.json()
        # Même DB que d'autres tests → bornes inférieures sur le seed.
        assert body["total_turns"] >= 3
        assert body["turns_with_data_need"] >= 2
        assert body["data_need_gap_count"] >= 1
        tw = body["turns_with_data_need"]
        gc = body["data_need_gap_count"]
        expected_rate = (
            0.0 if tw == 0 else round(100.0 * gc / tw, 2)
        )
        assert body["data_need_gap_rate"] == expected_rate

    def test_data_need_gaps_structure(
        self, client: TestClient, seeded_observability
    ):
        res = client.get(
            f"{BASE}/data-need-gaps?period_days=1", headers=ADMIN_HEADERS
        )
        assert res.status_code == 200
        body = res.json()
        assert body["data_need_gap_count"] >= 1
        agent_labels = {b["label"] for b in body["gap_by_agent"]}
        assert "advisor" in agent_labels
        assert any(b["label"] == "account_data" for b in body["gap_by_data_need"])
        labels = {b["label"] for b in body["top_missing_tools"]}
        assert "read_compliance_state" in labels
        assert "read_documents" in labels

    def test_tool_usage_excludes_router_and_policy(
        self, client: TestClient, seeded_observability
    ):
        res = client.get(
            f"{BASE}/tool-usage?period_days=1", headers=ADMIN_HEADERS
        )
        assert res.status_code == 200
        body = res.json()
        assert body["total_tool_calls"] >= 1
        by_label = {t["label"]: t["count"] for t in body["tools"]}
        assert by_label.get("read_compliance_state", 0) >= 1
        assert "router_classify" not in by_label
        assert "policy_data_need_reads" not in by_label
