"""Tests unitaires — neutralisation des liens article non fiables."""

from services.assistance.assistant_output_sanitize import (
    strip_phantom_cta_invitations,
    strip_untrusted_article_links,
)


def test_strip_markdown_article_links_keeps_label():
    raw = (
        "Voir [Comment ça marche ?]"
        "(vancelian://app/article/fake-slug) pour plus d'infos."
    )
    out, n = strip_untrusted_article_links(raw)
    assert n == 1
    assert "vancelian://" not in out
    assert "Comment ça marche ?" in out


def test_trusted_slug_keeps_markdown_link():
    raw = (
        "Voir [Titre analysis]"
        "(vancelian://app/article/real-slug) pour plus."
    )
    out, n = strip_untrusted_article_links(
        raw, trusted_slugs={"real-slug"}
    )
    assert n == 0
    assert out == raw
    assert "vancelian://app/article/real-slug" in out


def test_strip_markdown_case_insensitive():
    raw = "[x](VANCELIAN://app/article/Y)"
    out, n = strip_untrusted_article_links(raw)
    assert n == 1
    assert out == "x"


def test_strip_bare_url():
    raw = "Lien brut vancelian://app/article/foo/bar ici"
    out, n = strip_untrusted_article_links(raw)
    assert n == 1
    assert "vancelian://" not in out


def test_trusted_bare_url_kept():
    raw = "Voir vancelian://app/article/real-slug pour la suite."
    out, n = strip_untrusted_article_links(
        raw, trusted_slugs={"real-slug"}
    )
    assert n == 0
    assert "vancelian://app/article/real-slug" in out


def test_idempotent_and_no_false_positive_instrument():
    raw = "Ouvre [BTC](vancelian://app/instrument/BTC/buy)"
    out, n = strip_untrusted_article_links(raw)
    assert n == 0
    assert out == raw


def test_strip_phantom_invite_closing_adds_fallback_links():
    raw = (
        "Voici la procédure.\n\n"
        "Si vous souhaitez voir vos transactions ou effectuer un dépôt, "
        "je vous invite à cliquer sur le bouton ci-dessous."
    )
    out, n = strip_phantom_cta_invitations(raw)
    assert n == 1
    assert "bouton ci-dessous" not in out.lower()
    assert "vancelian://app/deposit" in out
    assert "vancelian://app/transactions" in out


def test_strip_phantom_reverts_if_would_empty():
    raw = "Cliquez sur le bouton ci-dessous pour continuer."
    out, n = strip_phantom_cta_invitations(raw)
    assert n == 0
    assert out == raw


def test_strip_phantom_no_double_fallback_links():
    raw = (
        "Dépôt possible.\n\n"
        "Le bouton ci-dessous vous aide. "
        "[Dépôt](vancelian://app/deposit)"
    )
    out, n = strip_phantom_cta_invitations(raw)
    assert n >= 1
    assert out.count("vancelian://app/deposit") >= 1
