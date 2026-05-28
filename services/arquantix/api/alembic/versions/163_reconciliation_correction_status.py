"""Ajoute status sur reconciliation_corrections (workflow Phase 5B)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "163"
down_revision = "162"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "reconciliation_corrections",
        sa.Column("status", sa.String(20), server_default="preview", nullable=False),
        schema="public",
    )
    op.create_index(
        "ix_reconciliation_corrections_status",
        "reconciliation_corrections",
        ["status"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_reconciliation_corrections_status",
        table_name="reconciliation_corrections",
        schema="public",
    )
    op.drop_column("reconciliation_corrections", "status", schema="public")
