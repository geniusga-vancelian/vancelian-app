"""add_jurisdiction_configs_table

Revision ID: 006
Revises: 005
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'jurisdiction_configs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('jurisdiction', sa.Text(), nullable=False),
        sa.Column('purpose', sa.Text(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('config_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jurisdiction', 'purpose', 'version', name='uq_jurisdiction_configs_jurisdiction_purpose_version'),
        schema='public'
    )
    
    # Composite index on (jurisdiction, purpose, status)
    op.create_index(
        'ix_jurisdiction_configs_jurisdiction_purpose_status',
        'jurisdiction_configs',
        ['jurisdiction', 'purpose', 'status'],
        unique=False,
        schema='public'
    )
    
    # GIN index on config_json
    op.create_index(
        'ix_jurisdiction_configs_config_json',
        'jurisdiction_configs',
        ['config_json'],
        unique=False,
        postgresql_using='gin',
        schema='public'
    )
    
    # Create trigger function for auto-updating updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_jurisdiction_configs_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger
    op.execute("""
        CREATE TRIGGER jurisdiction_configs_updated_at_trigger
        BEFORE UPDATE ON public.jurisdiction_configs
        FOR EACH ROW
        EXECUTE FUNCTION update_jurisdiction_configs_updated_at();
    """)


def downgrade() -> None:
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS jurisdiction_configs_updated_at_trigger ON public.jurisdiction_configs")
    
    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_jurisdiction_configs_updated_at()")
    
    # Drop indexes
    op.drop_index('ix_jurisdiction_configs_config_json', table_name='jurisdiction_configs', schema='public')
    op.drop_index('ix_jurisdiction_configs_jurisdiction_purpose_status', table_name='jurisdiction_configs', schema='public')
    
    # Drop table
    op.drop_table('jurisdiction_configs', schema='public')
