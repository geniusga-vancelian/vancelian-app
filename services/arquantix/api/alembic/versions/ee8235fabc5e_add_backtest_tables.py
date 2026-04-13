"""add_backtest_tables

Revision ID: ee8235fabc5e
Revises: dd7124eabc4d
Create Date: 2026-01-09 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ee8235fabc5e'
down_revision = 'dd7124eabc4d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Backtest runs table
    op.create_table(
        'backtest_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('effective_start_date', sa.Date(), nullable=True),
        sa.Column('effective_end_date', sa.Date(), nullable=True),
        sa.Column('rebalance', sa.String(length=20), nullable=False),
        sa.Column('strategy_type', sa.String(length=50), nullable=False),
        sa.Column('strategy_params_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('fees_bps', sa.Numeric(precision=10, scale=4), nullable=False, server_default='0.0'),
        sa.Column('slippage_bps', sa.Numeric(precision=10, scale=4), nullable=False, server_default='0.0'),
        sa.Column('allow_weekend_trading', sa.String(length=10), nullable=False, server_default='true'),
        sa.Column('instrument_ids_json', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['created_by_user_id'], ['admin_users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    op.create_index(op.f('ix_backtest_runs_id'), 'backtest_runs', ['id'], unique=False, schema='public')
    
    # Backtest portfolio series table
    op.create_table(
        'backtest_portfolio_series',
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('nav_base100', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('portfolio_return', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('drawdown', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('turnover', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('costs', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('weights_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('tradable_json', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['backtest_runs.id'], ),
        sa.PrimaryKeyConstraint('run_id', 'date'),
        sa.UniqueConstraint('run_id', 'date', name='uq_backtest_portfolio_series_run_date'),
        schema='public'
    )
    op.create_index(op.f('ix_backtest_portfolio_series_run_id'), 'backtest_portfolio_series', ['run_id'], unique=False, schema='public')
    op.create_index(op.f('ix_backtest_portfolio_series_date'), 'backtest_portfolio_series', ['date'], unique=False, schema='public')
    
    # Backtest instrument series table
    op.create_table(
        'backtest_instrument_series',
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('instrument_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('base100', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('instrument_return', sa.Numeric(precision=20, scale=8), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['backtest_runs.id'], ),
        sa.ForeignKeyConstraint(['instrument_id'], ['market_data_instruments.id'], ),
        sa.PrimaryKeyConstraint('run_id', 'instrument_id', 'date'),
        sa.UniqueConstraint('run_id', 'instrument_id', 'date', name='uq_backtest_instrument_series_run_inst_date'),
        schema='public'
    )
    op.create_index(op.f('ix_backtest_instrument_series_run_id'), 'backtest_instrument_series', ['run_id'], unique=False, schema='public')
    op.create_index(op.f('ix_backtest_instrument_series_instrument_id'), 'backtest_instrument_series', ['instrument_id'], unique=False, schema='public')
    op.create_index(op.f('ix_backtest_instrument_series_date'), 'backtest_instrument_series', ['date'], unique=False, schema='public')
    
    # Backtest metrics table
    op.create_table(
        'backtest_metrics',
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('scope', sa.String(length=20), nullable=False),
        sa.Column('instrument_id', sa.Integer(), nullable=True),
        sa.Column('key', sa.String(length=50), nullable=False),
        sa.Column('value', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['backtest_runs.id'], ),
        sa.ForeignKeyConstraint(['instrument_id'], ['market_data_instruments.id'], ),
        sa.PrimaryKeyConstraint('run_id', 'scope', 'instrument_id', 'key'),
        sa.UniqueConstraint('run_id', 'scope', 'instrument_id', 'key', name='uq_backtest_metrics_run_scope_inst_key'),
        schema='public'
    )
    op.create_index(op.f('ix_backtest_metrics_run_id'), 'backtest_metrics', ['run_id'], unique=False, schema='public')


def downgrade() -> None:
    op.drop_index(op.f('ix_backtest_metrics_run_id'), table_name='backtest_metrics', schema='public')
    op.drop_table('backtest_metrics', schema='public')
    op.drop_index(op.f('ix_backtest_instrument_series_date'), table_name='backtest_instrument_series', schema='public')
    op.drop_index(op.f('ix_backtest_instrument_series_instrument_id'), table_name='backtest_instrument_series', schema='public')
    op.drop_index(op.f('ix_backtest_instrument_series_run_id'), table_name='backtest_instrument_series', schema='public')
    op.drop_table('backtest_instrument_series', schema='public')
    op.drop_index(op.f('ix_backtest_portfolio_series_date'), table_name='backtest_portfolio_series', schema='public')
    op.drop_index(op.f('ix_backtest_portfolio_series_run_id'), table_name='backtest_portfolio_series', schema='public')
    op.drop_table('backtest_portfolio_series', schema='public')
    op.drop_index(op.f('ix_backtest_runs_id'), table_name='backtest_runs', schema='public')
    op.drop_table('backtest_runs', schema='public')






