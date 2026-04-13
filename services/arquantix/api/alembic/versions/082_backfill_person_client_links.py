"""Backfill person<->client links and harden constraints.

Phase 1B:
1. For each pe_client without a person_id, create a matching person row
   and establish the bidirectional link.
2. For each person without a client_id, log a warning (no pe_client to link).
3. Validate zero orphans among linked rows.
4. Harden columns to NOT NULL (only if backfill leaves zero NULLs).

Revision ID: 082
Revises: 081
"""
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import text

revision = "082"
down_revision = "081"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.migration.082")


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------
    # Step 1: Backfill pe_clients that have no linked person
    # ------------------------------------------------------------------
    unlinked_clients = conn.execute(
        text("SELECT id, email, kyc_status FROM public.pe_clients WHERE person_id IS NULL")
    ).fetchall()
    logger.info("Backfill: %d pe_clients without person_id", len(unlinked_clients))

    for client_row in unlinked_clients:
        client_id = client_row[0]
        kyc_status = client_row[2] or "not_started"

        # Create a person for this client
        conn.execute(
            text("""
                INSERT INTO public.persons (id, status, jurisdiction, profile_json, client_id, kyc_status, created_at, updated_at)
                VALUES (gen_random_uuid(), 'active', NULL, '{}', :client_id, :kyc_status, now(), now())
                RETURNING id
            """),
            {"client_id": client_id, "kyc_status": kyc_status},
        )
        # Retrieve the newly created person id
        result = conn.execute(
            text("SELECT id FROM public.persons WHERE client_id = :client_id"),
            {"client_id": client_id},
        ).fetchone()
        person_id = result[0]

        # Link pe_client back to person
        conn.execute(
            text("UPDATE public.pe_clients SET person_id = :person_id WHERE id = :client_id"),
            {"person_id": person_id, "client_id": client_id},
        )

    logger.info("Backfill: linked %d pe_clients to new persons", len(unlinked_clients))

    # ------------------------------------------------------------------
    # Step 2: Handle persons without a client_id (standalone compliance records)
    # ------------------------------------------------------------------
    orphan_persons = conn.execute(
        text("SELECT COUNT(*) FROM public.persons WHERE client_id IS NULL")
    ).scalar()
    if orphan_persons > 0:
        logger.warning(
            "Backfill: %d persons have no client_id (standalone compliance records). "
            "These will NOT be hardened to NOT NULL in this migration.",
            orphan_persons,
        )

    # ------------------------------------------------------------------
    # Step 3: Validate integrity for linked rows
    # ------------------------------------------------------------------
    broken_clients = conn.execute(
        text("SELECT COUNT(*) FROM public.pe_clients WHERE person_id IS NULL")
    ).scalar()
    broken_persons_with_client = conn.execute(
        text("""
            SELECT COUNT(*) FROM public.persons p
            WHERE p.client_id IS NOT NULL
            AND NOT EXISTS (SELECT 1 FROM public.pe_clients c WHERE c.id = p.client_id)
        """)
    ).scalar()

    if broken_clients > 0:
        raise RuntimeError(
            f"Integrity check failed: {broken_clients} pe_clients still have NULL person_id after backfill"
        )
    if broken_persons_with_client > 0:
        raise RuntimeError(
            f"Integrity check failed: {broken_persons_with_client} persons reference a non-existent pe_client"
        )

    # ------------------------------------------------------------------
    # Step 4: Harden constraints
    # ------------------------------------------------------------------
    # pe_clients.person_id -> NOT NULL (every client MUST have a person)
    op.alter_column(
        "pe_clients", "person_id",
        nullable=False,
        schema="public",
    )
    logger.info("Hardened: pe_clients.person_id is now NOT NULL")

    # persons.kyc_status -> NOT NULL (every person has a KYC status)
    # First, fill any remaining NULLs with default
    conn.execute(
        text("UPDATE public.persons SET kyc_status = 'not_started' WHERE kyc_status IS NULL")
    )
    op.alter_column(
        "persons", "kyc_status",
        nullable=False,
        server_default="not_started",
        schema="public",
    )
    logger.info("Hardened: persons.kyc_status is now NOT NULL")

    # persons.client_id stays NULLABLE for now:
    # standalone compliance persons (no trading account yet) are valid.
    # This will be addressed in a future hardening phase if needed.
    logger.info(
        "Note: persons.client_id remains NULLABLE — "
        "standalone compliance records without a trading account are allowed."
    )

    total_linked = conn.execute(
        text("SELECT COUNT(*) FROM public.pe_clients WHERE person_id IS NOT NULL")
    ).scalar()
    logger.info("Backfill complete: %d pe_clients fully linked to persons", total_linked)


def downgrade() -> None:
    # Revert NOT NULL constraints
    op.alter_column("pe_clients", "person_id", nullable=True, schema="public")
    op.alter_column("persons", "kyc_status", nullable=True, schema="public")

    # Remove backfilled links (restore to pre-backfill state)
    conn = op.get_bind()
    conn.execute(text("UPDATE public.pe_clients SET person_id = NULL"))
    # Delete persons that were auto-created during backfill
    # (identified by having a client_id set and empty profile_json)
    conn.execute(
        text("""
            DELETE FROM public.persons
            WHERE client_id IS NOT NULL
            AND profile_json = '{}'::jsonb
            AND jurisdiction IS NULL
        """)
    )
    conn.execute(text("UPDATE public.persons SET client_id = NULL"))
