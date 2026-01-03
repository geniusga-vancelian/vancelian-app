"""Initial migration

Revision ID: 001_initial
Revises: 
Create Date: 2026-01-01

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Admin users
    op.create_table(
        'admin_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_admin_users_id'), 'admin_users', ['id'], unique=False)
    op.create_index(op.f('ix_admin_users_email'), 'admin_users', ['email'], unique=True)
    
    # Global settings
    op.create_table(
        'global_settings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('site_name', sa.String(length=255), nullable=False, server_default='Arquantix'),
        sa.Column('tagline', sa.String(length=500), nullable=True),
        sa.Column('socials_json', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('seo_json', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_global_settings_id'), 'global_settings', ['id'], unique=False)
    
    # Pages
    op.create_table(
        'pages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('locale', sa.String(length=10), nullable=False, server_default='fr'),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('sections_json', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('seo_json', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('status', sa.Enum('DRAFT', 'PUBLISHED', name='statusenum'), nullable=False, server_default='DRAFT'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pages_id'), 'pages', ['id'], unique=False)
    op.create_index('ix_pages_slug_locale', 'pages', ['slug', 'locale'], unique=True)
    
    # News
    op.create_table(
        'news',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('locale', sa.String(length=10), nullable=False, server_default='fr'),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('excerpt', sa.Text(), nullable=True),
        sa.Column('content_markdown', sa.Text(), nullable=True),
        sa.Column('cover_image_url', sa.String(length=1000), nullable=True),
        sa.Column('status', sa.Enum('DRAFT', 'PUBLISHED', name='statusenum'), nullable=False, server_default='DRAFT'),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_news_id'), 'news', ['id'], unique=False)
    op.create_index('ix_news_slug_locale', 'news', ['slug', 'locale'], unique=True)
    
    # Contact submissions
    op.create_table(
        'contact_submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('ip', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_contact_submissions_id'), 'contact_submissions', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_contact_submissions_id'), table_name='contact_submissions')
    op.drop_table('contact_submissions')
    op.drop_index('ix_news_slug_locale', table_name='news')
    op.drop_index(op.f('ix_news_id'), table_name='news')
    op.drop_table('news')
    op.drop_index('ix_pages_slug_locale', table_name='pages')
    op.drop_index(op.f('ix_pages_id'), table_name='pages')
    op.drop_table('pages')
    op.drop_index(op.f('ix_global_settings_id'), table_name='global_settings')
    op.drop_table('global_settings')
    op.drop_index(op.f('ix_admin_users_email'), table_name='admin_users')
    op.drop_index(op.f('ix_admin_users_id'), table_name='admin_users')
    op.drop_table('admin_users')
    op.execute('DROP TYPE IF EXISTS statusenum')


