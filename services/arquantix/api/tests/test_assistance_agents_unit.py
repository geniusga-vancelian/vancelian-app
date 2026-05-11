"""Tests unitaires Phase 1 multi-agents — router + registry + QCM builder.

Pas d'appel OpenAI réel ici : on monkeypatch `chat_completion_with_tools`
pour simuler les réponses LLM et tester le parsing / la sanitization.

Cf. `docs/arquantix/MULTI_AGENTS.md` § 7.
"""

from __future__ import annotations

import json

import pytest

from services.assistance.agents import registry, router as router_mod
from services.assistance.agents.base import (
    AGENT_ACTION_ID,
    AGENT_ADVISOR_ID,
    AGENT_COMPLIANCE_ID,
    AGENT_DEFAULT_ID,
    AGENT_MARKET_ID,
    AGENT_PRODUCT_ID,
    AGENT_ROUTER_ID,
    KNOWN_AGENT_IDS,
    RESUME_TOPIC_HINT_ID,
    AgentInput,
    ChoiceOption,
    RouterDecision,
)
from services.assistance.agents.config import (
    assistance_agent_model,
    assistance_agent_temperature,
    assistance_multi_agent_enabled,
    assistance_router_confidence_min,
    assistance_router_temperature,
)


# ── Config / env vars ───────────────────────────────────────────────────


