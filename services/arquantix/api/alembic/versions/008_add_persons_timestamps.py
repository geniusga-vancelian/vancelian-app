"""add_persons_timestamps

Revision ID: 008
Revises: 007
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('persons', sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), schema='public')
    op.add_column('persons', sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False), schema='public')


def downgrade() -> None:
    op.drop_column('persons', 'updated_at', schema='public')
    op.drop_column('persons', 'created_at', schema='public')
