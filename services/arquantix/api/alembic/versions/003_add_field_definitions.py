"""add_field_definitions

Revision ID: 003
Revises: cc6123cabd3c
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = 'a39b971e0c8c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'field_definitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slug', sa.Text(), nullable=False),
        sa.Column('field_name_en', sa.Text(), nullable=False),
        sa.Column('field_type', sa.Text(), nullable=False),
        sa.Column('category', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        schema='public'
    )
    
    # Create btree index on category
    op.create_index(
        'ix_field_definitions_category',
        'field_definitions',
        ['category'],
        unique=False,
        schema='public'
    )
    
    # Create trigger function for auto-updating updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_field_definitions_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger
    op.execute("""
        CREATE TRIGGER field_definitions_updated_at_trigger
        BEFORE UPDATE ON public.field_definitions
        FOR EACH ROW
        EXECUTE FUNCTION update_field_definitions_updated_at();
    """)


def downgrade() -> None:
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS field_definitions_updated_at_trigger ON public.field_definitions")
    
    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_field_definitions_updated_at()")
    
    # Drop index
    op.drop_index('ix_field_definitions_category', table_name='field_definitions', schema='public')
    
    # Drop table
    op.drop_table('field_definitions', schema='public')