class TestConfig:
    def test_multi_agent_enabled_default_true(self, monkeypatch):
        monkeypatch.delenv("ASSISTANCE_MULTI_AGENT_ENABLED", raising=False)
        assert assistance_multi_agent_enabled() is True

    @pytest.mark.parametrize("val", ["false", "0", "no", "off", "FALSE"])
    def test_multi_agent_disabled_falsy(self, monkeypatch, val):
        monkeypatch.setenv("ASSISTANCE_MULTI_AGENT_ENABLED", val)
        assert assistance_multi_agent_enabled() is False

    @pytest.mark.parametrize("val", ["true", "1", "yes", "on", "TRUE"])
    def test_multi_agent_enabled_truthy(self, monkeypatch, val):
        monkeypatch.setenv("ASSISTANCE_MULTI_AGENT_ENABLED", val)
        assert assistance_multi_agent_enabled() is True

    def test_router_confidence_min_default(self, monkeypatch):
        monkeypatch.delenv("ASSISTANCE_ROUTER_CONFIDENCE_MIN", raising=False)
        assert assistance_router_confidence_min() == 0.5

    def test_router_confidence_min_custom(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_CONFIDENCE_MIN", "0.7")
        assert assistance_router_confidence_min() == 0.7

    @pytest.mark.parametrize("bad", ["abc", "-0.1", "1.5", ""])
    def test_router_confidence_min_invalid_falls_back(self, monkeypatch, bad):
        monkeypatch.setenv("ASSISTANCE_ROUTER_CONFIDENCE_MIN", bad)
        assert assistance_router_confidence_min() == 0.5

    def test_router_temperature_clamp(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_TEMPERATURE", "5.0")
        assert assistance_router_temperature() == 2.0
        monkeypatch.setenv("ASSISTANCE_ROUTER_TEMPERATURE", "-1.0")
        assert assistance_router_temperature() == 0.0

    def test_agent_model_resolution_priority(self, monkeypatch):
        # 1. Var spécifique gagne sur tout.
        monkeypatch.setenv("ASSISTANCE_AGENT_ADVISOR_MODEL", "gpt-4o")
        monkeypatch.setenv("ASSISTANCE_OPENAI_MODEL", "gpt-3.5")
        assert assistance_agent_model("advisor") == "gpt-4o"
        # 2. Sans la spécifique, fallback sur ASSISTANCE_OPENAI_MODEL.
        monkeypatch.delenv("ASSISTANCE_AGENT_ADVISOR_MODEL", raising=False)
        assert assistance_agent_model("advisor") == "gpt-3.5"

    def test_agent_temperature_per_agent(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_AGENT_COMPLIANCE_TEMPERATURE", "0.0")
        assert assistance_agent_temperature("compliance", default=0.7) == 0.0
        # Default si var absente.
        monkeypatch.delenv("ASSISTANCE_AGENT_COMPLIANCE_TEMPERATURE", raising=False)
        assert assistance_agent_temperature("compliance", default=0.3) == 0.3


# ── Registry ────────────────────────────────────────────────────────────


class TestRegistry:
    def test_get_default_agent(self):
        a = registry.get_agent(AGENT_DEFAULT_ID)
        assert a.agent_id == AGENT_DEFAULT_ID

    def test_get_compliance_agent_with_client_id(self):
        a = registry.get_agent(AGENT_COMPLIANCE_ID, client_id="abcd-uuid")
        assert a.agent_id == AGENT_COMPLIANCE_ID
        assert a._client_id == "abcd-uuid"  # noqa: SLF001 — testing internal

    def test_get_advisor_agent_with_client_id(self):
        a = registry.get_agent(AGENT_ADVISOR_ID, client_id="abcd-uuid")
        assert a.agent_id == AGENT_ADVISOR_ID
        assert a._client_id == "abcd-uuid"

    def test_get_product_agent_no_client_id_needed(self):
        a = registry.get_agent(AGENT_PRODUCT_ID)
        assert a.agent_id == AGENT_PRODUCT_ID

    def test_get_market_agent(self):
        a = registry.get_agent(AGENT_MARKET_ID)
        assert a.agent_id == AGENT_MARKET_ID

    def test_get_unknown_agent_raises(self):
        with pytest.raises(ValueError):
            registry.get_agent("does_not_exist")


# ── RouterDecision dataclass ────────────────────────────────────────────


class TestRouterDecision:
    def test_is_decisive_true_above_threshold(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_CONFIDENCE_MIN", "0.5")
        d = RouterDecision(agent_id=AGENT_ADVISOR_ID, confidence=0.8)
        assert d.is_decisive is True

    def test_is_decisive_false_below_threshold(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_CONFIDENCE_MIN", "0.5")
        d = RouterDecision(agent_id=AGENT_DEFAULT_ID, confidence=0.3)
        assert d.is_decisive is False

    def test_is_decisive_at_threshold_inclusive(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_CONFIDENCE_MIN", "0.5")
        d = RouterDecision(agent_id=AGENT_DEFAULT_ID, confidence=0.5)
        assert d.is_decisive is True

    def test_to_log_dict_round_confidence(self):
        d = RouterDecision(
            agent_id=AGENT_COMPLIANCE_ID,
            confidence=0.87654321,
            reasoning="parce que",
        )
        log = d.to_log_dict()
        assert log["agent_id"] == AGENT_COMPLIANCE_ID
        assert log["confidence"] == 0.877
        assert log["reasoning"] == "parce que"
        assert log["off_topic"] is False

    def test_is_off_topic_false_by_default(self):
        d = RouterDecision(agent_id=AGENT_ADVISOR_ID, confidence=0.9)
        assert d.is_off_topic is False

    def test_is_off_topic_true_when_bridge_set(self):
        d = RouterDecision(
            agent_id=AGENT_DEFAULT_ID,
            confidence=0.49,
            redirect_bridge="On parlait de ton allocation, on y revient ?",
        )
        assert d.is_off_topic is True
        assert d.to_log_dict()["off_topic"] is True


# ── ChoiceOption ────────────────────────────────────────────────────────


class TestChoiceOption:
    def test_to_dict(self):
        c = ChoiceOption(id="compliance", label="Mon compte")
        assert c.to_dict() == {"id": "compliance", "label": "Mon compte"}


# ── Router : parsing tool calls ─────────────────────────────────────────


def _stub_message(tool_calls):
    """Construit une réponse OpenAI mockée."""
    return {"role": "assistant", "content": None, "tool_calls": tool_calls}


def _route_to_call(agent_id, confidence, reasoning="r"):
    return [
        {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "route_to",
                "arguments": json.dumps(
                    {
                        "agent_id": agent_id,
                        "confidence": confidence,
                        "reasoning": reasoning,
                    }
                ),
            },
        }
    ]


def _ask_clarification_call(prompt, options):
    return [
        {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "ask_clarification",
                "arguments": json.dumps(
                    {"prompt": prompt, "options": options}
                ),
            },
        }
    ]


def _redirect_off_topic_call(bridge, options=None):
    args = {"bridge": bridge}
    if options is not None:
        args["options"] = options
    return [
        {
            "id": "call_1",
            "type": "function",
            "function": {
                "name": "redirect_off_topic",
                "arguments": json.dumps(args),
            },
        }
    ]


def _make_input():
    return AgentInput(
        user_message="hello",
        recent_turns=[{"role": "user", "content": "hello"}],
        memory_state={},
    )


class TestRouterClassify:
    def test_route_to_compliance_high_confidence(self, monkeypatch):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                _route_to_call(AGENT_COMPLIANCE_ID, 0.92, "blocked deposit")
            ),
        )
        d = router_mod.classify(_make_input())
        assert d.agent_id == AGENT_COMPLIANCE_ID
        assert d.confidence == 0.92
        assert d.reasoning == "blocked deposit"
        assert d.fallback_choices == []

    def test_route_to_unknown_agent_falls_back_to_default(self, monkeypatch):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(_route_to_call("hacker", 0.99)),
        )
        d = router_mod.classify(_make_input())
        assert d.agent_id == AGENT_DEFAULT_ID

    def test_route_to_confidence_clamped(self, monkeypatch):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(_route_to_call(AGENT_MARKET_ID, 1.5)),
        )
        d = router_mod.classify(_make_input())
        assert d.confidence == 1.0

    def test_route_to_negative_confidence_clamped_to_zero(self, monkeypatch):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(_route_to_call(AGENT_PRODUCT_ID, -0.3)),
        )
        d = router_mod.classify(_make_input())
        assert d.confidence == 0.0

    def test_ask_clarification_with_valid_options(self, monkeypatch):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                _ask_clarification_call(
                    "Précise s'il te plaît",
                    [
                        {"id": "compliance", "label": "Mon compte"},
                        {"id": "advisor", "label": "Conseil placement"},
                    ],
                )
            ),
        )
        monkeypatch.setenv("ASSISTANCE_ROUTER_CONFIDENCE_MIN", "0.5")
        d = router_mod.classify(_make_input())
        assert d.agent_id == AGENT_DEFAULT_ID  # placeholder
        assert d.is_decisive is False  # forcera le QCM
        assert len(d.fallback_choices) == 2
        assert d.fallback_choices[0].id == "compliance"
        assert d.reasoning == "Précise s'il te plaît"

    def test_ask_clarification_invalid_options_falls_back_default(self, monkeypatch):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                _ask_clarification_call(
                    "?",
                    [
                        {"id": "fakeagent", "label": "X"},  # id invalide
                        {"id": "another", "label": ""},  # label vide
                    ],
                )
            ),
        )
        d = router_mod.classify(_make_input())
        assert d.agent_id == AGENT_DEFAULT_ID
        assert d.fallback_choices == []
        assert d.reasoning == "ask_clarification_no_valid_options"

    def test_ask_clarification_dedupes_options(self, monkeypatch):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                _ask_clarification_call(
                    "?",
                    [
                        {"id": "compliance", "label": "A"},
                        {"id": "compliance", "label": "B"},  # doublon → ignoré
                        {"id": "advisor", "label": "C"},
                    ],
                )
            ),
        )
        d = router_mod.classify(_make_input())
        assert len(d.fallback_choices) == 2
        assert d.fallback_choices[0].label == "A"

    def test_router_no_tool_call_falls_back_default(self, monkeypatch):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: {
                "role": "assistant",
                "content": "I refuse",
                "tool_calls": [],
            },
        )
        d = router_mod.classify(_make_input())
        assert d.agent_id == AGENT_DEFAULT_ID
        assert d.confidence == 0.0
        assert d.reasoning == "router_no_tool_call"

    def test_router_invalid_args_falls_back_default(self, monkeypatch):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                [
                    {
                        "function": {
                            "name": "route_to",
                            "arguments": "not json {{{",
                        }
                    }
                ]
            ),
        )
        d = router_mod.classify(_make_input())
        assert d.agent_id == AGENT_DEFAULT_ID
        assert d.reasoning == "router_invalid_args"

    def test_router_unknown_function_falls_back_default(self, monkeypatch):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                [{"function": {"name": "drop_database", "arguments": "{}"}}]
            ),
        )
        d = router_mod.classify(_make_input())
        assert d.agent_id == AGENT_DEFAULT_ID
        assert "router_unknown_function" in d.reasoning

    def test_router_llm_error_falls_back_default(self, monkeypatch):
        from services.assistance.llm import LLMError

        def _raises(*a, **kw):
            raise LLMError("upstream_status_500")

        monkeypatch.setattr(router_mod, "chat_completion_with_tools", _raises)
        d = router_mod.classify(_make_input())
        assert d.agent_id == AGENT_DEFAULT_ID
        assert d.confidence == 0.0
        assert d.reasoning == "router_llm_failed"


