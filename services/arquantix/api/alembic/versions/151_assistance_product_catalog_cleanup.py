"""Phase 2 wiki v1.4 patch 3 — Cleanup catalog + nouvelle fiche overview.

Cette migration agit en **2 axes** sur la table ``product_knowledge``
(seedée en 149) pour éliminer les hallucinations observées en prod
sur la conv ``534d545b`` (« Vancelian propose des SCPI », « livret
rémunéré », « mandat de gestion ») :

──────────────────────────────────────────────────────────────────────
A) Soft-delete (`is_active=false`) de 3 fiches non-canoniques

Ces fiches ont des **titres affirmatifs** (« Investir en SCPI sur
Vancelian », « Le compte d'épargne rémunéré Vancelian », « Le mandat
de gestion Vancelian ») mais des **corps purement définitionnels**
qui ne précisent ni « Vancelian propose ce produit » ni le contraire.
Le LLM les lit → assume qu'ils sont dans la gamme → hallucine.

La gamme **canonique** Vancelian (validée par l'équipe produit, cf.
réponse du chatbot Slack en référence) se compose de :

  1. **Coffres d'épargne** — Coffre Flexible + Coffre Avenir.
  2. **Offres Exclusives** — Cloud Mining (Hearst Éthiopie), Dubai
     Villa Al Barari, Munduk Bali, Niseko Japan.
  3. **Crypto Baskets** — Top 2, Top 5.
  4. **Trading spot** — achat/vente direct de crypto-actifs.
  5. **Compte EUR + carte VISA** — IBAN dédié + carte de retrait.

→ ni livret rémunéré, ni SCPI, ni mandat de gestion ne sont
proposés. Désactivation à coup de ``is_active=false`` (soft-delete
préservant l'historique d'audit) :

  * ``product_basics_scpi``           (titre + corps trompeurs)
  * ``product_basics_livret_vancelian`` (idem)
  * ``product_basics_managed_mandate``  (idem)

──────────────────────────────────────────────────────────────────────
B) Insert d'une nouvelle fiche ``vancelian_product_catalog``

Fiche **overview** des 5 familles, à appeler en priorité par
l'agent ``product`` quand le client demande une vue d'ensemble
(« quels sont les produits Vancelian ? », « découvrir Vancelian »,
« la gamme »). Texte calibré, factuel, court, qui couvre les 5
familles et invite à demander des précisions.

──────────────────────────────────────────────────────────────────────
Migration purement additive (sur le slot des nouvelles entrées) +
soft-delete (sur les 3 fiches désactivées). Aucun DROP de colonne,
aucun rename, aucune contrainte FK touchée.

Revision ID: 151
Revises: 150
"""

from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy import inspect

revision = "151"
down_revision = "150"
branch_labels = None
depends_on = None


# ─────────────────────────────────────────────────────────────────────
# Slugs neutralisés (corps trompeurs ou produits non offerts par Vancelian).
# Cf. analyse conv 534d545b 2026-05-04 + comparaison réponse référence
# du chatbot Slack du wiki source.
# ─────────────────────────────────────────────────────────────────────

DEACTIVATED_SLUGS: list[str] = [
    "product_basics_scpi",
    "product_basics_livret_vancelian",
    "product_basics_managed_mandate",
]


# ─────────────────────────────────────────────────────────────────────
# Nouvelle fiche overview des 5 familles produits Vancelian.
# Texte référence : aligné sur la réponse du chatbot Slack v3 du
# wiki source (Jean Guillou, 2026-04-12). À tenir à jour à chaque
# évolution catalogue (= rare, c'est la gamme structurelle).
# ─────────────────────────────────────────────────────────────────────

