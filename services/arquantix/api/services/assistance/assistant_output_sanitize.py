"""Post-traitement du Markdown assistant avant persistance SSE.

Phase FAQ intégrité (2026-05-06) — les deep-links ``vancelian://app/article/{slug}``
dans le corps du message **ne sont pas validés** par le runtime (contrairement
aux options ``ask_user_question`` et aux ``actions`` d'embeds). Le modèle peut
donc inventer des slugs inexistants. On neutralise ces liens Markdown en
conservant le libellé visible (texte plat), et on trace le nombre de
suppressions en log.

Si le tour émet un embed ``featured_articles_list`` (slugs issus de la base),
passer ``trusted_slugs`` à ``strip_untrusted_article_links`` : les liens dont
le slug est dans cet ensemble sont **conservés** afin que le markdown et le
widget pointent vers les mêmes articles.

Les URLs canoniques d'ouverture d'article restent aussi portées par le widget
``featured_articles_list`` émis via ``show_featured_articles``.
"""

from __future__ import annotations

import re
from typing import AbstractSet, List, Optional, Tuple
from urllib.parse import unquote

# [libellé](vancelian://app/article/slug-ici) — groupe 2 = URL.
_ARTICLE_MARKDOWN_LINK = re.compile(
    r"\[([^\]]*)\]\(\s*(vancelian://app/article/[^)]*)\)",
    flags=re.IGNORECASE,
)

# Rareté : lien « brut » dans le flux (pas du Markdown valide).
_BARE_ARTICLE_VANCELIAN = re.compile(
    r"vancelian://app/article/[^\s\)\]>]+",
    flags=re.IGNORECASE,
)


def _extract_slug_from_vancelian_article_url(url: str) -> Optional[str]:
    u = url.strip()
    m = re.match(r"vancelian://app/article/([^)\s?#]+)", u, re.IGNORECASE)
    if not m:
        return None
    return unquote(m.group(1)).strip().rstrip("/")


# ── Promesses de bouton sans `ask_user_question` (Cognitive / compliance) ──
# Le client ne voit de QCM/boutons que si le runtime a émis `choices`.
# Le modèle invente souvent une phrase de clôture « cliquez sur le bouton ».

_RX_PHANTOM_STRIPS: List[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"(?:\n{2,}|\A)\s*"
            r"(?:Si vous souhaitez|Si tu souhaites|S'il vous plaît|S'il te plaît)\b[\s\S]{0,520}?"
            r"(?:bouton ci-dessous|le bouton ci-dessous|cliquer sur le bouton|"
            r"cliquez sur le bouton|sur le bouton ci-dessous)\b[\s\S]{0,100}?[.!?]\s*",
            re.IGNORECASE | re.MULTILINE,
        ),
        "invite_si_bouton",
    ),
    (
        re.compile(
            r"(?:\n|^)\s*[^\n]{0,320}?"
            r"(?:j['’]?\s?ai\b.?)?(?:je vous invite|je t['’]?invite|nous vous invitons)\b"
            r"[\s\S]{0,200}?"
            r"(?:bouton ci-dessous|le bouton|cliquer sur le bouton|cliquez sur le bouton)\b"
            r"[\s\S]{0,120}?[.!?]\s*",
            re.IGNORECASE | re.MULTILINE,
        ),
        "invite_je_bouton",
    ),
    (
        re.compile(
            r"(?:\n|^)\s*[^\n]{0,240}?"
            r"\b(?:cliquez sur le bouton|cliquer sur le bouton|"
            r"click on the button|tap the button below)\b"
            r"[^\n.!?]{0,120}[.!?]?\s*",
            re.IGNORECASE | re.MULTILINE,
        ),
        "click_button_line",
    ),
    (
        re.compile(
            r"(?:\n|^)\s*[^\n]{0,320}?"
            r"\b(?:le )?bouton ci-dessous\b[^\n.!?]{0,160}[.!?]\s*",
            re.IGNORECASE | re.MULTILINE,
        ),
        "bouton_ci_dessous_line",
    ),
]

# Liens profonds whitelistés (alignés `action_cta_catalog.deep_link_template`).
_FALLBACK_APP_LINKS = (
    "\n\n*Raccourcis (app mobile) :* "
    "[Dépôt](vancelian://app/deposit) · "
    "[Transactions](vancelian://app/transactions)"
)


