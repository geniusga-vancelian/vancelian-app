"""Table auth_refresh_tokens — chaîne de rotation par jti + audit reuse.

Revision ID: 131
Revises: 130
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "131"
down_revision = "130"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.auth_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("jti", sa.String(64), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_jti", sa.String(64), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_auth_refresh_tokens_session_id",
        "auth_refresh_tokens",
        ["session_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_auth_refresh_tokens_jti",
        "auth_refresh_tokens",
        ["jti"],
        unique=True,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_auth_refresh_tokens_jti", table_name="auth_refresh_tokens", schema="public")
    op.drop_index("ix_auth_refresh_tokens_session_id", table_name="auth_refresh_tokens", schema="public")
    op.drop_table("auth_refresh_tokens", schema="public")
