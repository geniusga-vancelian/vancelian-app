"""persons.login_frozen — gel connexion (admin) sans suppression du profil.

Revision ID: 128
Revises: 127
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "128"
down_revision = "127"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "persons",
        sa.Column(
            "login_frozen",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("persons", "login_frozen", schema="public")
