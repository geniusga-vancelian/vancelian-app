"""Tests unitaires pour ``router_intent_tags.py`` (Lot 2a, router v2).

Vérifient :
  * Cohérence du catalogue (ids uniques, familles connues).
  * ``classify_message_tags`` détecte correctement par mot-clé FR + EN.
  * Le ``primary_tag`` privilégie l'ordre du catalogue (familles).
  * Un message off-topic mixé avec un sujet in-scope reste in-scope.
  * Robustesse aux entrées vides / accentuées / casse / délimiteurs.
"""

from __future__ import annotations

import pytest

from services.assistance.agents.router_intent_tags import (
    TAG_CATALOG,
    TAG_FAMILY_COMPTE_OPS,
    TAG_FAMILY_EPARGNE,
    TAG_FAMILY_HORS_SUJET,
    TAG_FAMILY_INVESTIR,
    TAG_FAMILY_MARCHES,
    TAG_FAMILY_TRANSVERSE,
    TAGS_BY_NAME,
    classify_message_tags,
    render_classification_for_prompt,
)


class TestCatalogShape:
    def test_unique_tag_ids(self):
        ids = [td.tag for td in TAG_CATALOG]
        assert len(ids) == len(set(ids)), f"duplicate tag ids: {ids}"

    def test_index_consistent(self):
        assert len(TAGS_BY_NAME) == len(TAG_CATALOG)

    def test_all_families_present(self):
        families = {td.family for td in TAG_CATALOG}
        expected = {
            TAG_FAMILY_EPARGNE,
            TAG_FAMILY_INVESTIR,
            TAG_FAMILY_COMPTE_OPS,
            TAG_FAMILY_MARCHES,
            TAG_FAMILY_TRANSVERSE,
            TAG_FAMILY_HORS_SUJET,
        }
        assert families == expected, families

    def test_each_tag_has_at_least_one_keyword(self):
        for td in TAG_CATALOG:
            assert (
                td.keywords_fr or td.keywords_en
            ), f"tag {td.tag} has no keyword"


class TestKeywordMatching:
    @pytest.mark.parametrize(
        "message,expected_tag,expected_family,expected_level",
        [
            # Épargne
            (
                "j'aimerais bien épargner",
                "epargner",
                TAG_FAMILY_EPARGNE,
                2,
            ),
            (
                "comment fonctionne le coffre flexible",
                "livret_coffre",
                TAG_FAMILY_EPARGNE,
                2,
            ),
            # Investir
            ("parle moi des bundle", "bundle_crypto", TAG_FAMILY_INVESTIR, 2),
            (
                "je veux preparer ma retraite",
                "retraite",
                TAG_FAMILY_INVESTIR,
                2,
            ),
            (
                "que penses tu du BTC en ce moment",
                "instrument_cote",
                TAG_FAMILY_INVESTIR,
                2,
            ),
            # Compte ops → niveau 1
            (
                "mon dépôt SEPA n'est pas arrivé",
                "depot",
                TAG_FAMILY_COMPTE_OPS,
                1,
            ),
            (
                "comment effectuer un retrait",
                "retrait",
                TAG_FAMILY_COMPTE_OPS,
                1,
            ),
            # Marchés
            (
                "actualité crypto",
                "actu_marche",
                TAG_FAMILY_MARCHES,
                2,
            ),
            # Transverse
            (
                "l'argent c'est important",
                "argent_general",
                TAG_FAMILY_TRANSVERSE,
                2,
            ),
            (
                "donne moi des articles de la faq",
                "centre_aide_faq",
                TAG_FAMILY_TRANSVERSE,
                2,
            ),
            # Off-topic
            (
                "parle moi de la pluie et du beau temps",
                "off_topic_meteo",
                TAG_FAMILY_HORS_SUJET,
                3,
            ),
            (
                "tu connais une bonne recette de tiramisu ?",
                "off_topic_cuisine",
                TAG_FAMILY_HORS_SUJET,
                3,
            ),
        ],
    )
    def test_classifies_typical_messages(
        self, message, expected_tag, expected_family, expected_level
    ):
        c = classify_message_tags(message)
        assert c.primary_tag == expected_tag, (
            f"got {c.primary_tag} for {message!r}"
        )
        assert c.family == expected_family
        assert c.scope_level == expected_level

    def test_in_scope_wins_over_off_topic_when_mixed(self):
        # Si un message mixe pluie + bundle, on doit garder bundle comme primary.
        c = classify_message_tags("la pluie tombe et je pense à un bundle")
        assert c.primary_tag == "bundle_crypto"
        assert "off_topic_meteo" in c.tags  # mais reste détecté en secondaire

    def test_empty_message_returns_no_tag(self):
        c = classify_message_tags("")
        assert c.primary_tag is None
        assert c.scope_level == 0
        assert c.tags == ()

    def test_whitespace_only_returns_no_tag(self):
        c = classify_message_tags("   \n\t  ")
        assert c.primary_tag is None

    def test_accents_normalized(self):
        c1 = classify_message_tags("épargner")
        c2 = classify_message_tags("EPARGNER")
        c3 = classify_message_tags("epargner")
        assert c1.primary_tag == c2.primary_tag == c3.primary_tag == "epargner"

    def test_no_match_returns_level_0(self):
        c = classify_message_tags("xyzabc qqqq foo bar")
        assert c.primary_tag is None
        assert c.scope_level == 0

    def test_kw_must_be_token_boundary(self):
        # « Bali » ne doit pas matcher dans « basilique » (faux positif).
        # On utilise un matcher avec délimiteur \W.
        c = classify_message_tags("la basilique est belle")
        # Pas de tag attendu — basilique n'est pas un mot-clé.
        assert c.primary_tag is None or c.primary_tag != "exclusive_offer"

    def test_preferred_agent_propagated(self):
        c = classify_message_tags("je veux investir")
        assert c.primary_tag == "investir"
        assert c.preferred_agent == "advisor"


class TestRenderForPrompt:
    def test_renders_block_when_tag_found(self):
        c = classify_message_tags("parle moi des bundle")
        rendered = render_classification_for_prompt(c)
        assert rendered is not None
        assert rendered.startswith("[INTENT TAGS]")
        assert "bundle_crypto" in rendered
        assert "investir" in rendered
        assert "scope_level = 2" in rendered

    def test_renders_none_when_no_tag(self):
        c = classify_message_tags("")
        rendered = render_classification_for_prompt(c)
        assert rendered is None

    def test_renders_other_tags_when_multiple(self):
        c = classify_message_tags("bundle et performance crypto")
        rendered = render_classification_for_prompt(c)
        assert rendered is not None
        # Le bloc mentionne primary_tag + soit other_tags si plus d'un.
        assert "primary_tag" in rendered
