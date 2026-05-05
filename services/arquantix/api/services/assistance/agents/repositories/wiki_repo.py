"""Repository de la base de connaissance markdown du wiki produit — Phase 2.

Lit le filesystem ``services/assistance/data/wiki/`` (243 fiches MD
importées en Phase 1 depuis le vault Obsidian source). Aucun accès DB,
aucun appel LLM dans ce module.

──────────────────────────────────────────────────────────────────────
Sources de vérité (rappel)
──────────────────────────────────────────────────────────────────────

Le wiki MD **complète** la table SQL ``product_knowledge`` :

  * ``product_knowledge`` (10 fiches courtes canoniques) — citation
    littérale par les sub-agents compliance via ``consult_specialist``.
  * Wiki MD (243 fiches) — couverture large : FAQ produits + transverses
    (account, transfers-cards, legal-compliance, …).

Cf. ``docs/arquantix/PRODUCT_AGENT.md`` §9.1 et
``docs/arquantix/product-wiki/README.md``.

──────────────────────────────────────────────────────────────────────
Structure attendue du filesystem
──────────────────────────────────────────────────────────────────────

::

    services/assistance/data/wiki/
    ├── index.md                  (catalog humain — non chargé par ce repo)
    ├── chatbot-spec.md           (réf — non chargé)
    ├── system-prompt-v2.md       (réf — non chargé)
    ├── log.md                    (réf — non chargé)
    ├── faq/<category>/<slug>.md  (222 fiches client-facing)
    ├── concepts/<slug>.md        (7 fiches transverses)
    ├── entities/<slug>.md        (8 fiches partenaires)
    └── policies/<slug>.md        (2 fiches policy)

Chaque fiche markdown commence par un frontmatter YAML-like délimité
par ``---`` :

::

    ---
    title: "Are there any risks of capital loss?"
    slug: are-there-any-risks-of-capital-loss
    category: savings
    audience: client
    status: verified
    last_reviewed: 2026-04-12
    sources:
      - raw/<filename>
    related:
      - <other-page>.md
    tags: [tag1, tag2]
    questions:
      - <question phrasing #1>
      - ... 5–8 total
    ---

    # <Title>
    ## Short answer
    ...
    ## Details
    ...

──────────────────────────────────────────────────────────────────────
Garanties
──────────────────────────────────────────────────────────────────────

  * **Best-effort** — toute erreur d'I/O ou de parsing renvoie ``None``
    ou ``[]``. Jamais d'exception remontée au caller (cf. convention
    ``MULTI_AGENTS_RUNTIME.md`` § 2 — un tool ne lève pas).
  * **Cache RAM** thread-safe avec TTL 5 min. Premier hit après reload
    → relit l'intégralité du dossier (243 fichiers, ≤ 2 MB) — coût
    ~150 ms en moyenne. Tous les hits suivants sont O(1) ou O(N) sans
    I/O.
  * **Sandbox** : le tool caller ne reçoit jamais le ``Path`` brut, juste
    des dicts JSON-serializable. Pas de path traversal possible (slug
    et category validés contre les fiches effectivement présentes).
  * **Aucune PII** — par construction (validé éditorial Jean Guillou,
    cf. ``CLAUDE.md`` du vault source §"Writing rules for Chatbot-facing
    content").

──────────────────────────────────────────────────────────────────────
Choix de design — pas de YAML lib
──────────────────────────────────────────────────────────────────────

Le repo n'a pas ``PyYAML`` en dépendance. Comme le frontmatter du wiki
respecte un schéma **très contraint** (scalaires, listes plates ``-``,
listes inline ``[a, b]``, pas de nesting, pas d'anchors), on utilise un
parseur maison de ~80 lignes. C'est volontaire :

  * pas de nouvelle dépendance Python (charte
    ``arquantix-environment-stability``),
  * comportement déterministe testable,
  * tolérant aux fiches mal formées (on retourne ce qu'on peut).
"""

