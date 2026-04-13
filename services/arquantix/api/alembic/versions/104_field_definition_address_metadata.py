"""Optional field_definition for Google Places traceability (address_metadata JSON).

Revision ID: 104
Revises: 103
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "104"
down_revision = "103"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        text(
            """
            INSERT INTO public.field_definitions (
                id, slug, field_name_en, field_type, category, is_active,
                ui_label, component_type_default, required_default, options_json,
                created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                'address-metadata',
                'Address lookup metadata',
                'json',
                'address',
                true,
                'Address metadata',
                'text_input',
                false,
                NULL,
                now(),
                now()
            WHERE NOT EXISTS (
                SELECT 1 FROM public.field_definitions fd0 WHERE fd0.slug = 'address-metadata'
            )
            """
        )
    )


def downgrade() -> None:
    op.execute(
        text(
            "DELETE FROM public.field_definitions WHERE slug = 'address-metadata'"
        )
    )
