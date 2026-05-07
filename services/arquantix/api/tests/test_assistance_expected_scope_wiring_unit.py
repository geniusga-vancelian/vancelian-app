"""Tests — wiring `expected_answer_scope` dans `_build_choices_payload` (service)."""

from __future__ import annotations

from services.assistance.agents.base import ChoiceOption, RouterDecision
from services.assistance.agents.expected_answer_scope import EXPECTED_ANSWER_SCOPE_KEY
from services.assistance.service import _build_choices_payload


class TestBuildChoicesPayloadExpectedScope:
    def test_router_qcm_payload_has_expected_answer_scope(self):
        decision = RouterDecision(
            agent_id="router",
            confidence=0.2,
            reasoning="Tu veux parler de quoi ?",
            fallback_choices=[
                ChoiceOption(id="product", label="Produits"),
                ChoiceOption(id="compliance", label="Opérations"),
            ],
        )
        prompt, options, payload_dict, _fallback = _build_choices_payload(decision)
        assert "freeform" in {o.id for o in options}
        scope = payload_dict.get(EXPECTED_ANSWER_SCOPE_KEY)
        assert isinstance(scope, dict)
        assert scope["kind"] == "multiple_choice"
        assert scope["source"] == "router_qcm"
        assert scope["prompt_excerpt"].startswith(prompt[: min(len(prompt), 400)])
        ids = {c.get("id") for c in scope["choices"]}
        assert ids == {"product", "compliance"}
        assert "freeform" not in ids

    def test_freeform_only_in_runtime_options_not_in_scope_choices(self):
        decision = RouterDecision(
            agent_id="router",
            confidence=0.2,
            reasoning="?",
            fallback_choices=[ChoiceOption(id="only", label="Une option")],
        )
        _, _options, payload_dict, _ = _build_choices_payload(decision)
        scope = payload_dict[EXPECTED_ANSWER_SCOPE_KEY]
        assert len(scope["choices"]) == 1
        assert scope["choices"][0]["id"] == "only"
