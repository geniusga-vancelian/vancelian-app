"""add_email_tables

Revision ID: cc6123cabd3c
Revises: 002
Create Date: 2026-01-08 11:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'cc6123cabd3c'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types (drop first if they exist, then create)
    # This handles cases where DB was created from a template with existing types
    op.execute("DROP TYPE IF EXISTS emailstatusenum CASCADE")
    op.execute("DROP TYPE IF EXISTS emailmoduletypeenum CASCADE")
    op.execute("DROP TYPE IF EXISTS emailheropolicyenum CASCADE")
    op.execute("DROP TYPE IF EXISTS translationstatusenum CASCADE")
    
    # Now create them fresh
    op.execute("CREATE TYPE emailstatusenum AS ENUM ('DRAFT', 'VALIDATED')")
    op.execute("CREATE TYPE emailmoduletypeenum AS ENUM ('HEADER', 'FOOTER', 'LEGAL', 'SIGNATURE', 'SOCIAL', 'DISCLAIMER', 'CUSTOM')")
    op.execute("CREATE TYPE emailheropolicyenum AS ENUM ('REQUIRED', 'OPTIONAL')")
    op.execute("CREATE TYPE translationstatusenum AS ENUM ('ORIGINAL', 'MACHINE', 'APPROVED')")
    
    # Email modules table
    # Note: We use native_enum=False to prevent SQLAlchemy from auto-creating the ENUM types
    # The types are created manually above
    op.create_table(
        'email_modules',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('module_type', postgresql.ENUM('HEADER', 'FOOTER', 'LEGAL', 'SIGNATURE', 'SOCIAL', 'DISCLAIMER', 'CUSTOM', name='emailmoduletypeenum', create_type=False), nullable=False),
        sa.Column('theme', sa.String(), server_default='arquantix_v1', nullable=True),
        sa.Column('status', postgresql.ENUM('DRAFT', 'VALIDATED', name='emailstatusenum', create_type=False), server_default='DRAFT', nullable=True),
        sa.Column('spec', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_email_modules_id'), 'email_modules', ['id'], unique=False)
    
    # Email module i18n table
    op.create_table(
        'email_module_i18n',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('module_id', sa.String(), nullable=False),
        sa.Column('locale', sa.String(), nullable=False),
        sa.Column('spec', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('translation_status', postgresql.ENUM('ORIGINAL', 'MACHINE', 'APPROVED', name='translationstatusenum', create_type=False), server_default='MACHINE', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='public'
    )
    op.create_index(op.f('ix_email_module_i18n_module_id'), 'email_module_i18n', ['module_id'], unique=False, schema='public')
    
    # Email template entities table
    op.create_table(
        'email_template_entities',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('theme', sa.String(), server_default='arquantix_v1', nullable=True),
        sa.Column('status', postgresql.ENUM('DRAFT', 'VALIDATED', name='emailstatusenum', create_type=False), server_default='DRAFT', nullable=True),
        sa.Column('hero_policy', postgresql.ENUM('REQUIRED', 'OPTIONAL', name='emailheropolicyenum', create_type=False), server_default='REQUIRED', nullable=True),
        sa.Column('header_module_id', sa.String(), nullable=False),
        sa.Column('footer_module_id', sa.String(), nullable=False),
        sa.Column('body_starter_module_id', sa.String(), nullable=True),
        sa.Column('fixed_module_ids', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('body_template', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('lock_policy', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug')
    )
    op.create_index(op.f('ix_email_template_entities_header_module_id'), 'email_template_entities', ['header_module_id'], unique=False)
    op.create_index(op.f('ix_email_template_entities_footer_module_id'), 'email_template_entities', ['footer_module_id'], unique=False)
    op.create_index(op.f('ix_email_template_entities_body_starter_module_id'), 'email_template_entities', ['body_starter_module_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_email_template_entities_body_starter_module_id'), table_name='email_template_entities')
    op.drop_index(op.f('ix_email_template_entities_footer_module_id'), table_name='email_template_entities')
    op.drop_index(op.f('ix_email_template_entities_header_module_id'), table_name='email_template_entities')
    op.drop_table('email_template_entities')
    op.drop_index(op.f('ix_email_module_i18n_module_id'), table_name='email_module_i18n', schema='public')
    op.drop_table('email_module_i18n', schema='public')
    op.drop_index(op.f('ix_email_modules_id'), table_name='email_modules')
    op.drop_table('email_modules')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS translationstatusenum')
    op.execute('DROP TYPE IF EXISTS emailheropolicyenum')
    op.execute('DROP TYPE IF EXISTS emailmoduletypeenum')
    op.execute('DROP TYPE IF EXISTS emailstatusenum')
