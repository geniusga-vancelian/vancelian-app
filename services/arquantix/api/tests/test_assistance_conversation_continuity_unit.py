"""Tests Lot 7 — Conversation Continuity Layer.

Couvre :

  * ``should_embed_previous_bot_turn`` : règle déterministe (longueur
    sur message court ; plus de veto « standalone keyword » depuis Lot 8).
  * ``build_previous_bot_context_block`` : structure du bloc de
    pré-pend.
  * ``extract_assistant_listing`` : listes numérotées, bullets,
    avec/sans question, mix de formats.
  * ``auto_qcm_from_listing`` : whitelist agents, hard-cap 7,
    soft-cap 5, kill-switch env.
"""

from __future__ import annotations

import os

import pytest

from services.assistance.agents.conversation_continuity import (
    AUTO_QCM_AGENTS,
    EMBEDS_WITH_BUILTIN_CTAS,
    LACONIC_WORD_THRESHOLD,
    NEXT_BEST_ACTIONS_AUTO_QCM_FORBIDDEN,
    QCM_AUTO_PROMOTE_MIN_ITEMS,
    QCM_HARD_CAP,
    QCM_SOFT_CAP,
    SKIP_AGENT_NOT_WHITELISTED,
    SKIP_DISABLED,
    SKIP_EMBED_HAS_CTAS,
    SKIP_LISTING_NO_QUESTION,
    SKIP_LISTING_TOO_SHORT,
    SKIP_NO_LISTING,
    SKIP_OBJECTIVE_FORBIDS,
    SKIP_OBJECTIVE_STOP_PUSHING,
    SKIP_RUNTIME_CHOICES_PRESENT,
    AutoQcmCandidate,
    AutoQcmDecision,
    ExtractedListing,
    ListingItem,
    auto_qcm_from_listing,
    build_previous_bot_context_block,
    contains_standalone_token,
    decide_auto_qcm,
    extract_assistant_listing,
    should_embed_previous_bot_turn,
)


# ─── 1. should_embed_previous_bot_turn ────────────────────────────────────


class TestShouldEmbed:
    def test_short_message_without_token_embeds(self):
        assert should_embed_previous_bot_turn("Les offres") is True

    def test_short_message_with_vancelian_token_still_embeds(self):
        assert should_embed_previous_bot_turn("Le coffre flexible") is True
        assert should_embed_previous_bot_turn("Bundle Top 5") is True
        assert should_embed_previous_bot_turn("Cloud Mining") is True

    def test_short_message_with_instrument_token_still_embeds(self):
        assert should_embed_previous_bot_turn("BTC") is True
        assert should_embed_previous_bot_turn("ETH ?") is True

    def test_short_message_with_project_token_still_embeds(self):
        assert should_embed_previous_bot_turn("la maison") is True
        assert should_embed_previous_bot_turn("ma retraite") is True

    def test_long_message_does_not_embed(self):
        msg = " ".join(["mot"] * (LACONIC_WORD_THRESHOLD + 2))
        assert should_embed_previous_bot_turn(msg) is False

    def test_empty_does_not_embed(self):
        assert should_embed_previous_bot_turn("") is False
        assert should_embed_previous_bot_turn("   ") is False

    def test_kill_switch_env_disables(self, monkeypatch):
        monkeypatch.setenv(
            "ASSISTANCE_PREVIOUS_BOT_CONTEXT_INJECTION_ENABLED", "false"
        )
        assert should_embed_previous_bot_turn("Les offres") is False


# ─── 2. build_previous_bot_context_block ──────────────────────────────────


class TestBuildBlock:
    def test_returns_none_when_no_embed(self):
        msg = " ".join(
            ["je veux acheter une maison de trois cent mille euros sur quatre ans"]
            + ["avec un prêt amortissable détaillé et des mensualités stables"]
        )
        out = build_previous_bot_context_block(
            user_message=msg,
            last_assistant_text="...",
        )
        assert out is None

    def test_returns_block_for_laconic_message(self):
        out = build_previous_bot_context_block(
            user_message="Les offres",
            last_assistant_text=(
                "Voici les 5 familles : Coffres, Offres Exclusives, "
                "Crypto Baskets, Spot, Carte VISA. Lequel t'intéresse ?"
            ),
        )
        assert out is not None
        assert "[RÉPONSE ASSISTANT PRÉCÉDENTE" in out
        assert "[DEMANDE / RÉPONSE UTILISATEUR SUR CE TOUR]" in out
        assert "Les offres" in out
        assert "Offres Exclusives" in out

    def test_returns_none_when_assistant_text_empty(self):
        out = build_previous_bot_context_block(
            user_message="Les offres",
            last_assistant_text="",
        )
        assert out is None


