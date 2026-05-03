"""Repository de l'agent **product** — Phase 2c.

Lit la table `product_knowledge` (cf. migration 149) qui contient des
fiches courtes (200-500 mots) factuelles sur les produits Vancelian
et les délais standards (dépôt SEPA, retrait, KYC, swap…).

──────────────────────────────────────────────────────────────────────
Garanties (lecture)
──────────────────────────────────────────────────────────────────────

  - **Read-side : best-effort** — tout échec DB retourne ``None`` ou ``[]``
    (le tool caller fait fallback gracieux).
  - **Pas de PII** : la table ne contient que du contenu pédagogique
    générique, donc rien à filtrer côté tipping-off.
  - **Soft-delete** : `is_active=false` masque silencieusement (le
    LLM ne voit pas le contenu retiré).

──────────────────────────────────────────────────────────────────────
Garanties (écriture admin — ajouté en Phase 2d)
──────────────────────────────────────────────────────────────────────

Les fonctions ``create_knowledge``, ``update_knowledge``, ``delete_knowledge``
sont **réservées au router admin**. Elles :

  - **Lèvent** les erreurs (``ValueError`` / ``KeyError``) — l'admin a besoin
    d'un retour explicite, pas d'un swallow silencieux.
  - **N'invalident PAS** le cache du builder par elles-mêmes : c'est le
    routeur qui le fait après ``db.commit()`` réussi (séparation des
    responsabilités, cf. ``services/assistance/admin_knowledge_router.py``).
  - **Ne committent pas** : le router pilote le commit pour pouvoir
    enchaîner plusieurs opérations dans une seule transaction si besoin.

Phase 5 (RAG) : ce repo restera pertinent pour les FAQ courtes.
La recherche vectorielle viendra dans un module dédié `product_rag.py`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import ProductKnowledge

logger = logging.getLogger(__name__)


# Topics autorisés (validation côté admin). On reste permissif côté lecture
# (la table peut contenir d'autres topics historiques) mais on contraint
# côté écriture pour éviter la prolifération.
ALLOWED_TOPICS: frozenset[str] = frozenset({
    "transaction_kind",  # mapping types de transactions client
    "definition",        # fiches produits éditoriales
    "delay",             # délais standards (SEPA, KYC, swap…)
    "faq",               # FAQ courtes (réservé pour usage futur)
})


def fetch_knowledge_by_slug(
    db: Session, *, slug: str
) -> Optional[dict[str, Any]]:
    """Retourne le contenu d'une fiche `product_knowledge` par slug.

    Args:
        db: session SQLAlchemy ouverte.
        slug: identifiant canonique (ex. ``"deposit_delay_sepa_in"``).

    Returns:
        Dict :
            ``{"slug", "topic", "title", "body", "metadata", "updated_at"}``
        ou ``None`` si :
            - le slug est vide / inconnu,
            - la fiche est désactivée (`is_active=false`),
            - une erreur DB survient (best-effort).

    Notes:
        Le contenu peut être renvoyé tel quel au LLM : il est conçu
        pour être client-facing et passe par revue éditoriale humaine
        avant d'être seedé.
    """
    if not slug:
        return None

    try:
        row = (
            db.query(ProductKnowledge)
            .filter(ProductKnowledge.slug == slug)
            .filter(ProductKnowledge.is_active.is_(True))
            .one_or_none()
        )
    except Exception:  # noqa: BLE001
        logger.exception("product_repo.fetch_knowledge_by_slug failed slug=%s", slug)
        return None

    if row is None:
        return None

    return {
        "slug": row.slug,
        "topic": row.topic,
        "title": row.title,
        "body": row.body,
        "metadata": row.metadata_json or {},
        "updated_at": (
            row.updated_at.isoformat() if row.updated_at else None
        ),
    }


def list_known_slugs(
    db: Session, *, topic: Optional[str] = None, limit: int = 100
) -> list[dict[str, str]]:
    """Liste les slugs disponibles (pour aide de debug / introspection).

    Args:
        db: session SQLAlchemy ouverte.
        topic: filtre optionnel par catégorie (``"delay"``, ``"definition"``).
        limit: borne hard 1..200, clampée silencieusement.

    Returns:
        Liste de dict ``[{"slug", "topic", "title"}, ...]`` triée par
        slug ASC. Liste vide si erreur ou aucun résultat.

    Notes:
        Pas de body ni metadata ici (volontairement minimal pour éviter
        de dump tout le contenu d'un coup au LLM ; le LLM doit cibler
        un slug précis via `fetch_knowledge_by_slug`).
    """
    safe_limit = max(1, min(int(limit or 100), 200))

    try:
        q = db.query(
            ProductKnowledge.slug,
            ProductKnowledge.topic,
            ProductKnowledge.title,
        ).filter(ProductKnowledge.is_active.is_(True))
        if topic:
            q = q.filter(ProductKnowledge.topic == topic)
        rows = q.order_by(ProductKnowledge.slug.asc()).limit(safe_limit).all()
    except Exception:  # noqa: BLE001
        logger.exception("product_repo.list_known_slugs failed topic=%s", topic)
        return []

    return [
        {"slug": r.slug, "topic": r.topic, "title": r.title}
        for r in rows
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Admin API — read paginé + write
#
# Convention :
#   - Les fonctions ci-dessous N'AVALENT PAS les exceptions DB (au contraire
#     de la lecture LLM). Le router admin propage les erreurs au client HTTP.
#   - Aucune ne committe (le router gère le commit, voir module docstring).
# ─────────────────────────────────────────────────────────────────────────────


def _row_to_admin_dict(row: ProductKnowledge) -> dict[str, Any]:
    """Sérialise une row en dict admin (inclut body, metadata, is_active, timestamps)."""
    return {
        "slug": row.slug,
        "topic": row.topic,
        "title": row.title,
        "body": row.body,
        "metadata": row.metadata_json or {},
        "is_active": bool(row.is_active),
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def admin_list_knowledge(
    db: Session,
    *,
    topic: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[dict[str, Any]], int]:
    """Liste paginée pour l'admin (avec total).

    Args:
        topic: filtre exact sur ``topic``.
        is_active: ``True``/``False`` ou ``None`` pour ne pas filtrer.
        search: substring case-insensitive sur ``slug``, ``title`` ou ``body``.
        skip: offset (>= 0).
        limit: 1..200, clampé silencieusement.

    Returns:
        ``(items, total)`` — items est une liste de dicts admin, total est le
        nombre de rows matchant les filtres (avant pagination).
    """
    safe_skip = max(0, int(skip or 0))
    safe_limit = max(1, min(int(limit or 50), 200))

    q = db.query(ProductKnowledge)
    if topic:
        q = q.filter(ProductKnowledge.topic == topic)
    if is_active is True:
        q = q.filter(ProductKnowledge.is_active.is_(True))
    elif is_active is False:
        q = q.filter(ProductKnowledge.is_active.is_(False))
    if search:
        like = f"%{search.strip()}%"
        q = q.filter(
            or_(
                ProductKnowledge.slug.ilike(like),
                ProductKnowledge.title.ilike(like),
                ProductKnowledge.body.ilike(like),
            )
        )

    total = q.count()
    rows = (
        q.order_by(ProductKnowledge.topic.asc(), ProductKnowledge.slug.asc())
        .offset(safe_skip)
        .limit(safe_limit)
        .all()
    )
    return [_row_to_admin_dict(r) for r in rows], total


def admin_get_knowledge(db: Session, *, slug: str) -> Optional[dict[str, Any]]:
    """Récupère une fiche par slug, indépendamment de ``is_active``.

    Distingué de ``fetch_knowledge_by_slug`` qui filtre les inactifs : ici
    l'admin doit pouvoir voir et ré-activer une fiche désactivée.
    """
    if not slug:
        return None
    row = (
        db.query(ProductKnowledge)
        .filter(ProductKnowledge.slug == slug)
        .one_or_none()
    )
    return _row_to_admin_dict(row) if row else None


def _validate_write_payload(
    *,
    slug: str,
    topic: str,
    title: str,
    body: str,
    metadata: dict[str, Any] | None,
) -> None:
    """Validation commune create/update. Lève ``ValueError`` si invalide."""
    if not slug or not slug.strip():
        raise ValueError("slug is required")
    if len(slug) > 80:
        raise ValueError("slug too long (max 80 chars)")
    # Slug : lowercase ASCII, digits, underscore, dash. On accepte aussi
    # le point au cas où des slugs hiérarchiques apparaissent (rare).
    import re as _re

    if not _re.match(r"^[a-z0-9][a-z0-9_.\-]*$", slug):
        raise ValueError(
            "slug must be lowercase ASCII (a-z, 0-9, _, -, .) and start with [a-z0-9]"
        )
    if not topic or topic not in ALLOWED_TOPICS:
        raise ValueError(
            f"topic must be one of {sorted(ALLOWED_TOPICS)} (got {topic!r})"
        )
    if not title or len(title) > 200:
        raise ValueError("title is required and must be <= 200 chars")
    if not body or not body.strip():
        raise ValueError("body is required")
    if metadata is not None and not isinstance(metadata, dict):
        raise ValueError("metadata must be a JSON object (dict)")


def create_knowledge(
    db: Session,
    *,
    slug: str,
    topic: str,
    title: str,
    body: str,
    metadata: dict[str, Any] | None = None,
    is_active: bool = True,
) -> dict[str, Any]:
    """Crée une nouvelle fiche. Lève ``ValueError`` si payload invalide ou slug déjà pris."""
    _validate_write_payload(
        slug=slug, topic=topic, title=title, body=body, metadata=metadata
    )
    existing = (
        db.query(ProductKnowledge.slug)
        .filter(ProductKnowledge.slug == slug)
        .one_or_none()
    )
    if existing is not None:
        raise ValueError(f"slug {slug!r} already exists")

    row = ProductKnowledge(
        slug=slug,
        topic=topic,
        title=title.strip(),
        body=body,
        metadata_json=metadata or {},
        is_active=bool(is_active),
    )
    db.add(row)
    db.flush()  # Permet de récupérer created_at/updated_at avant commit.
    return _row_to_admin_dict(row)


def update_knowledge(
    db: Session,
    *,
    slug: str,
    topic: Optional[str] = None,
    title: Optional[str] = None,
    body: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    is_active: Optional[bool] = None,
) -> dict[str, Any]:
    """Met à jour une fiche existante (champs partiels). Lève si introuvable / invalide."""
    if not slug:
        raise ValueError("slug is required")

    row = (
        db.query(ProductKnowledge)
        .filter(ProductKnowledge.slug == slug)
        .one_or_none()
    )
    if row is None:
        raise KeyError(slug)

    # Snapshot fusionné pour validation cohérente.
    new_topic = topic if topic is not None else row.topic
    new_title = title if title is not None else row.title
    new_body = body if body is not None else row.body
    new_metadata = metadata if metadata is not None else (row.metadata_json or {})
    _validate_write_payload(
        slug=slug,
        topic=new_topic,
        title=new_title,
        body=new_body,
        metadata=new_metadata,
    )

    row.topic = new_topic
    row.title = (new_title or "").strip()
    row.body = new_body
    row.metadata_json = new_metadata
    if is_active is not None:
        row.is_active = bool(is_active)
    row.updated_at = datetime.now(timezone.utc)
    db.flush()
    return _row_to_admin_dict(row)


def delete_knowledge(db: Session, *, slug: str) -> dict[str, Any]:
    """Supprime physiquement une fiche. Lève ``KeyError`` si introuvable.

    Pour un soft-delete, utiliser plutôt ``update_knowledge(slug=..., is_active=False)``.
    Le delete physique est réservé aux rows créées par erreur ou obsolètes
    (rare en pratique).
    """
    row = (
        db.query(ProductKnowledge)
        .filter(ProductKnowledge.slug == slug)
        .one_or_none()
    )
    if row is None:
        raise KeyError(slug)
    snapshot = _row_to_admin_dict(row)
    db.delete(row)
    db.flush()
    return snapshot


def admin_count_by_topic(db: Session) -> dict[str, dict[str, int]]:
    """Pour la page admin : compteurs par topic (active / inactive).

    Retourne ``{topic: {"active": N, "inactive": M}}``.
    """
    from sqlalchemy import func

    rows = (
        db.query(
            ProductKnowledge.topic,
            ProductKnowledge.is_active,
            func.count().label("n"),
        )
        .group_by(ProductKnowledge.topic, ProductKnowledge.is_active)
        .all()
    )
    out: dict[str, dict[str, int]] = {}
    for topic, active, n in rows:
        bucket = out.setdefault(topic, {"active": 0, "inactive": 0})
        bucket["active" if active else "inactive"] = int(n)
    return out