CATALOG_SLUG = "vancelian_product_catalog"
CATALOG_TITLE = "Découvrir les produits Vancelian"
CATALOG_TOPIC = "definition"
CATALOG_BODY = """\
La gamme Vancelian s'organise en **5 familles de produits**, accessibles à partir de **1 EUR**.

**1. Coffres d'épargne** (Coffre Flexible et Coffre Avenir) — produits qui allouent les fonds à des programmes générateurs de rendement (mining, offres exclusives) tout en maintenant une réserve liquide en EURC. Rendements quotidiens, automatiquement réinvestis. Accès à tout moment pour le **Coffre Flexible** ; engagement de **12 mois** pour le **Coffre Avenir**.

**2. Offres Exclusives** (Cloud Mining, Dubai Villa Al Barari, Munduk Bali, Niseko Japan) — investissements structurés à durée déterminée, avec rendements plus élevés et engagements contractuels spécifiques. **Cloud Mining** = achat de puissance de calcul Bitcoin opérée par Hearst en Éthiopie. Les **immobilières** (Dubai, Bali, Niseko) = prêts crypto à des contreparties identifiées (Solaria Group, The Heights Bali, etc.).

**3. Crypto Baskets** (Top 2, Top 5) — paniers d'actifs crypto thématiques avec allocation prédéfinie et rebalancing automatique. Souscription en EUR, exposition diversifiée aux principaux crypto-actifs.

**4. Trading spot** — achat et vente directs de crypto-actifs individuels (BTC, ETH, USDC, etc.) avec frais de trading qui dépendent du **statut Privilege Club** (Bronze à Elite).

**5. Compte EUR + carte VISA** — un IBAN dédié pour les virements SEPA entrants et sortants, et une carte VISA pour retirer ou dépenser les fonds depuis le solde EUR.

**Ce que Vancelian ne propose PAS** (à ne pas confondre) : SCPI, livret rémunéré bancaire classique, mandat de gestion patrimoniale, actions / obligations cotées, OPCVM. Si une question porte sur ces produits, oriente le client vers un interlocuteur adapté.

Quel type de produit intéresse le client en particulier ? Tu peux ensuite expliquer le fonctionnement, les conditions, ou les risques associés en t'appuyant sur les fiches dédiées (Coffre, Offres Exclusives, Crypto Baskets).
"""

CATALOG_METADATA: dict[str, object] = {
    "applies_to": ["all_clients"],
    "source": "wiki_source_chatbot_v3_canonical",
    "valid_until": None,
    "version": "1.0",
    "audience": "agent_product",
}


# ─────────────────────────────────────────────────────────────────────
# Upgrade / Downgrade
# ─────────────────────────────────────────────────────────────────────


def upgrade() -> None:
    bind = op.get_bind()
    if not inspect(bind).has_table("product_knowledge", schema="public"):
        # Bases jamais passées par 149 (ou stamp partiel) : pas de table → no-op
        # pour ne pas bloquer le démarrage API / Alembic.
        return

    # A) Soft-delete des 3 fiches non-canoniques.
    bind.execute(
        sa.text(
            "UPDATE product_knowledge "
            "SET is_active = FALSE, "
            "    updated_at = :now "
            "WHERE slug = ANY(:slugs)"
        ),
        {
            "slugs": DEACTIVATED_SLUGS,
            "now": datetime.now(timezone.utc),
        },
    )

    # B) Insert de la fiche overview catalogue (idempotent — ON CONFLICT
    # DO UPDATE pour permettre une re-application sans erreur).
    bind.execute(
        sa.text(
            "INSERT INTO product_knowledge "
            "(slug, topic, title, body, metadata_json, is_active, updated_at) "
            "VALUES "
            "(:slug, :topic, :title, :body, CAST(:metadata AS JSONB), TRUE, :now) "
            "ON CONFLICT (slug) DO UPDATE SET "
            "  topic         = EXCLUDED.topic, "
            "  title         = EXCLUDED.title, "
            "  body          = EXCLUDED.body, "
            "  metadata_json = EXCLUDED.metadata_json, "
            "  is_active     = TRUE, "
            "  updated_at    = EXCLUDED.updated_at"
        ),
        {
            "slug": CATALOG_SLUG,
            "topic": CATALOG_TOPIC,
            "title": CATALOG_TITLE,
            "body": CATALOG_BODY,
            "metadata": __import__("json").dumps(CATALOG_METADATA),
            "now": datetime.now(timezone.utc),
        },
    )


def downgrade() -> None:
    bind = op.get_bind()
    if not inspect(bind).has_table("product_knowledge", schema="public"):
        return

    # B) Retirer la fiche catalogue (DELETE — pas de soft, c'est un seed
    # technique sans valeur d'historique en cas de rollback).
    bind.execute(
        sa.text("DELETE FROM product_knowledge WHERE slug = :slug"),
        {"slug": CATALOG_SLUG},
    )

    # A) Réactiver les 3 fiches désactivées (cohérence : avant 151 elles
    # étaient actives, on les remet dans cet état).
    bind.execute(
        sa.text(
            "UPDATE product_knowledge "
            "SET is_active = TRUE, "
            "    updated_at = :now "
            "WHERE slug = ANY(:slugs)"
        ),
        {
            "slugs": DEACTIVATED_SLUGS,
            "now": datetime.now(timezone.utc),
        },
    )
