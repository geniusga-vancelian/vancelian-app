"""fix_backtest_metrics_pk_allow_null_instrument_id

Revision ID: a8723d70ea70
Revises: a7d0e489def9
Create Date: 2026-01-08 18:38:35.197991

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a8723d70ea70'
down_revision: Union[str, None] = 'a7d0e489def9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: Create sequence first, then add a serial ID column as the new primary key
    op.execute("CREATE SEQUENCE IF NOT EXISTS backtest_metrics_id_seq;")
    op.add_column(
        'backtest_metrics',
        sa.Column('id', sa.Integer(), nullable=False, server_default=sa.text("nextval('backtest_metrics_id_seq'::regclass)")),
        schema='public'
    )
    
    # Step 2: Drop the existing PRIMARY KEY constraint (which includes instrument_id)
    op.drop_constraint(
        'uq_backtest_metrics_run_scope_inst_key',
        'backtest_metrics',
        type_='primary',
        schema='public'
    )
    
    # Step 3: Make instrument_id nullable
    op.alter_column(
        'backtest_metrics',
        'instrument_id',
        nullable=True,
        schema='public'
    )
    
    # Step 4: Set ID values for existing rows (if any)
    op.execute("""
        UPDATE public.backtest_metrics 
        SET id = nextval('backtest_metrics_id_seq')
        WHERE id IS NULL;
    """)
    
    # Step 5: Make ID the primary key
    op.create_primary_key(
        'pk_backtest_metrics',
        'backtest_metrics',
        ['id'],
        schema='public'
    )
    
    # Step 6: Create UNIQUE constraint on (run_id, scope, instrument_id, key)
    # PostgreSQL allows NULL in UNIQUE constraints, treating each NULL as distinct
    # This ensures:
    # - Portfolio metrics: (run_id, 'portfolio', NULL, key) is unique per combination
    # - Instrument metrics: (run_id, 'instrument', instrument_id, key) is unique per instrument
    op.create_unique_constraint(
        'uq_backtest_metrics_run_scope_inst_key',
        'backtest_metrics',
        ['run_id', 'scope', 'instrument_id', 'key'],
        schema='public'
    )


def downgrade() -> None:
    # Drop the UNIQUE constraint
    op.drop_constraint(
        'uq_backtest_metrics_run_scope_inst_key',
        'backtest_metrics',
        type_='unique',
        schema='public'
    )
    
    # Drop the new PRIMARY KEY
    op.drop_constraint(
        'pk_backtest_metrics',
        'backtest_metrics',
        type_='primary',
        schema='public'
    )
    
    # Drop the ID column
    op.drop_column('backtest_metrics', 'id', schema='public')
    
    # Drop the sequence
    op.execute("DROP SEQUENCE IF EXISTS backtest_metrics_id_seq;")
    
    # Make instrument_id NOT NULL again (this will fail if NULL values exist)
    op.alter_column(
        'backtest_metrics',
        'instrument_id',
        nullable=False,
        schema='public'
    )
    
    # Recreate original PRIMARY KEY with instrument_id
    op.create_primary_key(
        'uq_backtest_metrics_run_scope_inst_key',
        'backtest_metrics',
        ['run_id', 'scope', 'instrument_id', 'key'],
        schema='public'
    )


