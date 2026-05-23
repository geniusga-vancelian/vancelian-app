"""person_external_identities + person_crypto_wallets — bridge Privy / wallets non-custodial.

Identités externes (provider + subject) ancrées sur ``persons.id`` uniquement.
Wallets user-controlled (embedded/external) séparés des tables custody / crypto_positions.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "156"
down_revision = "155"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "person_external_identities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.persons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("external_subject", sa.Text(), nullable=False),
        sa.Column("external_email", sa.Text(), nullable=True),
        sa.Column("external_phone", sa.Text(), nullable=True),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        schema="public",
    )
    op.create_index(
        "ix_person_external_identities_person_id",
        "person_external_identities",
        ["person_id"],
        unique=False,
        schema="public",
    )
    op.create_unique_constraint(
        "uq_person_external_identities_provider_subject",
        "person_external_identities",
        ["provider", "external_subject"],
        schema="public",
    )

    op.create_table(
        "person_crypto_wallets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.persons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "pe_client_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("public.pe_clients.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("wallet_type", sa.Text(), nullable=False),
        sa.Column("chain_type", sa.Text(), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=True),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column(
            "metadata_json",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_person_crypto_wallets_person_id",
        "person_crypto_wallets",
        ["person_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_person_crypto_wallets_pe_client_id",
        "person_crypto_wallets",
        ["pe_client_id"],
        unique=False,
        schema="public",
    )
    op.create_unique_constraint(
        "uq_person_crypto_wallets_provider_chain_address",
        "person_crypto_wallets",
        ["provider", "chain_type", "address"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_person_crypto_wallets_provider_chain_address",
        "person_crypto_wallets",
        schema="public",
        type_="unique",
    )
    op.drop_index(
        "ix_person_crypto_wallets_pe_client_id",
        table_name="person_crypto_wallets",
        schema="public",
    )
    op.drop_index(
        "ix_person_crypto_wallets_person_id",
        table_name="person_crypto_wallets",
        schema="public",
    )
    op.drop_table("person_crypto_wallets", schema="public")

    op.drop_constraint(
        "uq_person_external_identities_provider_subject",
        "person_external_identities",
        schema="public",
        type_="unique",
    )
    op.drop_index(
        "ix_person_external_identities_person_id",
        table_name="person_external_identities",
        schema="public",
    )
    op.drop_table("person_external_identities", schema="public")
