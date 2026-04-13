"""Canonical snake_case field_definitions for address_step (+ catalog labels).

Revision ID: 106
Revises: 105

- Renames legacy kebab slugs to underscore forms when the target slug is free
  (aligns bindings: address_line_1, postal_code, country_of_residence, address_metadata).
- Inserts any still-missing definitions so + Address in Admin Registration Builder resolves
  field_catalogItemForAddressLine1.
- Sets policy_scope = residence on country_of_residence; fixes address_metadata JSON row defaults.
"""
from __future__ import annotations

from alembic import op
from sqlalchemy import text

revision = "106"
down_revision = "105"
branch_labels = None
depends_on = None


_RENAMES = (
    ("address-line-1", "address_line_1"),
    ("address-line-2", "address_line_2"),
    ("postal-code", "postal_code"),
    ("country-of-residence", "country_of_residence"),
    ("address-metadata", "address_metadata"),
)


def upgrade() -> None:
    conn = op.get_bind()

    for old_slug, new_slug in _RENAMES:
        conn.execute(
            text(
                """
                UPDATE public.field_definitions AS fd
                SET slug = :new_slug, updated_at = now()
                WHERE fd.slug = :old_slug
                  AND NOT EXISTS (
                      SELECT 1 FROM public.field_definitions x WHERE x.slug = :new_slug
                  )
                """
            ),
            {"old_slug": old_slug, "new_slug": new_slug},
        )

    # --- Inserts when no row normalizes to the same binding (kebab or snake) ---
    conn.execute(
        text(
            """
            INSERT INTO public.field_definitions (
                id, slug, field_name_en, field_type, category, is_active,
                ui_label, component_type_default, required_default, policy_scope, options_json,
                created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                'address_line_1',
                'Primary street address',
                'string',
                'address',
                true,
                'Street name, building',
                'text_input',
                true,
                NULL,
                NULL,
                now(),
                now()
            WHERE NOT EXISTS (
                SELECT 1 FROM public.field_definitions fd
                WHERE REPLACE(fd.slug, '-', '_') = 'address_line_1'
            )
            """
        )
    )

    conn.execute(
        text(
            """
            INSERT INTO public.field_definitions (
                id, slug, field_name_en, field_type, category, is_active,
                ui_label, component_type_default, required_default, policy_scope, options_json,
                created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                'address_line_2',
                'Additional address details',
                'string',
                'address',
                true,
                'Floor, unit number',
                'text_input',
                false,
                NULL,
                NULL,
                now(),
                now()
            WHERE NOT EXISTS (
                SELECT 1 FROM public.field_definitions fd
                WHERE REPLACE(fd.slug, '-', '_') = 'address_line_2'
            )
            """
        )
    )

    conn.execute(
        text(
            """
            INSERT INTO public.field_definitions (
                id, slug, field_name_en, field_type, category, is_active,
                ui_label, component_type_default, required_default, policy_scope, options_json,
                created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                'postal_code',
                'ZIP or postal code',
                'string',
                'address',
                true,
                'Postal code',
                'text_input',
                true,
                NULL,
                NULL,
                now(),
                now()
            WHERE NOT EXISTS (
                SELECT 1 FROM public.field_definitions fd
                WHERE REPLACE(fd.slug, '-', '_') = 'postal_code'
            )
            """
        )
    )

    conn.execute(
        text(
            """
            INSERT INTO public.field_definitions (
                id, slug, field_name_en, field_type, category, is_active,
                ui_label, component_type_default, required_default, policy_scope, options_json,
                created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                'city',
                'City or town',
                'string',
                'address',
                true,
                'City',
                'text_input',
                true,
                NULL,
                NULL,
                now(),
                now()
            WHERE NOT EXISTS (
                SELECT 1 FROM public.field_definitions fd WHERE fd.slug = 'city'
            )
            """
        )
    )

    conn.execute(
        text(
            """
            INSERT INTO public.field_definitions (
                id, slug, field_name_en, field_type, category, is_active,
                ui_label, component_type_default, required_default, policy_scope, options_json,
                created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                'country_of_residence',
                'Country of residence ISO2',
                'string',
                'address',
                true,
                'Country',
                'country_picker',
                true,
                'residence',
                NULL,
                now(),
                now()
            WHERE NOT EXISTS (
                SELECT 1 FROM public.field_definitions fd
                WHERE REPLACE(fd.slug, '-', '_') = 'country_of_residence'
            )
            """
        )
    )

    conn.execute(
        text(
            """
            INSERT INTO public.field_definitions (
                id, slug, field_name_en, field_type, category, is_active,
                ui_label, component_type_default, required_default, policy_scope, options_json,
                created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                'address_metadata',
                'Google Places metadata',
                'json',
                'address',
                true,
                'Address metadata',
                NULL,
                false,
                NULL,
                NULL,
                now(),
                now()
            WHERE NOT EXISTS (
                SELECT 1 FROM public.field_definitions fd
                WHERE REPLACE(fd.slug, '-', '_') = 'address_metadata'
            )
            """
        )
    )

    # Ensure residence policy + metadata shape even on pre-existing rows
    conn.execute(
        text(
            """
            UPDATE public.field_definitions
            SET policy_scope = 'residence',
                component_type_default = 'country_picker',
                field_type = 'string',
                ui_label = COALESCE(NULLIF(TRIM(ui_label), ''), 'Country'),
                field_name_en = CASE
                    WHEN field_name_en IN ('Country of Residence', 'country-of-residence')
                        THEN 'Country of residence ISO2'
                    ELSE field_name_en
                END,
                updated_at = now()
            WHERE REPLACE(slug, '-', '_') = 'country_of_residence'
            """
        )
    )

    conn.execute(
        text(
            """
            UPDATE public.field_definitions
            SET field_type = 'json',
                required_default = false,
                component_type_default = NULL,
                field_name_en = CASE
                    WHEN field_name_en IN ('Address lookup metadata', 'address-metadata')
                        THEN 'Google Places metadata'
                    ELSE field_name_en
                END,
                ui_label = COALESCE(NULLIF(TRIM(ui_label), ''), 'Address metadata'),
                updated_at = now()
            WHERE REPLACE(slug, '-', '_') = 'address_metadata'
            """
        )
    )

    conn.execute(
        text(
            """
            UPDATE public.field_definitions
            SET field_name_en = 'City or town',
                ui_label = COALESCE(NULLIF(TRIM(ui_label), ''), 'City'),
                updated_at = now()
            WHERE slug = 'city' AND field_name_en IN ('City', 'city')
            """
        )
    )

    conn.execute(
        text(
            """
            UPDATE public.field_definitions
            SET ui_label = COALESCE(NULLIF(TRIM(ui_label), ''), 'Street name, building'),
                field_name_en = CASE
                    WHEN field_name_en IN ('Address Line 1', 'address-line-1')
                        THEN 'Primary street address'
                    ELSE field_name_en
                END,
                updated_at = now()
            WHERE slug = 'address_line_1'
            """
        )
    )

    conn.execute(
        text(
            """
            UPDATE public.field_definitions
            SET ui_label = COALESCE(NULLIF(TRIM(ui_label), ''), 'Floor, unit number'),
                field_name_en = CASE
                    WHEN field_name_en IN ('Address Line 2', 'address-line-2')
                        THEN 'Additional address details'
                    ELSE field_name_en
                END,
                required_default = false,
                updated_at = now()
            WHERE slug = 'address_line_2'
            """
        )
    )

    conn.execute(
        text(
            """
            UPDATE public.field_definitions
            SET ui_label = COALESCE(NULLIF(TRIM(ui_label), ''), 'Postal code'),
                field_name_en = CASE
                    WHEN field_name_en IN ('Postal Code', 'postal-code') THEN 'ZIP or postal code'
                    ELSE field_name_en
                END,
                updated_at = now()
            WHERE slug = 'postal_code'
            """
        )
    )


def downgrade() -> None:
    # Data migration: restoring kebab slugs may break bindings; leave as no-op.
    pass
