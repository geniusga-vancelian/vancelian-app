"""Fix pe_clients.kyc_status for pending_review sync.

For clients whose linked person has kyc_status = 'pending_review', update
pe_clients.kyc_status from 'in_progress' to 'pending_review'.

The old mapping downgraded pending_review → in_progress; this migration
corrects existing data to match the new 1:1 mapping.

Revision ID: 083
Revises: 082
"""
import logging

from alembic import op
from sqlalchemy import text

revision = "083"
down_revision = "082"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    conn = op.get_bind()

    result = conn.execute(text("""
        UPDATE public.pe_clients c
        SET kyc_status = 'pending_review'
        FROM public.persons p
        WHERE c.person_id = p.id
          AND p.kyc_status = 'pending_review'
          AND c.kyc_status = 'in_progress'
        RETURNING c.id
    """))
    rows = result.fetchall()
    count = len(rows)
    logger.info("[083] Fixed %d pe_clients: in_progress -> pending_review", count)


def downgrade() -> None:
    conn = op.get_bind()

    conn.execute(text("""
        UPDATE public.pe_clients c
        SET kyc_status = 'in_progress'
        FROM public.persons p
        WHERE c.person_id = p.id
          AND p.kyc_status = 'pending_review'
          AND c.kyc_status = 'pending_review'
    """))
