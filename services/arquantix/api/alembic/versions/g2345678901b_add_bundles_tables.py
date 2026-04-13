"""add_bundles_tables

Revision ID: g2345678901b
Revises: f1234567890a
Create Date: 2026-01-09 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'g2345678901b'
down_revision = 'f1234567890a'
branch_labels = None
depends_on = None


def _table_exists(conn, schema: str, table: str) -> bool:
    r = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = :schema AND table_name = :t"
        ),
        {"schema": schema, "t": table},
    )
    return r.scalar() is not None


def _constraint_exists(conn, name: str) -> bool:
    r = conn.execute(
        sa.text("SELECT 1 FROM pg_constraint WHERE conname = :n"),
        {"n": name},
    )
    return r.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _table_exists(conn, "public", "bundles"):
        op.create_table(
            "bundles",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("asset_class", sa.String(length=20), nullable=False),
            sa.Column("type", sa.String(length=50), nullable=False, server_default="FIXED_WEIGHT"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("is_active", sa.String(length=10), nullable=False, server_default="true"),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("created_by_email", sa.String(length=255), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("name", "asset_class", name="uq_bundles_name_asset_class"),
            schema="public",
        )
        op.create_index("ix_bundles_asset_class_is_active", "bundles", ["asset_class", "is_active"], unique=False, schema="public")
        op.create_index("ix_bundles_id", "bundles", ["id"], unique=False, schema="public")

    if not _table_exists(conn, "public", "bundle_allocations"):
        op.create_table(
            "bundle_allocations",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("bundle_id", sa.Integer(), nullable=False),
            sa.Column("instrument_id", sa.Integer(), nullable=False),
            sa.Column("weight", sa.Numeric(precision=10, scale=4), nullable=False),
            sa.Column("position_order", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.ForeignKeyConstraint(["bundle_id"], ["public.bundles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["instrument_id"], ["public.market_data_instruments.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("bundle_id", "instrument_id", name="uq_bundle_allocations_bundle_instrument"),
            schema="public",
        )
        op.create_index("ix_bundle_allocations_bundle_id", "bundle_allocations", ["bundle_id"], unique=False, schema="public")
        op.create_index("ix_bundle_allocations_instrument_id", "bundle_allocations", ["instrument_id"], unique=False, schema="public")

    if _table_exists(conn, "public", "bundle_allocations") and not _constraint_exists(conn, "chk_bundle_allocations_weight_non_negative"):
        op.execute(
            "ALTER TABLE public.bundle_allocations "
            "ADD CONSTRAINT chk_bundle_allocations_weight_non_negative CHECK (weight >= 0)"
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "public", "bundle_allocations"):
        if _constraint_exists(conn, "chk_bundle_allocations_weight_non_negative"):
            op.execute("ALTER TABLE public.bundle_allocations DROP CONSTRAINT chk_bundle_allocations_weight_non_negative")
        op.drop_index("ix_bundle_allocations_instrument_id", table_name="bundle_allocations", schema="public")
        op.drop_index("ix_bundle_allocations_bundle_id", table_name="bundle_allocations", schema="public")
        op.drop_table("bundle_allocations", schema="public")
    if _table_exists(conn, "public", "bundles"):
        op.drop_index("ix_bundles_id", table_name="bundles", schema="public")
        op.drop_index("ix_bundles_asset_class_is_active", table_name="bundles", schema="public")
        op.drop_table("bundles", schema="public")

