"""add pe_position_relations table (Portfolio Engine — relation layer)

Revision ID: 027
Revises: 026
Create Date: 2026-02-18

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "027"
down_revision = "026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_position_relations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_position_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("target_position_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relation_type", sa.String(length=50), nullable=False),
        sa.Column("parameters", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_position_id"], ["public.pe_position_atoms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_position_id"], ["public.pe_position_atoms.id"], ondelete="CASCADE"),
        sa.UniqueConstraint(
            "source_position_id", "target_position_id", "relation_type",
            name="uq_pe_position_relations_src_tgt_type",
        ),
        schema="public",
    )

    op.create_index("ix_pe_position_relations_source", "pe_position_relations", ["source_position_id"], unique=False, schema="public")
    op.create_index("ix_pe_position_relations_target", "pe_position_relations", ["target_position_id"], unique=False, schema="public")
    op.create_index("ix_pe_position_relations_type", "pe_position_relations", ["relation_type"], unique=False, schema="public")


def downgrade() -> None:
    op.drop_index("ix_pe_position_relations_type", table_name="pe_position_relations", schema="public")
    op.drop_index("ix_pe_position_relations_target", table_name="pe_position_relations", schema="public")
    op.drop_index("ix_pe_position_relations_source", table_name="pe_position_relations", schema="public")
    op.drop_table("pe_position_relations", schema="public")
