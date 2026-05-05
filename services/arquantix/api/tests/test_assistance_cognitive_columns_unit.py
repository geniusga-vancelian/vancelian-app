"""Tests Lot 6 — colonnes cognitives natives + double-write.

Couvre :

  * `audit.persist_decision(extra_columns=...)` : les valeurs sont
    appliquées sur les attributs ORM correspondants ; les clés inconnues
    sont silently ignorées (best-effort).
  * Double-write réel (chemin nominal) : une décision ``router_classify``
    persistée via le runtime cognitif aboutit à la **fois** dans
    ``arguments_json`` (JSONB) et dans les colonnes natives.
  * Lecture priorisée du funnel : ``_aggregate_dimension`` retourne
    la valeur de la **colonne native** quand elle existe, et fallback
    sur le JSONB sinon.
  * ``_trust_level_stats`` mixe les 2 sources via COALESCE (colonne
    native + cast JSONB).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from database import (
    AssistanceAgentDecision,
    AssistanceConversation,
    Person,
)
from services.assistance.admin_cognitive_router import (
    _aggregate_dimension,
    _trust_level_stats,
)
from services.assistance.agents.tools.shared import audit
from services.portfolio_engine.clients.models import Client as PEClient


# ─────────────────────────────────────────────────────────────────────
# Fixtures partagées
# ─────────────────────────────────────────────────────────────────────


@pytest.fixture
def base_client(db) -> dict:
    """1 person + 1 pe_client + 1 conv vide pour héberger les décisions."""
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
        title="Lot 6 test",
        status="active",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(conv)
    db.flush()
    return {
        "client_id": client_uuid,
        "conversation_id": conv.id,
    }


# ─────────────────────────────────────────────────────────────────────
# audit.persist_decision(extra_columns=…)
# ─────────────────────────────────────────────────────────────────────


class TestPersistDecisionExtraColumns:
    def test_extra_columns_applied_on_known_attrs(self, db, base_client):
        row_id = audit.persist_decision(
            db,
            conversation_id=base_client["conversation_id"],
            agent_id="router",
            iteration=0,
            tool_name="router_classify",
            autonomy_level="L0",
            arguments={
                "decision_kind": "route_to",
                "agent_id": "advisor",
                "cognitive_state": {
                    "emotional_intent": "CURIOSITY",
                    "conversation_stage": "discovery",
                    "trust_level": 0.7,
                    "knowledge_level": "low",
                },
                "objective": {
                    "primary_goal": "educate",
                    "next_best_action": "ask_question",
                },
            },
            extra_columns={
                "emotional_intent": "CURIOSITY",
                "conversation_stage": "discovery",
                "knowledge_level": "low",
                "trust_level": 0.7,
                "primary_goal": "educate",
                "next_best_action": "ask_question",
            },
        )
        db.commit()

        assert row_id is not None
        row = (
            db.query(AssistanceAgentDecision)
            .filter(AssistanceAgentDecision.id == row_id)
            .one()
        )
        assert row.emotional_intent == "CURIOSITY"
        assert row.conversation_stage == "discovery"
        assert row.knowledge_level == "low"
        assert row.trust_level == pytest.approx(0.7, abs=1e-6)
        assert row.primary_goal == "educate"
        assert row.next_best_action == "ask_question"
        # JSONB toujours présent (source de vérité conservée).
        assert (
            row.arguments_json["cognitive_state"]["emotional_intent"]
            == "CURIOSITY"
        )

    def test_unknown_extra_keys_are_silently_ignored(
        self, db, base_client
    ):
        # Une clé qui ne matche aucun attribut ORM ne doit pas faire
        # crasher la persistance — best-effort par design.
        row_id = audit.persist_decision(
            db,
            conversation_id=base_client["conversation_id"],
            agent_id="router",
            iteration=1,
            tool_name="router_classify",
            autonomy_level="L0",
            arguments={"decision_kind": "route_to", "agent_id": "advisor"},
            extra_columns={
                "emotional_intent": "FEAR_RISK",
                "totally_unknown_attr": "whatever",
            },
        )
        db.commit()
        assert row_id is not None
        row = (
            db.query(AssistanceAgentDecision)
            .filter(AssistanceAgentDecision.id == row_id)
            .one()
        )
        assert row.emotional_intent == "FEAR_RISK"
        # Pas d'erreur, juste ignoré.
        assert not hasattr(row, "totally_unknown_attr")

    def test_none_values_skipped(self, db, base_client):
        # Une valeur None ne doit pas écraser une potentielle valeur
        # déjà présente (pas d'overwrite involontaire).
        row_id = audit.persist_decision(
            db,
            conversation_id=base_client["conversation_id"],
            agent_id="router",
            iteration=2,
            tool_name="router_classify",
            autonomy_level="L0",
            arguments={"decision_kind": "route_to", "agent_id": "advisor"},
            extra_columns={
                "emotional_intent": None,
                "conversation_stage": "discovery",
            },
        )
        db.commit()
        row = (
            db.query(AssistanceAgentDecision)
            .filter(AssistanceAgentDecision.id == row_id)
            .one()
        )
        assert row.emotional_intent is None
        assert row.conversation_stage == "discovery"


# ─────────────────────────────────────────────────────────────────────
# Lecture funnel — priorité colonne native + fallback JSONB
# ─────────────────────────────────────────────────────────────────────


def _make_decision(
    *,
    conversation_id,
    iteration: int,
    cognitive: dict | None,
    objective: dict | None,
    column_overrides: dict | None,
    agent_id: str,
    created_at: datetime,
) -> AssistanceAgentDecision:
    args: dict = {
        "decision_kind": "route_to",
        "agent_id": agent_id,
        "confidence": 0.85,
    }
    if cognitive is not None:
        args["cognitive_state"] = cognitive
    if objective is not None:
        args["objective"] = objective

    row = AssistanceAgentDecision(
        id=uuid4(),
        conversation_id=conversation_id,
        message_id=None,
        agent_id="router",
        iteration=iteration,
        tool_name="router_classify",
        autonomy_level="L0",
        arguments_json=args,
        review_status="auto",
        created_at=created_at,
    )
    if column_overrides:
        for k, v in column_overrides.items():
            if hasattr(row, k):
                setattr(row, k, v)
    return row


@pytest.fixture
def funnel_seed(db, base_client) -> dict:
    """3 patterns :

      * (a) **double-write** : JSONB + colonne native peuplées de la
        même valeur → la colonne native est lue.
      * (b) **legacy** : JSONB seul, colonne native à NULL → fallback
        JSONB doit kicker.
      * (c) **incohérence** : colonne native ≠ JSONB → la colonne
        native gagne (priorité).
    """
    now = datetime.now(timezone.utc)
    rows: list[AssistanceAgentDecision] = []

    # (a) double-write CURIOSITY/discovery
    rows.append(
        _make_decision(
            conversation_id=base_client["conversation_id"],
            iteration=0,
            cognitive={
                "emotional_intent": "CURIOSITY",
                "conversation_stage": "discovery",
                "trust_level": 0.6,
            },
            objective={
                "primary_goal": "educate",
                "next_best_action": "ask_question",
            },
            column_overrides={
                "emotional_intent": "CURIOSITY",
                "conversation_stage": "discovery",
                "trust_level": 0.6,
                "primary_goal": "educate",
                "next_best_action": "ask_question",
            },
            agent_id="advisor",
            created_at=now - timedelta(minutes=1),
        )
    )

    # (b) legacy JSONB only — pas de colonne (NULL)
    rows.append(
        _make_decision(
            conversation_id=base_client["conversation_id"],
            iteration=1,
            cognitive={
                "emotional_intent": "FEAR_RISK",
                "conversation_stage": "clarification",
                "trust_level": 0.3,
            },
            objective={
                "primary_goal": "reassure",
                "next_best_action": "give_proof",
            },
            column_overrides=None,
            agent_id="trust",
            created_at=now - timedelta(minutes=2),
        )
    )

    # (c) incohérence : JSONB dit ANGER mais colonne dit CURIOSITY.
    # Le funnel doit lire la **colonne** (CURIOSITY), pas le JSONB.
    rows.append(
        _make_decision(
            conversation_id=base_client["conversation_id"],
            iteration=2,
            cognitive={
                "emotional_intent": "ANGER",
                "conversation_stage": "discovery",
                "trust_level": 0.8,
            },
            objective=None,
            column_overrides={
                "emotional_intent": "CURIOSITY",
                "conversation_stage": "discovery",
                "trust_level": 0.8,
            },
            agent_id="advisor",
            created_at=now - timedelta(minutes=3),
        )
    )

    db.add_all(rows)
    db.commit()
    return {
        "now": now,
    }


class TestFunnelReadPriority:
    def test_column_takes_priority_over_jsonb(
        self, db, base_client, funnel_seed
    ):
        end = funnel_seed["now"] + timedelta(seconds=1)
        start = end - timedelta(minutes=10)
        out = _aggregate_dimension(
            db,
            column=AssistanceAgentDecision.emotional_intent,
            json_path=("cognitive_state", "emotional_intent"),
            period_start=start,
            period_end=end,
        )
        labels = {b.label: b.count for b in out}
        # (a) CURIOSITY natif + (c) CURIOSITY natif (qui contredit le
        # JSONB ANGER) → 2 CURIOSITY ; (b) FEAR_RISK fallback JSONB → 1.
        # ANGER ne doit JAMAIS apparaître (la colonne native gagne).
        assert labels.get("CURIOSITY", 0) >= 2
        assert labels.get("FEAR_RISK", 0) >= 1
        assert labels.get("ANGER", 0) == 0

    def test_legacy_jsonb_is_used_when_column_is_null(
        self, db, base_client, funnel_seed
    ):
        end = funnel_seed["now"] + timedelta(seconds=1)
        start = end - timedelta(minutes=10)
        out = _aggregate_dimension(
            db,
            column=AssistanceAgentDecision.primary_goal,
            json_path=("objective", "primary_goal"),
            period_start=start,
            period_end=end,
        )
        labels = {b.label: b.count for b in out}
        # (a) educate natif → educate ≥ 1
        # (b) reassure JSONB-only → fallback doit faire apparaître reassure ≥ 1
        assert labels.get("educate", 0) >= 1
        assert labels.get("reassure", 0) >= 1

    def test_unknown_when_both_null(self, db, base_client, funnel_seed):
        # Décision ``router_classify`` sans cognitive_state ni colonne →
        # bucket "unknown".
        bare = _make_decision(
            conversation_id=base_client["conversation_id"],
            iteration=99,
            cognitive=None,
            objective=None,
            column_overrides=None,
            agent_id="default",
            created_at=funnel_seed["now"] - timedelta(seconds=10),
        )
        db.add(bare)
        db.commit()
        end = funnel_seed["now"] + timedelta(seconds=1)
        start = end - timedelta(minutes=10)
        out = _aggregate_dimension(
            db,
            column=AssistanceAgentDecision.emotional_intent,
            json_path=("cognitive_state", "emotional_intent"),
            period_start=start,
            period_end=end,
        )
        labels = {b.label: b.count for b in out}
        assert labels.get("unknown", 0) >= 1

    def test_trust_level_stats_uses_column_or_jsonb(
        self, db, base_client, funnel_seed
    ):
        end = funnel_seed["now"] + timedelta(seconds=1)
        start = end - timedelta(minutes=10)
        stats = _trust_level_stats(
            db, period_start=start, period_end=end
        )
        # 3 décisions seedées (toutes avec trust_level défini par
        # colonne ou JSONB) → sample_size ≥ 3.
        assert stats.sample_size >= 3
        assert stats.min is not None
        assert stats.max is not None
        # min ≈ 0.3 (legacy JSONB), max ≈ 0.8 (incohérence colonne).
        assert stats.min <= 0.3 + 1e-6
        assert stats.max >= 0.8 - 1e-6
