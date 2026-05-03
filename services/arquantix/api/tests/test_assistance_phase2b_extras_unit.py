"""Tests unitaires Phase 2b — tools nouveaux + ChoiceOption + ask_user_question.

Couvre :
  - `propose_resume_registration` (L0)
  - `read_transaction_detail` (L0, ownership check)
  - `ChoiceOption.to_dict()` propage `agent_hint` et `deep_link`
  - `ask_user_question` strip les deep-links non-whitelistés
  - `ask_user_question` strip `deep_link` quand `agent_hint` est aussi présent

Spec : `docs/arquantix/COMPLIANCE_TOPICS.md` § 5 et § 8ter.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from services.assistance.agents.base import ChoiceOption
from services.assistance.agents.tools.compliance import (
    propose_resume_registration,
    read_transaction_detail,
)
from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.shared import ask_user_question
from services.assistance.agents.tools.shared.classify_actor import ActorKind


def _ctx(
    *,
    client_id: str | None = "11111111-1111-1111-1111-111111111111",
    person_id: str | None = "22222222-2222-2222-2222-222222222222",
) -> ToolContext:
    return ToolContext(
        db=MagicMock(),
        client_id=client_id,
        person_id=person_id,
        user_id=42,
        actor_kind=ActorKind.CUSTOMER,
        agent_id="compliance.registration",
        conversation_id=str(uuid4()),
        iteration=0,
        audit_session_id=str(uuid4()),
        correlation_id="t-p2b",
    )


# ─────────────────────────────────────────────────────────────────────────
# A. propose_resume_registration
# ─────────────────────────────────────────────────────────────────────────


class TestProposeResumeRegistration:
    def test_returns_action_when_session_in_progress(self):
        with patch.object(
            propose_resume_registration.compliance_repo,
            "fetch_registration_progress",
            return_value={
                "session_status": "in_progress",
                "current_step_id": "step_3",
                "completed_steps": 2,
                "total_steps_recorded": 5,
            },
        ):
            result = propose_resume_registration.execute(_ctx())
        assert result["available"] is True
        assert result["session_status"] == "in_progress"
        assert result["completed_steps"] == 2
        assert result["total_steps_recorded"] == 5
        assert result["action"]["kind"] == "resume_registration"
        assert (
            result["action"]["deep_link"]
            == "vancelian://app/registration_resume"
        )

    def test_returns_action_when_current_step_present(self):
        # Même si `session_status` est inconnu, la présence d'un
        # `current_step_id` indique une session active.
        with patch.object(
            propose_resume_registration.compliance_repo,
            "fetch_registration_progress",
            return_value={
                "session_status": None,
                "current_step_id": "step_X",
            },
        ):
            result = propose_resume_registration.execute(_ctx())
        assert result["available"] is True

    def test_returns_unavailable_when_no_session(self):
        with patch.object(
            propose_resume_registration.compliance_repo,
            "fetch_registration_progress",
            return_value={
                "session_status": "completed",
                "current_step_id": None,
            },
        ):
            result = propose_resume_registration.execute(_ctx())
        assert result["available"] is False
        assert result["reason"] == "no_active_session"

    def test_returns_unavailable_no_person_id(self):
        result = propose_resume_registration.execute(_ctx(person_id=None))
        assert result["available"] is False
        assert result["reason"] == "no_person_id"

    def test_returns_unavailable_on_repo_error(self):
        with patch.object(
            propose_resume_registration.compliance_repo,
            "fetch_registration_progress",
            side_effect=RuntimeError("db down"),
        ):
            result = propose_resume_registration.execute(_ctx())
        assert result["available"] is False
        assert result["reason"] == "repo_unavailable"

    def test_spec_metadata(self):
        spec = propose_resume_registration.SPEC
        assert spec["function"]["name"] == "propose_resume_registration"
        assert spec["autonomy_level"] == "L0"
        assert spec["agent_id"] == "compliance.registration"


# ─────────────────────────────────────────────────────────────────────────
# B. read_transaction_detail
# ─────────────────────────────────────────────────────────────────────────


class TestReadTransactionDetail:
    def test_returns_safe_detail_and_emits_embed(self):
        # Phase 2c.2 — Le tool ne retourne plus d'`action` inline mais
        # enregistre un embed UI dans `ctx.embeds_to_emit` (consommé
        # par le runtime pour le `done` event SSE).
        ctx = _ctx()
        with patch.object(
            read_transaction_detail.compliance_repo,
            "fetch_transaction_detail",
            return_value={
                "transaction_id": "abc-123",
                "status": "completed",
                "kind": "deposit_eur",
                "created_at": "2026-05-02T10:00:00+00:00",
                "updated_at": "2026-05-02T10:01:00+00:00",
                "is_inbound": True,
            },
        ):
            result = read_transaction_detail.execute(
                ctx, transaction_id="abc-123"
            )
        # 1. Tool result au LLM : retour minimal, anti-tipping-off.
        assert result["transaction_id"] == "abc-123"
        assert result["status"] == "completed"
        assert result["is_inbound"] is True
        assert "action" not in result, "L'`action` inline est remplacée par l'embed."

        # 2. Embed UI poussé dans le ToolContext.
        assert len(ctx.embeds_to_emit) == 1
        emb = ctx.embeds_to_emit[0]
        assert emb["type"] == "transaction_detail"
        assert emb["transaction_id"] == "abc-123"
        # Hint visuel sans montant, sans contrepartie.
        assert emb["status"] == "completed"
        assert emb["kind"] == "deposit_eur"
        assert emb["is_inbound"] is True

        # 3. Deux actions whitelistées : view + download statement.
        kinds = {a["kind"] for a in emb["actions"]}
        assert "view_transaction_detail" in kinds
        assert "download_transaction_statement" in kinds
        view_action = next(
            a for a in emb["actions"] if a["kind"] == "view_transaction_detail"
        )
        assert (
            view_action["deep_link"]
            == "vancelian://app/transactions/abc-123"
        )
        download_action = next(
            a
            for a in emb["actions"]
            if a["kind"] == "download_transaction_statement"
        )
        assert (
            download_action["deep_link"]
            == "vancelian://app/transactions/abc-123/statement"
        )

    def test_returns_not_found_when_repo_says_not_found(self):
        ctx = _ctx()
        with patch.object(
            read_transaction_detail.compliance_repo,
            "fetch_transaction_detail",
            return_value={
                "transaction_id": "abc-123",
                "error": "not_found",
            },
        ):
            result = read_transaction_detail.execute(
                ctx, transaction_id="abc-123"
            )
        assert result["error"] == "not_found"
        # Pas d'action attachée ni d'embed généré si la transaction
        # n'existe pas / n'appartient pas au client (anti-tipping-off).
        assert "action" not in result
        assert ctx.embeds_to_emit == []

    def test_no_client_context(self):
        result = read_transaction_detail.execute(
            _ctx(client_id=None), transaction_id="abc-123"
        )
        assert result["error"] == "no_client_context"

    def test_missing_transaction_id_param(self):
        result = read_transaction_detail.execute(_ctx(), transaction_id="")
        assert result["error"] == "missing_transaction_id"

    def test_spec_metadata(self):
        spec = read_transaction_detail.SPEC
        assert spec["function"]["name"] == "read_transaction_detail"
        assert spec["autonomy_level"] == "L0"
        assert spec["agent_id"] == "compliance.transactional"
        # Param transaction_id est requis.
        assert "transaction_id" in spec["function"]["parameters"]["required"]


# ─────────────────────────────────────────────────────────────────────────
# C. ChoiceOption.to_dict() — Phase 2b extension
# ─────────────────────────────────────────────────────────────────────────


class TestChoiceOptionSerialization:
    def test_to_dict_minimal(self):
        opt = ChoiceOption(id="x", label="X")
        d = opt.to_dict()
        assert d == {"id": "x", "label": "X"}
        assert "agent_hint" not in d
        assert "deep_link" not in d

    def test_to_dict_with_agent_hint(self):
        opt = ChoiceOption(id="x", label="X", agent_hint="product")
        d = opt.to_dict()
        assert d["agent_hint"] == "product"
        assert "deep_link" not in d

    def test_to_dict_with_deep_link(self):
        opt = ChoiceOption(
            id="x",
            label="Reprendre",
            deep_link="vancelian://app/registration_resume",
        )
        d = opt.to_dict()
        assert d["deep_link"] == "vancelian://app/registration_resume"
        assert "agent_hint" not in d


# ─────────────────────────────────────────────────────────────────────────
# D. ask_user_question — sanitization Phase 2b
# ─────────────────────────────────────────────────────────────────────────


class TestAskUserQuestionPhase2b:
    def test_strips_deep_link_when_agent_hint_also_present(self):
        result = ask_user_question.execute(
            _ctx(),
            prompt="Test",
            options=[
                {
                    "id": "a",
                    "label": "A",
                    "agent_hint": "product",
                    "deep_link": "vancelian://app/deposit",
                }
            ],
        )
        opts = result["options"]
        assert len(opts) == 1
        assert opts[0]["agent_hint"] == "product"
        # Mutual exclusion → deep_link strippé.
        assert "deep_link" not in opts[0]

    def test_keeps_whitelisted_deep_link(self):
        result = ask_user_question.execute(
            _ctx(),
            prompt="Test",
            options=[
                {
                    "id": "a",
                    "label": "Reprendre",
                    "deep_link": "vancelian://app/registration_resume",
                }
            ],
        )
        assert result["options"][0]["deep_link"] == (
            "vancelian://app/registration_resume"
        )

    def test_strips_non_whitelisted_deep_link(self):
        result = ask_user_question.execute(
            _ctx(),
            prompt="Test",
            options=[
                {
                    "id": "a",
                    "label": "Hack",
                    "deep_link": "vancelian://malicious/wipe",
                }
            ],
        )
        opts = result["options"]
        # Option conservée, mais `deep_link` strippé.
        assert len(opts) == 1
        assert "deep_link" not in opts[0]

    def test_strips_http_url_outside_app(self):
        result = ask_user_question.execute(
            _ctx(),
            prompt="Test",
            options=[
                {
                    "id": "a",
                    "label": "Click",
                    "deep_link": "http://other.com/admin",
                }
            ],
        )
        assert "deep_link" not in result["options"][0]

    def test_truncates_agent_hint(self):
        result = ask_user_question.execute(
            _ctx(),
            prompt="Test",
            options=[
                {
                    "id": "a",
                    "label": "A",
                    "agent_hint": "x" * 100,
                }
            ],
        )
        assert len(result["options"][0]["agent_hint"]) <= 32

    def test_preserves_payload_shape(self):
        result = ask_user_question.execute(
            _ctx(), prompt="Q ?", options=[]
        )
        assert result["interrupt_with_question"] is True
        assert result["prompt"] == "Q ?"
        assert result["options"] == []
        assert result["allow_freeform"] is True
