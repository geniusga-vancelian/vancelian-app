"""field_definitions.policy_scope + backfill + component props policy_scope.

Revision ID: 103
Revises: 102
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "103"
down_revision = "102"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "field_definitions",
        sa.Column("policy_scope", sa.Text(), nullable=True),
        schema="public",
    )
    op.execute(
        text(
            """
            UPDATE public.field_definitions SET policy_scope = 'phone'
            WHERE slug = 'phone_number' AND (policy_scope IS NULL OR policy_scope = '');
            """
        )
    )
    op.execute(
        text(
            """
            UPDATE public.field_definitions SET policy_scope = 'residence'
            WHERE slug = 'country_of_residence' AND (policy_scope IS NULL OR policy_scope = '');
            """
        )
    )
    op.execute(
        text(
            """
            UPDATE public.field_definitions SET policy_scope = 'nationality'
            WHERE slug = 'nationality' AND (policy_scope IS NULL OR policy_scope = '');
            """
        )
    )
    op.execute(
        text(
            """
            UPDATE public.registration_screen_components c
            SET props_json = jsonb_set(
                COALESCE(c.props_json::jsonb, '{}'::jsonb),
                '{policy_scope}',
                '"phone"'::jsonb,
                true
            )
            WHERE c.component_type = 'phone_input'
              AND (c.props_json->>'policy_scope' IS NULL OR c.props_json->>'policy_scope' = '');
            """
        )
    )
    op.execute(
        text(
            """
            UPDATE public.registration_screen_components c
            SET props_json = jsonb_set(
                COALESCE(c.props_json::jsonb, '{}'::jsonb),
                '{policy_scope}',
                '"nationality"'::jsonb,
                true
            )
            WHERE c.binding_slug = 'nationality'
              AND c.component_type = 'country_picker'
              AND (c.props_json->>'policy_scope' IS NULL OR c.props_json->>'policy_scope' = '');
            """
        )
    )
    op.execute(
        text(
            """
            UPDATE public.registration_screen_components c
            SET props_json = jsonb_set(
                COALESCE(c.props_json::jsonb, '{}'::jsonb),
                '{policy_scope}',
                '"residence"'::jsonb,
                true
            )
            WHERE c.binding_slug = 'country_of_residence'
              AND c.component_type = 'country_picker'
              AND (c.props_json->>'policy_scope' IS NULL OR c.props_json->>'policy_scope' = '');
            """
        )
    )


def downgrade() -> None:
    op.drop_column("field_definitions", "policy_scope", schema="public")
