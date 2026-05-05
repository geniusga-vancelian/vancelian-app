"""Tests unitaires pour ``router_clarification_catalog.py`` (Lot 3, router v2).

Vérifient :
  * Le catalogue couvre tous les tags non-off-topic du Lot 2.
  * Chaque entrée a un prompt non vide + 2 à 5 options bien formées.
  * Les ``agent_id`` référencés dans les options sont des agents
    routables connus.
  * ``get_clarification_for_tag`` est résilient aux entrées vides /
    inconnues.
"""

from __future__ import annotations

import pytest

from services.assistance.agents.router_clarification_catalog import (
    CLARIFICATION_BY_TAG,
    get_clarification_for_tag,
)
from services.assistance.agents.router_intent_tags import (
    TAG_CATALOG,
    TAG_FAMILY_HORS_SUJET,
)


ROUTABLE_AGENTS = {"compliance", "advisor", "product", "market"}


class TestCatalogCoverage:
    def test_all_in_scope_tags_have_an_entry(self):
        # Tous les tags non-off-topic doivent avoir une entrée
        # canonique pour que le pattern hybride fonctionne sans
        # fallback systématique.
        in_scope_tags = [
            td.tag for td in TAG_CATALOG if td.family != TAG_FAMILY_HORS_SUJET
        ]
        missing = [t for t in in_scope_tags if t not in CLARIFICATION_BY_TAG]
        assert not missing, f"missing clarification entries: {missing}"

    def test_no_off_topic_in_catalog(self):
        # Les hors-sujets utilisent redirect_off_topic, pas
        # ask_clarification — ils ne doivent pas être dans le catalogue.
        off_topic_tags = {
            td.tag for td in TAG_CATALOG if td.family == TAG_FAMILY_HORS_SUJET
        }
        for ot in off_topic_tags:
            assert ot not in CLARIFICATION_BY_TAG, ot


class TestEntryShape:
    @pytest.mark.parametrize("tag", list(CLARIFICATION_BY_TAG.keys()))
    def test_each_entry_has_valid_prompt_and_options(self, tag):
        entry = CLARIFICATION_BY_TAG[tag]
        assert entry.get("prompt"), f"empty prompt for {tag}"
        opts = entry.get("options") or []
        assert 2 <= len(opts) <= 5, f"{tag} has {len(opts)} options"
        for opt in opts:
            assert opt.get("agent_id") in ROUTABLE_AGENTS, (
                f"{tag} option has invalid agent_id={opt.get('agent_id')!r}"
            )
            assert opt.get("label"), f"{tag} option has empty label"

    @pytest.mark.parametrize("tag", list(CLARIFICATION_BY_TAG.keys()))
    def test_options_are_distinct_pairs(self, tag):
        entry = CLARIFICATION_BY_TAG[tag]
        pairs = [
            (opt["agent_id"], opt["label"]) for opt in entry["options"]
        ]
        assert len(pairs) == len(set(pairs)), (
            f"{tag} has duplicate (agent_id, label) pairs"
        )


class TestGetter:
    def test_known_tag_returns_entry(self):
        entry = get_clarification_for_tag("epargner")
        assert entry is not None
        assert "épargne" in entry["prompt"].lower()
        assert any(
            opt["agent_id"] == "product" for opt in entry["options"]
        )

    def test_unknown_tag_returns_none(self):
        assert get_clarification_for_tag("xxx_unknown_tag") is None

    def test_none_returns_none(self):
        assert get_clarification_for_tag(None) is None

    def test_empty_string_returns_none(self):
        assert get_clarification_for_tag("") is None
