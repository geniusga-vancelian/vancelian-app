"""PR4 — admin_users / pe_clients : email nullable, unique partiel (WHERE email IS NOT NULL), backfill @signup.internal → NULL.

Revision ID: 130
Revises: 129
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "130"
down_revision = "129"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- admin_users ---
    op.execute(sa.text("DROP INDEX IF EXISTS public.ix_admin_users_email"))
    op.execute(sa.text("ALTER TABLE public.admin_users ALTER COLUMN email DROP NOT NULL"))
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX ix_admin_users_email
            ON public.admin_users (email)
            WHERE email IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE public.admin_users
            SET email = NULL
            WHERE email IS NOT NULL
              AND (
                lower(email::text) LIKE '%@signup.internal'
                OR lower(email::text) LIKE '%@internal'
              )
            """
        )
    )

    # --- pe_clients ---
    op.execute(sa.text("DROP INDEX IF EXISTS public.ix_pe_clients_email"))
    op.execute(sa.text("ALTER TABLE public.pe_clients ALTER COLUMN email DROP NOT NULL"))
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX ix_pe_clients_email
            ON public.pe_clients (email)
            WHERE email IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE public.pe_clients
            SET email = NULL
            WHERE email IS NOT NULL
              AND (
                lower(email::text) LIKE '%@signup.internal'
                OR lower(email::text) LIKE '%@internal'
              )
            """
        )
    )


def downgrade() -> None:
    raise NotImplementedError(
        "PR4 downgrade non supporté : réintroduire des e-mails techniques ou NOT NULL sans données."
    )
