"""persons.account_state — état produit PARTIAL / ACTIVE (aligné sur passcode + PeClient).

Revision ID: 129
Revises: 128
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "129"
down_revision = "128"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "persons",
        sa.Column("account_state", sa.String(16), nullable=True),
        schema="public",
    )
    # Backfill : ACTIVE = passcode ACK + pe_clients ; PARTIAL = compte app mobile sans ACTIVE.
    op.execute(
        sa.text(
            """
            UPDATE public.persons p
            SET account_state = 'ACTIVE'
            WHERE EXISTS (SELECT 1 FROM public.pe_clients c WHERE c.person_id = p.id)
            AND (p.profile_json->'security'->>'local_passcode_registered_at') IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE public.persons p
            SET account_state = 'PARTIAL'
            WHERE p.account_state IS NULL
            AND EXISTS (
              SELECT 1 FROM public.admin_users u
              WHERE u.person_id = p.id
              AND u.mobile_app_allowed = true
              AND (
                u.email LIKE '%@signup.internal'
                OR (u.mobile_e164 IS NOT NULL AND trim(u.mobile_e164) <> '')
              )
            )
            """
        )
    )


def downgrade() -> None:
    op.drop_column("persons", "account_state", schema="public")