# ─── 3. extract_assistant_listing ─────────────────────────────────────────


class TestExtractListing:
    def test_numbered_list_with_question(self):
        text = (
            "Voici les options :\n"
            "1. Coffre Flexible\n"
            "2. Coffre Avenir\n"
            "3. Crypto Baskets\n"
            "Lequel t'intéresse ?"
        )
        out = extract_assistant_listing(text)
        assert out is not None
        assert len(out.items) == 3
        assert out.items[0].label == "Coffre Flexible"
        assert out.items[2].label == "Crypto Baskets"
        assert out.has_question_after is True

    def test_bullet_list_with_question_trigger_no_qmark(self):
        text = (
            "Tu peux choisir entre :\n"
            "- Une maison\n"
            "- Une voiture\n"
            "- Des vacances\n"
            "Tu préfères lequel"  # pas de ?
        )
        out = extract_assistant_listing(text)
        assert out is not None
        assert len(out.items) == 3
        assert out.has_question_after is True  # trigger keyword

    def test_listing_without_question_is_extracted_but_not_qcm_eligible(self):
        text = (
            "Voici trois options :\n"
            "1. A\n"
            "2. B\n"
            "3. C\n"
            "Bonne journée."
        )
        out = extract_assistant_listing(text)
        assert out is not None
        assert out.has_question_after is False

    def test_too_short_listing_returns_none(self):
        text = "Voici :\n1. A\nBonne journée."
        assert extract_assistant_listing(text) is None

    def test_no_listing_returns_none(self):
        assert (
            extract_assistant_listing("Pas de liste ici, juste du texte.")
            is None
        )

    def test_empty_returns_none(self):
        assert extract_assistant_listing("") is None
        assert extract_assistant_listing("   ") is None

    def test_clean_label_strips_markdown(self):
        text = (
            "Options :\n"
            "1. **Coffre Flexible** : retraits libres\n"
            "2. **Coffre Avenir** : engagement 12 mois\n"
            "Lequel ?"
        )
        out = extract_assistant_listing(text)
        assert out.items[0].label == "Coffre Flexible"
        assert out.items[1].label == "Coffre Avenir"

    def test_seven_items_extracted_intact(self):
        items = "\n".join(f"{i}. Item {i}" for i in range(1, 8))
        text = f"Voici les options :\n{items}\nLequel ?"
        out = extract_assistant_listing(text)
        assert len(out.items) == 7


# ─── 4. auto_qcm_from_listing ─────────────────────────────────────────────


def _listing_with(n: int, *, has_question: bool = True) -> ExtractedListing:
    items = [
        ListingItem(index=i + 1, label=f"Option {i + 1}", raw=f"Option {i + 1}")
        for i in range(n)
    ]
    return ExtractedListing(
        items=items,
        has_question_after=has_question,
        raw_question="Lequel t'intéresse ?",
    )