# ── Router : garde-fou transactionnel (court-circuit avant LLM) ───────────


class TestTransactionalRouteGuard:
    def test_crypto_buy_explicit_short_circuits_without_llm(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_CRYPTO_INVESTMENT_INTENT_V1_ONLY", "false")

        def _never_call_llm(*_a, **_kw):
            raise AssertionError("LLM must not be called when guard matches")

        monkeypatch.setattr(router_mod, "chat_completion_with_tools", _never_call_llm)
        inp = AgentInput(
            user_message="Je veux acheter du Bitcoin pour 1000 €",
            recent_turns=[
                {"role": "user", "content": "Je veux acheter du Bitcoin pour 1000 €"}
            ],
            memory_state={},
        )
        d = router_mod.classify(inp)
        assert d.agent_id == AGENT_ACTION_ID
        assert d.is_decisive is True
        assert "transactional_guard:crypto_buy" in d.reasoning
        orch = d.orchestration or {}
        assert orch.get("business_intent") == "action_request"
        assert orch.get("transaction_kind") == "crypto_buy"
        assert orch.get("routing_confidence") == pytest.approx(0.95)

    def test_advisory_buy_question_not_short_circuited(self):
        """« Dois-je acheter » reste hors garde ; le LLM doit trancher."""
        assert router_mod._transactional_route_guard(
            "dois-je acheter du bitcoin pour ma retraite ?"
        ) is None

    def test_blocked_deposit_not_action_deposit(self):
        assert router_mod._transactional_route_guard(
            "mon dépôt est bloqué depuis hier"
        ) is None

    def test_generic_crypto_no_named_asset_not_short_circuited(self):
        """« Crypto » seul : éducation / flou — laisser le routeur LLM décider."""
        assert (
            router_mod._transactional_route_guard(
                "je veux acheter de la crypto avec 500 €"
            )
            is None
        )

    def test_exclusive_offer_buy_not_short_circuited(self):
        assert (
            router_mod._transactional_route_guard(
                "achète-moi une offre exclusive en bitcoin pour 500 €"
            )
            is None
        )

    def test_crypto_investment_intent_when_v1_only_flag(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_CRYPTO_INVESTMENT_INTENT_V1_ONLY", "true")
        d = router_mod._transactional_route_guard(
            "Je veux acheter du bitcoin pour 1000 €",
        )
        assert d is not None
        assert d.agent_id == AGENT_ACTION_ID
        orch = d.orchestration or {}
        assert orch.get("transaction_kind") == "crypto_investment_intent"
        assert orch.get("routing_confidence") == pytest.approx(0.95)

    def test_investis_usdc_into_eth_crypto_intent(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_CRYPTO_INVESTMENT_INTENT_V1_ONLY", "true")
        d = router_mod._transactional_route_guard(
            "Investis tout mon USDC en ETH",
        )
        assert d is not None
        orch = d.orchestration or {}
        assert orch.get("transaction_kind") == "crypto_investment_intent"
        assert orch.get("routing_confidence") == pytest.approx(0.93)

    def test_convertir_usdc_en_eth_swaps_not_intent(self):
        d = router_mod._transactional_route_guard(
            "je veux convertir mes USDC en ETH",
        )
        assert d is not None
        orch = d.orchestration or {}
        assert orch.get("transaction_kind") == "crypto_swap"
        assert orch.get("routing_confidence") == pytest.approx(0.91)


# ── Router : redirect_off_topic (règle 6) ───────────────────────────────


class TestRouterRedirectOffTopic:
    def test_off_topic_with_bridge_and_options(self, monkeypatch):
        """Cas : pas d'historique, message client = « pluie et beau temps ».

        Router v2 (Lot 1) : peu importe les options envoyées par le LLM,
        le runtime substitue par la liste FIXE
        (cf. `router_off_topic_options.OFF_TOPIC_FIXED_OPTIONS`).
        """
        monkeypatch.setenv("ASSISTANCE_ROUTER_CONFIDENCE_MIN", "0.5")
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                _redirect_off_topic_call(
                    "Sur la pluie et le beau temps, je ne pourrai pas "
                    "t'éclairer ici — cet espace est dédié à ton compte "
                    "Vancelian, tes placements et nos produits. Tu veux "
                    "qu'on regarde quelque chose de ce côté ?",
                    # Les options envoyées par le LLM sont ignorées
                    # depuis Router v2 — on les laisse présentes ici
                    # pour vérifier qu'elles ne pollutent PAS le résultat.
                    [
                        {"id": "compliance", "label": "Mon compte"},
                        {"id": "advisor", "label": "Conseil placement"},
                    ],
                )
            ),
        )
        d = router_mod.classify(_make_input())
        assert d.agent_id == AGENT_DEFAULT_ID  # placeholder
        assert d.is_off_topic is True
        assert d.is_decisive is False  # forcera le path choices
        assert "pluie" in d.redirect_bridge.lower()
        assert "vancelian" in d.redirect_bridge.lower()
        assert d.reasoning == "off_topic_redirect"
        # Liste FIXE Router v2 = 5 entrées.
        assert len(d.fallback_choices) == 5
        ids = {o.id for o in d.fallback_choices}
        assert "compliance" in ids
        assert "advisor" in ids
        assert "product" in ids
        assert "market" in ids

    def test_off_topic_with_resume_topic_option(self, monkeypatch):
        """Router v2 — le slot `resume_topic` est ajouté par le runtime
        depuis `memory_state["current_topic"]`, plus par le LLM.
        """
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                _redirect_off_topic_call(
                    "Pour le tiramisu, je vais devoir te laisser chercher "
                    "ailleurs ! Ici on est plutôt sur ton compte et tes "
                    "placements Vancelian — et on était justement en train "
                    "de regarder ton allocation, on y revient ?",
                )
            ),
        )
        # current_topic présent en mémoire → resume_topic doit
        # apparaître en 1ʳᵉ position du QCM.
        agent_input = _make_input()
        agent_input.memory_state = {
            "current_topic": {"display_label": "l'allocation"}
        }
        d = router_mod.classify(agent_input)
        assert d.is_off_topic is True
        assert "tiramisu" in d.redirect_bridge.lower()
        # 1 resume + 5 fixes = 6 options.
        assert len(d.fallback_choices) == 6
        assert d.fallback_choices[0].id == RESUME_TOPIC_HINT_ID
        assert "allocation" in d.fallback_choices[0].label.lower()

    def test_off_topic_without_options(self, monkeypatch):
        """Router v2 — même sans options du LLM, la liste fixe est appliquée.

        Le LLM peut très bien ne plus passer d'options du tout (c'est
        d'ailleurs ce que le tool spec v2 attend) — le runtime fournit
        la liste fixe complète.
        """
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                _redirect_off_topic_call(
                    "Pour les blagues, ce n'est pas vraiment la place : "
                    "cet espace est fait pour parler finance, compte et "
                    "placements Vancelian. Sur quoi puis-je t'aider ?",
                )
            ),
        )
        d = router_mod.classify(_make_input())
        assert d.is_off_topic is True
        # Router v2 — 5 options fixes même sans options envoyées.
        assert len(d.fallback_choices) == 5
        assert "blagues" in d.redirect_bridge.lower()
        assert "vancelian" in d.redirect_bridge.lower()

    def test_off_topic_empty_bridge_falls_back_default(self, monkeypatch):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                _redirect_off_topic_call("   ", [{"id": "advisor", "label": "X"}])
            ),
        )
        d = router_mod.classify(_make_input())
        assert d.agent_id == AGENT_DEFAULT_ID
        assert d.is_off_topic is False
        assert d.confidence == 0.0
        assert d.reasoning == "redirect_off_topic_no_bridge"

    def test_off_topic_invalid_option_id_filtered_out(self, monkeypatch):
        """Router v2 — les options du LLM sont **totalement ignorées**,
        donc des `id` invalides ne peuvent plus passer. La liste fixe
        ne contient que des agents whitelist.
        """
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                _redirect_off_topic_call(
                    "Recentrons.",
                    [
                        {"id": "router", "label": "X"},
                        {"id": "freeform", "label": "Y"},
                        {"id": "advisor", "label": "Conseil"},
                    ],
                )
            ),
        )
        d = router_mod.classify(_make_input())
        assert d.is_off_topic is True
        # Aucun id "router" ou "freeform" — on a la liste fixe.
        ids = {o.id for o in d.fallback_choices}
        assert "router" not in ids
        assert "freeform" not in ids
        assert ids.issubset(
            {"compliance", "advisor", "product", "market", "resume_topic"}
        )

    def test_off_topic_dedupes_options(self, monkeypatch):
        """Router v2 — la liste fixe est par construction dédupliquée
        sur le couple (id, label). On vérifie qu'aucun doublon ne
        se faufile peu importe ce que le LLM envoie.
        """
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                _redirect_off_topic_call(
                    "B",
                    [
                        {"id": "advisor", "label": "A"},
                        {"id": "advisor", "label": "A"},
                        {"id": "compliance", "label": "C"},
                    ],
                )
            ),
        )
        d = router_mod.classify(_make_input())
        # Liste fixe = 5 entrées, toutes uniques sur (id, label).
        pairs = [(o.id, o.label) for o in d.fallback_choices]
        assert len(pairs) == len(set(pairs))

    def test_off_topic_bridge_truncated_to_500(self, monkeypatch):
        long_bridge = "x" * 900
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                _redirect_off_topic_call(long_bridge)
            ),
        )
        d = router_mod.classify(_make_input())
        assert len(d.redirect_bridge) == 500


