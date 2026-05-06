"""Tests unitaires Politique éditoriale Vancelian (2026-05-06) —
``services.assistance.text_sanitizer``.

Couvre :

  * ``strip_emojis`` :
    - None / chaîne vide → preserved
    - Texte sans emoji → identité (fast path)
    - Emojis simples (1F600 emoticons : 😀 🥲 🙃)
    - Pictogrammes (1F300 misc : 🎉 🌟 🔥)
    - Symboles Unicode tolérés vs interdits :
      - ✅ ❌ ⚠️ → strip (Dingbats / Misc Symbols + variation
        selector)
      - ⭐ ☀ → strip
      - © ® ™ ÷ ± → → preserve (politique éditoriale)
      - é è à ç œ → preserve (français)
      - « » " ' – — … → preserve (typographie)
    - Drapeaux (regional indicators) 🇫🇷 → strip
    - Skin tones 👋🏻 → strip (modificateur + emoji)
    - ZWJ sequences 👨‍👩‍👧 → strip (emojis composés)
    - Idempotence : strip(strip(s)) == strip(s)
    - Espaces normalisés (collapse multi-spaces, espace avant
      ponctuation)

  * ``contains_emojis`` :
    - True/False sur cas standards
    - None / vide → False

  * ``strip_emojis_with_metrics`` :
    - Compteur cohérent avec le nb de codepoints supprimés
    - Pas de strip → (text, 0)

  * Politique : symboles non-emoji utiles **ne sont pas strippés**
    (régression-proof : on ne veut pas casser une réponse qui dit
    « 5 ÷ 2 = 2.5 » ou « ©Vancelian 2026 »).
"""

from __future__ import annotations

import pytest

from services.assistance.text_sanitizer import (
    contains_emojis,
    strip_emojis,
    strip_emojis_with_metrics,
)


# ─────────────────────────────────────────────────────────────────────
# strip_emojis — None / vide / fast path
# ─────────────────────────────────────────────────────────────────────


class TestStripEmojisEdgeCases:
    def test_none_is_preserved(self):
        assert strip_emojis(None) is None

    def test_empty_string_is_preserved(self):
        assert strip_emojis("") == ""

    def test_text_without_emoji_returns_identity(self):
        text = "Bonjour, comment allez-vous ?"
        assert strip_emojis(text) == text

    def test_idempotence(self):
        text = "Bonjour 👋 ! Coucou 🌟"
        once = strip_emojis(text)
        twice = strip_emojis(once)
        assert once == twice


# ─────────────────────────────────────────────────────────────────────
# Catégories emoji — strip
# ─────────────────────────────────────────────────────────────────────