class TestAutoQcm:
    def test_basic_promotion(self):
        out = auto_qcm_from_listing(_listing_with(3), agent_id="product")
        assert out is not None
        assert out.prompt == "Lequel t'intéresse ?"
        assert len(out.options) == 3
        assert out.options[0]["agent_hint"] == "product"
        assert out.truncated is False

    def test_blocked_for_compliance_agent(self):
        # compliance.* hors whitelist → on ne promote pas
        out = auto_qcm_from_listing(
            _listing_with(3), agent_id="compliance.general"
        )
        assert out is None

    def test_blocked_when_no_question(self):
        out = auto_qcm_from_listing(
            _listing_with(3, has_question=False), agent_id="advisor"
        )
        assert out is None

    def test_blocked_when_only_one_item(self):
        out = auto_qcm_from_listing(_listing_with(1), agent_id="advisor")
        assert out is None

    def test_hard_cap_truncates_at_7(self):
        out = auto_qcm_from_listing(_listing_with(10), agent_id="product")
        assert out is not None
        assert len(out.options) == QCM_HARD_CAP
        assert out.truncated is True

    def test_soft_cap_does_not_truncate_but_allows(self):
        out = auto_qcm_from_listing(_listing_with(6), agent_id="product")
        assert out is not None
        assert len(out.options) == 6  # soft cap = 5 mais pas blocant
        assert out.truncated is False

    def test_kill_switch_env_disables(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_AUTO_QCM_ENABLED", "false")
        out = auto_qcm_from_listing(_listing_with(3), agent_id="product")
        assert out is None

    def test_to_choices_payload_format(self):
        out = auto_qcm_from_listing(_listing_with(3), agent_id="trust")
        payload = out.to_choices_payload()
        assert "prompt" in payload
        assert "options" in payload
        assert isinstance(payload["options"], list)
        assert all("id" in opt and "label" in opt for opt in payload["options"])

    def test_min_items_param_blocks_below_3_by_default(self):
        # V1.1 (2026-05-05) : seuil minimum durci à 3 pour
        # auto-promote (cf. QCM_AUTO_PROMOTE_MIN_ITEMS).
        out = auto_qcm_from_listing(_listing_with(2), agent_id="product")
        assert out is None

    def test_min_items_param_can_be_lowered(self):
        out = auto_qcm_from_listing(
            _listing_with(2), agent_id="product", min_items=2
        )
        assert out is not None
        assert len(out.options) == 2


# ─── 5. Smoke tokens standalone ───────────────────────────────────────────


# ─── 6. decide_auto_qcm — orchestrateur runtime SSE ──────────────────────


_LISTING_TEXT_OK = (
    "Voici ce qu'on peut faire :\n"
    "1. Coffre Flexible\n"
    "2. Coffre Avenir\n"
    "3. Crypto Baskets\n"
    "Lequel t'intéresse ?"
)


_LISTING_TEXT_TWO_ITEMS = (
    "Deux options :\n"
    "1. Plan A\n"
    "2. Plan B\n"
    "Lequel ?"
)


_LISTING_TEXT_NO_QUESTION = (
    "Voici les infos :\n"
    "1. A\n"
    "2. B\n"
    "3. C\n"
    "Bonne journée."
)


class TestDecideAutoQcm:
    def test_promotes_nominal_case(self):
        d = decide_auto_qcm(
            full_text=_LISTING_TEXT_OK,
            agent_id="product",
            runtime_choices_present=False,
            runtime_embeds=None,
            objective={"next_best_action": "ask_question",
                       "stop_pushing": False},
        )
        assert d.promoted is True
        assert d.candidate is not None
        assert len(d.candidate.options) == 3
        assert d.skip_reason is None

    def test_skips_when_runtime_choices_already_present(self):
        d = decide_auto_qcm(
            full_text=_LISTING_TEXT_OK,
            agent_id="product",
            runtime_choices_present=True,
            runtime_embeds=None,
            objective=None,
        )
        assert d.promoted is False
        assert d.skip_reason == SKIP_RUNTIME_CHOICES_PRESENT

    def test_skips_for_unknown_agent(self):
        d = decide_auto_qcm(
            full_text=_LISTING_TEXT_OK,
            agent_id="compliance.transactional",
            runtime_choices_present=False,
            runtime_embeds=None,
            objective=None,
        )
        assert d.promoted is False
        assert d.skip_reason == SKIP_AGENT_NOT_WHITELISTED

    def test_skips_when_embed_has_builtin_ctas(self):
        for embed_type in EMBEDS_WITH_BUILTIN_CTAS:
            d = decide_auto_qcm(
                full_text=_LISTING_TEXT_OK,
                agent_id="product",
                runtime_choices_present=False,
                runtime_embeds=[{"type": embed_type, "data": {}}],
                objective=None,
            )
            assert d.promoted is False, embed_type
            assert d.skip_reason == SKIP_EMBED_HAS_CTAS, embed_type

    def test_skips_when_objective_stop_pushing(self):
        d = decide_auto_qcm(
            full_text=_LISTING_TEXT_OK,
            agent_id="trust",
            runtime_choices_present=False,
            runtime_embeds=None,
            objective={"next_best_action": "give_proof", "stop_pushing": True},
        )
        assert d.promoted is False
        # stop_pushing prime sur next_best_action dans le tagging
        assert d.skip_reason == SKIP_OBJECTIVE_STOP_PUSHING

    def test_skips_for_each_forbidden_next_best_action(self):
        for nba in NEXT_BEST_ACTIONS_AUTO_QCM_FORBIDDEN:
            d = decide_auto_qcm(
                full_text=_LISTING_TEXT_OK,
                agent_id="advisor",
                runtime_choices_present=False,
                runtime_embeds=None,
                objective={"next_best_action": nba, "stop_pushing": False},
            )
            assert d.promoted is False, nba
            assert d.skip_reason == SKIP_OBJECTIVE_FORBIDS, nba

    def test_promotes_for_recommend_objective(self):
        d = decide_auto_qcm(
            full_text=_LISTING_TEXT_OK,
            agent_id="advisor",
            runtime_choices_present=False,
            runtime_embeds=None,
            objective={"next_best_action": "recommend",
                       "stop_pushing": False},
        )
        assert d.promoted is True

    def test_promotes_when_objective_is_none(self):
        d = decide_auto_qcm(
            full_text=_LISTING_TEXT_OK,
            agent_id="product",
            runtime_choices_present=False,
            runtime_embeds=None,
            objective=None,
        )
        assert d.promoted is True

    def test_skips_when_no_listing_in_text(self):
        d = decide_auto_qcm(
            full_text="Pas de liste, juste un paragraphe explicatif.",
            agent_id="product",
            runtime_choices_present=False,
            runtime_embeds=None,
            objective=None,
        )
        assert d.promoted is False
        assert d.skip_reason == SKIP_NO_LISTING

    def test_skips_when_listing_has_no_question(self):
        d = decide_auto_qcm(
            full_text=_LISTING_TEXT_NO_QUESTION,
            agent_id="product",
            runtime_choices_present=False,
            runtime_embeds=None,
            objective=None,
        )
        assert d.promoted is False
        assert d.skip_reason == SKIP_LISTING_NO_QUESTION

    def test_skips_when_listing_too_short(self):
        d = decide_auto_qcm(
            full_text=_LISTING_TEXT_TWO_ITEMS,
            agent_id="product",
            runtime_choices_present=False,
            runtime_embeds=None,
            objective=None,
        )
        assert d.promoted is False
        assert d.skip_reason == SKIP_LISTING_TOO_SHORT

    def test_kill_switch_env_disables(self, monkeypatch):
        monkeypatch.setenv("ASSISTANCE_AUTO_QCM_ENABLED", "false")
        d = decide_auto_qcm(
            full_text=_LISTING_TEXT_OK,
            agent_id="product",
            runtime_choices_present=False,
            runtime_embeds=None,
            objective=None,
        )
        assert d.promoted is False
        assert d.skip_reason == SKIP_DISABLED

    def test_ignores_unknown_embed_types(self):
        # Un embed quelconque sans CTA built-in ne doit pas bloquer.
        d = decide_auto_qcm(
            full_text=_LISTING_TEXT_OK,
            agent_id="product",
            runtime_choices_present=False,
            runtime_embeds=[{"type": "portfolio_allocation_donut", "data": {}}],
            objective=None,
        )
        assert d.promoted is True


class TestStandaloneTokens:
    def test_vancelian_products(self):
        for token in (
            "Coffre Flexible",
            "Bundle Top 5",
            "Cloud Mining",
            "Privilege Club",
            "Vancelian Card",
            "Dubai Villa",
        ):
            assert contains_standalone_token(token) is True, token

    def test_instruments(self):
        for token in ("BTC", "ETH", "USDC"):
            assert contains_standalone_token(token) is True, token

    def test_projects(self):
        for token in (
            "maison",
            "retraite",
            "vacances",
            "house",
            "wedding",
        ):
            assert contains_standalone_token(token) is True, token

    def test_neutral(self):
        assert contains_standalone_token("offres") is False
        assert contains_standalone_token("oui") is False
