"""Tests unitaires Phase 2 wiki v1.4 patch — hot-path router follow-up.

Couvre :
  * `should_skip_router` — matrice de cas (positifs/négatifs) :
      - longueur du message, agent précédent, agent_hint, signaux
        de changement de sujet, kill-switch env var.
  * `extract_last_assistant_agent` — parsing de `recent_turns`.
  * `has_topic_change_signal` / `has_deictic` — heuristiques.

Cas réel ayant motivé la fonctionnalité : conv `5bef01e9` 2026-05-04,
turn 3 où le LLM router a routé sur `market` après que l'agent `product`
a répondu sur le bundle TOP_5, alors que le user a envoyé « précisément
les perf sont bonne sur ce bundle ? » (28 chars, déictique fort).
"""

from __future__ import annotations

import pytest

from services.assistance.agents.base import AgentInput, RouterDecision
from services.assistance.router_hot_path import (
    EXPERT_AGENTS_FOR_HOT_PATH,
    extract_last_assistant_agent,
    has_deictic,
    has_personalized_advice_signal,
    has_topic_change_signal,
    len_of_prior_assistant_reply,
    should_skip_router,
    should_skip_router_from_input,
)


# ─────────────────────────────────────────────────────────────────────
# extract_last_assistant_agent
# ─────────────────────────────────────────────────────────────────────


class TestExtractLastAssistantAgent:
    def test_returns_last_assistant_agent_used(self):
        turns = [
            {"role": "user", "content": "salut"},
            {"role": "assistant", "content": "Bonjour", "agent_used": "default"},
            {"role": "user", "content": "Top 5 ?"},
            {"role": "assistant", "content": "Voici TOP_5", "agent_used": "product"},
        ]
        assert extract_last_assistant_agent(turns) == "product"

    def test_returns_none_when_empty(self):
        assert extract_last_assistant_agent([]) is None
        assert extract_last_assistant_agent(None) is None

    def test_returns_none_when_no_assistant(self):
        turns = [{"role": "user", "content": "hello"}]
        assert extract_last_assistant_agent(turns) is None

    def test_returns_none_when_legacy_message_without_agent_used(self):
        """Conv pré-migration 147 : `agent_used` absent → on retourne
        None (le hot-path se désactive naturellement)."""
        turns = [
            {"role": "user", "content": "x"},
            {"role": "assistant", "content": "y"},  # pas d'agent_used
        ]
        assert extract_last_assistant_agent(turns) is None

    def test_skips_user_messages_at_end(self):
        turns = [
            {"role": "assistant", "content": "x", "agent_used": "advisor"},
            {"role": "user", "content": "ok"},
            {"role": "user", "content": "et ?"},
        ]
        assert extract_last_assistant_agent(turns) == "advisor"


# ─────────────────────────────────────────────────────────────────────
# has_topic_change_signal
# ─────────────────────────────────────────────────────────────────────


class TestHasPersonalizedAdviceSignal:
    @pytest.mark.parametrize(
        "msg",
        [
            "quel placement me conseilles tu pour ma retraite ?",
            "quels placement me conseille tu pour ma retraite ?",
            "Que me recommandes-tu ?",
            "qu'est-ce que tu me conseilles sur le coffre ?",
            "What should I invest in for retirement?",
        ],
    )
    def test_detects(self, msg: str):
        assert has_personalized_advice_signal(msg) is True

    @pytest.mark.parametrize(
        "msg",
        [
            "perf de ce bundle ?",
            "c'est quoi le coffre flexible ?",
            "et les frais ?",
            "",
        ],
    )
    def test_does_not_trigger_on_product_followup(self, msg: str):
        assert has_personalized_advice_signal(msg) is False


class TestHasTopicChangeSignal:
    @pytest.mark.parametrize(
        "msg",
        [
            "Par contre, c'est quoi un IBAN ?",
            "par contre",
            "Sinon comment ça marche ?",
            "D'ailleurs, j'ai une autre question",
            "Au fait, mes frais c'est quoi ?",
            "Maintenant parlons des frais",
            "BTW, t'as les perf en EUR ?",
            "Another question please",
        ],
    )
    def test_detects_signal(self, msg: str):
        assert has_topic_change_signal(msg) is True

    @pytest.mark.parametrize(
        "msg",
        [
            "ce bundle ?",
            "perf ?",
            "et les perf ?",
            "il est risqué ?",
            "ça vaut le coup ?",
            "",
        ],
    )
    def test_does_not_detect_on_followup(self, msg: str):
        assert has_topic_change_signal(msg) is False


