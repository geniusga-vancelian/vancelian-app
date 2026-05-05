"""Tests d'intégration du router admin
``/api/admin/assistance/cognitive`` (Cognitive Bot v4 — Lot 5).

Couvre :

  * Auth : 401/403 si pas admin/ops.
  * GET /funnel : 200 + structure complète, agrégats par stage,
    emotional_intent, primary_goal, next_best_action, agent_id et
    stats trust_level.
  * Bornes ``period_days`` : <1 ou >90 → 422.
  * Comportement défensif : décisions ``router_classify`` legacy sans
    ``cognitive_state`` ne cassent pas l'agrégation et sont comptées
    sous ``"unknown"``.
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
    "X-Actor-Id": "test-admin-cog@example.com",
    "X-Actor-Roles": "admin",
}
OPS_HEADERS = {
    "X-Actor-Type": "admin",
    "X-Actor-Id": "test-ops-cog@example.com",
    "X-Actor-Roles": "ops",
}
CLIENT_HEADERS = {
    "X-Actor-Type": "user",
    "X-Actor-Id": "test-user-cog@example.com",
    "X-Actor-Roles": "client",
}

BASE = "/api/admin/assistance/cognitive"


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


def _make_decision(
    *,
    conversation_id,
    iteration: int,
    cognitive: dict | None,
    objective: dict | None,
    agent_id: str,
    created_at: datetime,
) -> AssistanceAgentDecision:
    """Construit une décision ``router_classify`` minimaliste pour le test."""
    args: dict = {
        "decision_kind": "route_to",
        "agent_id": agent_id,
        "confidence": 0.85,
        "intent_classification": None,
    }
    if cognitive is not None:
        args["cognitive_state"] = cognitive
    if objective is not None:
        args["objective"] = objective
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
        correlation_id="test-cog",
        created_at=created_at,
    )


@pytest.fixture
def seeded_funnel(db) -> dict:
    """Crée 1 client + 1 conv + 5 décisions ``router_classify`` couvrant
    les principales dimensions cognitives :

      * 2 décisions stage=discovery + emotional=CURIOSITY → advisor.
      * 2 décisions stage=clarification + emotional=FEAR_RISK → trust.
      * 1 décision sans cognitive_state (legacy) → product.

    Ainsi on peut vérifier les agrégats et le bucket ``"unknown"``.
    """
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
    pe_client = PEClient(id=client_uuid, person_id=person_uuid)
    db.add(pe_client)
    db.flush()

    conv = AssistanceConversation(
        id=uuid4(),
        client_id=client_uuid,
        title="Funnel test",
        status="active",
        created_at=datetime.now(timezone.utc) - timedelta(hours=1),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(conv)
    db.flush()

    now = datetime.now(timezone.utc)

    # 2x discovery / CURIOSITY → advisor.
    for i in range(2):
        db.add(
            _make_decision(
                conversation_id=conv.id,
                iteration=i,
                cognitive={
                    "emotional_intent": "CURIOSITY",
                    "conversation_stage": "discovery",
                    "trust_level": 0.6,
                    "knowledge_level": "low",
                },
                objective={
                    "primary_goal": "educate",
                    "next_best_action": "ask_question",
                    "stop_pushing": False,
                },
                agent_id="advisor",
                created_at=now - timedelta(minutes=10 + i),
            )
        )

    # 2x clarification / FEAR_RISK → trust.
    for i in range(2):
        db.add(
            _make_decision(
                conversation_id=conv.id,
                iteration=10 + i,
                cognitive={
                    "emotional_intent": "FEAR_RISK",
                    "conversation_stage": "clarification",
                    "trust_level": 0.3,
                    "knowledge_level": "medium",
                },
                objective={
                    "primary_goal": "reassure",
                    "next_best_action": "give_proof",
                    "stop_pushing": True,
                },
                agent_id="trust",
                created_at=now - timedelta(minutes=20 + i),
            )
        )

    # 1x legacy (sans cognitive_state ni objective) → product.
    db.add(
        _make_decision(
            conversation_id=conv.id,
            iteration=20,
            cognitive=None,
            objective=None,
            agent_id="product",
            created_at=now - timedelta(minutes=30),
        )
    )

    db.commit()

    return {
        "client_id": str(client_uuid),
        "conversation_id": str(conv.id),
    }


# ─────────────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────────────


class TestAuth:
    def test_no_headers_rejected(self, client: TestClient):
        res = client.get(f"{BASE}/funnel")
        assert res.status_code in (401, 403)

    def test_client_role_rejected(self, client: TestClient):
        res = client.get(f"{BASE}/funnel", headers=CLIENT_HEADERS)
        assert res.status_code in (401, 403)

    def test_admin_accepted(self, client: TestClient):
        res = client.get(f"{BASE}/funnel", headers=ADMIN_HEADERS)
        assert res.status_code == 200

    def test_ops_accepted(self, client: TestClient):
        res = client.get(f"{BASE}/funnel", headers=OPS_HEADERS)
        assert res.status_code == 200


# ─────────────────────────────────────────────────────────────────────
# Bornes period_days
# ─────────────────────────────────────────────────────────────────────


class TestQueryBounds:
    def test_period_days_too_low_rejected(self, client: TestClient):
        res = client.get(
            f"{BASE}/funnel?period_days=0", headers=ADMIN_HEADERS
        )
        assert res.status_code == 422

    def test_period_days_too_high_rejected(self, client: TestClient):
        res = client.get(
            f"{BASE}/funnel?period_days=91", headers=ADMIN_HEADERS
        )
        assert res.status_code == 422

    def test_period_days_default_is_7(self, client: TestClient):
        res = client.get(f"{BASE}/funnel", headers=ADMIN_HEADERS)
        assert res.status_code == 200
        assert res.json()["period_days"] == 7


# ─────────────────────────────────────────────────────────────────────
# Aggregations
# ─────────────────────────────────────────────────────────────────────


class TestFunnel:
    def test_returns_full_structure(
        self, client: TestClient, seeded_funnel
    ):
        res = client.get(
            f"{BASE}/funnel?period_days=1", headers=ADMIN_HEADERS
        )
        assert res.status_code == 200
        body = res.json()
        for key in (
            "period_start",
            "period_end",
            "period_days",
            "total_decisions",
            "by_stage",
            "by_emotional_intent",
            "by_primary_goal",
            "by_next_best_action",
            "by_agent_id",
            "trust_level",
        ):
            assert key in body, f"missing key {key} in funnel response"

    def test_total_decisions_counts_all_classify_decisions(
        self, client: TestClient, seeded_funnel
    ):
        res = client.get(
            f"{BASE}/funnel?period_days=1", headers=ADMIN_HEADERS
        )
        assert res.status_code == 200
        body = res.json()
        # 5 décisions seedées (2 advisor + 2 trust + 1 product).
        # Note: d'autres tests peuvent seeder dans la même DB → on
        # vérifie au minimum le seed (>=5).
        assert body["total_decisions"] >= 5

    def test_by_agent_id_contains_seeded_agents(
        self, client: TestClient, seeded_funnel
    ):
        res = client.get(
            f"{BASE}/funnel?period_days=1", headers=ADMIN_HEADERS
        )
        body = res.json()
        labels = {b["label"] for b in body["by_agent_id"]}
        for expected in ("advisor", "trust", "product"):
            assert expected in labels, (
                f"expected agent {expected} in by_agent_id, got {labels}"
            )

    def test_by_stage_groups_discovery_clarification_unknown(
        self, client: TestClient, seeded_funnel
    ):
        res = client.get(
            f"{BASE}/funnel?period_days=1", headers=ADMIN_HEADERS
        )
        body = res.json()
        labels = {b["label"]: b["count"] for b in body["by_stage"]}
        # Seedés : 2 discovery, 2 clarification, 1 unknown (legacy).
        assert labels.get("discovery", 0) >= 2
        assert labels.get("clarification", 0) >= 2
        assert labels.get("unknown", 0) >= 1

    def test_by_emotional_intent_includes_curiosity_and_fear(
        self, client: TestClient, seeded_funnel
    ):
        res = client.get(
            f"{BASE}/funnel?period_days=1", headers=ADMIN_HEADERS
        )
        body = res.json()
        labels = {b["label"]: b["count"] for b in body["by_emotional_intent"]}
        assert labels.get("CURIOSITY", 0) >= 2
        assert labels.get("FEAR_RISK", 0) >= 2

    def test_by_primary_goal_includes_educate_and_reassure(
        self, client: TestClient, seeded_funnel
    ):
        res = client.get(
            f"{BASE}/funnel?period_days=1", headers=ADMIN_HEADERS
        )
        body = res.json()
        labels = {b["label"]: b["count"] for b in body["by_primary_goal"]}
        assert labels.get("educate", 0) >= 2
        assert labels.get("reassure", 0) >= 2

    def test_by_next_best_action_includes_ask_question_and_give_proof(
        self, client: TestClient, seeded_funnel
    ):
        res = client.get(
            f"{BASE}/funnel?period_days=1", headers=ADMIN_HEADERS
        )
        body = res.json()
        labels = {
            b["label"]: b["count"] for b in body["by_next_best_action"]
        }
        assert labels.get("ask_question", 0) >= 2
        assert labels.get("give_proof", 0) >= 2

    def test_trust_level_stats_computed(
        self, client: TestClient, seeded_funnel
    ):
        res = client.get(
            f"{BASE}/funnel?period_days=1", headers=ADMIN_HEADERS
        )
        body = res.json()
        stats = body["trust_level"]
        assert stats["sample_size"] >= 4
        # Seedés : 2x 0.6 et 2x 0.3 → min ≤ 0.3, max ≥ 0.6.
        assert stats["min"] is not None and stats["min"] <= 0.3 + 1e-6
        assert stats["max"] is not None and stats["max"] >= 0.6 - 1e-6
        assert stats["avg"] is not None
        assert 0.3 - 1e-6 <= stats["avg"] <= 0.6 + 1e-6

    def test_pct_sums_to_100_per_dimension(
        self, client: TestClient, seeded_funnel
    ):
        res = client.get(
            f"{BASE}/funnel?period_days=1", headers=ADMIN_HEADERS
        )
        body = res.json()
        for key in (
            "by_stage",
            "by_emotional_intent",
            "by_primary_goal",
            "by_next_best_action",
            "by_agent_id",
        ):
            buckets = body[key]
            if not buckets:
                continue
            total_pct = sum(b["pct"] for b in buckets)
            # Tolérance d'arrondi (round 2 décimales sur N buckets).
            assert abs(total_pct - 100.0) < 1.0, (
                f"{key} pct sum = {total_pct} (expected ~100)"
            )
