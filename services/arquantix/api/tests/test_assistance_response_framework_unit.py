"""Tests unitaires pour le Response Framework auto-injecté
(Cognitive Bot v4 — Lot 3).

Vérifient :
  * Le fragment ``_response_framework.md`` existe et contient les
    sections clés (4 temps, hiérarchie des signaux, interdits).
  * ``load_agent_system_prompt`` concatène le framework pour les agents
    listés dans ``RESPONSE_FRAMEWORK_AGENTS``.
  * L'agent ``product`` reçoit en plus le wiki ``index.md`` embarqué.
  * Le router et le summarizer N'ont PAS le framework concaténé.
  * Tous les agents experts utilisés en production sont bien dans la
    whitelist (sanity check anti-régression).
  * Le cache module-level fonctionne (N appels = 1 lecture disque).
"""

from __future__ import annotations

from pathlib import Path

import pytest

import services.assistance.agents.prompt_builder as prompt_builder
from services.assistance.agents.prompt_builder import (
    RESPONSE_FRAMEWORK_AGENTS,
    _load_response_framework_fragment,
    load_agent_system_prompt,
)


# ─────────────────────────────────────────────────────────────────────
# Fragment fichier
# ─────────────────────────────────────────────────────────────────────


class TestResponseFrameworkFragment:
    def test_fragment_file_exists(self):
        path = (
            Path(prompt_builder.__file__).resolve().parent.parent
            / "prompts"
            / "_response_framework.md"
        )
        assert path.exists(), f"missing fragment: {path}"

    def test_fragment_contains_4_step_structure(self):
        content = _load_response_framework_fragment()
        assert content is not None
        # Les 4 sections doivent être listées.
        assert "ACK émotionnel" in content
        assert "Reformulation intelligente" in content
        assert "Apport de valeur" in content
        assert "Next Best Action" in content

    def test_fragment_mentions_objective_block(self):
        content = _load_response_framework_fragment()
        assert content is not None
        assert "[OBJECTIVE]" in content
        assert "stop_pushing" in content

    def test_fragment_mentions_emotional_intents(self):
        content = _load_response_framework_fragment()
        assert content is not None
        for intent in ("fear", "anger", "curiosity", "compliance"):
            assert intent in content, (
                f"intent {intent} missing from response framework"
            )

    def test_fragment_lists_next_best_actions(self):
        content = _load_response_framework_fragment()
        assert content is not None
        for action in (
            "ask_question",
            "recommend",
            "call_to_action",
            "give_proof",
            "give_control",
            "micro_step",
        ):
            assert action in content, (
                f"action {action} missing from response framework"
            )

    def test_fragment_explicit_interdits(self):
        content = _load_response_framework_fragment()
        assert content is not None
        # « N'hésite pas… » est explicitement interdit (pattern passif).
        assert "N'hésite pas" in content or "n'hésite pas" in content
        assert "stop_pushing" in content


# ─────────────────────────────────────────────────────────────────────
# Whitelist — qui reçoit le framework
# ─────────────────────────────────────────────────────────────────────


class TestResponseFrameworkWhitelist:
    def test_expert_agents_in_whitelist(self):
        # Tous les agents experts qui produisent une réponse client.
        for agent_id in (
            "default",
            "advisor",
            "product",
            "market",
            "compliance.registration",
            "compliance.transactional",
            "compliance.general",
            "compliance.remediation",
        ):
            assert agent_id in RESPONSE_FRAMEWORK_AGENTS, (
                f"missing from whitelist: {agent_id}"
            )

    def test_router_not_in_whitelist(self):
        # Le router est function-calling pur, pas une réponse client.
        assert "router" not in RESPONSE_FRAMEWORK_AGENTS

    def test_summarizer_not_in_whitelist(self):
        # Le summarizer extrait du JSON, pas une réponse client.
        assert "summarizer" not in RESPONSE_FRAMEWORK_AGENTS

    def test_compliance_top_level_not_in_whitelist(self):
        # Top-level `compliance` est juste un dispatcher (appel
        # `diagnose_compliance_topic`). Il ne produit pas de réponse
        # client directement.
        assert "compliance" not in RESPONSE_FRAMEWORK_AGENTS