# ── _build_choices_payload (service.py) ─────────────────────────────────


class TestBuildChoicesPayload:
    def test_adds_freeform_option(self):
        from services.assistance.service import _build_choices_payload

        decision = RouterDecision(
            agent_id=AGENT_DEFAULT_ID,
            confidence=0.4,
            reasoning="Précise s'il te plaît",
            fallback_choices=[
                ChoiceOption(id="compliance", label="Mon compte"),
                ChoiceOption(id="advisor", label="Conseil placement"),
            ],
        )
        prompt, options, payload, fallback_text = _build_choices_payload(decision)
        assert prompt == "Précise s'il te plaît"
        # Freeform ajoutée.
        assert any(o.id == "freeform" for o in options)
        assert len(options) == 3
        assert payload["allow_freeform"] is True
        assert len(payload["options"]) == 3
        # Fallback texte contient prompt + 3 options numérotées.
        assert "Précise s'il te plaît" in fallback_text
        assert "1. Mon compte" in fallback_text
        assert "2. Conseil placement" in fallback_text
        assert "3. Rien de tout ça" in fallback_text

    def test_does_not_duplicate_freeform_when_already_present(self):
        from services.assistance.service import _build_choices_payload

        decision = RouterDecision(
            agent_id=AGENT_DEFAULT_ID,
            confidence=0.4,
            reasoning="?",
            fallback_choices=[
                ChoiceOption(id="compliance", label="Mon compte"),
                ChoiceOption(id="freeform", label="Custom freeform"),
            ],
        )
        _, options, _, _ = _build_choices_payload(decision)
        assert sum(1 for o in options if o.id == "freeform") == 1
        # Le label custom est conservé (on ne réécrit pas).
        freeform = next(o for o in options if o.id == "freeform")
        assert freeform.label == "Custom freeform"

    def test_default_prompt_when_reasoning_empty(self):
        from services.assistance.service import _build_choices_payload

        decision = RouterDecision(
            agent_id=AGENT_DEFAULT_ID,
            confidence=0.3,
            reasoning="",
            fallback_choices=[ChoiceOption(id="compliance", label="X")],
        )
        prompt, _, _, _ = _build_choices_payload(decision)
        assert "Pour mieux te répondre" in prompt

    def test_off_topic_bridge_takes_priority_over_reasoning(self):
        """Cas règle 6 : `redirect_bridge` doit gagner sur `reasoning`."""
        from services.assistance.service import _build_choices_payload

        decision = RouterDecision(
            agent_id=AGENT_DEFAULT_ID,
            confidence=0.49,
            reasoning="off_topic_redirect",  # technique, pas user-facing
            redirect_bridge="On parlait de ton allocation, on y revient ?",
            fallback_choices=[
                ChoiceOption(id="resume_topic", label="Reprendre l'allocation"),
            ],
        )
        prompt, options, payload, fallback_text = _build_choices_payload(decision)
        assert prompt == "On parlait de ton allocation, on y revient ?"
        # Le reasoning technique ne doit pas fuiter côté user-facing.
        assert "off_topic_redirect" not in prompt
        assert "off_topic_redirect" not in fallback_text
        # Freeform ajoutée même quand il n'y a qu'1 option de catégorie.
        assert any(o.id == "freeform" for o in options)
        assert payload["allow_freeform"] is True

    def test_off_topic_bridge_with_no_options(self):
        """Bridge seul → QCM avec uniquement le bridge + freeform."""
        from services.assistance.service import _build_choices_payload

        decision = RouterDecision(
            agent_id=AGENT_DEFAULT_ID,
            confidence=0.49,
            reasoning="off_topic_redirect",
            redirect_bridge="Je suis ton assistant Vancelian. Comment puis-je t'aider ?",
            fallback_choices=[],
        )
        prompt, options, _, fallback_text = _build_choices_payload(decision)
        assert prompt.startswith("Je suis ton assistant Vancelian")
        assert len(options) == 1
        assert options[0].id == "freeform"
        assert "1. Rien de tout ça" in fallback_text