# ─────────────────────────────────────────────────────────────────────
# has_deictic
# ─────────────────────────────────────────────────────────────────────


class TestHasDeictic:
    @pytest.mark.parametrize(
        "msg",
        [
            "ce bundle est top",
            "et il vaut combien ?",
            "ses perf",
            "ça me va",
            "leurs allocations ?",
        ],
    )
    def test_detects(self, msg):
        assert has_deictic(msg) is True

    @pytest.mark.parametrize(
        "msg",
        [
            "perf TOP_5 ?",
            "TOP 5",
            "BTC vs ETH",
            "",
        ],
    )
    def test_does_not_detect(self, msg):
        assert has_deictic(msg) is False


# ─────────────────────────────────────────────────────────────────────
# should_skip_router — cas positifs
# ─────────────────────────────────────────────────────────────────────


class TestShouldSkipRouterPositive:
    def test_short_followup_keeps_product_agent(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true")
        decision = should_skip_router(
            user_message="précisément les perf sont bonnes sur ce bundle ?",
            last_assistant_agent="product",
        )
        assert decision is not None
        assert decision.agent_id == "product"
        assert decision.reasoning == "hot_path_short_followup"
        assert 0.5 < decision.confidence <= 1.0

    def test_short_followup_compliance(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true")
        decision = should_skip_router(
            user_message="et c'est combien ?",
            last_assistant_agent="compliance",
        )
        assert decision is not None
        assert decision.agent_id == "compliance"

    def test_normalizes_agent_id_lowercase(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true")
        decision = should_skip_router(
            user_message="ok ?",
            last_assistant_agent="Product",
        )
        assert decision is not None
        assert decision.agent_id == "product"


# ─────────────────────────────────────────────────────────────────────
# should_skip_router — cas négatifs
# ─────────────────────────────────────────────────────────────────────


class TestShouldSkipRouterNegative:
    def test_kill_switch_disabled(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "false")
        decision = should_skip_router(
            user_message="ce bundle ?",
            last_assistant_agent="product",
        )
        assert decision is None

    def test_no_previous_agent(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true")
        decision = should_skip_router(
            user_message="ce bundle ?",
            last_assistant_agent=None,
        )
        assert decision is None

    def test_previous_agent_default(self, monkeypatch):
        """`default` n'est pas un agent expert — pas de hot-path."""
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true")
        decision = should_skip_router(
            user_message="ce bundle ?",
            last_assistant_agent="default",
        )
        assert decision is None

    def test_previous_agent_router(self, monkeypatch):
        """`router` n'est pas un agent expert non plus."""
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true")
        decision = should_skip_router(
            user_message="ce bundle ?",
            last_assistant_agent="router",
        )
        assert decision is None

    def test_message_too_long(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true")
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_MAX_CHARS", "60")
        long_msg = "x" * 100
        decision = should_skip_router(
            user_message=long_msg,
            last_assistant_agent="product",
        )
        assert decision is None

    def test_topic_change_signal_blocks(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true")
        for msg in (
            "par contre c'est quoi un IBAN ?",
            "Sinon, mes frais ?",
            "Au fait, comment je retire ?",
        ):
            decision = should_skip_router(
                user_message=msg,
                last_assistant_agent="product",
            )
            assert decision is None, f"hot-path should NOT trigger on {msg!r}"

    def test_personalized_advice_signal_blocks(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true")
        decision = should_skip_router(
            user_message="quel placement me conseilles tu pour ma retraite ?",
            last_assistant_agent="product",
        )
        assert decision is None

    def test_agent_hint_present_blocks(self, monkeypatch):
        """Si le client a fourni un hint (clic QCM), `service.py` gère
        déjà la continuité — le hot-path ne doit pas se mêler."""
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true")
        decision = should_skip_router(
            user_message="ok",
            last_assistant_agent="product",
            agent_hint="advisor",
        )
        assert decision is None

    def test_empty_message_blocks(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true")
        for msg in ("", "   ", "\n\t"):
            decision = should_skip_router(
                user_message=msg,
                last_assistant_agent="product",
            )
            assert decision is None


# ─────────────────────────────────────────────────────────────────────
# should_skip_router_from_input — wrapper haut-niveau
# ─────────────────────────────────────────────────────────────────────


class TestShouldSkipRouterFromInput:
    def test_extracts_last_agent_and_decides(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true")
        ai = AgentInput(
            user_message="ses perf ?",
            recent_turns=[
                {"role": "user", "content": "Top 5 ?"},
                {
                    "role": "assistant",
                    "content": "Voici",
                    "agent_used": "product",
                },
            ],
            memory_state={},
        )
        decision = should_skip_router_from_input(ai)
        assert decision is not None
        assert decision.agent_id == "product"

    def test_long_prior_assistant_skips_hotpath_for_router(self, monkeypatch):
        """Question courte + dernier bot de fond → le superviseur décide."""
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true")
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_MIN_PRIOR_ASSISTANT_CHARS", "40")
        ai = AgentInput(
            user_message="sur quoi investir ?",
            recent_turns=[
                {"role": "user", "content": "rétaite"},
                {"role": "assistant", "content": "A" * 80, "agent_used": "product"},
                {"role": "user", "content": "sur quoi investir ?"},
            ],
            memory_state={},
        )
        assert should_skip_router_from_input(ai) is None

    def test_min_prior_zero_restores_legacy_hotpath(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true")
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_MIN_PRIOR_ASSISTANT_CHARS", "0")
        ai = AgentInput(
            user_message="ok",
            recent_turns=[
                {"role": "assistant", "content": "B" * 300, "agent_used": "product"},
                {"role": "user", "content": "ok"},
            ],
            memory_state={},
        )
        decision = should_skip_router_from_input(ai)
        assert decision is not None
        assert decision.agent_id == "product"

    def test_len_prior_assistant_ignores_trailing_user(self):
        turns = [
            {"role": "assistant", "content": "Z" * 50},
            {"role": "user", "content": "suite"},
        ]
        assert len_of_prior_assistant_reply(turns) == 50

    def test_len_prior_counts_enriched_choices_labels(self):
        turns = [
            {
                "role": "assistant",
                "content": "Suite ?",
                "message_type": "choices",
                "message_payload": {
                    "options": [
                        {"label": "Option A avec un libellé assez long"},
                        {"label": "Option B tout aussi longue pour le test"},
                    ]
                },
            },
            {"role": "user", "content": "ok"},
        ]
        assert len_of_prior_assistant_reply(turns) >= 40

    def test_returns_none_when_first_turn(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true")
        ai = AgentInput(
            user_message="bonjour",
            recent_turns=[],
            memory_state={},
        )
        assert should_skip_router_from_input(ai) is None


# ─────────────────────────────────────────────────────────────────────
# Sanity check du périmètre
# ─────────────────────────────────────────────────────────────────────


class TestExpertAgentsPerimeter:
    def test_includes_product(self):
        assert "product" in EXPERT_AGENTS_FOR_HOT_PATH

    def test_includes_compliance(self):
        assert "compliance" in EXPERT_AGENTS_FOR_HOT_PATH

    def test_excludes_default(self):
        assert "default" not in EXPERT_AGENTS_FOR_HOT_PATH

    def test_excludes_router(self):
        assert "router" not in EXPERT_AGENTS_FOR_HOT_PATH


# ─────────────────────────────────────────────────────────────────────
# Sanity du retour : doit être un RouterDecision exploitable par service.py
# ─────────────────────────────────────────────────────────────────────


class TestRouterDecisionShape:
    def test_returns_router_decision_instance(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_ROUTER_HOT_PATH_ENABLED", "true")
        decision = should_skip_router(
            user_message="ok",
            last_assistant_agent="product",
        )
        assert isinstance(decision, RouterDecision)
        # On expose les attributs requis par service.py.
        assert hasattr(decision, "agent_id")
        assert hasattr(decision, "confidence")
        assert hasattr(decision, "reasoning")
