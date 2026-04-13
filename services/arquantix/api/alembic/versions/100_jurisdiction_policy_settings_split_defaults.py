"""Jurisdiction policy settings + split default flags (residence vs phone).

Revision ID: 100
Revises: 099
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "100"
down_revision = "099"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "jurisdiction_country_policies",
        sa.Column("is_default_residence", sa.Boolean(), nullable=False, server_default="false"),
        schema="public",
    )
    op.add_column(
        "jurisdiction_country_policies",
        sa.Column("is_default_phone", sa.Boolean(), nullable=False, server_default="false"),
        schema="public",
    )

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE public.jurisdiction_country_policies
            SET is_default_residence = is_default, is_default_phone = is_default
            """
        )
    )

    op.drop_column("jurisdiction_country_policies", "is_default", schema="public")

    op.create_table(
        "jurisdiction_policy_settings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("jurisdiction_code", sa.Text(), nullable=False),
        sa.Column(
            "inherit_phone_countries_from_residence",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
        sa.Column("default_residence_iso2", sa.Text(), nullable=True),
        sa.Column("default_phone_iso2", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(
            ["default_residence_iso2"],
            ["public.country_directory.iso2"],
            name="fk_jps_default_residence_iso2",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["default_phone_iso2"],
            ["public.country_directory.iso2"],
            name="fk_jps_default_phone_iso2",
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint("jurisdiction_code", name="uq_jurisdiction_policy_settings_code"),
        schema="public",
    )

    now = datetime.now(timezone.utc)
    rows = conn.execute(
        sa.text(
            "SELECT DISTINCT jurisdiction_code FROM public.jurisdiction_country_policies"
        )
    ).fetchall()
    for (jcode,) in rows:
        conn.execute(
            sa.text(
                """
                INSERT INTO public.jurisdiction_policy_settings
                (id, jurisdiction_code, inherit_phone_countries_from_residence, default_residence_iso2, default_phone_iso2, updated_at)
                VALUES (:id, :jc, false, NULL, NULL, :ts)
                """
            ),
            {"id": uuid.uuid4(), "jc": jcode, "ts": now},
        )

    conn.execute(
        sa.text(
            """
            UPDATE public.jurisdiction_policy_settings s
            SET default_residence_iso2 = p.country_iso2
            FROM public.jurisdiction_country_policies p
            WHERE p.jurisdiction_code = s.jurisdiction_code
              AND p.is_default_residence = true
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE public.jurisdiction_policy_settings s
            SET default_phone_iso2 = p.country_iso2
            FROM public.jurisdiction_country_policies p
            WHERE p.jurisdiction_code = s.jurisdiction_code
              AND p.is_default_phone = true
            """
        )
    )


def downgrade() -> None:
    op.drop_table("jurisdiction_policy_settings", schema="public")

    op.add_column(
        "jurisdiction_country_policies",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        schema="public",
    )
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE public.jurisdiction_country_policies
            SET is_default = (is_default_residence OR is_default_phone)
            """
        )
    )
    op.drop_column("jurisdiction_country_policies", "is_default_phone", schema="public")
    op.drop_column("jurisdiction_country_policies", "is_default_residence", schema="public")
