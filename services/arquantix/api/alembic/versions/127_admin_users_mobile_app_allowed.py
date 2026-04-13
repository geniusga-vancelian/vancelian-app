"""admin_users.mobile_app_allowed — comptes réservés au back-office web (pas d’app mobile).

Revision ID: 127
Revises: 126
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "127"
down_revision = "126"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "admin_users",
        sa.Column(
            "mobile_app_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("admin_users", "mobile_app_allowed")
