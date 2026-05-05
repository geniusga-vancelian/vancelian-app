"""Tests router v2 — couverture e2e du ``classify(...)`` avec mock LLM
sur les 3 chemins de tool calls (route_to / ask_clarification /
redirect_off_topic) en intégrant les nouveautés Lot 1, 2 et 3.

Pas d'appel OpenAI réel.
"""

from __future__ import annotations

import json

import pytest

from services.assistance.agents import router as router_mod
from services.assistance.agents.base import AgentInput


# ─────────────────────────────────────────────────────────────────────
# Fabricators
# ─────────────────────────────────────────────────────────────────────


def _stub_message(tool_call: dict) -> dict:
    return {
        "role": "assistant",
        "content": "",
        "tool_calls": [tool_call],
    }


def _redirect_off_topic_call(bridge: str, options: list[dict] | None = None):
    args = {"bridge": bridge}
    if options is not None:
        args["options"] = options
    return {
        "id": "call_1",
        "type": "function",
        "function": {
            "name": "redirect_off_topic",
            "arguments": json.dumps(args),
        },
    }


def _ask_clarification_call(
    *,
    tag: str | None = None,
    prompt: str = "",
    options: list[dict] | None = None,
):
    args: dict = {"prompt": prompt, "options": options or []}
    if tag is not None:
        args["tag"] = tag
    return {
        "id": "call_2",
        "type": "function",
        "function": {
            "name": "ask_clarification",
            "arguments": json.dumps(args),
        },
    }


def _make_input(
    user_message: str = "hello",
    *,
    memory: dict | None = None,
    recent_turns: list[dict] | None = None,
):
    return AgentInput(
        user_message=user_message,
        recent_turns=recent_turns
        or [{"role": "user", "content": user_message}],
        memory_state=memory or {},
    )


# ─────────────────────────────────────────────────────────────────────
# Lot 1 — redirect_off_topic uses fixed options regardless of LLM output
# ─────────────────────────────────────────────────────────────────────


class TestRedirectOffTopicE2E:
    def test_classify_substitutes_fixed_options(self, monkeypatch):
        # Le LLM renvoie des options bidons → on doit avoir la liste fixe.
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                _redirect_off_topic_call(
                    "Sur la météo, ce n'est pas notre terrain.",
                    options=[
                        {"id": "fake", "label": "Foo"},
                    ],
                )
            ),
        )
        d = router_mod.classify(_make_input("parle moi de la pluie"))
        assert d.redirect_bridge is not None
        assert "météo" in d.redirect_bridge.lower()
        # 5 options fixes (pas de current_topic).
        assert len(d.fallback_choices) == 5
        ids = [c.id for c in d.fallback_choices]
        assert "fake" not in ids
        assert "compliance" in ids
        assert "product" in ids

    def test_classify_adds_resume_slot_when_topic_present(self, monkeypatch):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                _redirect_off_topic_call(
                    "Sur la cuisine, je ne pourrai pas t'aider ici.",
                )
            ),
        )
        d = router_mod.classify(
            _make_input(
                "tu as une recette ?",
                memory={
                    "current_topic": {"product_code": "TOP_5"},
                },
            )
        )
        # Resume + 5 fixed = 6 options.
        assert len(d.fallback_choices) == 6
        assert d.fallback_choices[0].id == "resume_topic"
        assert "TOP_5" in d.fallback_choices[0].label


# ─────────────────────────────────────────────────────────────────────
# Lot 2 — intent_classification attached to RouterDecision
# ─────────────────────────────────────────────────────────────────────


class TestIntentClassificationAttached:
    def test_route_to_with_known_keyword_attaches_classification(
        self, monkeypatch
    ):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                {
                    "id": "c",
                    "type": "function",
                    "function": {
                        "name": "route_to",
                        "arguments": json.dumps(
                            {
                                "agent_id": "product",
                                "confidence": 0.9,
                                "reasoning": "bundle nommé",
                            }
                        ),
                    },
                }
            ),
        )
        d = router_mod.classify(_make_input("parle moi des bundle"))
        assert d.intent_classification is not None
        assert d.intent_classification["primary_tag"] == "bundle_crypto"
        assert d.intent_classification["family"] == "investir"
        assert d.intent_classification["scope_level"] == 2

    def test_no_keyword_match_no_classification(self, monkeypatch):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                {
                    "id": "c",
                    "type": "function",
                    "function": {
                        "name": "route_to",
                        "arguments": json.dumps(
                            {
                                "agent_id": "default",
                                "confidence": 0.6,
                                "reasoning": "salutation",
                            }
                        ),
                    },
                }
            ),
        )
        d = router_mod.classify(_make_input("xyz qqqq"))
        # Aucun keyword reconnu → pas de classification attachée.
        assert d.intent_classification is None


# ─────────────────────────────────────────────────────────────────────
# Lot 3 — ask_clarification(tag=...) substitutes options from catalog
# ─────────────────────────────────────────────────────────────────────


class TestClarificationCatalogE2E:
    def test_tag_known_uses_catalog_options(self, monkeypatch):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                _ask_clarification_call(
                    tag="epargner",
                    prompt="ignored llm prompt",
                    options=[{"id": "default", "label": "ignored"}],
                )
            ),
        )
        monkeypatch.setenv("ASSISTANCE_ROUTER_CONFIDENCE_MIN", "0.5")
        d = router_mod.classify(_make_input("j'aimerais bien épargner"))
        assert d.is_decisive is False
        # 3 options canoniques pour epargner.
        assert len(d.fallback_choices) == 3
        # Le prompt vient du catalogue.
        assert "épargne" in d.reasoning.lower()
        ids = {c.id for c in d.fallback_choices}
        assert "product" in ids
        assert "advisor" in ids

    def test_tag_unknown_uses_llm_options(self, monkeypatch):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                _ask_clarification_call(
                    tag="zzz_nope",
                    prompt="Custom LLM prompt",
                    options=[
                        {"id": "advisor", "label": "Custom A"},
                        {"id": "market", "label": "Custom B"},
                    ],
                )
            ),
        )
        monkeypatch.setenv("ASSISTANCE_ROUTER_CONFIDENCE_MIN", "0.5")
        d = router_mod.classify(_make_input("question floue"))
        assert d.reasoning == "Custom LLM prompt"
        assert len(d.fallback_choices) == 2

    def test_no_tag_works_as_legacy(self, monkeypatch):
        monkeypatch.setattr(
            router_mod,
            "chat_completion_with_tools",
            lambda *a, **kw: _stub_message(
                _ask_clarification_call(
                    prompt="Quel angle ?",
                    options=[
                        {"id": "compliance", "label": "Mon compte"},
                    ],
                )
            ),
        )
        monkeypatch.setenv("ASSISTANCE_ROUTER_CONFIDENCE_MIN", "0.5")
        d = router_mod.classify(_make_input("question vague"))
        assert d.reasoning == "Quel angle ?"
        assert len(d.fallback_choices) == 1
