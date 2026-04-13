"""remove_backtest_fk_admin_users_add_email

Revision ID: ff1234abcd56
Revises: ee8235fabc5e
Create Date: 2026-01-09 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ff1234abcd56'
down_revision = 'ee8235fabc5e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop FK constraint on created_by_user_id (quant DB doesn't have admin_users)
    # Use safe drop with IF EXISTS check
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
    
    # Add created_by_email column only if it doesn't exist
    op.execute("""
        DO $$ 
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public'
                AND table_name = 'backtest_runs'
                AND column_name = 'created_by_email'
            ) THEN
                ALTER TABLE public.backtest_runs 
                ADD COLUMN created_by_email VARCHAR(255);
            END IF;
        END $$;
    """)


def downgrade() -> None:
    # Remove created_by_email column only if it exists
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_schema = 'public'
                AND table_name = 'backtest_runs'
                AND column_name = 'created_by_email'
            ) THEN
                ALTER TABLE public.backtest_runs 
                DROP COLUMN created_by_email;
            END IF;
        END $$;
    """)
    
    # Re-add FK constraint (if admin_users table exists)
    op.execute("""
        DO $$ 
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'admin_users'
            ) THEN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.table_constraints 
                    WHERE constraint_name = 'backtest_runs_created_by_user_id_fkey' 
                    AND table_schema = 'public'
                    AND table_name = 'backtest_runs'
                ) THEN
                    ALTER TABLE public.backtest_runs 
                    ADD CONSTRAINT backtest_runs_created_by_user_id_fkey 
                    FOREIGN KEY (created_by_user_id) 
                    REFERENCES public.admin_users(id);
                END IF;
            END IF;
        END $$;
    """)

