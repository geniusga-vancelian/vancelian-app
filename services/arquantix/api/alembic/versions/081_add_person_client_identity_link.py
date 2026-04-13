"""Add person<->client identity link columns and persons.kyc_status.

Phase 1A: All new columns are NULLABLE to allow safe rollout.
Phase 1B (migration 082) will backfill and harden to NOT NULL.

Changes:
- persons: add client_id (UUID, UNIQUE) + kyc_status (TEXT)
- pe_clients: add person_id (UUID, UNIQUE, FK -> persons.id)

Revision ID: 081
Revises: 080
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "081"
down_revision = "080"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- persons: add client_id (nullable, unique) ---
    op.add_column(
        "persons",
        sa.Column("client_id", UUID(as_uuid=True), nullable=True),
        schema="public",
    )
    op.create_unique_constraint(
        "uq_persons_client_id", "persons", ["client_id"], schema="public"
    )

    # --- persons: add kyc_status ---
    op.add_column(
        "persons",
        sa.Column("kyc_status", sa.Text(), nullable=True, server_default="not_started"),
        schema="public",
    )

    # --- pe_clients: add person_id (nullable, unique, FK -> persons.id) ---
    op.add_column(
        "pe_clients",
        sa.Column("person_id", UUID(as_uuid=True), nullable=True),
        schema="public",
    )
    op.create_unique_constraint(
        "uq_pe_clients_person_id", "pe_clients", ["person_id"], schema="public"
    )
    op.create_foreign_key(
        "fk_pe_clients_person_id",
        "pe_clients",
        "persons",
        ["person_id"],
        ["id"],
        source_schema="public",
        referent_schema="public",
    )

    # Indexes for fast lookups
    op.create_index(
        "ix_persons_client_id", "persons", ["client_id"], schema="public"
    )
    op.create_index(
        "ix_pe_clients_person_id", "pe_clients", ["person_id"], schema="public"
    )


def downgrade() -> None:
    op.drop_index("ix_pe_clients_person_id", table_name="pe_clients", schema="public")
    op.drop_index("ix_persons_client_id", table_name="persons", schema="public")
    op.drop_constraint("fk_pe_clients_person_id", "pe_clients", schema="public", type_="foreignkey")
    op.drop_constraint("uq_pe_clients_person_id", "pe_clients", schema="public", type_="unique")
    op.drop_column("pe_clients", "person_id", schema="public")
    op.drop_column("persons", "kyc_status", schema="public")
    op.drop_constraint("uq_persons_client_id", "persons", schema="public", type_="unique")
    op.drop_column("persons", "client_id", schema="public")
