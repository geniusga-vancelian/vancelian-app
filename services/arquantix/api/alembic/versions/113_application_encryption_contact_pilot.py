"""Application encryption Tier 1 — colonnes chiffrées (contact_submissions pilot).

Revision ID: 113
Revises: 112
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "113"
down_revision = "112"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "contact_submissions",
        sa.Column("name_encrypted", sa.Text(), nullable=True),
        schema="public",
    )
    op.add_column(
        "contact_submissions",
        sa.Column("email_encrypted", sa.Text(), nullable=True),
        schema="public",
    )
    op.add_column(
        "contact_submissions",
        sa.Column("message_encrypted", sa.Text(), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("contact_submissions", "message_encrypted", schema="public")
    op.drop_column("contact_submissions", "email_encrypted", schema="public")
    op.drop_column("contact_submissions", "name_encrypted", schema="public")