def strip_phantom_cta_invitations(text: str) -> Tuple[str, int]:
    """Supprime les phrases qui promettent un bouton sans qu'un QCM n'ait été émis.

    Utiliser **uniquement** lorsque le tour ne se termine pas par un event
    ``choices`` (``ask_user_question``). Sinon on laisserait le client sans
    bouton malgré le texte.

    Retourne ``(nouveau_texte, nombre_de_blocs_supprimés)``. Idempotent.
    Optionnellement ajoute une ligne avec **deux** liens Markdown
    ``vancelian://app/…`` whitelistés lorsque le texte d'origine évoquait
    dépôt / transactions — pour offrir une alternative au tap sur bouton.
    """
    if not text or not text.strip():
        return text, 0

    original_lower = text.lower()
    t = text
    removals = 0

    changed = True
    while changed:
        changed = False
        for rx, _tag in _RX_PHANTOM_STRIPS:
            new = rx.sub("\n", t)
            if new != t:
                removals += 1
                t = new
                changed = True
                break

    t = re.sub(r"\n{3,}", "\n\n", t).strip()

    # Phrases finales souvent sur 1–3 lignes sans double saut de paragraphe avant.
    if removals == 0:
        lines = t.split("\n")
        max_k = min(6, len(lines))
        for k in range(max_k, 0, -1):
            chunk = "\n".join(lines[-k:]).lower()
            if not chunk.strip():
                continue
            looks_phantom = (
                "bouton ci-dessous" in chunk
                or "cliquez sur le bouton" in chunk
                or "cliquer sur le bouton" in chunk
                or "click on the button" in chunk
            ) and (
                "invite" in chunk
                or "souhaitez" in chunk
                or "souhaites" in chunk
                or "cliquez sur le bouton" in chunk
            )
            if looks_phantom and k < len(lines):
                # Ne pas tout effacer : au moins une ligne doit rester.
                t = "\n".join(lines[:-k]).strip()
                removals += 1
                t = re.sub(r"\n{3,}", "\n\n", t).strip()
                break

    if removals == 0:
        return t, 0

    if not t.strip():
        # Ne pas renvoyer un message vide (phrase fantôme = seul contenu).
        return text, 0

    # Pas de doublon si l'agent a déjà injecté ces liens.
    if "vancelian://app/deposit" in t or "vancelian://app/transactions" in t:
        return t, removals

    if re.search(
        r"dép[oô]t|deposit|transaction|virement|retir|withdraw|déposer|voir vos",
        original_lower,
    ):
        t = f"{t}{_FALLBACK_APP_LINKS}"

    return t, removals


def strip_untrusted_article_links(
    text: str,
    trusted_slugs: AbstractSet[str] | None = None,
) -> Tuple[str, int]:
    """Retire les liens article non vérifiés du Markdown assistant.

    Si ``trusted_slugs`` est fourni (slugs issus de ``featured_articles_list``
    sur le même tour), les liens ``vancelian://app/article/{slug}`` dont le
    slug appartient à l'ensemble sont **conservés**.

    Retourne ``(nouveau_texte, nombre_de_substitutions)``. Idempotent.
    """
    if not text:
        return text, 0

    trusted = frozenset(s.strip() for s in trusted_slugs) if trusted_slugs else frozenset()
    n = 0

    def _md_sub(m: re.Match[str]) -> str:
        nonlocal n
        label = m.group(1).strip()
        url = m.group(2).strip()
        slug = _extract_slug_from_vancelian_article_url(url)
        if slug and slug in trusted:
            return m.group(0)
        n += 1
        return label

    out = _ARTICLE_MARKDOWN_LINK.sub(_md_sub, text)

    def _bare_sub(m: re.Match[str]) -> str:
        nonlocal n
        url = m.group(0)
        slug = _extract_slug_from_vancelian_article_url(url)
        if slug and slug in trusted:
            return url
        n += 1
        return ""

    out = _BARE_ARTICLE_VANCELIAN.sub(_bare_sub, out)
    return out, n


__all__ = [
    "strip_untrusted_article_links",
    "strip_phantom_cta_invitations",
]
