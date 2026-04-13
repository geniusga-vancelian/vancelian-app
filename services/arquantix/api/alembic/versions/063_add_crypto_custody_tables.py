"""Add crypto_custody_accounts and crypto_custody_balances.

Revision ID: 063
Revises: 062
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "063"
down_revision = "062"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crypto_custody_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("account_type", sa.String(50), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_account_id", sa.String(255), nullable=True),
        sa.Column("label", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("metadata_", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset", "account_type", name="uq_crypto_custody_accounts_asset_type"),
        schema="public",
    )
    op.create_index(
        "ix_crypto_custody_accounts_asset",
        "crypto_custody_accounts",
        ["asset"],
        schema="public",
    )
    op.create_index(
        "ix_crypto_custody_accounts_account_type",
        "crypto_custody_accounts",
        ["account_type"],
        schema="public",
    )

    op.create_table(
        "crypto_custody_balances",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.crypto_custody_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("actual_balance", sa.Numeric(30, 18), nullable=False, server_default="0"),
        sa.Column("expected_balance", sa.Numeric(30, 18), nullable=False, server_default="0"),
        sa.Column("updated_from_provider_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("account_id", name="uq_crypto_custody_balances_account_id"),
        schema="public",
    )
    op.create_index(
        "ix_crypto_custody_balances_account_id",
        "crypto_custody_balances",
        ["account_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_table("crypto_custody_balances", schema="public")
    op.drop_table("crypto_custody_accounts", schema="public")
