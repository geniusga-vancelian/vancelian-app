"""Tests unitaires `handoff_to_agent` — Phase 2c.

Couvre l'étage **tool** :
  - whitelist `_ALLOWED_HANDOFFS` : transitions autorisées / refusées
  - `investigation_done` : précondition tools sur `compliance.remediation`
  - cas execute() : signal `interrupt_with_handoff` + erreurs

Le branchement runtime (préconditions runtime, switch agent_id, max
1 handoff) est testé dans `test_assistance_orchestration_chain_unit.py`.

Spec : `services/assistance/agents/tools/shared/handoff_to_agent.py`.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.shared import handoff_to_agent
from services.assistance.agents.tools.shared.classify_actor import ActorKind


def _ctx(*, agent_id: str) -> ToolContext:
    return ToolContext(
        db=MagicMock(),
        client_id="11111111-1111-1111-1111-111111111111",
        person_id="22222222-2222-2222-2222-222222222222",
        user_id=42,
        actor_kind=ActorKind.CUSTOMER,
        agent_id=agent_id,
        conversation_id=str(uuid4()),
        iteration=0,
        audit_session_id=str(uuid4()),
        correlation_id="t-handoff",
    )


class TestHandoffWhitelist:
    def test_remediation_to_transactional_allowed(self):
        assert handoff_to_agent.is_handoff_allowed(
            source_agent="compliance.remediation",
            target_agent="compliance.transactional",
        )

    def test_remediation_to_general_allowed(self):
        assert handoff_to_agent.is_handoff_allowed(
            source_agent="compliance.remediation",
            target_agent="compliance.general",
        )

    def test_transactional_cannot_handoff_anywhere(self):
        # Transactional est terminal — aucun handoff autorisé.
        for target in (
            "compliance.remediation",
            "compliance.general",
            "compliance.registration",
        ):
            assert not handoff_to_agent.is_handoff_allowed(
                source_agent="compliance.transactional",
                target_agent=target,
            )

    def test_registration_to_general_allowed(self):
        assert handoff_to_agent.is_handoff_allowed(
            source_agent="compliance.registration",
            target_agent="compliance.general",
        )

    def test_registration_to_transactional_forbidden(self):
        # En KYC pending, pas de handoff vers transactional.
        assert not handoff_to_agent.is_handoff_allowed(
            source_agent="compliance.registration",
            target_agent="compliance.transactional",
        )

    def test_self_handoff_forbidden(self):
        assert not handoff_to_agent.is_handoff_allowed(
            source_agent="compliance.remediation",
            target_agent="compliance.remediation",
        )

    def test_unknown_source_returns_false(self):
        assert not handoff_to_agent.is_handoff_allowed(
            source_agent="random",
            target_agent="compliance.general",
        )


class TestInvestigationDone:
    def test_remediation_requires_min_2_tools(self):
        ok, missing = handoff_to_agent.investigation_done(
            source_agent="compliance.remediation",
            tools_called=["read_documents"],
        )
        assert ok is False
        assert "read_external_aml_signals" in missing

    def test_remediation_2_distinct_tools_ok(self):
        ok, missing = handoff_to_agent.investigation_done(
            source_agent="compliance.remediation",
            tools_called=["read_documents", "read_external_aml_signals"],
        )
        assert ok is True
        assert missing == []

    def test_remediation_2_same_tool_calls_not_enough(self):
        # Même tool appelé deux fois ne compte que pour 1 distinct.
        ok, _missing = handoff_to_agent.investigation_done(
            source_agent="compliance.remediation",
            tools_called=["read_documents", "read_documents"],
        )
        assert ok is False

    def test_general_no_precondition(self):
        ok, missing = handoff_to_agent.investigation_done(
            source_agent="compliance.general",
            tools_called=[],
        )
        assert ok is True
        assert missing == []

    def test_registration_no_precondition(self):
        ok, _missing = handoff_to_agent.investigation_done(
            source_agent="compliance.registration",
            tools_called=[],
        )
        assert ok is True


class TestHandoffExecute:
    def test_nominal_returns_signal(self):
        result = handoff_to_agent.execute(
            _ctx(agent_id="compliance.remediation"),
            target_agent="compliance.transactional",
            reason="no_compliance_signal_detected",
        )
        assert result.get("interrupt_with_handoff") is True
        assert result["target_agent"] == "compliance.transactional"
        assert result["reason"] == "no_compliance_signal_detected"
        assert result["source_agent"] == "compliance.remediation"

    def test_disallowed_transition_returns_error(self):
        result = handoff_to_agent.execute(
            _ctx(agent_id="compliance.transactional"),
            target_agent="compliance.remediation",
            reason="back_to_aml",
        )
        assert result.get("error") == "handoff_not_allowed"
        assert result["allowed"] == []

    def test_missing_target_rejected(self):
        result = handoff_to_agent.execute(
            _ctx(agent_id="compliance.remediation"),
            target_agent="",
            reason="empty",
        )
        assert result.get("error") == "missing_target_agent"

    def test_missing_reason_rejected(self):
        result = handoff_to_agent.execute(
            _ctx(agent_id="compliance.remediation"),
            target_agent="compliance.general",
            reason="",
        )
        assert result.get("error") == "missing_reason"
