"""Cognitive Bot v4 — Lot 7 — discovery projet client + paramètres adossés.

Crée 2 tables additives qui matérialisent le **modèle multi-projet
client** vu en discussion Lot 7 (cf. ``COGNITIVE_BOT.md`` § 12 et le
nouveau ``CLIENT_DISCOVERY.md``).

──────────────────────────────────────────────────────────────────────
Contexte fonctionnel
──────────────────────────────────────────────────────────────────────

Avant ce Lot, le bot mémorisait **l'émotion** (`cognitive_state` Lot 1)
et **le sujet catalogue en cours** (`current_topic` Lot 1.4) mais **pas
le projet du client** (« acheter une maison », « préparer ma retraite »,
« épargner pour les vacances »). Conséquence audit conv ``f9d59f98`` :

  * tour #11 — le user demande « investissements » au milieu d'un
    parcours « achat maison » → le router redémarre à zéro
    thématiquement (4 options génériques, aucune ne mentionne la
    maison),
  * le bot ne peut pas adapter ses recommandations aux paramètres
    réels (horizon, montant, risque) parce qu'aucun n'est persisté.

Le modèle multi-projet introduit en Lot 7 capture le ``why`` du client
(projet) et **le ``how``** (paramètres : horizon, target_amount,
recurring, liquidity_need, risk_appetite, …) **adossés au projet**.
Plusieurs projets peuvent coexister actifs ; un projet peut être paused
quand le client switche.

──────────────────────────────────────────────────────────────────────
Tables créées
──────────────────────────────────────────────────────────────────────

A) ``assistance_client_discovery_projects`` — un projet client (achat
   maison, retraite, vacances, …). Lié à la **personne** (FK
   ``persons.id``) plus qu'au ``pe_clients`` : un même client peut
   parler de ses projets à travers plusieurs conversations, voire
   plusieurs ``pe_clients`` sous la même personne morale (crypto +
   fiat + corporate). La conversation source est tracée pour audit
   mais n'est **pas** la source de propriété (cf. lookup cross-conv).

B) ``assistance_floating_parameters`` — paramètres extraits par le
   discovery extractor mais **non attribués** à un projet (le client a
   dit « 4 ans » sans nommer le projet associé, par exemple). Reste
   en attente jusqu'au prochain tour de clarification ou jusqu'à
   discard automatique après N tours.

──────────────────────────────────────────────────────────────────────
Stratégie 100 % additive
──────────────────────────────────────────────────────────────────────

  * Aucune contrainte CHECK sur ``status`` ou ``parameter_kind`` (les
    enums applicatifs peuvent évoluer en V2 — classifieur ML, nouveaux
    paramètres comme « ESG preference »).
  * Aucune NOT NULL contrainte autre que les FK et les timestamps.
  * Aucune modif des tables existantes.
  * Migration testable, downgrade clean.

──────────────────────────────────────────────────────────────────────
Index
──────────────────────────────────────────────────────────────────────

Pour ``assistance_client_discovery_projects`` :
  * ``(person_id, status)`` partial sur ``status='active'`` — lookup
    rapide « les projets actifs de cette personne » (le cas usuel
    appelé à chaque tour).
  * ``(person_id, last_touched_at_turn DESC)`` — sort par récence.
  * ``conversation_id_source`` simple — audit par conv.

Pour ``assistance_floating_parameters`` :
  * ``(conversation_id, status)`` partial sur ``status='pending_attribution'``
    — le runtime cherche les floating à attribuer au tour suivant.

──────────────────────────────────────────────────────────────────────
Revision ID: 153
Revises: 152
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "153"
down_revision = "152"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── A) assistance_client_discovery_projects ─────────────────────
    op.create_table(
        "assistance_client_discovery_projects",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "public.persons.id",
                ondelete="CASCADE",
                name="fk_acdp_person_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "conversation_id_source",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "public.assistance_conversations.id",
                ondelete="SET NULL",
                name="fk_acdp_conversation_id_source",
            ),
            nullable=True,
        ),
        sa.Column("label", sa.String(length=80), nullable=False),
        # ``status`` ∈ {active, paused, completed, abandoned}. Pas de
        # CHECK volontaire pour laisser respirer (cf. doc).
        sa.Column(
            "status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        # Confidence (0..1) de l'extraction qui a créé/maj ce projet.
        sa.Column("confidence", sa.Float(), nullable=True),
        # ``parameters`` = ClientProjectParameters (cf.
        # ``services/assistance/agents/client_discovery.py``). JSONB
        # pour ne pas figer le schéma — V2 ajoutera ESG, fiscalité, etc.
        sa.Column(
            "parameters",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        # Trace turn_index de création / dernier touch (pour règles
        # d'attribution et expirations potentielles).
        sa.Column("created_at_turn", sa.Integer(), nullable=True),
        sa.Column("last_touched_at_turn", sa.Integer(), nullable=True),
        # Trace audit qualitative libre (≤ 200 chars, contraintes
        # applicatives, non DB).
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="public",
    )
    op.create_index(
        "ix_acdp_person_active",
        "assistance_client_discovery_projects",
        ["person_id"],
        schema="public",
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "ix_acdp_person_touched",
        "assistance_client_discovery_projects",
        ["person_id", sa.text("last_touched_at_turn DESC")],
        schema="public",
    )
    op.create_index(
        "ix_acdp_conv_source",
        "assistance_client_discovery_projects",
        ["conversation_id_source"],
        schema="public",
    )

    # ─── B) assistance_floating_parameters ───────────────────────────
    op.create_table(
        "assistance_floating_parameters",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "public.assistance_conversations.id",
                ondelete="CASCADE",
                name="fk_afp_conversation_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "public.persons.id",
                ondelete="CASCADE",
                name="fk_afp_person_id",
            ),
            nullable=False,
        ),
        # Type de paramètre : horizon_years / target_amount /
        # initial_amount / recurring_amount / recurring_frequency /
        # liquidity_need / risk_appetite / known_constraint. Volontaire-
        # ment varchar libre (pas de CHECK).
        sa.Column("parameter_kind", sa.String(length=32), nullable=False),
        sa.Column(
            "parameter_value",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        # ``status`` ∈ {pending_attribution, attributed, discarded}.
        sa.Column(
            "status",
            sa.String(length=24),
            nullable=False,
            server_default=sa.text("'pending_attribution'"),
        ),
        # Si attribué : id du projet cible (FK soft, pas de CASCADE
        # pour ne pas perdre l'audit du parameter si le project est
        # supprimé).
        sa.Column(
            "attributed_project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "public.assistance_client_discovery_projects.id",
                ondelete="SET NULL",
                name="fk_afp_attributed_project_id",
            ),
            nullable=True,
        ),
        sa.Column("created_at_turn", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "resolved_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        schema="public",
    )
    op.create_index(
        "ix_afp_conv_pending",
        "assistance_floating_parameters",
        ["conversation_id"],
        schema="public",
        postgresql_where=sa.text("status = 'pending_attribution'"),
    )


def downgrade() -> None:
    op.drop_index(
        "ix_afp_conv_pending",
        table_name="assistance_floating_parameters",
        schema="public",
    )
    op.drop_table("assistance_floating_parameters", schema="public")

    op.drop_index(
        "ix_acdp_conv_source",
        table_name="assistance_client_discovery_projects",
        schema="public",
    )
    op.drop_index(
        "ix_acdp_person_touched",
        table_name="assistance_client_discovery_projects",
        schema="public",
    )
    op.drop_index(
        "ix_acdp_person_active",
        table_name="assistance_client_discovery_projects",
        schema="public",
    )
    op.drop_table(
        "assistance_client_discovery_projects", schema="public"
    )
