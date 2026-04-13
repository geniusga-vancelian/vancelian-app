"""Country directory + jurisdiction country policies (phone / residence).

Revision ID: 099
Revises: 098
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "099"
down_revision = "098"
branch_labels = None
depends_on = None


def _now():
    return datetime.now(timezone.utc)


# (iso2, iso3, en, fr, dial) — explicit EU/EEA list + AE (no implicit “all Europe” rule)
_COUNTRY_ROWS: list[tuple[str, str, str, str, str]] = [
    ("AT", "AUT", "Austria", "Autriche", "+43"),
    ("BE", "BEL", "Belgium", "Belgique", "+32"),
    ("BG", "BGR", "Bulgaria", "Bulgarie", "+359"),
    ("HR", "HRV", "Croatia", "Croatie", "+385"),
    ("CY", "CYP", "Cyprus", "Chypre", "+357"),
    ("CZ", "CZE", "Czechia", "Tchéquie", "+420"),
    ("DK", "DNK", "Denmark", "Danemark", "+45"),
    ("EE", "EST", "Estonia", "Estonie", "+372"),
    ("FI", "FIN", "Finland", "Finlande", "+358"),
    ("FR", "FRA", "France", "France", "+33"),
    ("DE", "DEU", "Germany", "Allemagne", "+49"),
    ("GR", "GRC", "Greece", "Grèce", "+30"),
    ("HU", "HUN", "Hungary", "Hongrie", "+36"),
    ("IE", "IRL", "Ireland", "Irlande", "+353"),
    ("IT", "ITA", "Italy", "Italie", "+39"),
    ("LV", "LVA", "Latvia", "Lettonie", "+371"),
    ("LT", "LTU", "Lithuania", "Lituanie", "+370"),
    ("LU", "LUX", "Luxembourg", "Luxembourg", "+352"),
    ("MT", "MLT", "Malta", "Malte", "+356"),
    ("NL", "NLD", "Netherlands", "Pays-Bas", "+31"),
    ("PL", "POL", "Poland", "Pologne", "+48"),
    ("PT", "PRT", "Portugal", "Portugal", "+351"),
    ("RO", "ROU", "Romania", "Roumanie", "+40"),
    ("SK", "SVK", "Slovakia", "Slovaquie", "+421"),
    ("SI", "SVN", "Slovenia", "Slovénie", "+386"),
    ("ES", "ESP", "Spain", "Espagne", "+34"),
    ("SE", "SWE", "Sweden", "Suède", "+46"),
    ("IS", "ISL", "Iceland", "Islande", "+354"),
    ("LI", "LIE", "Liechtenstein", "Liechtenstein", "+423"),
    ("NO", "NOR", "Norway", "Norvège", "+47"),
    ("AE", "ARE", "United Arab Emirates", "Émirats arabes unis", "+971"),
]


def upgrade() -> None:
    op.create_table(
        "country_directory",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("iso2", sa.Text(), nullable=False),
        sa.Column("iso3", sa.Text(), nullable=False),
        sa.Column("display_name_en", sa.Text(), nullable=False),
        sa.Column("display_name_fr", sa.Text(), nullable=False),
        sa.Column("phone_country_code", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("iso2", name="uq_country_directory_iso2"),
        sa.UniqueConstraint("iso3", name="uq_country_directory_iso3"),
        schema="public",
    )

    op.create_table(
        "jurisdiction_country_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("jurisdiction_code", sa.Text(), nullable=False),
        sa.Column("country_iso2", sa.Text(), nullable=False),
        sa.Column("allow_residence", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("allow_phone_country_code", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(
            ["country_iso2"],
            ["public.country_directory.iso2"],
            name="fk_jcp_country_iso2",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("jurisdiction_code", "country_iso2", name="uq_jcp_jurisdiction_country"),
        schema="public",
    )
    op.create_index(
        "ix_jcp_jurisdiction_code",
        "jurisdiction_country_policies",
        ["jurisdiction_code"],
        schema="public",
    )

    conn = op.get_bind()
    now = _now()
    for iso2, iso3, en, fr, dial in _COUNTRY_ROWS:
        conn.execute(
            sa.text(
                """
                INSERT INTO public.country_directory
                (id, iso2, iso3, display_name_en, display_name_fr, phone_country_code, is_active, created_at)
                VALUES (:id, :iso2, :iso3, :en, :fr, :dial, true, :created_at)
                """
            ),
            {
                "id": uuid.uuid4(),
                "iso2": iso2,
                "iso3": iso3,
                "en": en,
                "fr": fr,
                "dial": dial,
                "created_at": now,
            },
        )

    eu_iso2 = [r[0] for r in _COUNTRY_ROWS if r[0] != "AE"]
    for jcode in ("EU", "EU_VS"):
        pos = 0
        for iso2 in eu_iso2:
            is_def = iso2 == "FR"
            conn.execute(
                sa.text(
                    """
                    INSERT INTO public.jurisdiction_country_policies
                    (id, jurisdiction_code, country_iso2, allow_residence, allow_phone_country_code, is_default, position, created_at)
                    VALUES (:id, :j, :iso2, true, true, :is_def, :pos, :created_at)
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "j": jcode,
                    "iso2": iso2,
                    "is_def": is_def,
                    "pos": pos,
                    "created_at": now,
                },
            )
            pos += 1

    conn.execute(
        sa.text(
            """
            INSERT INTO public.jurisdiction_country_policies
            (id, jurisdiction_code, country_iso2, allow_residence, allow_phone_country_code, is_default, position, created_at)
            VALUES (:id, 'UAE', 'AE', true, true, true, 0, :created_at)
            """
        ),
        {"id": uuid.uuid4(), "created_at": now},
    )


def downgrade() -> None:
    op.drop_index("ix_jcp_jurisdiction_code", table_name="jurisdiction_country_policies", schema="public")
    op.drop_table("jurisdiction_country_policies", schema="public")
    op.drop_table("country_directory", schema="public")
