"""MVP D.1.4.2 — Indicateur « non lu » sur les conversations d'assistance.

Ajoute deux colonnes timestamps sur `assistance_conversations` :
- `last_assistant_message_at` : horodatage de la dernière réponse assistant
  insérée côté serveur. Sert de référence « il y a quelque chose de nouveau ».
- `last_read_at` : horodatage de la dernière lecture par l'utilisateur
  (envoi d'un nouveau tour OU ouverture de l'historique côté Flutter).

`unread` se calcule en lecture seule comme :
    last_assistant_message_at IS NOT NULL
    AND (last_read_at IS NULL OR last_read_at < last_assistant_message_at)

Backfill : pour les conversations existantes (créées avant cette migration),
on initialise les deux champs à `last_message_at` afin qu'elles soient
considérées comme **déjà lues** — sinon toute conversation pré-existante
remonterait avec une pastille visuelle, ce qui ne reflète pas l'usage réel.

Revision ID: 145
Revises: 144
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "145"
down_revision = "144"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assistance_conversations",
        sa.Column(
            "last_assistant_message_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        schema="public",
    )
    op.add_column(
        "assistance_conversations",
        sa.Column(
            "last_read_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        schema="public",
    )

    # Backfill : les conversations pré-existantes sont considérées « lues ».
    # Sans cela, elles arriveraient toutes avec une pastille au prochain
    # affichage de la liste, alors qu'elles ont déjà été consultées en
    # session synchrone.
    op.execute(
        """
        UPDATE public.assistance_conversations
        SET last_assistant_message_at = last_message_at,
            last_read_at = last_message_at
        WHERE last_message_at IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column(
        "assistance_conversations",
        "last_read_at",
        schema="public",
    )
    op.drop_column(
        "assistance_conversations",
        "last_assistant_message_at",
        schema="public",
    )
