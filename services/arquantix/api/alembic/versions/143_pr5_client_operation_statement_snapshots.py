"""PR5 — Snapshots documentaires OperationStatementPayload (audit / relecture).

Revision ID: 143
Revises: 142
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "143"
down_revision = "142"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "client_operation_statement_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.pe_clients.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_system", sa.String(20), nullable=False),
        sa.Column("source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("schema_version", sa.String(32), nullable=False),
        sa.Column(
            "payload_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("content_sha256", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("pdf_sha256", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "client_id",
            "source_system",
            "source_id",
            name="uq_client_operation_statement_snapshots_client_source",
        ),
        schema="public",
    )
    op.create_index(
        "ix_client_operation_statement_snapshots_client_id",
        "client_operation_statement_snapshots",
        ["client_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_client_operation_statement_snapshots_client_id",
        table_name="client_operation_statement_snapshots",
        schema="public",
    )
    op.drop_table("client_operation_statement_snapshots", schema="public")