# ── _resolve_resume_topic_hint (service.py) ─────────────────────────────


class TestResolveResumeTopicHint:
    """Lookup serveur-side de l'option `resume_topic` d'un QCM off-topic.

    Plutôt que de monter une vraie session SQLAlchemy, on mock l'API
    `query().filter().order_by().limit().scalar()` avec un fake léger.
    """

    def _fake_db(self, *, scalar_value):
        class _Q:
            def filter(self, *a, **kw):
                return self

            def order_by(self, *a, **kw):
                return self

            def limit(self, *a, **kw):
                return self

            def scalar(self):
                return scalar_value

        class _DB:
            def query(self, *a, **kw):
                return _Q()

        return _DB()

    def test_returns_last_specialist_agent(self):
        from uuid import uuid4

        from services.assistance.service import _resolve_resume_topic_hint

        db = self._fake_db(scalar_value="advisor")
        result = _resolve_resume_topic_hint(db, conversation_id=uuid4())
        assert result == "advisor"

    def test_returns_none_when_no_prior_specialist(self):
        from uuid import uuid4

        from services.assistance.service import _resolve_resume_topic_hint

        db = self._fake_db(scalar_value=None)
        assert _resolve_resume_topic_hint(db, conversation_id=uuid4()) is None

    def test_rejects_router_agent(self):
        """`router` n'est pas un sujet à reprendre."""
        from uuid import uuid4

        from services.assistance.service import _resolve_resume_topic_hint

        db = self._fake_db(scalar_value=AGENT_ROUTER_ID)
        # En théorie le filter SQL exclut déjà router, mais on garde
        # une garde défensive Python.
        assert _resolve_resume_topic_hint(db, conversation_id=uuid4()) is None

    def test_rejects_unknown_agent(self):
        from uuid import uuid4

        from services.assistance.service import _resolve_resume_topic_hint

        db = self._fake_db(scalar_value="hacker")
        assert _resolve_resume_topic_hint(db, conversation_id=uuid4()) is None


