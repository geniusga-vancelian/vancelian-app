"""fix_backtest_constraint_safe

Revision ID: 010
Revises: f01ee54920d6
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '010'
down_revision = 'f01ee54920d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Safely drop constraint if it exists
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.table_constraints 
                WHERE constraint_name = 'backtest_runs_created_by_user_id_fkey' 
                AND table_schema = 'public'
                AND table_name = 'backtest_runs'
            ) THEN
                ALTER TABLE public.backtest_runs 
                DROP CONSTRAINT backtest_runs_created_by_user_id_fkey;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Re-add constraint if admin_users table exists
    conn = op.get_bind()
    result = conn.execute(sa.text("""
        SELECT 1 FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_name = 'admin_users'
    """))
    
    if result.fetchone():
        try:
            op.create_foreign_key(
                'backtest_runs_created_by_user_id_fkey',
                'backtest_runs',
                'admin_users',
                ['created_by_user_id'],
                ['id'],
                source_schema='public',
                referent_schema='public'
            )
        except Exception:
            pass