from __future__ import annotations

import logging
import re
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Constantes structurelles
# ──────────────────────────────────────────────────────────────────────


# Racine du wiki — relative au package ``services/assistance/``.
# Resolution : ``…/services/assistance/agents/repositories/wiki_repo.py``
# → on remonte de 3 niveaux pour atteindre ``services/assistance/``,
# puis on descend dans ``data/wiki``.
WIKI_ROOT: Path = Path(__file__).resolve().parent.parent.parent / "data" / "wiki"


# Catégories FAQ valides (validation côté tools, anti path-traversal).
# Doit rester en phase avec ``docs/arquantix/product-wiki/README.md``.
FAQ_CATEGORIES: frozenset[str] = frozenset(
    {
        "savings",
        "exclusive-offers",
        "crypto",
        "aktio",
        "memberships",
        "account",
        "transfers-cards",
        "legal-compliance",
        "company",
        "business",
        "affiliate-partner",
        "b2b-agent",
        # Cognitive Bot v4 — Lot 4 (2026-05-04) : seed dédié à l'agent
        # ``trust`` (rassurance régulation/custody/sécurité). Distinct
        # de ``legal-compliance`` (référentiel juridique) — ces fiches
        # sont écrites avec un angle ACK émotionnel + factualité.
        "trust-security",
        "other",
    }
)


# Dossiers top-level non-FAQ (concepts transverses, fiches entités, policies).
NON_FAQ_DIRS: frozenset[str] = frozenset({"concepts", "entities", "policies"})


# Toutes catégories valides pour ``read_wiki_page`` (FAQ + non-FAQ).
ALL_CATEGORIES: frozenset[str] = FAQ_CATEGORIES | NON_FAQ_DIRS


# Cache TTL en secondes. À 5 min, le wiki MD peut être édité à chaud
# par un dev sans avoir à redémarrer l'API (utile en dev local).
_CACHE_TTL_SECONDS: float = 300.0


# ──────────────────────────────────────────────────────────────────────
# Modèle de page parsée
# ──────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class WikiPage:
    """Représentation immutable d'une fiche markdown parsée.

    Attributs principaux :
      * ``category``  — sous-dossier de premier niveau (ex. ``savings``).
      * ``slug``      — nom du fichier sans extension.
      * ``title``     — frontmatter ``title:`` (ou slug si absent).
      * ``status``    — ``draft`` | ``verified`` | ``stale`` (défaut ``draft``).
      * ``questions`` — liste des phrasings client (utilisée pour le
        retrieval keyword).
      * ``short_answer`` — section ``## Short answer`` (≤ 4 phrases).
      * ``details``   — section ``## Details`` (markdown plein).
    """

    category: str
    slug: str
    title: str
    status: str
    audience: str
    last_reviewed: str
    questions: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    related: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    short_answer: str | None = None
    details: str | None = None
    body_markdown: str = ""

    def to_select_dict(self, *, score: float, matched_terms: list[str]) -> dict:
        """Représentation compacte pour ``select_wiki_pages``.

        Volontairement **minimale** : 3 question phrasings de preview
        suffisent au LLM pour décider quelle fiche lire ensuite via
        ``read_wiki_page``. On ne dump jamais le ``body`` ici.
        """
        return {
            "category": self.category,
            "slug": self.slug,
            "title": self.title,
            "status": self.status,
            "matched_questions_preview": list(self.questions[:3]),
            "tags": list(self.tags[:5]),
            "score": round(score, 3),
            "matched_terms": matched_terms[:10],
        }

    def to_read_dict(self) -> dict:
        """Représentation complète pour ``read_wiki_page``.

        Inclut ``short_answer`` + ``details`` + métadonnées éditoriales.
        On exclut le ``body_markdown`` brut pour éviter le bruit (le
        LLM n'a pas besoin du markdown intégral si on lui donne déjà
        les sections séparées).
        """
        return {
            "category": self.category,
            "slug": self.slug,
            "title": self.title,
            "status": self.status,
            "audience": self.audience,
            "last_reviewed": self.last_reviewed,
            "short_answer": self.short_answer,
            "details": self.details,
            "questions": list(self.questions),
            "tags": list(self.tags),
            "related": list(self.related),
            "sources": list(self.sources),
        }


