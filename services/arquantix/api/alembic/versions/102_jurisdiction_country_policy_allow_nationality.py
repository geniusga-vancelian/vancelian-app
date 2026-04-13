"""Add allow_nationality to jurisdiction_country_policies + EU/UAE backfill.

Revision ID: 102
Revises: 101
"""
from __future__ import annotations

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
revision = "102"
down_revision = "101"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jurisdiction_country_policies",
        sa.Column(
            "allow_nationality",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        schema="public",
    )

    conn = op.get_bind()
    now = datetime.now(timezone.utc)

    # A) Existing rows for EU / UAE: nationality allowed on the same rows (residence list unchanged).
    conn.execute(
        text(
            """
            UPDATE public.jurisdiction_country_policies
            SET allow_nationality = true
            WHERE jurisdiction_code IN ('EU', 'UAE')
            """
        )
    )

    # B) For EU and UAE: add nationality-only rows for every active directory country missing from policy.
    for jcode in ("EU", "UAE"):
        conn.execute(
            text(
                """
                INSERT INTO public.jurisdiction_country_policies (
                    id,
                    jurisdiction_code,
                    country_iso2,
                    allow_residence,
                    allow_phone_country_code,
                    allow_nationality,
                    is_default_residence,
                    is_default_phone,
                    position,
                    created_at
                )
                SELECT
                    gen_random_uuid(),
                    :jcode,
                    cd.iso2,
                    false,
                    false,
                    true,
                    false,
                    false,
                    20000 + ROW_NUMBER() OVER (ORDER BY cd.iso2),
                    :created_at
                FROM public.country_directory cd
                WHERE cd.is_active = true
                  AND NOT EXISTS (
                      SELECT 1
                      FROM public.jurisdiction_country_policies j
                      WHERE j.jurisdiction_code = :jcode
                        AND j.country_iso2 = cd.iso2
                  )
                """
            ),
            {"jcode": jcode, "created_at": now},
        )

    # Server default was only for backfill; new rows should set explicitly in app layer.
    op.alter_column(
        "jurisdiction_country_policies",
        "allow_nationality",
        server_default=None,
        schema="public",
    )


def downgrade() -> None:
    op.drop_column("jurisdiction_country_policies", "allow_nationality", schema="public")
