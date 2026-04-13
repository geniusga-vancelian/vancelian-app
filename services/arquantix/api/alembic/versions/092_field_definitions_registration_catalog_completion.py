"""Complete registration field_definitions catalog + link orphan field-bound components.

Adds missing field_definitions for bindings used by seeds 085/087 (and slug_aliases
canonical `country-of-residence`) so legacy normalization no longer flags
`no_field_definition_for_binding` for those slugs.

Backfills `field_definition_id` via replace(binding_slug, '_', '-') = fd.slug.

Repairs field-bound rows missing both binding_slug and field_definition_id when
`component_key` matches known seed keys (non-destructive: sets snake_case binding
aligned to existing flows).

Revision ID: 092
Revises: 091
"""
from __future__ import annotations

import json
from typing import Any, Optional

from alembic import op
from sqlalchemy import text

revision = "092"
down_revision = "091"
branch_labels = None
depends_on = None

# Options mirror 085_seed_registration_flows.py (EU/UAE professional + risk steps)
_ANNUAL_INCOME_OPTIONS = [
    {"value": "under_25k", "label": "Under €25,000"},
    {"value": "25k_50k", "label": "€25,000 – €50,000"},
    {"value": "50k_100k", "label": "€50,000 – €100,000"},
    {"value": "100k_250k", "label": "€100,000 – €250,000"},
    {"value": "over_250k", "label": "Over €250,000"},
]

_KNOWN_ASSET_OPTIONS = [
    {"value": "stocks", "label": "Stocks"},
    {"value": "bonds", "label": "Bonds"},
    {"value": "crypto", "label": "Cryptocurrency"},
    {"value": "real_estate", "label": "Real estate"},
    {"value": "commodities", "label": "Commodities"},
]


def _insert_fd_if_missing(
    conn,
    *,
    slug: str,
    field_name_en: str,
    field_type: str,
    category: str,
    ui_label: str,
    component_type_default: str,
    required_default: bool,
    options_json: Optional[Any] = None,
) -> None:
    opts_literal = json.dumps(options_json) if options_json is not None else None
    conn.execute(
        text(
            """
            INSERT INTO public.field_definitions (
                id, slug, field_name_en, field_type, category, is_active,
                ui_label, component_type_default, required_default, options_json,
                created_at, updated_at
            )
            SELECT
                gen_random_uuid(),
                :slug,
                :field_name_en,
                :field_type,
                :category,
                true,
                :ui_label,
                :component_type_default,
                :required_default,
                CAST(:options_json AS jsonb),
                now(),
                now()
            WHERE NOT EXISTS (
                SELECT 1 FROM public.field_definitions fd0 WHERE fd0.slug = :slug
            )
            """
        ),
        {
            "slug": slug,
            "field_name_en": field_name_en,
            "field_type": field_type,
            "category": category,
            "ui_label": ui_label,
            "component_type_default": component_type_default,
            "required_default": required_default,
            "options_json": opts_literal,
        },
    )


