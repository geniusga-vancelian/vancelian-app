"""Rename legacy SQLAlchemy `pages` to `legacy_json_pages` (Prisma CMS uses `pages`).

Revision ID: 105
Revises: 104

Unblocks single-database operation: API legacy JSON pages vs Prisma Page model
are incompatible (integer id + sections_json vs cuid + url_path).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "105"
down_revision = "104"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    row = conn.execute(
        sa.text(
            """
            SELECT c.data_type
            FROM information_schema.columns c
            WHERE c.table_schema = 'public'
              AND c.table_name = 'pages'
              AND c.column_name = 'id'
            """
        )
    ).fetchone()
    if row and row[0] in ("integer", "bigint", "smallint"):
        op.execute(sa.text('ALTER TABLE public.pages RENAME TO legacy_json_pages'))
    # If no `pages` or id is not integer (e.g. already Prisma), no-op.


def downgrade() -> None:
    conn = op.get_bind()
    row = conn.execute(
        sa.text(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'legacy_json_pages'
            """
        )
    ).fetchone()
    if row:
        op.execute(sa.text("ALTER TABLE public.legacy_json_pages RENAME TO pages"))
