"""Add source_ip to two_factor_challenges for IP-based rate limits.

Revision ID: 097
Revises: 096
"""
from alembic import op
import sqlalchemy as sa

revision = "097"
down_revision = "096"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "two_factor_challenges",
        sa.Column("source_ip", sa.Text(), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_two_factor_challenges_source_ip_created",
        "two_factor_challenges",
        ["source_ip", "created_at"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_two_factor_challenges_source_ip_created", table_name="two_factor_challenges", schema="public")
    op.drop_column("two_factor_challenges", "source_ip", schema="public")
