"""Add investment_envelopes and investment_envelope_entries — Phase 2A.16.

Envelope Entry Wallet Abstraction: encapsulates conversion, fees, and
allocation inside an investment envelope instead of polluting the user's
crypto wallet with intermediate balances.

Revision ID: 078
Revises: 077
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


revision = "078"
down_revision = "077"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "investment_envelopes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("client_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("reference_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="active"),
        sa.Column("metadata_", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "investment_envelope_entries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("envelope_id", UUID(as_uuid=True), sa.ForeignKey("investment_envelopes.id"), nullable=False, index=True),
        sa.Column("commitment_id", UUID(as_uuid=True), nullable=True),
        sa.Column("entry_asset", sa.String(20), nullable=False),
        sa.Column("entry_amount", sa.Numeric(precision=30, scale=10), nullable=False),
        sa.Column("target_asset", sa.String(20), nullable=False),
        sa.Column("converted_amount", sa.Numeric(precision=30, scale=10), nullable=False),
        sa.Column("fx_rate", sa.Numeric(precision=20, scale=10), nullable=True),
        sa.Column("conversion_type", sa.String(20), nullable=False, server_default="none"),
        sa.Column("conversion_fee", sa.Numeric(precision=30, scale=10), nullable=False, server_default="0"),
        sa.Column("platform_fee", sa.Numeric(precision=30, scale=10), nullable=False, server_default="0"),
        sa.Column("net_allocated", sa.Numeric(precision=30, scale=10), nullable=False),
        sa.Column("external_reference", sa.String(255), nullable=True),
        sa.Column("conversion_details", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("investment_envelope_entries")
    op.drop_table("investment_envelopes")