def upgrade() -> None:
    conn = op.get_bind()

    _insert_fd_if_missing(
        conn,
        slug="country-of-residence",
        field_name_en="Country of Residence",
        field_type="string",
        category="address",
        ui_label="Country of residence",
        component_type_default="country_picker",
        required_default=True,
    )
    _insert_fd_if_missing(
        conn,
        slug="annual-income-range",
        field_name_en="Annual Income Range",
        field_type="enum",
        category="financial",
        ui_label="Annual income range",
        component_type_default="select",
        required_default=True,
        options_json={"options": _ANNUAL_INCOME_OPTIONS},
    )
    _insert_fd_if_missing(
        conn,
        slug="known-asset-classes",
        field_name_en="Known Asset Classes",
        field_type="array",
        category="knowledge",
        ui_label="Asset classes you have invested in",
        component_type_default="multi_select",
        required_default=False,
        options_json={"options": _KNOWN_ASSET_OPTIONS},
    )
    _insert_fd_if_missing(
        conn,
        slug="terms-accepted",
        field_name_en="Terms and Privacy Acceptance (combined)",
        field_type="boolean",
        category="consents",
        ui_label="I accept the Terms of Service and Privacy Policy",
        component_type_default="checkbox",
        required_default=True,
    )
    _insert_fd_if_missing(
        conn,
        slug="terms-and-conditions",
        field_name_en="Terms and Conditions Accepted",
        field_type="boolean",
        category="consents",
        ui_label="I accept the Terms and Conditions",
        component_type_default="checkbox",
        required_default=True,
    )
    _insert_fd_if_missing(
        conn,
        slug="privacy-policy",
        field_name_en="Privacy Policy Accepted",
        field_type="boolean",
        category="consents",
        ui_label="I accept the Privacy Policy",
        component_type_default="checkbox",
        required_default=True,
    )

    # Link any component with binding but missing FK
    conn.execute(
        text(
            """
            UPDATE public.registration_screen_components rsc
            SET field_definition_id = fd.id
            FROM public.field_definitions fd
            WHERE rsc.field_definition_id IS NULL
              AND rsc.binding_slug IS NOT NULL
              AND length(trim(rsc.binding_slug)) > 0
              AND replace(rsc.binding_slug, '_', '-') = fd.slug
            """
        )
    )

    # Orphan field-bound: infer binding + FD from component_key (seed-aligned)
    conn.execute(
        text(
            """
            WITH fixes(component_key, binding_slug, fd_slug) AS (
                VALUES
                    ('first_name'::text, 'first_name'::text, 'first-name'::text),
                    ('last_name', 'last_name', 'last-name'),
                    ('email', 'email', 'email'),
                    ('phone_number', 'phone_number', 'phone-number'),
                    ('phone', 'phone_number', 'phone-number'),
                    ('dob', 'date_of_birth', 'date-of-birth'),
                    ('country', 'country_of_residence', 'country-of-residence'),
                    ('country_of_residence', 'country_of_residence', 'country-of-residence'),
                    ('nationality', 'nationality', 'nationality'),
                    ('income_range', 'annual_income_range', 'annual-income-range'),
                    ('asset_classes', 'known_asset_classes', 'known-asset-classes'),
                    ('terms_accepted', 'terms_accepted', 'terms-accepted'),
                    ('terms_and_conditions', 'terms_and_conditions', 'terms-and-conditions'),
                    ('privacy_policy', 'privacy_policy', 'privacy-policy'),
                    ('data_consent', 'data_processing_consent', 'data-processing-consent'),
                    ('marketing_consent', 'marketing_consent', 'marketing-consent'),
                    ('employment', 'employment_status', 'employment-status'),
                    ('source_of_funds', 'source_of_funds', 'source-of-funds'),
                    ('investment_experience', 'investment_experience', 'investment-experience'),
                    ('risk_tolerance', 'risk_tolerance', 'risk-tolerance'),
                    ('employer', 'employer_name', 'employer-name'),
                    ('city', 'city', 'city'),
                    ('address', 'address_line_1', 'address-line-1'),
                    ('postal_code', 'postal_code', 'postal-code')
            )
            UPDATE public.registration_screen_components rsc
            SET
                binding_slug = f.binding_slug,
                field_definition_id = fd.id
            FROM fixes f
            INNER JOIN public.field_definitions fd ON fd.slug = f.fd_slug
            WHERE rsc.component_key = f.component_key
              AND rsc.component_type IN (
                  'text_input', 'phone_input', 'select', 'multi_select',
                  'checkbox', 'country_picker', 'date_picker'
              )
              AND (rsc.binding_slug IS NULL OR length(trim(rsc.binding_slug)) = 0)
              AND rsc.field_definition_id IS NULL
            """
        )
    )


def downgrade() -> None:
    # Data migration: leave rows in place to avoid breaking FK on components.
    pass
