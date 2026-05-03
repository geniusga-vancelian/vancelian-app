"""Phase 2a multi-agents — table d'audit trail des décisions agentiques.

Crée la table `assistance_agent_decisions` qui journalise tout appel
d'outil par un agent du runtime (cf. `docs/arquantix/MULTI_AGENTS_RUNTIME.md`
§ 4 « Table agent_decisions »).

──────────────────────────────────────────────────────────────────────
Pourquoi cette table

Le runtime agentique introduit en Phase 2a appelle des « tools » via
function-calling itératif (1..MAX_ITER tours par message client). On
doit pouvoir reconstruire post-fact, pour chaque tour assistant :

  - quels tools ont été appelés et dans quel ordre,
  - avec quels arguments (LLM peut halluciner / dériver),
  - pour quel résultat (résumé gated, anti-tipping-off),
  - à quel niveau d'autonomie (L0/L1/L2/L3),
  - et — pour les actions L1 (advisory) — quelle a été la décision
    humaine de review (approve / reject).

C'est aussi le **substrat** de la future UI BO admin (Phase 2c) qui
permettra à un compliance officer de valider/rejeter les actions
proposées par l'agent.

──────────────────────────────────────────────────────────────────────
Colonnes

  id, conversation_id, message_id, agent_id, iteration, tool_name,
  autonomy_level, arguments_json, result_summary,
  proposed_action, target_client_id, target_person_id,
  reasoning_summary, review_status, reviewed_by, reviewed_at,
  duration_ms, error_code, correlation_id, created_at.

Voir `MULTI_AGENTS_RUNTIME.md` § 4.1 pour les rôles précis.

──────────────────────────────────────────────────────────────────────
Sanitization tipping-off

Le champ `reasoning_summary` est passé par le sanitizer
TIPPING_OFF_BLACKLIST côté code (cf. `MULTI_AGENTS_RUNTIME.md` § 4.3 et
§ 5.2) avant écriture. Aucune contrainte SQL ne le force, c'est une
discipline applicative protégée par les tests CI bloquants
(`test_assistance_tipping_off_*`).

──────────────────────────────────────────────────────────────────────
Index

  - (conversation_id, iteration)        — reconstruire un tour
  - (agent_id, created_at)              — analytics par agent
  - tool_name                            — distribution d'usage
  - autonomy_level                       — analytics niveau
  - review_status WHERE='pending'        — file de review BO admin
  - (target_client_id, created_at)       — historique par client

──────────────────────────────────────────────────────────────────────
Migration purement additive : aucune autre table touchée.

Revision ID: 148
Revises: 147
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "148"
down_revision = "147"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistance_agent_decisions",
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
                name="fk_assistance_agent_decisions_conversation_id",
            ),
            nullable=False,
        ),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "public.assistance_messages.id",
                ondelete="SET NULL",
                name="fk_assistance_agent_decisions_message_id",
            ),
            nullable=True,
        ),
        sa.Column("agent_id", sa.String(length=32), nullable=False),
        sa.Column("iteration", sa.SmallInteger(), nullable=False),
        sa.Column("tool_name", sa.String(length=64), nullable=False),
        sa.Column("autonomy_level", sa.String(length=4), nullable=False),
        sa.Column(
            "arguments_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "result_summary",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column("proposed_action", sa.String(length=64), nullable=True),
        sa.Column(
            "target_client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "public.pe_clients.id",
                ondelete="SET NULL",
                name="fk_assistance_agent_decisions_target_client",
            ),
            nullable=True,
        ),
        sa.Column(
            "target_person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey(
                "public.persons.id",
                ondelete="SET NULL",
                name="fk_assistance_agent_decisions_target_person",
            ),
            nullable=True,
        ),
        sa.Column("reasoning_summary", sa.Text(), nullable=True),
        sa.Column(
            "review_status",
            sa.String(length=16),
            nullable=False,
            server_default=sa.text("'auto'"),
        ),
        sa.Column(
            "reviewed_by",
            sa.Integer(),
            sa.ForeignKey(
                "public.admin_users.id",
                ondelete="SET NULL",
                name="fk_assistance_agent_decisions_reviewed_by",
            ),
            nullable=True,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_code", sa.String(length=32), nullable=True),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        # Contrainte CHECK : autonomy_level ∈ {L0, L1, L2, L3}
        sa.CheckConstraint(
            "autonomy_level IN ('L0','L1','L2','L3')",
            name="ck_assistance_agent_decisions_autonomy_level",
        ),
        # Contrainte CHECK : review_status ∈ {auto, pending, approved, rejected}
        sa.CheckConstraint(
            "review_status IN ('auto','pending','approved','rejected')",
            name="ck_assistance_agent_decisions_review_status",
        ),
        schema="public",
    )

    # Index principaux
    op.create_index(
        "ix_assistance_agent_decisions_conv_iter",
        "assistance_agent_decisions",
        ["conversation_id", "iteration"],
        schema="public",
    )
    op.create_index(
        "ix_assistance_agent_decisions_agent_created",
        "assistance_agent_decisions",
        ["agent_id", "created_at"],
        schema="public",
    )
    op.create_index(
        "ix_assistance_agent_decisions_tool_name",
        "assistance_agent_decisions",
        ["tool_name"],
        schema="public",
    )
    op.create_index(
        "ix_assistance_agent_decisions_autonomy_level",
        "assistance_agent_decisions",
        ["autonomy_level"],
        schema="public",
    )
    # Index partiel : file de review en attente (Phase 2c BO admin)
    op.create_index(
        "ix_assistance_agent_decisions_review_pending",
        "assistance_agent_decisions",
        ["review_status"],
        schema="public",
        postgresql_where=sa.text("review_status = 'pending'"),
    )
    op.create_index(
        "ix_assistance_agent_decisions_target_client",
        "assistance_agent_decisions",
        ["target_client_id", "created_at"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_assistance_agent_decisions_target_client",
        table_name="assistance_agent_decisions",
        schema="public",
    )
    op.drop_index(
        "ix_assistance_agent_decisions_review_pending",
        table_name="assistance_agent_decisions",
        schema="public",
    )
    op.drop_index(
        "ix_assistance_agent_decisions_autonomy_level",
        table_name="assistance_agent_decisions",
        schema="public",
    )
    op.drop_index(
        "ix_assistance_agent_decisions_tool_name",
        table_name="assistance_agent_decisions",
        schema="public",
    )
    op.drop_index(
        "ix_assistance_agent_decisions_agent_created",
        table_name="assistance_agent_decisions",
        schema="public",
    )
    op.drop_index(
        "ix_assistance_agent_decisions_conv_iter",
        table_name="assistance_agent_decisions",
        schema="public",
    )
    op.drop_table("assistance_agent_decisions", schema="public")
