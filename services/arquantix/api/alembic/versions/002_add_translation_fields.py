"""add_translation_fields_to_pages

Revision ID: 002
Revises: 001_initial
Create Date: 2026-01-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade():
    # Add translation fields to pages table
    op.add_column('pages', sa.Column('source_page_id', sa.Integer(), nullable=True))
    op.add_column('pages', sa.Column('translation_status', sa.String(), nullable=False, server_default='manual'))
    op.add_column('pages', sa.Column('translation_meta_json', postgresql.JSON(astext_type=sa.Text()), nullable=True))
    
    # Add foreign key constraint (optional, can be deferred)
    op.create_foreign_key(
        'fk_pages_source_page_id',
        'pages', 'pages',
        ['source_page_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade():
    op.drop_constraint('fk_pages_source_page_id', 'pages', type_='foreignkey')
    op.drop_column('pages', 'translation_meta_json')
    op.drop_column('pages', 'translation_status')
    op.drop_column('pages', 'source_page_id')