# ──────────────────────────────────────────────────────────────────────
# Parseur de frontmatter (mini-YAML)
# ──────────────────────────────────────────────────────────────────────


_FRONTMATTER_RE = re.compile(
    r"\A---\s*\n(?P<fm>.*?)\n---\s*\n(?P<body>.*)", re.DOTALL
)
_LIST_INLINE_RE = re.compile(r"\A\s*\[(.*)\]\s*\Z")
_KEY_VALUE_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.*)$")


def _strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in {'"', "'"}:
        return s[1:-1]
    return s


def _parse_inline_list(raw: str) -> list[str]:
    """Parse ``[a, b, "c with spaces"]`` → ``["a", "b", "c with spaces"]``."""
    inner = raw.strip()
    if not inner:
        return []
    out: list[str] = []
    # Split simple sur la virgule ; on ne supporte pas les chaînes contenant
    # des virgules dans le wiki actuel (contrainte schéma).
    for token in inner.split(","):
        cleaned = _strip_quotes(token)
        if cleaned:
            out.append(cleaned)
    return out


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Sépare le frontmatter du body.

    Retourne ``({}, original_text)`` si pas de frontmatter ou mal formé.
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm_text = m.group("fm")
    body = m.group("body")

    fm: dict[str, object] = {}
    current_key: str | None = None
    current_list: list[str] | None = None

    for raw_line in fm_text.splitlines():
        # Extension list (ligne commençant par "  - ")
        list_item = re.match(r"^\s+-\s+(.*)$", raw_line)
        if list_item is not None and current_list is not None:
            current_list.append(_strip_quotes(list_item.group(1)))
            continue

        # Sinon : clôture la liste ouverte si présente
        if current_list is not None and current_key is not None:
            fm[current_key] = current_list
            current_list = None
            current_key = None

        kv = _KEY_VALUE_RE.match(raw_line)
        if kv is None:
            continue
        key = kv.group(1).strip()
        value = kv.group(2).strip()

        if value == "":
            # Liste multi-lignes qui suit
            current_key = key
            current_list = []
            continue

        # Liste inline ?
        inline = _LIST_INLINE_RE.match(value)
        if inline is not None:
            fm[key] = _parse_inline_list(inline.group(1))
            continue

        # Scalaire simple
        fm[key] = _strip_quotes(value)

    # Clôture finale d'une liste qui irait jusqu'à la fin
    if current_list is not None and current_key is not None:
        fm[current_key] = current_list

    return fm, body


_SECTION_HEADER_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def _extract_section(body: str, section_name: str) -> str | None:
    """Extrait le contenu de ``## <section_name>`` jusqu'à la prochaine
    section ``##`` ou fin de fichier. Insensible à la casse.
    """
    if not body or not section_name:
        return None
    target = section_name.strip().lower()
    matches = list(_SECTION_HEADER_RE.finditer(body))
    for i, m in enumerate(matches):
        header = m.group(1).strip().lower()
        # Match exact OU "starts with" pour tolérer "Short answer" vs
        # "Short answer (overview)".
        if header == target or header.startswith(target + " "):
            start = m.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
            return body[start:end].strip()
    return None


# ──────────────────────────────────────────────────────────────────────
# Cache de pages (thread-safe, TTL 5 min)
# ──────────────────────────────────────────────────────────────────────


@dataclass
class _Cache:
    pages: tuple[WikiPage, ...] = ()
    by_key: dict[tuple[str, str], WikiPage] = field(default_factory=dict)
    loaded_at: float = 0.0


_cache: _Cache = _Cache()
_cache_lock = threading.Lock()