# ─────────────────────────────────────────────────────────────────────
# load_agent_system_prompt — concaténation
# ─────────────────────────────────────────────────────────────────────


class TestLoadAgentSystemPromptConcat:
    def test_advisor_prompt_includes_framework(self):
        prompt = load_agent_system_prompt("advisor")
        # Doit contenir au moins le titre du framework.
        assert "Pattern de réponse Cognitive Bot v4" in prompt
        assert "ACK émotionnel" in prompt

    def test_product_prompt_includes_framework(self):
        prompt = load_agent_system_prompt("product")
        assert "Pattern de réponse Cognitive Bot v4" in prompt

    def test_product_prompt_includes_wiki_index(self):
        prompt = load_agent_system_prompt("product")
        assert "Wiki — index.md (cartographie des pages)" in prompt
        assert "Vancelian Wiki — Index" in prompt

    def test_advisor_prompt_excludes_wiki_index_block(self):
        prompt = load_agent_system_prompt("advisor")
        assert "Wiki — index.md (cartographie des pages)" not in prompt

    def test_market_prompt_includes_framework(self):
        prompt = load_agent_system_prompt("market")
        assert "Pattern de réponse Cognitive Bot v4" in prompt

    def test_compliance_general_includes_framework(self):
        prompt = load_agent_system_prompt("compliance.general")
        assert "Pattern de réponse Cognitive Bot v4" in prompt

    def test_compliance_transactional_includes_framework(self):
        prompt = load_agent_system_prompt("compliance.transactional")
        assert "Pattern de réponse Cognitive Bot v4" in prompt

    def test_default_includes_framework(self):
        prompt = load_agent_system_prompt("default")
        assert "Pattern de réponse Cognitive Bot v4" in prompt

    def test_router_does_not_include_framework(self):
        prompt = load_agent_system_prompt("router")
        # Le router doit garder son prompt original SANS le framework
        # concaténé (sinon il perdrait des instructions de routing
        # cruciales en faveur d'un cadre de réponse qu'il n'utilise pas).
        assert "Pattern de réponse Cognitive Bot v4" not in prompt

    def test_compliance_top_level_does_not_include_framework(self):
        prompt = load_agent_system_prompt("compliance")
        # Top-level compliance = dispatcher pur, pas de framework
        # nécessaire (il sera ajouté pour les sub-agents).
        assert "Pattern de réponse Cognitive Bot v4" not in prompt

    def test_unknown_agent_uses_fallback_no_framework(self):
        # Un agent_id inconnu → fallback prompt + pas de framework
        # (puisque pas dans la whitelist).
        prompt = load_agent_system_prompt("__not_an_agent__")
        assert "assistant Vancelian" in prompt  # fallback identifiable
        assert "Pattern de réponse Cognitive Bot v4" not in prompt


# ─────────────────────────────────────────────────────────────────────
# Cache module-level
# ─────────────────────────────────────────────────────────────────────


class TestFrameworkCache:
    def test_cache_returns_same_content_twice(self):
        # Deux appels successifs doivent retourner le même contenu.
        a = _load_response_framework_fragment()
        b = _load_response_framework_fragment()
        assert a == b
        assert a is not None
        assert len(a) > 100  # sanity : fragment non-vide

    def test_concat_idempotent(self):
        # Charger 2x le prompt advisor doit donner exactement le même
        # contenu (pas de double-concat).
        p1 = load_agent_system_prompt("advisor")
        p2 = load_agent_system_prompt("advisor")
        assert p1 == p2
        # Vérifie qu'on a UNE seule occurrence du marqueur du framework.
        assert p1.count("Pattern de réponse Cognitive Bot v4") == 1

    def test_product_prompt_single_wiki_index_marker(self):
        p = load_agent_system_prompt("product")
        assert p.count("Wiki — index.md (cartographie des pages)") == 1
