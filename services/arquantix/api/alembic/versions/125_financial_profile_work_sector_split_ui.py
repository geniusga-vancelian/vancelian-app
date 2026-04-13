"""EU v4 financial_profile — écran work_sector dédié + labels inline masqués.

- Insère ``work_sector_form`` entre employment et work_details (liste secteur seule).
- Retire le composant ``work_sector`` de ``work_details_form`` (titres + employeur uniquement).
- Ajoute ``hide_inline_label: true`` sur les selects / multi_select des écrans financial listés.

Revision ID: 125
Revises: 124
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from alembic import op
from sqlalchemy import text

revision = "125"
down_revision = "124"
branch_labels = None
depends_on = None

STEP_FINANCIAL_PROFILE = "a4010001-0001-4001-8001-000000000002"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sector_options() -> str:
    return json.dumps(
        [
            {"value": "finance", "label": "Finance"},
            {"value": "technology", "label": "Technology"},
            {"value": "healthcare", "label": "Healthcare"},
            {"value": "education", "label": "Education"},
            {"value": "government", "label": "Government"},
            {"value": "construction", "label": "Construction"},
            {"value": "retail", "label": "Retail"},
            {"value": "hospitality", "label": "Hospitality"},
            {"value": "energy", "label": "Energy"},
            {"value": "crypto", "label": "Crypto"},
            {"value": "gambling", "label": "Gambling"},
            {"value": "other", "label": "Other"},
        ]
    )


def upgrade() -> None:
    conn = op.get_bind()
    now = _now()
    step_id = STEP_FINANCIAL_PROFILE

    # ── 1) Décaler les positions (financial_profile) : position >= 1
    conn.execute(
        text(
            """
            UPDATE public.registration_step_screens sc
            SET position = sc.position + 1, updated_at = CAST(:now AS timestamptz)
            WHERE sc.step_id = CAST(:step_id AS uuid)
              AND sc.position >= 1
            """
        ),
        {"step_id": step_id, "now": now},
    )

    new_screen_id = str(uuid.uuid4())

    conn.execute(
        text(
            """
            INSERT INTO public.registration_step_screens
            (id, step_id, screen_key, title, subtitle, position, layout_type,
             screen_type, interaction_type, config_json, title_i18n, subtitle_i18n,
             button_label, button_label_i18n, visibility_rule_json, created_at, updated_at)
            SELECT
              CAST(:sid AS uuid),
              CAST(:step_id AS uuid),
              'work_sector_form',
              'What sector do you work in?',
              'Choose the industry that best matches your role.',
              1,
              'form',
              'form',
              NULL,
              NULL,
              NULL,
              NULL,
              NULL,
              NULL,
              (SELECT ss2.visibility_rule_json
               FROM public.registration_step_screens ss2
               WHERE ss2.step_id = CAST(:step_id AS uuid)
                 AND ss2.screen_key = 'work_details_form'
               LIMIT 1),
              CAST(:now AS timestamptz),
              CAST(:now AS timestamptz)
            """
        ),
        {"sid": new_screen_id, "step_id": step_id, "now": now},
    )

    props = {
        "label": "Sector",
        "required": True,
        "hide_inline_label": True,
        "options": json.loads(_sector_options()),
    }
    conn.execute(
        text(
            """
            INSERT INTO public.registration_screen_components
            (id, screen_id, component_type, component_key, position, props_json,
             binding_slug, visibility_rule_json, validation_rule_json, field_definition_id,
             created_at, updated_at)
            VALUES
            (gen_random_uuid(), CAST(:screen_id AS uuid),
             'select', 'work_sector', 0, CAST(:props AS jsonb),
             'work_sector', NULL, NULL, NULL,
             CAST(:now AS timestamptz), CAST(:now AS timestamptz))
            """
        ),
        {"screen_id": new_screen_id, "props": json.dumps(props), "now": now},
    )

    conn.execute(
        text(
            """
            DELETE FROM public.registration_screen_components c
            USING public.registration_step_screens ss
            WHERE c.screen_id = ss.id
              AND ss.step_id = CAST(:step_id AS uuid)
              AND ss.screen_key = 'work_details_form'
              AND c.binding_slug = 'work_sector'
            """
        ),
        {"step_id": step_id},
    )

    conn.execute(
        text(
            """
            UPDATE public.registration_step_screens
            SET subtitle = 'Add your job title and employer or business name.',
                updated_at = CAST(:now AS timestamptz)
            WHERE step_id = CAST(:step_id AS uuid)
              AND screen_key = 'work_details_form'
            """
        ),
        {"step_id": step_id, "now": now},
    )

    for screen_key, binding in [
        ("employment_status_form", "employment_status"),
        ("annual_income_form", "annual_income_range"),
        ("net_worth_form", "net_worth_range"),
        ("source_of_wealth_form", "source_of_wealth"),
    ]:
        conn.execute(
            text(
                """
                UPDATE public.registration_screen_components c
                SET props_json = COALESCE(c.props_json, '{}'::jsonb)
                  || '{"hide_inline_label": true}'::jsonb,
                    updated_at = CAST(:now AS timestamptz)
                FROM public.registration_step_screens ss
                WHERE c.screen_id = ss.id
                  AND ss.step_id = CAST(:step_id AS uuid)
                  AND ss.screen_key = :screen_key
                  AND c.binding_slug = :binding
                """
            ),
            {
                "step_id": step_id,
                "screen_key": screen_key,
                "binding": binding,
                "now": now,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    now = _now()
    step_id = STEP_FINANCIAL_PROFILE

    conn.execute(
        text(
            """
            UPDATE public.registration_screen_components c
            SET props_json = c.props_json - 'hide_inline_label',
                updated_at = CAST(:now AS timestamptz)
            FROM public.registration_step_screens ss
            WHERE c.screen_id = ss.id
              AND ss.step_id = CAST(:step_id AS uuid)
              AND ss.screen_key IN (
                'employment_status_form', 'annual_income_form',
                'net_worth_form', 'source_of_wealth_form'
              )
            """
        ),
        {"step_id": step_id, "now": now},
    )

    conn.execute(
        text(
            """
            UPDATE public.registration_step_screens
            SET subtitle = 'Tell us about your current professional activity.',
                updated_at = CAST(:now AS timestamptz)
            WHERE step_id = CAST(:step_id AS uuid)
              AND screen_key = 'work_details_form'
            """
        ),
        {"step_id": step_id, "now": now},
    )

    conn.execute(
        text(
            """
            DELETE FROM public.registration_step_screens
            WHERE step_id = CAST(:step_id AS uuid)
              AND screen_key = 'work_sector_form'
            """
        ),
        {"step_id": step_id},
    )

    conn.execute(
        text(
            """
            UPDATE public.registration_step_screens sc
            SET position = sc.position - 1, updated_at = CAST(:now AS timestamptz)
            WHERE sc.step_id = CAST(:step_id AS uuid)
              AND sc.position >= 2
            """
        ),
        {"step_id": step_id, "now": now},
    )

    wd = conn.execute(
        text(
            """
            SELECT id::text FROM public.registration_step_screens
            WHERE step_id = CAST(:step_id AS uuid) AND screen_key = 'work_details_form'
            """
        ),
        {"step_id": step_id},
    ).scalar()
    if wd:
        props = {
            "label": "Sector",
            "required": True,
            "options": json.loads(_sector_options()),
        }
        conn.execute(
            text(
                """
                INSERT INTO public.registration_screen_components
                (id, screen_id, component_type, component_key, position, props_json,
                 binding_slug, visibility_rule_json, validation_rule_json, field_definition_id,
                 created_at, updated_at)
                VALUES
                (gen_random_uuid(), CAST(:wid AS uuid),
                 'select', 'work_sector', 3, CAST(:props AS jsonb),
                 'work_sector', NULL, NULL, NULL,
                 CAST(:now AS timestamptz), CAST(:now AS timestamptz))
                """
            ),
            {"wid": wd, "props": json.dumps(props), "now": now},
        )
