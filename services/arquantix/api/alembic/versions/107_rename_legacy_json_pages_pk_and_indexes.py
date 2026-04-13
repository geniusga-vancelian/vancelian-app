"""Rename legacy_json_pages PK/index/FK names so Prisma can create CMS `pages` (pages_pkey conflict).

Revision ID: 107
Revises: 106

After Alembic 105 renamed table `pages` -> `legacy_json_pages`, PostgreSQL kept the primary
constraint name `pages_pkey`, which blocks creating a new `pages` table via Prisma migrations
(PostgreSQL constraint names are unique per schema).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "107"
down_revision = "106"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    row = conn.execute(
        sa.text(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'legacy_json_pages'
            """
        )
    ).fetchone()
    if not row:
        return

    # Idempotent renames (skip if already applied).
    conn.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'pages_pkey'
                  AND conrelid = 'public.legacy_json_pages'::regclass
              ) THEN
                ALTER TABLE public.legacy_json_pages
                  RENAME CONSTRAINT pages_pkey TO legacy_json_pages_pkey;
              END IF;
            END $$;
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1 FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relname = 'ix_pages_id'
              ) THEN
                ALTER INDEX public.ix_pages_id RENAME TO ix_legacy_json_pages_id;
              END IF;
            END $$;
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1 FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relname = 'ix_pages_slug_locale'
              ) THEN
                ALTER INDEX public.ix_pages_slug_locale RENAME TO ix_legacy_json_pages_slug_locale;
              END IF;
            END $$;
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_pages_source_page_id'
                  AND conrelid = 'public.legacy_json_pages'::regclass
              ) THEN
                ALTER TABLE public.legacy_json_pages
                  RENAME CONSTRAINT fk_pages_source_page_id TO fk_legacy_json_pages_source_page_id;
              END IF;
            END $$;
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()
    row = conn.execute(
        sa.text(
            """
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = 'legacy_json_pages'
            """
        )
    ).fetchone()
    if not row:
        return

    conn.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_legacy_json_pages_source_page_id'
                  AND conrelid = 'public.legacy_json_pages'::regclass
              ) THEN
                ALTER TABLE public.legacy_json_pages
                  RENAME CONSTRAINT fk_legacy_json_pages_source_page_id TO fk_pages_source_page_id;
              END IF;
            END $$;
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1 FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relname = 'ix_legacy_json_pages_slug_locale'
              ) THEN
                ALTER INDEX public.ix_legacy_json_pages_slug_locale RENAME TO ix_pages_slug_locale;
              END IF;
            END $$;
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1 FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public' AND c.relname = 'ix_legacy_json_pages_id'
              ) THEN
                ALTER INDEX public.ix_legacy_json_pages_id RENAME TO ix_pages_id;
              END IF;
            END $$;
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DO $$
            BEGIN
              IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'legacy_json_pages_pkey'
                  AND conrelid = 'public.legacy_json_pages'::regclass
              ) THEN
                ALTER TABLE public.legacy_json_pages
                  RENAME CONSTRAINT legacy_json_pages_pkey TO pages_pkey;
              END IF;
            END $$;
            """
        )
    )