# ── _decide_agent — branche resume_topic ────────────────────────────────


class TestDecideAgentResumeTopic:
    def test_resume_topic_resolves_to_specialist(self, monkeypatch):
        from uuid import uuid4

        from services.assistance import service as svc

        monkeypatch.setattr(
            svc,
            "_resolve_resume_topic_hint",
            lambda db, *, conversation_id: "advisor",
        )
        d = svc._decide_agent(
            agent_input=_make_input(),
            agent_hint=RESUME_TOPIC_HINT_ID,
            conv_id=uuid4(),
            db=object(),  # juste non-None ; resolver mocké.
        )
        assert d.agent_id == AGENT_ADVISOR_ID
        assert d.confidence == 1.0
        assert d.reasoning == "resume_topic_resolved"

    def test_resume_topic_unresolved_falls_back_to_router(self, monkeypatch):
        """Pas de sujet à reprendre → on relance le router classique."""
        from uuid import uuid4

        from services.assistance import service as svc

        monkeypatch.setattr(
            svc,
            "_resolve_resume_topic_hint",
            lambda db, *, conversation_id: None,
        )
        # Le router "réel" doit être appelé : on le mock pour vérifier.
        called = {}

        def _fake_classify(agent_input):
            called["yes"] = True
            return RouterDecision(
                agent_id=AGENT_DEFAULT_ID,
                confidence=0.9,
                reasoning="from_router_after_unresolved_resume",
            )

        monkeypatch.setattr(svc.agent_router, "classify", _fake_classify)
        d = svc._decide_agent(
            agent_input=_make_input(),
            agent_hint=RESUME_TOPIC_HINT_ID,
            conv_id=uuid4(),
            db=object(),
        )
        assert called.get("yes") is True
        assert d.reasoning == "from_router_after_unresolved_resume"

    def test_resume_topic_without_db_falls_back_to_router(self, monkeypatch):
        from uuid import uuid4

        from services.assistance import service as svc

        called = {}

        def _fake_classify(agent_input):
            called["yes"] = True
            return RouterDecision(
                agent_id=AGENT_DEFAULT_ID,
                confidence=0.5,
                reasoning="r",
            )

        monkeypatch.setattr(svc.agent_router, "classify", _fake_classify)
        # db=None → on n'a pas de moyen de résoudre, on retombe sur le router
        # plutôt que de planter.
        svc._decide_agent(
            agent_input=_make_input(),
            agent_hint=RESUME_TOPIC_HINT_ID,
            conv_id=uuid4(),
            db=None,
        )
        assert called.get("yes") is True


# ── KNOWN_AGENT_IDS sanity ──────────────────────────────────────────────


