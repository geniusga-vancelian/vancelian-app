"""add_market_data_tables

Revision ID: dd7124eabc4d
Revises: cc6123cabd3c
Create Date: 2026-01-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'dd7124eabc4d'
down_revision = 'cc6123cabd3c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Market data instruments table
    op.create_table(
        'market_data_instruments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=True),
        sa.Column('asset_class', sa.String(length=20), nullable=False),
        sa.Column('weekend_tradable', sa.String(length=10), server_default='false', nullable=False),
        sa.Column('provider', sa.String(length=50), server_default='alphavantage', nullable=False),
        sa.Column('provider_symbol', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.String(length=10), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol'),
        schema='public'
    )
    op.create_index(op.f('ix_market_data_instruments_id'), 'market_data_instruments', ['id'], unique=False, schema='public')
    op.create_index(op.f('ix_market_data_instruments_symbol'), 'market_data_instruments', ['symbol'], unique=False, schema='public')
    
    # Market data bars D1 table
    op.create_table(
        'market_data_bars_d1',
        sa.Column('instrument_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('open', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('high', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('low', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('close', sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column('volume', sa.BigInteger(), nullable=False),
        sa.Column('source', sa.String(length=50), server_default='alphavantage', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['instrument_id'], ['market_data_instruments.id'], ),
        sa.PrimaryKeyConstraint('instrument_id', 'date'),
        sa.UniqueConstraint('instrument_id', 'date', name='uq_market_data_bars_d1_instrument_date'),
        schema='public'
    )
    op.create_index(op.f('ix_market_data_bars_d1_instrument_id'), 'market_data_bars_d1', ['instrument_id'], unique=False, schema='public')
    op.create_index(op.f('ix_market_data_bars_d1_date'), 'market_data_bars_d1', ['date'], unique=False, schema='public')


def downgrade() -> None:
    op.drop_index(op.f('ix_market_data_bars_d1_date'), table_name='market_data_bars_d1', schema='public')
    op.drop_index(op.f('ix_market_data_bars_d1_instrument_id'), table_name='market_data_bars_d1', schema='public')
    op.drop_table('market_data_bars_d1', schema='public')
    op.drop_index(op.f('ix_market_data_instruments_symbol'), table_name='market_data_instruments', schema='public')
    op.drop_index(op.f('ix_market_data_instruments_id'), table_name='market_data_instruments', schema='public')
    op.drop_table('market_data_instruments', schema='public')






