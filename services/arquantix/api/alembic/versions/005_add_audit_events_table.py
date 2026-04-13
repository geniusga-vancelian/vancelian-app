"""add_audit_events_table

Revision ID: 005
Revises: 004
Create Date: 2026-01-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('person_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.Text(), nullable=False),
        sa.Column('actor_type', sa.Text(), nullable=False),
        sa.Column('actor_id', sa.Text(), nullable=True),
        sa.Column('correlation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('schema_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['person_id'], ['public.persons.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    
    # Composite index on (person_id, created_at)
    op.create_index(
        'ix_audit_events_person_id_created_at',
        'audit_events',
        ['person_id', 'created_at'],
        unique=False,
        schema='public'
    )
    
    # Index on event_type
    op.create_index(
        'ix_audit_events_event_type',
        'audit_events',
        ['event_type'],
        unique=False,
        schema='public'
    )
    
    # Index on correlation_id
    op.create_index(
        'ix_audit_events_correlation_id',
        'audit_events',
        ['correlation_id'],
        unique=False,
        schema='public'
    )
    
    # GIN index on payload
    op.create_index(
        'ix_audit_events_payload',
        'audit_events',
        ['payload'],
        unique=False,
        postgresql_using='gin',
        schema='public'
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_audit_events_payload', table_name='audit_events', schema='public')
    op.drop_index('ix_audit_events_correlation_id', table_name='audit_events', schema='public')
    op.drop_index('ix_audit_events_event_type', table_name='audit_events', schema='public')
    op.drop_index('ix_audit_events_person_id_created_at', table_name='audit_events', schema='public')
    
    # Drop table
    op.drop_table('audit_events', schema='public')
