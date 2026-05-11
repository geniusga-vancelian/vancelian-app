"""Tool ``show_featured_articles`` — agents **market** + **advisor** + autres,
autonomy **L0**.

Phase 2c.7 — Carte chat ``featured_articles_list``. Pattern d'embed
**complémentaire** d'un message texte de l'agent (le LLM rédige sa
synthèse, le widget liste 1 à 5 articles à lire — chacun cliquable
vers le lecteur article).

Usage typique :
  - User : *« peux-tu me parler de l'actualité du marché ? »*
  - Agent ``market`` : appelle ``show_featured_articles(kind="NEWS")``
    → carte UI listant 3 articles "à la une" récents, chacun avec
    deep-link ``open_article``.
  - User : *« je veux des analyses sur les tendances macro »* →
    ``show_featured_articles(kind="ANALYSIS", query="macro")``.
  - User : *« note de recherche sur les ETF Bitcoin »* →
    ``show_featured_articles(kind="RESEARCH", query="bitcoin etf")``.

Sources de données (toutes publiques) :
  - Table ``articles`` (gérée par Prisma côté Next.js, lue ici en
    raw SQL pour éviter de redéfinir un modèle SQLAlchemy parallèle).
  - Filtres : ``status='PUBLISHED'``, ``article_type=<kind>``.
  - Tri : ``is_featured DESC, published_at DESC`` puis fallback
    ``published_at DESC`` quand aucun featured.
  - Si ``query`` fournie : filtre LIKE insensible à la casse sur
    titre i18n (``article_i18n.title``) ou sur le slug.

Sécurité :
  - ``kind`` whitelisté strict (NEWS / ANALYSIS / RESEARCH / HELP).
  - ``query`` capée à 80 chars + sanitizée (LIKE escape).
  - ``limit`` borné [1, 5].
  - Deep-links générés via ``action_cta_catalog.build_action`` avec
    ``article_slug`` (jamais d'URL libre).
  - Pas d'anti-tipping-off (articles publics).

Cf. ``docs/arquantix/CHAT_EMBEDS_CATALOG.md`` § 2.4.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import text

from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.assistance.agents.tools.shared.action_cta_catalog import (
    build_action,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────
# Whitelists
# ─────────────────────────────────────────────────────────────────────────

# Mappage kind public → article_type DB (table `articles`). On expose
# au LLM des kinds parlant (NEWS, ANALYSIS, RESEARCH, HELP) qui
# coïncident avec les constantes Prisma. HELP = articles d'aide / FAQ CMS
# (Phase 3 unification, `articleType='HELP'`).
_KIND_TO_ARTICLE_TYPE: dict[str, str] = {
    "NEWS": "NEWS",
    "ANALYSIS": "ANALYSIS",
    "RESEARCH": "RESEARCH",
    "HELP": "HELP",
}

_DEFAULT_LIMIT = 3
_MIN_LIMIT = 1
_MAX_LIMIT = 5
_QUERY_MAX_LEN = 80


# ─────────────────────────────────────────────────────────────────────────
# Spec
# ─────────────────────────────────────────────────────────────────────────


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "show_featured_articles",
        "description": (
            "Affiche un BLOC LISTE D'ARTICLES en complément de ta réponse "
            "texte (1 à 5 entrées ; chaque ligne ouvre le lecteur d’article "
            "in-app — slugs issus de la base de données).\n\n"
            "DÉCLENCHEMENT FAQ — si le client demande une **liste d’articles FAQ**, "
            "le **centre d’aide**, des « articles HELP », « montre les articles », "
            "etc., utilise **`kind=HELP`** avec `limit=5` et un `query` court "
            "déduit du besoin (ou générique vide). Tu ne refuses **pas** ces "
            "demandes sous prétexte d’orienter uniquement vers un site web.\n\n"
            "Réponse éditoriale (NEWS / ANALYSIS / RESEARCH en anglais comme en "
            "français) : couverture visible, titre, date ; même ouverture in-app "
            "`open_article`. Tu peux citer un ou plusieurs articles du résultat "
            "outil avec un lien Markdown **exact** "
            "`[titre ou extrait](vancelian://app/article/<slug>)` en reprenant "
            "le **slug** renvoyé pour chaque entrée (ne jamais inventer de slug)."
            "\n\n"
            "RÈGLE : tu rédiges aussi un court texte d’introduction au-dessus du "
            "widget ; le widget porte les liens cliquables vérifiés.\n"
            "\n"
            "PARAM `kind` (obligatoire, whitelist stricte) :\n"
            "- `NEWS` → actualités marché récentes ;\n"
            "- `ANALYSIS` → analyses & opinions de la rédaction ;\n"
            "- `RESEARCH` → notes de recherche ;\n"
            "- `HELP` → **aide & FAQ CMS** (articles publiés `article_type=HELP`). "
            "À utiliser quand tu veux proposer des lectures vérifiables : "
            "le widget émet les **seuls** deep-links article primaires. Pour le "
            "texte, si tu cites un article du résultat, tu peux ajouter "
            "`[libellé](vancelian://app/article/<slug>)` avec le **slug** "
            "fourni par l’outil — sinon pas de lien article dans le markdown.\n"
            "\n"
            "PARAM `query` (optionnel) : mots-clés du sujet "
            "(ex. \"bitcoin\", \"taux\", \"etf\"). Best-effort sur "
            "titres et slugs. N'invente pas un sujet : si la demande "
            "user est vague, omets `query` pour récupérer les articles "
            "à la une les plus récents.\n"
            "\n"
            "PARAM `limit` (optionnel) : 1 à 5, défaut 3. Idempotent."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["NEWS", "ANALYSIS", "RESEARCH", "HELP"],
                    "description": (
                        "Type d'article à afficher. NEWS = actu, "
                        "ANALYSIS = analyses/opinions, "
                        "RESEARCH = notes de recherche, "
                        "HELP = aide & FAQ (liens article validés serveur)."
                    ),
                },
                "query": {
                    "type": "string",
                    "description": (
                        "Mots-clés du sujet (≤ 80 caractères). Optionnel."
                    ),
                },
                "limit": {
                    "type": "integer",
                    "description": "Nombre d'articles (1-5, défaut 3).",
                    "minimum": 1,
                    "maximum": 5,
                },
            },
            "required": ["kind"],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "market",
}


# ─────────────────────────────────────────────────────────────────────────
# Implémentation
# ─────────────────────────────────────────────────────────────────────────


def execute(
    ctx: ToolContext,
    *,
    kind: Optional[str] = None,
    query: Optional[str] = None,
    limit: Optional[int] = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    raw_kind = (kind or "").strip().upper()
    if raw_kind not in _KIND_TO_ARTICLE_TYPE:
        return {
            "error": "invalid_kind",
            "supported_kinds": sorted(_KIND_TO_ARTICLE_TYPE.keys()),
        }
    article_type = _KIND_TO_ARTICLE_TYPE[raw_kind]

    eff_limit = _DEFAULT_LIMIT
    if isinstance(limit, int):
        eff_limit = max(_MIN_LIMIT, min(_MAX_LIMIT, limit))

    raw_query = (query or "").strip()
    if len(raw_query) > _QUERY_MAX_LEN:
        raw_query = raw_query[:_QUERY_MAX_LEN]

    rows = _fetch_articles(
        ctx.db,
        article_type=article_type,
        query=raw_query,
        limit=eff_limit,
    )

    if not rows:
        # Fallback : pas d'article correspondant ; le LLM doit expliquer.
        # On n'émet PAS l'embed (cf. règle "tester le rendu vide").
        logger.info(
            "show_featured_articles.empty kind=%s query=%r limit=%d",
            raw_kind,
            raw_query,
            eff_limit,
        )
        return {
            "kind": raw_kind,
            "query": raw_query or None,
            "articles": [],
            "embed_emitted": False,
        }

    items: list[dict[str, Any]] = []
    for row in rows:
        slug = row["slug"]
        action = build_action(
            "open_article", params={"article_slug": slug}
        )
        item: dict[str, Any] = {
            "id": row["id"],
            "slug": slug,
            "title": row["title"],
            "standfirst": row.get("standfirst") or "",
            "cover_url": row.get("cover_url"),
            "published_at": row.get("published_at"),
            "reading_time_minutes": row.get("reading_time_minutes"),
            "author_name": row.get("author_name"),
            "is_featured": bool(row.get("is_featured")),
            "deep_link": action["deep_link"] if action else None,
        }
        items.append(item)

    block_title = _BLOCK_TITLE_BY_KIND.get(raw_kind, "Articles")
    if raw_query:
        block_title = f"{block_title} — {raw_query[:40]}"

    embed: dict[str, Any] = {
        "type": "featured_articles_list",
        "kind": raw_kind,
        "query": raw_query or None,
        "title": block_title,
        "items": items,
    }
    ctx.embeds_to_emit.append(embed)

    # Retour LLM : payload synthétique pour qu'il puisse citer les
    # titres dans son intro texte (sans inventer).
    return {
        "kind": raw_kind,
        "query": raw_query or None,
        "articles": [
            {
                "slug": it["slug"],
                "title": it["title"],
                "standfirst": it["standfirst"],
                "published_at": it["published_at"],
            }
            for it in items
        ],
        "count": len(items),
        "embed_emitted": True,
    }


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


_BLOCK_TITLE_BY_KIND: dict[str, str] = {
    "NEWS": "À la une",
    "ANALYSIS": "Analyses",
    "RESEARCH": "Notes de recherche",
    "HELP": "Articles utiles",
}


def _fetch_articles(
    db,
    *,
    article_type: str,
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Charge les articles publiés via raw SQL (table Prisma `articles`).

    Convention de la table (cf. ``schema.prisma`` model `Article`) :
      - ``status`` = 'PUBLISHED' / 'DRAFT' (enum ContentStatus).
      - ``article_type`` ∈ {NEWS, ANALYSIS, RESEARCH, HELP, ACADEMY,
        OFFER, PROJECT, ...}.
      - ``is_featured`` boolean.
      - ``published_at`` timestamptz nullable.
      - ``slug`` unique.
      - ``cover_media_id`` FK vers ``media`` (résolution de l'URL en
        2e étape via ``media.path``).

    Le titre vient de ``article_i18n`` (locale 'fr' fallback locale
    quelconque) ; le standfirst aussi. On joint en LEFT pour ne pas
    perdre les articles sans i18n.

    Pas de fonction stockée, pas d'ORM Article : c'est volontairement
    minimal pour ne pas dupliquer Prisma côté Python. La requête est
    paramétrée (pas de SQL injection) et le filtre LIKE est appliqué
    sur les colonnes texte uniquement.

    Returns : liste de dicts (vide si rien ne match).
    """
    # NOTE : `article_i18n` n'a pas de colonne `reading_time` (cf.
    # `schema.prisma` § ArticleI18n). On laisse `reading_time_minutes`
    # à 0 ; le widget côté Flutter masque la chip de durée si 0.
    # Cover : `media.url` (chemin web absolu ou relatif côté CMS).
    sql_lines = [
        "SELECT a.id::text AS id,",
        "       a.slug AS slug,",
        "       a.is_featured AS is_featured,",
        "       a.is_highlighted AS is_highlighted,",
        "       a.published_at AS published_at,",
        "       a.author_name AS author_name,",
        "       COALESCE(i_fr.title, i_any.title, '(sans titre)') AS title,",
        "       COALESCE(i_fr.standfirst, i_any.standfirst, '') AS standfirst,",
        "       m.url AS cover_path",
        "FROM articles a",
        "LEFT JOIN article_i18n i_fr",
        "  ON i_fr.article_id = a.id AND i_fr.locale = 'fr'",
        "LEFT JOIN article_i18n i_any",
        "  ON i_any.article_id = a.id AND i_any.locale != 'fr'",
        "LEFT JOIN media m ON m.id = a.cover_media_id",
        "WHERE a.status = 'PUBLISHED'",
        "  AND a.article_type = :article_type",
    ]
    params: dict[str, Any] = {
        "article_type": article_type,
        "limit": int(limit),
    }
    if query:
        # LIKE insensitive : on s'appuie sur ILIKE PostgreSQL (la
        # base est PG). Le `%` est ajouté ici, pas dans `query` du LLM.
        sql_lines.append(
            "  AND (i_fr.title ILIKE :q "
            "    OR i_any.title ILIKE :q "
            "    OR i_fr.standfirst ILIKE :q "
            "    OR a.slug ILIKE :q)"
        )
        params["q"] = f"%{query}%"
    sql_lines.append(
        "ORDER BY a.is_featured DESC, "
        "         a.is_highlighted DESC, "
        "         a.published_at DESC NULLS LAST"
    )
    sql_lines.append("LIMIT :limit")
    sql = "\n".join(sql_lines)

    try:
        rows = db.execute(text(sql), params).mappings().all()
    except Exception:  # noqa: BLE001
        logger.exception(
            "show_featured_articles.sql_error article_type=%s",
            article_type,
        )
        return []

    out: list[dict[str, Any]] = []
    for r in rows:
        cover_url: Optional[str] = None
        path = r.get("cover_path")
        if isinstance(path, str) and path:
            # Convention : `Media.path` est déjà un chemin web (relatif
            # ou absolu). Le client préfixera `Config.baseUrl` si besoin.
            cover_url = path if path.startswith("http") else f"/media/{path}"
        published_at = r.get("published_at")
        published_iso: Optional[str] = None
        if published_at is not None:
            try:
                published_iso = published_at.isoformat()
            except Exception:  # noqa: BLE001
                published_iso = None
        out.append(
            {
                "id": r.get("id"),
                "slug": r.get("slug"),
                "title": (r.get("title") or "").strip()
                or "(sans titre)",
                "standfirst": (r.get("standfirst") or "").strip(),
                "cover_url": cover_url,
                "published_at": published_iso,
                # `article_i18n` n'a pas de `reading_time` ; valeur 0 =
                # widget masque la chip durée.
                "reading_time_minutes": 0,
                "author_name": (r.get("author_name") or "").strip()
                or None,
                "is_featured": bool(r.get("is_featured")),
            }
        )
    return out


__all__ = ["SPEC", "execute"]