class TestKnownAgentIds:
    def test_all_routable_in_known(self):
        for aid in router_mod.ROUTABLE_AGENTS:
            assert aid in KNOWN_AGENT_IDS

    def test_router_id_in_known_but_not_routable(self):
        assert AGENT_ROUTER_ID in KNOWN_AGENT_IDS
        assert AGENT_ROUTER_ID not in router_mod.ROUTABLE_AGENTS

    def test_off_topic_options_includes_specialists_and_resume(self):
        """`OFF_TOPIC_OPTION_IDS` = 4 agents experts + `resume_topic`.

        Notamment : `default` n'est PAS proposé (l'utilisateur est déjà
        en train d'être recentré, lui re-proposer la conversation libre
        n'a pas de sens), et `router` n'est jamais une option.
        """
        assert RESUME_TOPIC_HINT_ID in router_mod.OFF_TOPIC_OPTION_IDS
        assert AGENT_DEFAULT_ID not in router_mod.OFF_TOPIC_OPTION_IDS
        assert AGENT_ROUTER_ID not in router_mod.OFF_TOPIC_OPTION_IDS
        for aid in (
            AGENT_COMPLIANCE_ID,
            AGENT_ADVISOR_ID,
            AGENT_PRODUCT_ID,
            AGENT_MARKET_ID,
        ):
            assert aid in router_mod.OFF_TOPIC_OPTION_IDS


# ─────────────────────────────────────────────────────────────────────────
# Router prompt enrichments — Phase 2.6 (2026-05-04)
# Vocabulaire produit Vancelian + structure 3-niveaux explicite.
# Suite à la conv fbbf4f13 où "parle moi des bundle" a déclenché un QCM
# au lieu d'un routage direct vers l'agent product.
# ─────────────────────────────────────────────────────────────────────────


class TestRouterPromptVocabulary:
    """Le prompt système du router doit contenir le vocabulaire produit
    Vancelian propriétaire pour permettre un routage Niveau 1 (route_to
    direct) sans clarification quand un nom de produit propriétaire est
    cité par le client.

    Tests sur le **contenu textuel du fichier prompt** (déterministe).
    Les tests du comportement LLM réel sont par nature non-déterministes
    et donc hors scope de la suite unit.
    """

    @pytest.fixture
    def router_prompt(self) -> str:
        """Charge le prompt système router via le prompt_builder."""
        from services.assistance.agents.prompt_builder import (
            load_agent_system_prompt,
        )
        return load_agent_system_prompt("router")

    def test_three_levels_section_present(self, router_prompt: str):
        """La section explicite des 3 niveaux d'orchestration (Niveau 1 /
        Niveau 2 / Niveau 3) doit être présente en début de prompt."""
        # Section ajoutée 2026-05-04 (avant : structure dispersée dans les règles).
        assert "Les 3 niveaux d'orchestration" in router_prompt
        assert "Niveau 1 — Sujet identifié → routage direct" in router_prompt
        assert "Niveau 2 — Univers Vancelian mais ambigu → précision" in router_prompt
        assert "Niveau 3 — Hors univers Vancelian → recentrer" in router_prompt

    def test_action_app_first_preamble_present(self, router_prompt: str):
        """Préalable ACTION_APP_FIRST — achat crypto nommé doit aller sur action."""
        assert "ACTION_APP_FIRST" in router_prompt
        assert "m'aider à acheter" in router_prompt or "aider à acheter" in router_prompt
        assert "route_to(action" in router_prompt.lower() or "agent_id=\"action\"" in router_prompt

    def test_rule_0bis_present(self, router_prompt: str):
        """La règle 0bis (vocabulaire produit Vancelian) doit exister."""
        assert "0bis." in router_prompt
        assert "produit Vancelian propriétaire nommé" in router_prompt
        assert "PRIORITÉ ABSOLUE" in router_prompt

    @pytest.mark.parametrize(
        "vocab_term",
        [
            # Coffres
            "Coffre Flexible",
            "Coffre Avenir",
            "Flexible Vault",
            "Future Vault",
            # Crypto Baskets / Bundles (le cas qui a échoué dans la conv fbbf4f13)
            "Crypto Basket",
            "Bundle",
            "Crypto Bundle",
            # Exclusive offers
            "Exclusive Offer",
            "Cloud Mining",
            "Dubai Villa",
            # Loyalty
            "Privilege Club",
            "Vancelian Card",
        ],
    )
    def test_vocabulary_contains_product_term(
        self, router_prompt: str, vocab_term: str
    ):
        """Chaque terme produit Vancelian critique doit apparaître au
        moins une fois dans le prompt enrichi (sensibilité à la casse
        car les noms propres sont stables)."""
        assert vocab_term in router_prompt, (
            f"Le terme produit Vancelian '{vocab_term}' est absent du "
            f"prompt router — le LLM va manquer ce vocabulaire et "
            f"basculer en ask_clarification au lieu de route_to(product)."
        )

    def test_bundle_example_present(self, router_prompt: str):
        """L'exemple « parle moi des bundle » → product doit être
        documenté pour ancrer le LLM (cas réel de la conv fbbf4f13)."""
        assert "parle moi des bundle" in router_prompt
        # Et la justification doit citer le synonyme oral.
        assert (
            "synonyme oral" in router_prompt
            or "Bundle = Crypto Basket" in router_prompt
        )

    def test_coffre_flexible_example_present(self, router_prompt: str):
        """Idem pour Coffre Flexible — produit phare."""
        assert "coffre flexible" in router_prompt.lower()

    def test_anti_confusion_for_operational_questions(
        self, router_prompt: str
    ):
        """Le prompt doit clarifier la frontière product/compliance :
        si un terme produit est suivi d'un déterminant possessif +
        verbe opérationnel (« mon coffre n'est pas crédité »), router
        bascule sur compliance (règle 1), pas product."""
        assert (
            "mon coffre flexible n'est pas crédité" in router_prompt
            or "déterminant possessif" in router_prompt
        )

    def test_ambiguity_anti_confusion_section(self, router_prompt: str):
        """La règle anti-confusion entre les 3 niveaux doit être
        explicite (évite les faux Niveau 2 sur des Niveau 1)."""
        assert "anti-confusion" in router_prompt.lower()
        # Mention que le coût d'un Niveau 1 mal classé en Niveau 2 est élevé.
        assert (
            "doit reformuler" in router_prompt
            or "coût" in router_prompt.lower()
        )


