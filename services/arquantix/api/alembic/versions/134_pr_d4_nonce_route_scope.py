"""PR D4 — scope nonce par route (user + device + route).

Revision ID: 134
Revises: 133
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "134"
down_revision = "133"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "auth_device_signature_nonces",
        sa.Column("route_path", sa.String(length=512), nullable=True),
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("auth_device_signature_nonces", "route_path", schema="public")
