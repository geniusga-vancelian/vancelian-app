"""add_persons_table

Revision ID: 004
Revises: 003
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'persons',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', sa.Text(), server_default='active', nullable=False),
        sa.Column('jurisdiction', sa.Text(), nullable=True),
        sa.Column('profile_json', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    
    # Create GIN index on profile_json
    op.create_index(
        'ix_persons_profile_json',
        'persons',
        ['profile_json'],
        unique=False,
        postgresql_using='gin',
        schema='public'
    )
    
    # Create btree index on jurisdiction
    op.create_index(
        'ix_persons_jurisdiction',
        'persons',
        ['jurisdiction'],
        unique=False,
        schema='public'
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_persons_jurisdiction', table_name='persons', schema='public')
    op.drop_index('ix_persons_profile_json', table_name='persons', schema='public')
    
    # Drop table
    op.drop_table('persons', schema='public')