class TestRouterPromptIntegrity:
    """Sanity checks du prompt complet — invariants à préserver."""

    @pytest.fixture
    def router_prompt(self) -> str:
        from services.assistance.agents.prompt_builder import (
            load_agent_system_prompt,
        )
        return load_agent_system_prompt("router")

    def test_prompt_loads_non_empty(self, router_prompt: str):
        assert len(router_prompt) > 1000  # ordre de grandeur attendu

    def test_three_tools_documented(self, router_prompt: str):
        """Les 3 tools doivent être nommés dans le prompt."""
        assert "route_to" in router_prompt
        assert "ask_clarification" in router_prompt
        assert "redirect_off_topic" in router_prompt

    def test_no_emoji_in_prompt(self, router_prompt: str):
        """Pas d'emoji dans le prompt système (style Vancelian)."""
        # Quelques emojis fréquents — on tolère les flèches → ↑ ↓ ✓ ✗.
        for forbidden in ("😀", "🚀", "💰", "🔥", "📊", "✨", "❌", "✅"):
            assert forbidden not in router_prompt


class TestRouterPromptProfileAdvisorAndContextualQcm:
    """Tests des enrichissements 2026-05-04 (lot 1) — l'agent advisor doit
    être route_to direct sur "le plus adapté à mon profil/besoin", et le
    QCM ask_clarification doit contextualiser ses labels sur le sujet en
    cours quand l'historique contient un produit Vancelian nommé.

    Cas réel ayant motivé l'enrichissement : conv e5133711 turn 3 où
    « quel bundle est il le plus adapté à mon profil ? » a été classé
    en QCM générique au lieu d'un route_to(advisor) direct.
    """

    @pytest.fixture
    def router_prompt(self) -> str:
        from services.assistance.agents.prompt_builder import (
            load_agent_system_prompt,
        )
        return load_agent_system_prompt("router")

    def test_profile_advisor_subrule_present(self, router_prompt: str):
        """La règle 2 doit expliquer que « lequel pour moi/mon profil »
        sur un produit Vancelian nommé bascule sur advisor (et non
        product, malgré la règle 0bis)."""
        assert "le plus adapté à mon profil" in router_prompt
        # La règle 2 doit primer sur la règle 0bis dans ce cas. Test
        # robuste à la mise en forme : on compare le prompt entièrement
        # « unwrapé » (whitespace collapsé) pour tolérer les sauts de
        # ligne du markdown.
        import re
        flat = re.sub(r"\s+", " ", router_prompt.lower())
        assert "règle 2 prime sur la règle 0bis" in flat

    @pytest.mark.parametrize(
        "example_query",
        [
            "quel bundle est le plus adapté à mon profil ?",
            "quel coffre flexible me convient le mieux ?",
            "lequel de ces bundles je devrais choisir ?",
        ],
    )
    def test_profile_advisor_examples_present(
        self, router_prompt: str, example_query: str
    ):
        """Les 3 exemples calibrés (« le plus adapté à mon profil »,
        « me convient le mieux », « lequel je devrais choisir ») doivent
        figurer dans le bloc d'exemples route_to → advisor."""
        assert example_query in router_prompt
        # Et chacun doit clairement router vers advisor.
        idx = router_prompt.find(example_query)
        snippet = router_prompt[idx : idx + 400]
        assert "advisor" in snippet, (
            f"L'exemple '{example_query}' devrait router vers advisor "
            f"mais le snippet ne mentionne pas advisor : {snippet[:200]!r}"
        )

    def test_contextualization_rule_critical_marker(
        self, router_prompt: str
    ):
        """La règle critique « les labels d'options DOIVENT reprendre le
        sujet de recent_turns » doit être explicitement marquée comme
        critique pour que le LLM ne la zappe pas."""
        assert "Règle de contextualisation" in router_prompt
        # La criticité doit être marquée (sinon le LLM risque de la zapper).
        assert "CRITIQUE" in router_prompt

    def test_contextualization_anti_pattern_present(
        self, router_prompt: str
    ):
        """Le prompt doit contenir l'exemple ANTI (générique) ET BON
        (contextualisé bundle) pour ancrer le contraste."""
        # Anti-pattern : labels génériques recyclés malgré le contexte
        # bundle.
        assert "ne mentionne pas\n    bundle" in router_prompt or (
            "générique, ne mentionne pas" in router_prompt
        )
        # Pattern positif : labels qui reprennent « bundle ».
        assert "Adapter un bundle à mon profil" in router_prompt
        assert "Voir tous les bundles disponibles" in router_prompt
        assert "Comparer les performances des bundles" in router_prompt
