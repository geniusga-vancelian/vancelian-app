"""Tests unitaires pour ``router_off_topic_options.py`` (Lot 1, router v2).

Vérifient :
  * La liste fixe est bien renvoyée sans current_topic.
  * Le slot ``resume_topic`` est ajouté en 1ʳᵉ position si ``current_topic``
    contient un label exploitable.
  * Le format du label resume est résilient aux entrées partielles.
  * Aucun side-effect entre appels successifs (immutabilité).
"""

from __future__ import annotations

import pytest

from services.assistance.agents.router_off_topic_options import (
    OFF_TOPIC_FIXED_OPTIONS,
    OFF_TOPIC_RESUME_OPTION_ID,
    build_off_topic_options,
)


class TestFixedListShape:
    def test_fixed_list_length_and_ids(self):
        assert len(OFF_TOPIC_FIXED_OPTIONS) == 5
        ids = [opt["id"] for opt in OFF_TOPIC_FIXED_OPTIONS]
        # On veut couvrir les 4 agents experts + 1 angle advisor secondaire.
        assert "compliance" in ids
        assert "product" in ids
        assert ids.count("advisor") == 2  # 2 angles advisor distincts
        assert "market" in ids

    def test_fixed_list_labels_unique(self):
        labels = [opt["label"] for opt in OFF_TOPIC_FIXED_OPTIONS]
        assert len(labels) == len(set(labels)), labels

    def test_fixed_list_no_resume_slot_in_constants(self):
        # OFF_TOPIC_FIXED_OPTIONS ne doit PAS contenir le slot resume —
        # il est ajouté dynamiquement par build_off_topic_options.
        assert all(
            opt["id"] != OFF_TOPIC_RESUME_OPTION_ID
            for opt in OFF_TOPIC_FIXED_OPTIONS
        )


class TestBuildWithoutTopic:
    def test_returns_only_fixed_when_no_topic(self):
        result = build_off_topic_options(current_topic=None)
        assert len(result) == len(OFF_TOPIC_FIXED_OPTIONS)
        for got, expected in zip(result, OFF_TOPIC_FIXED_OPTIONS):
            assert got["id"] == expected["id"]
            assert got["label"] == expected["label"]

    def test_empty_dict_topic_no_resume_slot(self):
        result = build_off_topic_options(current_topic={})
        assert all(opt["id"] != OFF_TOPIC_RESUME_OPTION_ID for opt in result)

    def test_topic_without_useful_keys_no_resume(self):
        result = build_off_topic_options(
            current_topic={"some_random_key": "x"}
        )
        assert all(opt["id"] != OFF_TOPIC_RESUME_OPTION_ID for opt in result)

    def test_non_dict_topic_treated_as_none(self):
        # Robustesse : une string ou un int en input ne doit pas planter.
        result = build_off_topic_options(current_topic="not a dict")  # type: ignore[arg-type]
        assert all(opt["id"] != OFF_TOPIC_RESUME_OPTION_ID for opt in result)


class TestBuildWithTopic:
    def test_topic_with_display_label(self):
        result = build_off_topic_options(
            current_topic={"display_label": "Crypto Basket Top 5"}
        )
        assert result[0]["id"] == OFF_TOPIC_RESUME_OPTION_ID
        assert "Crypto Basket Top 5" in result[0]["label"]
        assert result[0]["label"].startswith("Reprendre")
        # Les options fixes suivent.
        assert len(result) == len(OFF_TOPIC_FIXED_OPTIONS) + 1

    def test_topic_falls_back_to_product_code(self):
        result = build_off_topic_options(
            current_topic={"product_code": "TOP_5"}
        )
        assert result[0]["id"] == OFF_TOPIC_RESUME_OPTION_ID
        assert "TOP_5" in result[0]["label"]

    def test_topic_falls_back_to_kind(self):
        result = build_off_topic_options(
            current_topic={"kind": "vancelian_product"}
        )
        assert result[0]["id"] == OFF_TOPIC_RESUME_OPTION_ID
        assert "vancelian_product" in result[0]["label"]

    def test_label_truncated_to_80_chars(self):
        long_label = "A" * 200
        result = build_off_topic_options(
            current_topic={"display_label": long_label}
        )
        assert result[0]["id"] == OFF_TOPIC_RESUME_OPTION_ID
        # Le préfixe "Reprendre " + 80 chars max.
        assert len(result[0]["label"]) <= 100

    def test_priority_display_label_over_product_code(self):
        result = build_off_topic_options(
            current_topic={
                "display_label": "Display X",
                "product_code": "FOO",
                "kind": "bar",
            }
        )
        assert "Display X" in result[0]["label"]
        assert "FOO" not in result[0]["label"]


class TestImmutability:
    def test_consecutive_calls_return_independent_lists(self):
        a = build_off_topic_options(current_topic={"product_code": "X"})
        b = build_off_topic_options(current_topic={"product_code": "Y"})
        # Modifier a ne doit pas affecter b.
        a.append({"id": "test", "label": "test"})
        assert all(opt["id"] != "test" for opt in b)

    def test_internal_constant_not_mutated(self):
        before = [dict(opt) for opt in OFF_TOPIC_FIXED_OPTIONS]
        build_off_topic_options(current_topic={"display_label": "Mutate?"})
        after = [dict(opt) for opt in OFF_TOPIC_FIXED_OPTIONS]
        assert before == after
