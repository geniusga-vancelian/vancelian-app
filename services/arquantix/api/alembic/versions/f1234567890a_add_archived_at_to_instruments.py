"""add_archived_at_to_instruments

Revision ID: f1234567890a
Revises: a8723d70ea70
Create Date: 2026-01-09 13:59:48.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f1234567890a'
down_revision = 'a8723d70ea70'
branch_labels = None
depends_on = None


def _column_exists(conn, schema: str, table: str, column: str) -> bool:
    r = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_schema = :schema AND table_name = :t AND column_name = :col"
        ),
        {"schema": schema, "t": table, "col": column},
    )
    return r.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()
    if not _column_exists(conn, "public", "market_data_instruments", "archived_at"):
        op.add_column(
            "market_data_instruments",
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
            schema="public",
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _column_exists(conn, "public", "market_data_instruments", "archived_at"):
        op.drop_column("market_data_instruments", "archived_at", schema="public")

