"""Tests unitaires `consult_specialist` — Phase 2c.

Couvre l'étage **tool** (validation purpose + params + signal) :
  - purpose inconnu → error
  - target inconnu / mismatch → error
  - params manquants / invalides → error
  - cas nominal → `interrupt_with_consult=True` + payload validé

Le branchement runtime (sous-loop sandbox) est testé séparément dans
`test_assistance_orchestration_chain_unit.py`.

Spec : `services/assistance/agents/tools/shared/consult_specialist.py`.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from services.assistance.agents.tools.contracts import ToolContext
from services.assistance.agents.tools.shared import consult_specialist
from services.assistance.agents.tools.shared.classify_actor import ActorKind


def _ctx(*, agent_id: str = "compliance.transactional") -> ToolContext:
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
        correlation_id="t-consult",
    )


class TestConsultSpecialistExecute:
    def test_unknown_purpose_returns_error(self):
        result = consult_specialist.execute(
            _ctx(),
            target="product",
            purpose="explain_market_swing",
            params={"foo": "bar"},
        )
        assert result.get("error") == "unknown_purpose"
        assert "available_purposes" in result
        assert "explain_deposit_delay" in result["available_purposes"]

    def test_target_mismatch_rejected(self):
        # Tous les purposes Phase 2c ciblent "product" : si le LLM
        # demande un autre target, on rejette.
        result = consult_specialist.execute(
            _ctx(),
            target="advisor",
            purpose="explain_deposit_delay",
            params={"method": "card"},
        )
        assert result.get("error") == "target_mismatch"
        assert result["target_for_purpose"] == "product"

    def test_missing_required_param_rejected(self):
        result = consult_specialist.execute(
            _ctx(),
            target="product",
            purpose="explain_deposit_delay",
            params={},
        )
        assert result.get("error") == "invalid_params"
        assert "missing_required:method" in result["details"]

    def test_bad_value_param_rejected(self):
        result = consult_specialist.execute(
            _ctx(),
            target="product",
            purpose="explain_deposit_delay",
            params={"method": "paypal"},
        )
        assert result.get("error") == "invalid_params"
        assert "bad_value:method" in result["details"]

    def test_unknown_param_rejected(self):
        result = consult_specialist.execute(
            _ctx(),
            target="product",
            purpose="explain_deposit_delay",
            params={"method": "card", "extra": "leak"},
        )
        assert result.get("error") == "invalid_params"
        assert "unknown_param:extra" in result["details"]

    def test_nominal_returns_interrupt_with_consult(self):
        result = consult_specialist.execute(
            _ctx(),
            target="product",
            purpose="explain_deposit_delay",
            params={"method": "bank_transfer_in"},
        )
        assert result.get("interrupt_with_consult") is True
        assert result["target_agent"] == "product"
        assert result["purpose"] == "explain_deposit_delay"
        assert result["params"] == {"method": "bank_transfer_in"}
        assert "virement SEPA entrant" in result["question"]

    def test_nominal_kyc_no_params_required(self):
        result = consult_specialist.execute(
            _ctx(),
            target="product",
            purpose="explain_kyc_review_typical_delay",
            params=None,
        )
        assert result.get("interrupt_with_consult") is True
        assert result["params"] == {}
        assert result["question"]

    def test_target_normalized_lowercase(self):
        result = consult_specialist.execute(
            _ctx(),
            target="PRODUCT",
            purpose="explain_swap_settlement_delay",
            params={},
        )
        assert result.get("interrupt_with_consult") is True
        assert result["target_agent"] == "product"