class TestStripEmojisCategories:
    @pytest.mark.parametrize(
        "input_text,expected",
        [
            # Emoticons (1F600-1F64F).
            # Note typographie française : on PRÉSERVE l'espace
            # avant `!` `?` `;` `:` (« Salut ! » est correct).
            ("Salut 😀 !", "Salut !"),
            ("Bien 🥲 ouais", "Bien ouais"),
            ("Ok 🙃", "Ok"),
            # Misc Symbols & Pictographs (1F300-1F5FF)
            ("Top 🎉", "Top"),
            ("Brillant 🌟 idée", "Brillant idée"),
            ("Le feu 🔥 est là", "Le feu est là"),
            # Transport & Map (1F680-1F6FF)
            ("Avion 🛫 décollage", "Avion décollage"),
            ("Voiture 🚗", "Voiture"),
            # Supplemental Symbols & Pictographs (1F900-1F9FF)
            ("Cerveau 🧠 actif", "Cerveau actif"),
            # Misc Symbols (2600-26FF)
            ("Soleil ☀ brille", "Soleil brille"),
            ("Attention ⚠ danger", "Attention danger"),
            # Misc Symbols and Arrows (2B00-2BFF) — ⭐ est U+2B50
            ("Etoile ⭐ filante", "Etoile filante"),
            # Dingbats (2700-27BF)
            ("Check ✅ valide", "Check valide"),
            ("Croix ❌ refus", "Croix refus"),
            ("Avion ✈ vol", "Avion vol"),
            # Variation selector + base symbol → strip both
            ("Warning ⚠️ prudent", "Warning prudent"),
            ("Check ✅ ok", "Check ok"),
        ],
    )
    def test_categories(self, input_text, expected):
        assert strip_emojis(input_text) == expected

    def test_regional_indicators_flags(self):
        # 🇫🇷 = U+1F1EB U+1F1F7 (deux regional indicators)
        text = "Vive la France 🇫🇷"
        assert strip_emojis(text) == "Vive la France"

    def test_skin_tone_modifiers(self):
        # 👋🏻 = U+1F44B + U+1F3FB
        text = "Salut 👋🏻 toi"
        assert strip_emojis(text) == "Salut toi"

    def test_zwj_emoji_sequences(self):
        # 👨‍👩‍👧 = U+1F468 U+200D U+1F469 U+200D U+1F467
        text = "Famille 👨‍👩‍👧 unie"
        assert strip_emojis(text) == "Famille unie"

    def test_multiple_emojis_in_one_string(self):
        text = "🎉 Top ! ✅ Réussi 💪 bien joué 🚀"
        result = strip_emojis(text)
        # Collapse des multi-spaces + cleanup espace avant !
        assert "🎉" not in result
        assert "✅" not in result
        assert "💪" not in result
        assert "🚀" not in result
        # Le texte utile reste
        assert "Top" in result
        assert "Réussi" in result
        assert "bien joué" in result


# ─────────────────────────────────────────────────────────────────────
# Préservation symboles tolérés (régression-proof)
# ─────────────────────────────────────────────────────────────────────


class TestPreserveAllowedSymbols:
    """Politique : seuls les emojis/pictogrammes sont strippés. Les
    symboles typographiques utiles (©, ®, ™, ÷, ±, →, …) restent."""

    @pytest.mark.parametrize(
        "text",
        [
            "©Vancelian 2026",
            "Marque® déposée",
            "Brand™ exclusive",
            "Calcul : 5 ÷ 2 = 2.5",
            "Marge : ± 0.5 %",
            "Variation : 100 → 105",
            "Approx : ≈ 3.14",
            "Plus grand : 10 ≥ 5",
            "Différent : a ≠ b",
            "Infini : ∞",
            "Racine : √2",
            "Somme : ∑(x)",
            "Bonjour, l'éditeur — c'est œuvré !",
            "Phrase « avec guillemets » française.",
            "Sigle : SCPI / FCPI / FIP …",
            "Note : voir page 3.",
            "Prix : 1 234,56 €",
            "Devise USD $, GBP £, JPY ¥",
            "Symbole pourcent : 12,5 %",
            "Section §3.2 ; §4.1.",
        ],
    )
    def test_preserves_typographic_symbols(self, text):
        # Aucun caractère ne doit être supprimé.
        assert strip_emojis(text) == text

    def test_french_accents_preserved(self):
        text = (
            "Café à l'éclair — déjà mangé. "
            "Œuvre œnologique. Maïs naïf cigüe."
        )
        assert strip_emojis(text) == text

    def test_arrows_simple_preserved(self):
        # Flèches U+2190-U+2199 (block Arrows, hors range emoji).
        text = "Cliquer ← retour, → avance, ↑ haut, ↓ bas, ↔ axe."
        assert strip_emojis(text) == text


# ─────────────────────────────────────────────────────────────────────
# Espaces normalisés
# ─────────────────────────────────────────────────────────────────────


