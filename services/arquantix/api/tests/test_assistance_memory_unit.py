"""Tests unitaires de `services.assistance.memory` (Palier 2 D.2).

Aucune dépendance externe : pas de DB, pas de réseau, pas d'asyncio.

Couvre les fonctions pures + helpers du module mémoire long-terme :
  - lecture des env vars (defaults + overrides + clamping + invalid)
  - `count_tokens` (tiktoken + fallback heuristique)
  - `should_consolidate`
  - `_format_memory_block` (toutes branches)
  - `build_context`
  - `_sanitize_facts`
  - `_merge_conv_facts`
  - `_merge_client_long_memory`
  - `_heuristic_summary_fallback`
  - `_load_system_prompt`

Conventions :
  - Une assertion par test (lisibilité), groupes thématiques par classe.
  - `monkeypatch.setenv` pour les vars (rollback automatique).
  - UUIDs déterministes pour la traçabilité des facts long-memory.
"""

from __future__ import annotations

import builtins
from datetime import datetime, timezone
from uuid import UUID

import pytest

from services.assistance import memory


# ─────────────────────────────────────────────────────────────────────────
# Configuration runtime (env vars)
# ─────────────────────────────────────────────────────────────────────────


class TestConfigEnvVars:
    """Lecture des env vars de configuration."""

    def test_summarizer_model_default(self, monkeypatch):
        monkeypatch.delenv("ASSISTANCE_SUMMARIZER_MODEL", raising=False)
        monkeypatch.delenv("OPENAI_MODEL", raising=False)
        assert memory.assistance_summarizer_model() == "gpt-4o-mini"

    def test_summarizer_model_dedicated_env_wins(self, monkeypatch):
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")
        monkeypatch.setenv("ASSISTANCE_SUMMARIZER_MODEL", "gpt-4o-mini")
        assert memory.assistance_summarizer_model() == "gpt-4o-mini"

    def test_summarizer_model_falls_back_to_openai_model(self, monkeypatch):
        monkeypatch.delenv("ASSISTANCE_SUMMARIZER_MODEL", raising=False)
        monkeypatch.setenv("OPENAI_MODEL", "gpt-4-turbo")
        assert memory.assistance_summarizer_model() == "gpt-4-turbo"

    def test_threshold_tokens_default(self, monkeypatch):
        monkeypatch.delenv("ASSISTANCE_SUMMARY_THRESHOLD_TOKENS", raising=False)
        assert memory.assistance_summary_threshold_tokens() == 6000

    def test_threshold_tokens_custom(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_SUMMARY_THRESHOLD_TOKENS", "1500")
        assert memory.assistance_summary_threshold_tokens() == 1500

    def test_threshold_tokens_invalid_falls_back(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_SUMMARY_THRESHOLD_TOKENS", "not_a_number")
        assert memory.assistance_summary_threshold_tokens() == 6000

    def test_threshold_tokens_clamped_to_minimum(self, monkeypatch):
        """Floor à 1000 pour éviter les valeurs aberrantes (consolide à chaque tour)."""
        monkeypatch.setenv("ASSISTANCE_SUMMARY_THRESHOLD_TOKENS", "100")
        assert memory.assistance_summary_threshold_tokens() == 1000

    def test_recent_turns_kept_default(self, monkeypatch):
        monkeypatch.delenv("ASSISTANCE_RECENT_TURNS_KEPT", raising=False)
        assert memory.assistance_recent_turns_kept() == 8

    def test_recent_turns_kept_custom(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_RECENT_TURNS_KEPT", "16")
        assert memory.assistance_recent_turns_kept() == 16

    def test_recent_turns_kept_clamped_to_minimum(self, monkeypatch):
        """Floor à 2 pour préserver au moins le dernier user/assistant exchange."""
        monkeypatch.setenv("ASSISTANCE_RECENT_TURNS_KEPT", "1")
        assert memory.assistance_recent_turns_kept() == 2

    def test_temperature_default(self, monkeypatch):
        monkeypatch.delenv("ASSISTANCE_SUMMARIZER_TEMPERATURE", raising=False)
        assert memory.assistance_summarizer_temperature() == 0.2

    def test_temperature_clamped_high(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_SUMMARIZER_TEMPERATURE", "5.0")
        assert memory.assistance_summarizer_temperature() == 2.0

    def test_temperature_clamped_low(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_SUMMARIZER_TEMPERATURE", "-1.0")
        assert memory.assistance_summarizer_temperature() == 0.0

    def test_temperature_invalid_falls_back(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_SUMMARIZER_TEMPERATURE", "abc")
        assert memory.assistance_summarizer_temperature() == 0.2


# ─────────────────────────────────────────────────────────────────────────
# Comptage tokens
# ─────────────────────────────────────────────────────────────────────────


class TestCountTokens:
    """`count_tokens` — tiktoken nominal + fallback heuristique."""

    def test_empty_messages(self):
        assert memory.count_tokens([]) > 0  # overhead conv ≈ 3

    def test_short_message_with_tiktoken(self):
        msgs = [{"role": "user", "content": "hello world"}]
        n = memory.count_tokens(msgs)
        # "hello world" = 2 tokens + overhead ~ 4-8 tokens, role + conv overhead
        assert 5 <= n <= 20

    def test_long_message_grows_linearly(self):
        short = [{"role": "user", "content": "x" * 100}]
        longer = [{"role": "user", "content": "x" * 10_000}]
        # Le long doit avoir significativement plus de tokens
        assert memory.count_tokens(longer) > memory.count_tokens(short) * 50

    def test_multiple_messages_accumulate(self):
        single = [{"role": "user", "content": "test"}]
        triple = [
            {"role": "user", "content": "test"},
            {"role": "assistant", "content": "test"},
            {"role": "user", "content": "test"},
        ]
        assert memory.count_tokens(triple) > memory.count_tokens(single) * 2

    def test_unknown_model_falls_back_to_cl100k(self):
        """Un modèle inconnu de tiktoken doit retomber sur l'encoding cl100k_base."""
        msgs = [{"role": "user", "content": "hello"}]
        n = memory.count_tokens(msgs, model="some-unknown-future-model")
        assert n > 0

    def test_handles_missing_role_or_content(self):
        """Robustesse : ne crash pas sur des messages mal formés."""
        msgs = [
            {"role": "user"},  # pas de content
            {"content": "orphan"},  # pas de role
            {},  # vide
        ]
        n = memory.count_tokens(msgs)
        assert n > 0

    def test_fallback_heuristic_when_tiktoken_unavailable(self, monkeypatch):
        """Si tiktoken raise ImportError, fallback char/4 prend le relais."""
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "tiktoken":
                raise ImportError("simulated tiktoken absent")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        msgs = [{"role": "user", "content": "hello world"}]
        n = memory.count_tokens(msgs)
        # heuristique : (11 chars content + 4 chars role + 8 overhead) / 4 ≈ 5
        assert 1 <= n <= 30


# ─────────────────────────────────────────────────────────────────────────
# `should_consolidate`
# ─────────────────────────────────────────────────────────────────────────


class TestShouldConsolidate:
    def test_below_threshold_returns_false(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_SUMMARY_THRESHOLD_TOKENS", "10000")
        msgs = [{"role": "user", "content": "court"}]
        assert memory.should_consolidate(msgs) is False

    def test_above_threshold_returns_true(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_SUMMARY_THRESHOLD_TOKENS", "1000")
        # Génère ~5000 tokens (~ 20k chars)
        big = "lorem ipsum dolor sit amet " * 1000
        msgs = [{"role": "user", "content": big}]
        assert memory.should_consolidate(msgs) is True

    def test_explicit_threshold_overrides_env(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_SUMMARY_THRESHOLD_TOKENS", "100000")
        big = "x" * 100_000
        msgs = [{"role": "user", "content": big}]
        # Env très haut → False
        assert memory.should_consolidate(msgs) is False
        # Override bas → True
        assert memory.should_consolidate(msgs, threshold=100) is True


# ─────────────────────────────────────────────────────────────────────────
# `_format_memory_block`
# ─────────────────────────────────────────────────────────────────────────


class TestFormatMemoryBlock:
    """Sérialisation Markdown de la mémoire pour le system prompt."""

    def test_empty_returns_none(self):
        assert memory._format_memory_block(summary=None, client_long_memory=None) is None
        assert memory._format_memory_block(summary="", client_long_memory={}) is None
        assert memory._format_memory_block(summary="   ", client_long_memory={"facts": []}) is None

    def test_summary_only(self):
        block = memory._format_memory_block(
            summary="Le client veut investir 100k€.",
            client_long_memory=None,
        )
        assert block is not None
        assert "## Résumé de la conversation en cours" in block
        assert "Le client veut investir 100k€." in block
        assert "Contexte client" not in block

    def test_long_memory_facts_only(self):
        block = memory._format_memory_block(
            summary=None,
            client_long_memory={
                "facts": [
                    {"type": "investment_target", "value": 50000, "confidence": 0.95},
                ]
            },
        )
        assert block is not None
        assert "## Contexte client" in block
        assert "**investment_target**" in block
        assert "50000" in block

    def test_both_summary_and_facts(self):
        block = memory._format_memory_block(
            summary="Conv en cours.",
            client_long_memory={
                "facts": [
                    {"type": "goal", "value": "PEA", "confidence": 0.9},
                ]
            },
        )
        assert "## Contexte client" in block
        assert "## Résumé" in block
        # L'ordre est important : d'abord client (plus stable), puis conv courante.
        assert block.index("## Contexte client") < block.index("## Résumé")

    def test_low_confidence_label_added(self):
        """Faits sous 0.7 doivent être annotés avec le score (transparence LLM)."""
        block = memory._format_memory_block(
            summary=None,
            client_long_memory={
                "facts": [
                    {"type": "preference", "value": "ESG", "confidence": 0.4},
                ]
            },
        )
        assert "_(confiance 0.4)_" in block

    def test_high_confidence_label_omitted(self):
        """Faits ≥ 0.7 ne doivent pas être annotés (cas nominal)."""
        block = memory._format_memory_block(
            summary=None,
            client_long_memory={
                "facts": [
                    {"type": "preference", "value": "ESG", "confidence": 0.95},
                ]
            },
        )
        assert "confiance" not in block

    def test_facts_without_value_skipped(self):
        block = memory._format_memory_block(
            summary=None,
            client_long_memory={
                "facts": [
                    {"type": "valid", "value": "ok"},
                    {"type": "broken"},  # no value
                    {"type": "broken2", "value": None},
                ]
            },
        )
        assert "valid" in block
        assert "broken" not in block

    def test_summary_whitespace_stripped(self):
        block = memory._format_memory_block(
            summary="  \n  Vrai contenu.  \n  ",
            client_long_memory=None,
        )
        assert "Vrai contenu." in block
        assert "  Vrai contenu.  " not in block


# ─────────────────────────────────────────────────────────────────────────
# `build_context`
# ─────────────────────────────────────────────────────────────────────────


class TestBuildContext:
    """Assemblage du payload OpenAI : system memory block + recent turns."""

    def test_no_memory_returns_recent_only(self):
        recent = [
            {"role": "user", "content": "salut"},
            {"role": "assistant", "content": "bonjour"},
        ]
        out = memory.build_context(
            summary=None, client_long_memory=None, recent_turns=recent
        )
        assert out == recent

    def test_empty_memory_returns_recent_only(self):
        """`{}` ou `{"facts": []}` ne doit pas injecter de bloc."""
        recent = [{"role": "user", "content": "hi"}]
        out = memory.build_context(
            summary="", client_long_memory={"facts": []}, recent_turns=recent
        )
        assert out == recent

    def test_with_summary_prepends_system(self):
        recent = [{"role": "user", "content": "et donc ?"}]
        out = memory.build_context(
            summary="Précédemment dans la conv...",
            client_long_memory=None,
            recent_turns=recent,
        )
        assert len(out) == 2
        assert out[0]["role"] == "system"
        assert "Précédemment" in out[0]["content"]
        assert out[1] == recent[0]

    def test_with_full_memory_prepends_system(self):
        recent = [{"role": "user", "content": "rebonjour"}]
        out = memory.build_context(
            summary="Résumé conv.",
            client_long_memory={
                "facts": [
                    {"type": "goal", "value": "PEA", "confidence": 0.9},
                ]
            },
            recent_turns=recent,
        )
        assert out[0]["role"] == "system"
        assert "## Contexte client" in out[0]["content"]
        assert "## Résumé" in out[0]["content"]
        assert out[-1] == recent[0]

    def test_preserves_recent_turn_order(self):
        recent = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "R1"},
            {"role": "user", "content": "Q2"},
        ]
        out = memory.build_context(
            summary="x", client_long_memory=None, recent_turns=recent
        )
        # System block d'abord, puis recent dans l'ordre exact
        assert out[1:] == recent


# ─────────────────────────────────────────────────────────────────────────
# `_sanitize_facts`
# ─────────────────────────────────────────────────────────────────────────


class TestSanitizeFacts:
    """Validation/normalisation des facts retournés par le LLM."""

    def test_valid_fact_passes_through(self):
        out = memory._sanitize_facts(
            [{"type": "investment_target", "value": 50000, "confidence": 0.9, "evidence": "evidence"}]
        )
        assert len(out) == 1
        assert out[0]["type"] == "investment_target"
        assert out[0]["value"] == 50000
        assert out[0]["confidence"] == 0.9

    def test_unknown_type_normalized_to_other(self):
        out = memory._sanitize_facts(
            [{"type": "weird_invented_type", "value": "x", "confidence": 0.5}]
        )
        assert out[0]["type"] == "other"

    def test_missing_value_skipped(self):
        out = memory._sanitize_facts(
            [
                {"type": "goal"},  # no value
                {"type": "goal", "value": ""},  # empty
                {"type": "goal", "value": None},  # None
            ]
        )
        assert out == []

    def test_confidence_clamped_above(self):
        out = memory._sanitize_facts(
            [{"type": "goal", "value": "PEA", "confidence": 5.0}]
        )
        assert out[0]["confidence"] == 1.0

    def test_confidence_clamped_below(self):
        out = memory._sanitize_facts(
            [{"type": "goal", "value": "PEA", "confidence": -0.5}]
        )
        assert out[0]["confidence"] == 0.0

    def test_invalid_confidence_defaults(self):
        out = memory._sanitize_facts(
            [{"type": "goal", "value": "PEA", "confidence": "not_a_float"}]
        )
        assert out[0]["confidence"] == 0.5

    def test_evidence_truncated_at_200_chars(self):
        long_evidence = "x" * 500
        out = memory._sanitize_facts(
            [{"type": "goal", "value": "PEA", "confidence": 0.9, "evidence": long_evidence}]
        )
        assert len(out[0]["evidence"]) == 200

    def test_non_dict_items_skipped(self):
        out = memory._sanitize_facts(
            ["not a dict", 42, None, {"type": "goal", "value": "OK"}]
        )
        assert len(out) == 1
        assert out[0]["value"] == "OK"

    def test_empty_list_returns_empty(self):
        assert memory._sanitize_facts([]) == []


# ─────────────────────────────────────────────────────────────────────────
# `_merge_conv_facts`
# ─────────────────────────────────────────────────────────────────────────


class TestMergeConvFacts:
    """Fusion intra-conv : 1 fact par type, replace si valeur change."""

    def test_adds_new_fact(self):
        existing = []
        new = [{"type": "goal", "value": "PEA", "confidence": 0.9}]
        out = memory._merge_conv_facts(existing=existing, new=new)
        assert len(out) == 1
        assert out[0]["value"] == "PEA"

    def test_same_type_same_value_keeps_higher_confidence(self):
        existing = [{"type": "goal", "value": "PEA", "confidence": 0.6}]
        new = [{"type": "goal", "value": "PEA", "confidence": 0.95}]
        out = memory._merge_conv_facts(existing=existing, new=new)
        assert len(out) == 1
        assert out[0]["confidence"] == 0.95

    def test_same_type_same_value_lower_confidence_keeps_existing(self):
        existing = [{"type": "goal", "value": "PEA", "confidence": 0.95}]
        new = [{"type": "goal", "value": "PEA", "confidence": 0.4}]
        out = memory._merge_conv_facts(existing=existing, new=new)
        assert out[0]["confidence"] == 0.95

    def test_same_type_different_value_replaces(self):
        """Cas update : horizon passe de 5 à 7 ans."""
        existing = [{"type": "investment_horizon", "value": 60, "confidence": 0.9}]
        new = [{"type": "investment_horizon", "value": 84, "confidence": 0.85}]
        out = memory._merge_conv_facts(existing=existing, new=new)
        assert len(out) == 1
        assert out[0]["value"] == 84

    def test_different_types_coexist(self):
        existing = [{"type": "goal", "value": "PEA", "confidence": 0.9}]
        new = [
            {"type": "investment_target", "value": 50000, "confidence": 0.9},
            {"type": "risk_appetite", "value": "prudent", "confidence": 0.8},
        ]
        out = memory._merge_conv_facts(existing=existing, new=new)
        assert len(out) == 3
        types = {f["type"] for f in out}
        assert types == {"goal", "investment_target", "risk_appetite"}

    def test_value_normalization_case_insensitive(self):
        """'PEA' et 'pea' doivent matcher (normalisation lower)."""
        existing = [{"type": "goal", "value": "PEA", "confidence": 0.6}]
        new = [{"type": "goal", "value": "pea", "confidence": 0.95}]
        out = memory._merge_conv_facts(existing=existing, new=new)
        assert len(out) == 1
        assert out[0]["confidence"] == 0.95


# ─────────────────────────────────────────────────────────────────────────
# `_merge_client_long_memory`
# ─────────────────────────────────────────────────────────────────────────


class TestMergeClientLongMemory:
    """Fusion cross-conv : append-mostly avec timestamps + traçabilité."""

    SOURCE_CONV_ID = UUID("00000000-0000-0000-0000-000000000001")
    NOW = datetime(2026, 5, 1, 22, 0, 0, tzinfo=timezone.utc)

    def test_adds_new_fact_with_full_metadata(self):
        out = memory._merge_client_long_memory(
            existing={},
            new_facts=[
                {"type": "goal", "value": "PEA", "confidence": 0.9, "evidence": "x"}
            ],
            source_conversation_id=self.SOURCE_CONV_ID,
            now=self.NOW,
        )
        assert "facts" in out
        assert "updated_at" in out
        assert len(out["facts"]) == 1
        f = out["facts"][0]
        assert f["type"] == "goal"
        assert f["source_conversation_id"] == str(self.SOURCE_CONV_ID)
        assert f["first_seen_at"] == self.NOW.isoformat()
        assert f["last_seen_at"] == self.NOW.isoformat()

    def test_existing_facts_preserved(self):
        existing = {
            "facts": [
                {
                    "type": "goal",
                    "value": "PEA",
                    "confidence": 0.9,
                    "first_seen_at": "2025-01-01T00:00:00+00:00",
                    "last_seen_at": "2025-01-01T00:00:00+00:00",
                    "source_conversation_id": "old-uuid",
                }
            ],
            "updated_at": "2025-01-01T00:00:00+00:00",
        }
        out = memory._merge_client_long_memory(
            existing=existing,
            new_facts=[{"type": "investment_target", "value": 50000, "confidence": 0.9}],
            source_conversation_id=self.SOURCE_CONV_ID,
            now=self.NOW,
        )
        assert len(out["facts"]) == 2

    def test_duplicate_fact_refreshes_last_seen(self):
        existing = {
            "facts": [
                {
                    "type": "goal",
                    "value": "PEA",
                    "confidence": 0.6,
                    "first_seen_at": "2025-01-01T00:00:00+00:00",
                    "last_seen_at": "2025-01-01T00:00:00+00:00",
                    "source_conversation_id": "old-uuid",
                }
            ]
        }
        out = memory._merge_client_long_memory(
            existing=existing,
            new_facts=[{"type": "goal", "value": "PEA", "confidence": 0.95}],
            source_conversation_id=self.SOURCE_CONV_ID,
            now=self.NOW,
        )
        assert len(out["facts"]) == 1
        f = out["facts"][0]
        assert f["first_seen_at"] == "2025-01-01T00:00:00+00:00"  # inchangé
        assert f["last_seen_at"] == self.NOW.isoformat()  # refresh
        assert f["source_conversation_id"] == "old-uuid"  # origine préservée

    def test_duplicate_fact_keeps_max_confidence(self):
        existing = {
            "facts": [
                {
                    "type": "goal",
                    "value": "PEA",
                    "confidence": 0.95,
                    "first_seen_at": "2025-01-01T00:00:00+00:00",
                    "last_seen_at": "2025-01-01T00:00:00+00:00",
                    "source_conversation_id": "old",
                }
            ]
        }
        # Nouveau fact moins confiant : on garde 0.95
        out = memory._merge_client_long_memory(
            existing=existing,
            new_facts=[{"type": "goal", "value": "PEA", "confidence": 0.4}],
            source_conversation_id=self.SOURCE_CONV_ID,
            now=self.NOW,
        )
        assert out["facts"][0]["confidence"] == 0.95

    def test_different_value_creates_new_entry(self):
        """Append-mostly : une valeur différente coexiste avec l'ancienne (évolution
        des objectifs : ex. horizon de 5 → 7 ans → on garde l'historique)."""
        existing = {
            "facts": [
                {
                    "type": "investment_horizon",
                    "value": 60,
                    "confidence": 0.9,
                    "first_seen_at": "2025-01-01T00:00:00+00:00",
                    "last_seen_at": "2025-01-01T00:00:00+00:00",
                    "source_conversation_id": "old",
                }
            ]
        }
        out = memory._merge_client_long_memory(
            existing=existing,
            new_facts=[
                {"type": "investment_horizon", "value": 84, "confidence": 0.9}
            ],
            source_conversation_id=self.SOURCE_CONV_ID,
            now=self.NOW,
        )
        assert len(out["facts"]) == 2

    def test_updated_at_refreshed(self):
        out = memory._merge_client_long_memory(
            existing={},
            new_facts=[{"type": "goal", "value": "PEA", "confidence": 0.9}],
            source_conversation_id=self.SOURCE_CONV_ID,
            now=self.NOW,
        )
        assert out["updated_at"] == self.NOW.isoformat()


# ─────────────────────────────────────────────────────────────────────────
# `_heuristic_summary_fallback`
# ─────────────────────────────────────────────────────────────────────────


class TestHeuristicFallback:
    """Fallback ultra-conservateur quand le LLM est down."""

    def test_no_previous_summary(self):
        out = memory._heuristic_summary_fallback(
            previous_summary="",
            new_turns=[{"role": "user", "content": "x"}, {"role": "assistant", "content": "y"}],
        )
        assert "[Mémoire dégradée]" in out["summary"]
        assert "2 nouvel" in out["summary"]
        assert out["facts"] == []

    def test_with_previous_summary_appends(self):
        out = memory._heuristic_summary_fallback(
            previous_summary="Le client est intéressé par l'épargne.",
            new_turns=[{"role": "user", "content": "x"}],
        )
        assert out["summary"].startswith("Le client est intéressé")
        assert "[Mémoire dégradée]" in out["summary"]

    def test_idempotent_marker_not_duplicated(self):
        """Si le marqueur dégradé est déjà présent, on ne le ré-ajoute pas."""
        previous = "Conv normale. [Mémoire dégradée] 3 nouvel échanges."
        out = memory._heuristic_summary_fallback(
            previous_summary=previous,
            new_turns=[{"role": "user", "content": "z"}],
        )
        assert out["summary"] == previous
        # Compte le nombre d'occurrences du marqueur
        assert out["summary"].count("[Mémoire dégradée]") == 1

    def test_empty_new_turns(self):
        out = memory._heuristic_summary_fallback(
            previous_summary="ok",
            new_turns=[],
        )
        assert "0 nouvel" in out["summary"]
        assert out["facts"] == []
        assert out["open_points"] == []


# ─────────────────────────────────────────────────────────────────────────
# `_load_system_prompt`
# ─────────────────────────────────────────────────────────────────────────


class TestLoadSystemPrompt:
    def test_loads_prompt_file(self):
        prompt = memory._load_system_prompt()
        # On vérifie que le contenu réel du prompt est chargé (pas le fallback)
        assert "summary" in prompt.lower()
        assert "facts" in prompt.lower()
        # Doit être substantiel (≠ fallback minimal)
        assert len(prompt) > 500

    def test_falls_back_when_file_missing(self, monkeypatch, tmp_path):
        """Si le fichier prompt disparaît, fallback minimal (best-effort)."""
        monkeypatch.setattr(memory, "_PROMPT_PATH", tmp_path / "missing.md")
        prompt = memory._load_system_prompt()
        assert "JSON" in prompt or "json" in prompt
        assert "summary" in prompt.lower()
