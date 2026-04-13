"""remove_updated_at_triggers

Revision ID: 009
Revises: 008
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop triggers
    op.execute("DROP TRIGGER IF EXISTS field_definitions_updated_at_trigger ON public.field_definitions")
    op.execute("DROP TRIGGER IF EXISTS jurisdiction_configs_updated_at_trigger ON public.jurisdiction_configs")
    op.execute("DROP TRIGGER IF EXISTS documents_updated_at_trigger ON public.documents")
    
    # Drop trigger functions
    op.execute("DROP FUNCTION IF EXISTS update_field_definitions_updated_at()")
    op.execute("DROP FUNCTION IF EXISTS update_jurisdiction_configs_updated_at()")
    op.execute("DROP FUNCTION IF EXISTS update_documents_updated_at()")


def downgrade() -> None:
    # Recreate trigger functions
    op.execute("""
        CREATE OR REPLACE FUNCTION update_field_definitions_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE OR REPLACE FUNCTION update_jurisdiction_configs_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE OR REPLACE FUNCTION update_documents_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Recreate triggers
    op.execute("""
        CREATE TRIGGER field_definitions_updated_at_trigger
        BEFORE UPDATE ON public.field_definitions
        FOR EACH ROW
        EXECUTE FUNCTION update_field_definitions_updated_at();
    """)
    
    op.execute("""
        CREATE TRIGGER jurisdiction_configs_updated_at_trigger
        BEFORE UPDATE ON public.jurisdiction_configs
        FOR EACH ROW
        EXECUTE FUNCTION update_jurisdiction_configs_updated_at();
    """)
    
    op.execute("""
        CREATE TRIGGER documents_updated_at_trigger
        BEFORE UPDATE ON public.documents
        FOR EACH ROW
        EXECUTE FUNCTION update_documents_updated_at();
    """)