def _is_cache_fresh() -> bool:
    return _cache.pages and (time.time() - _cache.loaded_at) < _CACHE_TTL_SECONDS


def _load_page(category: str, slug: str, path: Path) -> WikiPage | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        logger.warning(
            "wiki_repo: unreadable file %s/%s.md (path=%s)",
            category,
            slug,
            path,
        )
        return None

    fm, body = _parse_frontmatter(text)

    def _str_field(key: str, default: str = "") -> str:
        v = fm.get(key)
        return v if isinstance(v, str) else default

    def _list_field(key: str) -> tuple[str, ...]:
        v = fm.get(key)
        if isinstance(v, list):
            return tuple(str(x) for x in v if x is not None and str(x).strip())
        if isinstance(v, str) and v.strip():
            return (v.strip(),)
        return ()

    return WikiPage(
        category=category,
        slug=slug,
        title=_str_field("title", default=slug),
        status=_str_field("status", default="draft"),
        audience=_str_field("audience", default="client"),
        last_reviewed=_str_field("last_reviewed", default=""),
        questions=_list_field("questions"),
        sources=_list_field("sources"),
        related=_list_field("related"),
        tags=_list_field("tags"),
        short_answer=_extract_section(body, "Short answer"),
        details=_extract_section(body, "Details"),
        body_markdown=body.strip(),
    )


def _scan_filesystem() -> list[WikiPage]:
    """Walk ``WIKI_ROOT`` et parse toutes les fiches .md."""
    pages: list[WikiPage] = []
    if not WIKI_ROOT.exists():
        logger.warning("wiki_repo: WIKI_ROOT does not exist at %s", WIKI_ROOT)
        return pages

    # FAQ
    faq_root = WIKI_ROOT / "faq"
    if faq_root.exists():
        for cat_dir in sorted(p for p in faq_root.iterdir() if p.is_dir()):
            if cat_dir.name not in FAQ_CATEGORIES:
                logger.info(
                    "wiki_repo: skipping unknown FAQ category %r", cat_dir.name
                )
                continue
            for md_file in sorted(cat_dir.glob("*.md")):
                page = _load_page(cat_dir.name, md_file.stem, md_file)
                if page is not None:
                    pages.append(page)

    # Non-FAQ top-level (concepts, entities, policies)
    for top_name in sorted(NON_FAQ_DIRS):
        top_dir = WIKI_ROOT / top_name
        if not top_dir.exists():
            continue
        for md_file in sorted(top_dir.glob("*.md")):
            page = _load_page(top_name, md_file.stem, md_file)
            if page is not None:
                pages.append(page)

    return pages


def _refresh_cache() -> None:
    """Recharge l'intégralité du wiki en mémoire. À ne pas appeler depuis
    le hot path du tool — passer par ``_get_pages_cached``.
    """
    pages = _scan_filesystem()
    by_key = {(p.category, p.slug): p for p in pages}
    _cache.pages = tuple(pages)
    _cache.by_key = by_key
    _cache.loaded_at = time.time()
    logger.info(
        "wiki_repo: cache refreshed — %d pages loaded from %s",
        len(pages),
        WIKI_ROOT,
    )


def _get_pages_cached() -> tuple[WikiPage, ...]:
    """Retourne le snapshot courant du cache, refresh si TTL expiré."""
    with _cache_lock:
        if not _is_cache_fresh():
            try:
                _refresh_cache()
            except Exception:  # noqa: BLE001
                logger.exception("wiki_repo: cache refresh failed")
        return _cache.pages


def _get_by_key_cached() -> dict[tuple[str, str], WikiPage]:
    with _cache_lock:
        if not _is_cache_fresh():
            try:
                _refresh_cache()
            except Exception:  # noqa: BLE001
                logger.exception("wiki_repo: cache refresh failed")
        return _cache.by_key


