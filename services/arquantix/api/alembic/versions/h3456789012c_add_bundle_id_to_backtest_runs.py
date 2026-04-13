"""add_bundle_id_to_backtest_runs

Revision ID: h3456789012c
Revises: g2345678901b
Create Date: 2026-01-09 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'h3456789012c'
down_revision = 'g2345678901b'
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


def _constraint_exists(conn, name: str) -> bool:
    r = conn.execute(sa.text("SELECT 1 FROM pg_constraint WHERE conname = :n"), {"n": name})
    return r.scalar() is not None


def _index_exists(conn, schema: str, index_name: str) -> bool:
    r = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes WHERE schemaname = :schema AND indexname = :idx"
        ),
        {"schema": schema, "idx": index_name},
    )
    return r.scalar() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, "public", "backtest_runs", "bundle_id"):
        op.add_column(
            "backtest_runs",
            sa.Column("bundle_id", sa.Integer(), nullable=True),
            schema="public",
        )
    if not _column_exists(conn, "public", "backtest_runs", "rebalance_mode"):
        op.add_column(
            "backtest_runs",
            sa.Column("rebalance_mode", sa.String(length=50), nullable=True, server_default="strategy_based"),
            schema="public",
        )

    if not _constraint_exists(conn, "fk_backtest_runs_bundle_id"):
        op.create_foreign_key(
            "fk_backtest_runs_bundle_id",
            "backtest_runs",
            "bundles",
            ["bundle_id"],
            ["id"],
            ondelete="SET NULL",
            source_schema="public",
            referent_schema="public",
        )

    if not _index_exists(conn, "public", "ix_backtest_runs_bundle_id"):
        op.create_index(
            "ix_backtest_runs_bundle_id",
            "backtest_runs",
            ["bundle_id"],
            unique=False,
            schema="public",
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _index_exists(conn, "public", "ix_backtest_runs_bundle_id"):
        op.drop_index("ix_backtest_runs_bundle_id", table_name="backtest_runs", schema="public")
    if _constraint_exists(conn, "fk_backtest_runs_bundle_id"):
        op.drop_constraint("fk_backtest_runs_bundle_id", "backtest_runs", type_="foreignkey", schema="public")
    if _column_exists(conn, "public", "backtest_runs", "rebalance_mode"):
        op.drop_column("backtest_runs", "rebalance_mode", schema="public")
    if _column_exists(conn, "public", "backtest_runs", "bundle_id"):
        op.drop_column("backtest_runs", "bundle_id", schema="public")

