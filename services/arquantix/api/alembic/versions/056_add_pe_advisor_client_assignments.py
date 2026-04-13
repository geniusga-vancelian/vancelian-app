"""add pe_advisor_client_assignments table

Revision ID: 056
Revises: 055
Create Date: 2026-03-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "056"
down_revision = "055"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pe_advisor_client_assignments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("advisor_actor_id", sa.String(255), nullable=False),
        sa.Column(
            "client_id",
            UUID(as_uuid=True),
            sa.ForeignKey("pe_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_unique_constraint(
        "uq_advisor_client", "pe_advisor_client_assignments",
        ["advisor_actor_id", "client_id"],
    )
    op.create_index(
        "ix_pe_advisor_assign_advisor", "pe_advisor_client_assignments", ["advisor_actor_id"],
    )
    op.create_index(
        "ix_pe_advisor_assign_client", "pe_advisor_client_assignments", ["client_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_pe_advisor_assign_client", table_name="pe_advisor_client_assignments")
    op.drop_index("ix_pe_advisor_assign_advisor", table_name="pe_advisor_client_assignments")
    op.drop_constraint("uq_advisor_client", "pe_advisor_client_assignments", type_="unique")
    op.drop_table("pe_advisor_client_assignments")
