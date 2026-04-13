"""PR E — tier d’attestation métier persisté sur la session.

Revision ID: 135
Revises: 134
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "135"
down_revision = "134"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auth_sessions",
        sa.Column("device_attestation_tier", sa.String(length=16), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("auth_sessions", "device_attestation_tier", schema="public")