def invalidate_cache() -> None:
    """Force un reload au prochain appel. Utile pour les tests ou un
    futur endpoint admin.
    """
    with _cache_lock:
        _cache.pages = ()
        _cache.by_key = {}
        _cache.loaded_at = 0.0


# ──────────────────────────────────────────────────────────────────────
# Tokenisation + scoring keyword (retrieval Karpathy-style)
# ──────────────────────────────────────────────────────────────────────


# Stopwords FR + EN (mots trop fréquents, pas discriminants).
_STOPWORDS: frozenset[str] = frozenset(
    {
        # FR
        "le",
        "la",
        "les",
        "un",
        "une",
        "des",
        "de",
        "du",
        "et",
        "ou",
        "au",
        "aux",
        "ce",
        "cette",
        "ces",
        "mon",
        "ma",
        "mes",
        "ton",
        "ta",
        "tes",
        "son",
        "sa",
        "ses",
        "qui",
        "que",
        "quoi",
        "où",
        "quand",
        "comment",
        "pourquoi",
        "est",
        "sont",
        "ils",
        "elles",
        "elle",
        "nous",
        "vous",
        "pas",
        "ne",
        "pour",
        "par",
        "dans",
        "sur",
        "sous",
        "avec",
        "sans",
        "mais",
        "donc",
        "car",
        "alors",
        "puis",
        "très",
        "plus",
        "moins",
        "tout",
        "tous",
        "toute",
        "toutes",
        "non",
        "oui",
        "peut",
        "peux",
        "puis",
        "veux",
        "veut",
        # EN
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "on",
        "at",
        "by",
        "for",
        "with",
        "without",
        "this",
        "that",
        "these",
        "those",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "what",
        "where",
        "when",
        "why",
        "how",
        "who",
        "which",
        "whom",
        "do",
        "does",
        "did",
        "can",
        "could",
        "should",
        "would",
        "may",
        "might",
        "will",
        "shall",
        "from",
        "into",
        "out",
        "about",
        "than",
        "then",
        "such",
        "any",
        "all",
        "some",
        "more",
        "less",
        "few",
        "many",
        "much",
        "very",
        "not",
        "no",
        "yes",
        "you",
        "your",
        "yours",
        "they",
        "their",
        "theirs",
    }
)


_TOKEN_RE = re.compile(r"[\w'-]+", re.UNICODE)


def _tokenize(text: str) -> list[str]:
    """Tokenisation simple : lowercase, strip apostrophes/tirets de bord,
    élimine les stopwords et les tokens < 3 caractères.
    """
    if not text:
        return []
    raw = text.lower()
    tokens: list[str] = []
    for m in _TOKEN_RE.finditer(raw):
        tok = m.group(0).strip("'-")
        if len(tok) < 3:
            continue
        if tok in _STOPWORDS:
            continue
        tokens.append(tok)
    return tokens


def _score_page(page: WikiPage, q_tokens: set[str]) -> tuple[float, list[str]]:
    """Retourne ``(score, matched_terms)`` d'une page contre les tokens
    de la question.

    Heuristique :
      * +1.0 par token matché dans une phrasing ``questions:``
      * +0.5 par token matché dans le ``title``
      * +0.3 par token matché dans les ``tags``
      * Bonus ``status: verified`` ×1.2, malus ``stale`` ×0.5
      * Pas d'IDF — sur 243 fiches, le bruit est gérable et l'absence
        de corpus statistique stable simplifie les tests.
    """
    if not q_tokens:
        return 0.0, []

    score = 0.0
    matched: set[str] = set()

    for question in page.questions:
        q_text_tokens = set(_tokenize(question))
        overlap = q_tokens & q_text_tokens
        if overlap:
            score += float(len(overlap))
            matched |= overlap

    title_tokens = set(_tokenize(page.title))
    overlap = q_tokens & title_tokens
    if overlap:
        score += 0.5 * len(overlap)
        matched |= overlap

    for tag in page.tags:
        tag_tokens = set(_tokenize(tag))
        overlap = q_tokens & tag_tokens
        if overlap:
            score += 0.3 * len(overlap)
            matched |= overlap

    if page.status == "verified":
        score *= 1.2
    elif page.status == "stale":
        score *= 0.5

    return score, sorted(matched)


