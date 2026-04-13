"""Remove obsolete jurisdictions EU_VS and TEST_AUDIT (sessions, flows, policies, row).

Revision ID: 101
Revises: 100
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "101"
down_revision = "100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            """
            UPDATE public.registration_runtime_settings
            SET current_jurisdiction_code = 'EU'
            WHERE current_jurisdiction_code IN ('EU_VS', 'TEST_AUDIT')
            """
        )
    )
    conn.execute(
        text(
            """
            DO $$
            DECLARE
              jids uuid[];
            BEGIN
              SELECT array_agg(id) INTO jids
              FROM public.registration_jurisdictions
              WHERE code IN ('EU_VS', 'TEST_AUDIT');

              IF jids IS NULL THEN
                RETURN;
              END IF;

              DELETE FROM public.registration_sessions
              WHERE jurisdiction_id = ANY(jids);

              DELETE FROM public.registration_flows
              WHERE jurisdiction_id = ANY(jids);

              DELETE FROM public.jurisdiction_country_policies
              WHERE jurisdiction_code IN ('EU_VS', 'TEST_AUDIT');

              DELETE FROM public.jurisdiction_policy_settings
              WHERE jurisdiction_code IN ('EU_VS', 'TEST_AUDIT');

              DELETE FROM public.registration_jurisdictions
              WHERE id = ANY(jids);
            END $$;
            """
        )
    )


def downgrade() -> None:
    """Data removal is not reversible via migration."""
