"""add_documents_table

Revision ID: 007
Revises: 006
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('doc_type', sa.Text(), nullable=False),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('storage_provider', sa.Text(), nullable=False),
        sa.Column('storage_bucket', sa.Text(), nullable=False),
        sa.Column('storage_key', sa.Text(), nullable=False),
        sa.Column('content_type', sa.Text(), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('sha256', sa.Text(), nullable=False),
        sa.Column('metadata_json', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['public.persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    
    # Composite index on (person_id, created_at)
    op.create_index(
        'ix_documents_person_id_created_at',
        'documents',
        ['person_id', 'created_at'],
        unique=False,
        schema='public'
    )
    
    # GIN index on metadata_json
    op.create_index(
        'ix_documents_metadata_json',
        'documents',
        ['metadata_json'],
        unique=False,
        postgresql_using='gin',
        schema='public'
    )
    
    # Create trigger function for auto-updating updated_at
    op.execute("""
        CREATE OR REPLACE FUNCTION update_documents_updated_at()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = now();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # Create trigger
    op.execute("""
        CREATE TRIGGER documents_updated_at_trigger
        BEFORE UPDATE ON public.documents
        FOR EACH ROW
        EXECUTE FUNCTION update_documents_updated_at();
    """)


def downgrade() -> None:
    # Drop trigger
    op.execute("DROP TRIGGER IF EXISTS documents_updated_at_trigger ON public.documents")
    
    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS update_documents_updated_at()")
    
    # Drop indexes
    op.drop_index('ix_documents_metadata_json', table_name='documents', schema='public')
    op.drop_index('ix_documents_person_id_created_at', table_name='documents', schema='public')
    
    # Drop table
    op.drop_table('documents', schema='public')