# ──────────────────────────────────────────────────────────────────────
# API publique
# ──────────────────────────────────────────────────────────────────────


def fetch_page(*, category: str, slug: str) -> WikiPage | None:
    """Récupère une fiche par ``category`` + ``slug``.

    Retourne ``None`` si :
      * args vides,
      * category inconnue (anti path-traversal — pas de risque réel
        vu le pattern d'accès, mais défense en profondeur),
      * fiche absente du filesystem.
    """
    if not category or not slug:
        return None
    if category not in ALL_CATEGORIES:
        return None
    return _get_by_key_cached().get((category, slug))


def list_pages(
    *, category: str | None = None, limit: int = 50
) -> list[dict[str, str]]:
    """Liste minimale ``[{category, slug, title, status}]``.

    Utile pour debug / introspection côté admin futur. Pas de body.
    """
    safe_limit = max(1, min(int(limit or 50), 500))
    pages = _get_pages_cached()
    if category:
        if category not in ALL_CATEGORIES:
            return []
        pages = tuple(p for p in pages if p.category == category)
    return [
        {
            "category": p.category,
            "slug": p.slug,
            "title": p.title,
            "status": p.status,
        }
        for p in pages[:safe_limit]
    ]


def select_pages(
    *,
    question: str,
    top_k: int = 5,
    category: str | None = None,
    min_score: float = 0.5,
) -> list[tuple[WikiPage, float, list[str]]]:
    """Retourne les top_k fiches les mieux scorées contre la question.

    Args:
        question: phrase utilisateur (FR ou EN).
        top_k: 1..10 (clampé).
        category: filtre optionnel sur ``WikiPage.category``.
        min_score: seuil sous lequel on n'inclut pas la fiche
            (évite les matches accidentels sur 1 stopword survivant).

    Returns:
        Liste ``[(page, score, matched_terms), ...]`` triée par score
        décroissant. Liste vide si question vide ou aucun match.

    Notes:
        Pas d'exception. Pas de side-effect. Le caller (un tool runtime)
        attend un comportement déterministe.
    """
    if not question or not question.strip():
        return []

    # Clamp top_k explicitement (le `int(x or 5)` ne marche pas pour 0).
    if top_k is None:
        safe_top_k = 5
    else:
        safe_top_k = max(1, min(int(top_k), 10))
    q_tokens = set(_tokenize(question))
    if not q_tokens:
        return []

    pages = _get_pages_cached()
    if category:
        if category not in ALL_CATEGORIES:
            return []
        pages = tuple(p for p in pages if p.category == category)

    scored: list[tuple[WikiPage, float, list[str]]] = []
    for page in pages:
        score, matched = _score_page(page, q_tokens)
        if score >= min_score:
            scored.append((page, score, matched))

    scored.sort(key=lambda x: (-x[1], x[0].category, x[0].slug))
    return scored[:safe_top_k]


def total_pages_loaded() -> int:
    """Nombre de fiches actuellement en cache (pour debug / health)."""
    return len(_get_pages_cached())


def all_pages() -> tuple["WikiPage", ...]:
    """Retourne **toutes** les fiches indexées (cache TTL).

    API publique exposée pour ``wiki_llm_retriever`` qui a besoin de
    construire un catalogue compact (1 ligne / fiche) à passer au LLM
    retriever. Hot path → on retourne directement le tuple cached
    sans copie (les WikiPage sont immutables côté API publique).
    """
    return _get_pages_cached()


def _cache_ttl_seconds() -> float:
    """Expose le TTL du cache wiki à d'autres modules qui veulent
    aligner leur cache avec celui du repo (cf. wiki_llm_retriever).
    """
    return _CACHE_TTL_SECONDS