class TestSpaceNormalization:
    def test_collapse_multi_spaces_after_strip(self):
        text = "Foo 🎉 bar"
        # Sans normalisation : "Foo  bar" (deux espaces)
        # Avec : "Foo bar"
        result = strip_emojis(text)
        assert result == "Foo bar"
        assert "  " not in result

    def test_french_punctuation_space_preserved(self):
        """Typographie française : on conserve l'espace avant `!`,
        `?`, `;`, `:`. Le sanitizer ne doit PAS supprimer ces
        espaces (régression-proof)."""
        text = "Phrase 🎉 ! Suite 🌟 ?"
        result = strip_emojis(text)
        # L'emoji est strippé, l'espace avant `!` et `?` reste.
        assert result == "Phrase ! Suite ?"

    def test_trailing_emoji_no_trailing_space(self):
        text = "Salut 👋"
        assert strip_emojis(text) == "Salut"

    def test_leading_emoji_no_leading_space(self):
        text = "🎉 Top"
        assert strip_emojis(text) == "Top"

    def test_no_change_when_no_emoji(self):
        # Pas de strip → pas de normalisation parasite (fast path).
        text = "Hello  world  with   spaces."
        assert strip_emojis(text) == text


# ─────────────────────────────────────────────────────────────────────
# contains_emojis
# ─────────────────────────────────────────────────────────────────────


class TestContainsEmojis:
    @pytest.mark.parametrize(
        "text,expected",
        [
            (None, False),
            ("", False),
            ("Bonjour", False),
            ("Bonjour 👋", True),
            ("✅ ok", True),
            ("⚠️ attention", True),
            ("Café à l'éclair", False),
            ("Calcul ÷", False),  # ÷ n'est pas un emoji
            ("©Vancelian", False),
        ],
    )
    def test_contains_emojis(self, text, expected):
        assert contains_emojis(text) is expected


# ─────────────────────────────────────────────────────────────────────
# strip_emojis_with_metrics
# ─────────────────────────────────────────────────────────────────────


class TestStripEmojisWithMetrics:
    def test_no_emoji_returns_zero(self):
        cleaned, n = strip_emojis_with_metrics("Hello world")
        assert cleaned == "Hello world"
        assert n == 0

    def test_none_returns_zero(self):
        cleaned, n = strip_emojis_with_metrics(None)
        assert cleaned is None
        assert n == 0

    def test_single_emoji_counts_one(self):
        cleaned, n = strip_emojis_with_metrics("Salut 👋")
        assert cleaned == "Salut"
        assert n == 1

    def test_three_emojis_count_three(self):
        cleaned, n = strip_emojis_with_metrics("🎉 Top ✅ ok 🚀")
        assert n == 3
        for emoji in ("🎉", "✅", "🚀"):
            assert emoji not in cleaned

    def test_zwj_sequence_counts_components(self):
        """Une séquence ZWJ comme 👨‍👩‍👧 est composée de plusieurs
        codepoints (3 emojis + 2 ZWJ). Le compteur reflète le nb
        de codepoints individuellement strippés (pas le concept
        « 1 emoji visuel »). C'est une convention assumée du module."""
        text = "👨‍👩‍👧"
        cleaned, n = strip_emojis_with_metrics(text)
        assert cleaned == ""
        assert n >= 3  # au minimum les 3 emojis (sans compter ZWJ)


# ─────────────────────────────────────────────────────────────────────
# Cohérence avec contains_emojis
# ─────────────────────────────────────────────────────────────────────


class TestSelfConsistency:
    @pytest.mark.parametrize(
        "text",
        [
            "Plain text",
            "🎉 Festive",
            "Mix 🚀 of ✅ tokens",
            "©Vancelian — déjà 2026",
            None,
        ],
    )
    def test_contains_implies_strip_changes(self, text):
        """Si contains_emojis(t) est True, alors strip_emojis(t) doit
        modifier le texte (et inversement)."""
        had = contains_emojis(text)
        cleaned = strip_emojis(text)
        if had:
            assert cleaned != text
        else:
            assert cleaned == text
