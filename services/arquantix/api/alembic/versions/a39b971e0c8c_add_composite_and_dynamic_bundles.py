"""add_composite_and_dynamic_bundles

Revision ID: a39b971e0c8c
Revises: a8723d70ea70
Create Date: 2026-01-09 16:29:04.827790

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a39b971e0c8c'
down_revision: Union[str, None] = 'a8723d70ea70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Market data bundles table
    op.create_table(
        'market_data_bundles',
        sa.Column('id', sa.String(length=36), nullable=False),  # UUID as string (cuid format)
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('instrument_ids', postgresql.JSON(astext_type=sa.Text()), nullable=False),  # Array of instrument IDs
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    op.create_index(op.f('ix_market_data_bundles_id'), 'market_data_bundles', ['id'], unique=False, schema='public')
    op.create_index(op.f('ix_market_data_bundles_name'), 'market_data_bundles', ['name'], unique=False, schema='public')


def downgrade() -> None:
    op.drop_index(op.f('ix_market_data_bundles_name'), table_name='market_data_bundles', schema='public')
    op.drop_index(op.f('ix_market_data_bundles_id'), table_name='market_data_bundles', schema='public')
    op.drop_table('market_data_bundles', schema='public')


