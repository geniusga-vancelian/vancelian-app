"""EU registration flow v3 — module Financial Profile (wealth & employment).

- Archive le flux EU v2 (c8a4f0e1-…).
- Clone steps/screens/components v2 → nouveau flux v3.
- Ajoute 6 étapes ``financial_profile`` après les étapes fondation (terms).

Composants : types existants uniquement (``select``, ``text_input``, ``multi_select``, ``checkbox``).
Modal succès : signal côté CMS via ``config_json.show_success_modal_on_complete`` (Flutter).

Revision ID: 123
Revises: 122
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from alembic import op
from sqlalchemy import text

revision = "123"
down_revision = "122"
branch_labels = None
depends_on = None

FLOW_V2_ID = "c8a4f0e1-6b2d-4c91-9f3e-1a2b3c4d5e6f"
FLOW_V3_ID = "f1e2d3c4-b5a6-4789-9abc-def012345678"

# Étapes financial — IDs fixes (downgrade)
FP_STEPS = [
    "f3010001-0001-4001-8001-000000000001",  # employment_status
    "f3010001-0001-4001-8001-000000000002",  # work_details
    "f3010001-0001-4001-8001-000000000003",  # annual_income
    "f3010001-0001-4001-8001-000000000004",  # net_worth
    "f3010001-0001-4001-8001-000000000005",  # source_of_wealth
    "f3010001-0001-4001-8001-000000000006",  # financial_acknowledgements
]
FP_SCREENS = [
    "f3020002-0002-4002-8002-000000000001",
    "f3020002-0002-4002-8002-000000000002",
    "f3020002-0002-4002-8002-000000000003",
    "f3020002-0002-4002-8002-000000000004",
    "f3020002-0002-4002-8002-000000000005",
    "f3020002-0002-4002-8002-000000000006",
]


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _meta(step_key: str, description: str, required: bool) -> str:
    return json.dumps(
        {
            "step_metadata": {
                "step_key": step_key,
                "module": "financial_profile",
                "description": description,
                "required": required,
            }
        }
    )


def _emp_options() -> str:
    return json.dumps(
        [
            {"value": "employed", "label": "Employed"},
            {"value": "self_employed", "label": "Self-employed"},
            {"value": "student", "label": "Student"},
            {"value": "unemployed", "label": "Unemployed"},
            {"value": "retired", "label": "Retired"},
        ]
    )


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


def _income_options() -> str:
    return json.dumps(
        [
            {"value": "below_50k", "label": "Below €50,000"},
            {"value": "between_50k_100k", "label": "€50,000 – €100,000"},
            {"value": "between_100k_200k", "label": "€100,000 – €200,000"},
            {"value": "between_200k_300k", "label": "€200,000 – €300,000"},
            {"value": "above_300k", "label": "Above €300,000"},
        ]
    )


def _net_worth_options() -> str:
    return json.dumps(
        [
            {"value": "below_50k", "label": "Below €50,000"},
            {"value": "between_50k_100k", "label": "€50,000 – €100,000"},
            {"value": "between_100k_250k", "label": "€100,000 – €250,000"},
            {"value": "between_250k_500k", "label": "€250,000 – €500,000"},
            {"value": "between_500k_1m", "label": "€500,000 – €1,000,000"},
            {"value": "above_1m", "label": "Above €1,000,000"},
        ]
    )


def _sow_options() -> str:
    return json.dumps(
        [
            {"value": "salary", "label": "Salary"},
            {"value": "business_income", "label": "Business income"},
            {"value": "investment_income", "label": "Investment income"},
            {"value": "savings", "label": "Savings"},
            {"value": "inheritance", "label": "Inheritance"},
            {"value": "pension", "label": "Pension"},
            {"value": "real_estate", "label": "Real estate"},
            {"value": "crypto_income", "label": "Crypto income"},
            {"value": "gambling_income", "label": "Gambling income"},
            {"value": "other", "label": "Other"},
        ]
    )


def upgrade() -> None:
    conn = op.get_bind()
    now = _now()

    # ── Vérifier existence flux v2 ─────────────────────────────
    row = conn.execute(
        text(
            "SELECT id::text FROM public.registration_flows "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": FLOW_V2_ID},
    ).fetchone()
    if not row:
        raise RuntimeError(
            "123: flux EU v2 introuvable (attendu c8a4f0e1-6b2d-4c91-9f3e-1a2b3c4d5e6f). "
            "Appliquer migrations 121–122 avant."
        )

    jid = conn.execute(
        text(
            "SELECT jurisdiction_id::text FROM public.registration_flows "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": FLOW_V2_ID},
    ).scalar()
    if not jid:
        raise RuntimeError("123: jurisdiction_id introuvable pour le flux v2")

    # ── Archive v2 ─────────────────────────────────────────────
    conn.execute(
        text(
            """
            UPDATE public.registration_flows
            SET status = 'archived', updated_at = CAST(:now AS timestamptz)
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {"id": FLOW_V2_ID, "now": now},
    )

    # ── Insérer flux v3 ────────────────────────────────────────
    conn.execute(
        text(
            """
            INSERT INTO public.registration_flows
            (id, jurisdiction_id, name, version, status, entrypoint_type,
             published_at, published_by, created_at, updated_at)
            VALUES
            (CAST(:id AS uuid), CAST(:jid AS uuid),
             'EU Individual Onboarding v3', 3, 'active', 'individual',
             CAST(:now AS timestamptz), 'system',
             CAST(:now AS timestamptz), CAST(:now AS timestamptz))
            """
        ),
        {"id": FLOW_V3_ID, "jid": jid, "now": now},
    )

    # ── Clone steps v2 → v3 ─────────────────────────────────────
    conn.execute(
        text(
            """
            INSERT INTO public.registration_flow_steps
            (id, flow_id, step_key, title, description, position,
             is_optional, is_blocking, visibility_rule_json, title_i18n, description_i18n,
             completion_rule_json, created_at, updated_at)
            SELECT
              gen_random_uuid(),
              CAST(:v3 AS uuid),
              step_key,
              title,
              description,
              position,
              is_optional,
              is_blocking,
              visibility_rule_json,
              title_i18n,
              description_i18n,
              completion_rule_json,
              CAST(:now AS timestamptz),
              CAST(:now AS timestamptz)
            FROM public.registration_flow_steps
            WHERE flow_id = CAST(:v2 AS uuid)
            """
        ),
        {"v2": FLOW_V2_ID, "v3": FLOW_V3_ID, "now": now},
    )

    # ── Clone screens ──────────────────────────────────────────
    conn.execute(
        text(
            """
            INSERT INTO public.registration_step_screens
            (id, step_id, screen_key, title, subtitle, position, layout_type,
             screen_type, interaction_type, config_json, title_i18n, subtitle_i18n,
             button_label, button_label_i18n, created_at, updated_at)
            SELECT
              gen_random_uuid(),
              ns.id,
              ovs.screen_key,
              ovs.title,
              ovs.subtitle,
              ovs.position,
              ovs.layout_type,
              ovs.screen_type,
              ovs.interaction_type,
              ovs.config_json,
              ovs.title_i18n,
              ovs.subtitle_i18n,
              ovs.button_label,
              ovs.button_label_i18n,
              CAST(:now AS timestamptz),
              CAST(:now AS timestamptz)
            FROM public.registration_step_screens ovs
            JOIN public.registration_flow_steps os
              ON ovs.step_id = os.id AND os.flow_id = CAST(:v2 AS uuid)
            JOIN public.registration_flow_steps ns
              ON ns.step_key = os.step_key AND ns.flow_id = CAST(:v3 AS uuid)
            """
        ),
        {"v2": FLOW_V2_ID, "v3": FLOW_V3_ID, "now": now},
    )

    # ── Clone components ───────────────────────────────────────
    conn.execute(
        text(
            """
            INSERT INTO public.registration_screen_components
            (id, screen_id, component_type, component_key, position, props_json,
             binding_slug, visibility_rule_json, validation_rule_json, field_definition_id,
             created_at, updated_at)
            SELECT
              gen_random_uuid(),
              ns.id,
              occ.component_type,
              occ.component_key,
              occ.position,
              occ.props_json,
              occ.binding_slug,
              occ.visibility_rule_json,
              occ.validation_rule_json,
              occ.field_definition_id,
              CAST(:now AS timestamptz),
              CAST(:now AS timestamptz)
            FROM public.registration_screen_components occ
            JOIN public.registration_step_screens os ON occ.screen_id = os.id
            JOIN public.registration_flow_steps ost
              ON os.step_id = ost.id AND ost.flow_id = CAST(:v2 AS uuid)
            JOIN public.registration_flow_steps nst
              ON nst.step_key = ost.step_key AND nst.flow_id = CAST(:v3 AS uuid)
            JOIN public.registration_step_screens ns
              ON ns.step_id = nst.id AND ns.screen_key = os.screen_key
            """
        ),
        {"v2": FLOW_V2_ID, "v3": FLOW_V3_ID, "now": now},
    )

    # ── Financial profile steps (positions 7–12) ────────────────
    vis_work = json.dumps(
        {
            "operator": "in",
            "field": "employment_status",
            "values": ["employed", "self_employed"],
        }
    )
    vis_emp = json.dumps(
        {"operator": "equals", "field": "employment_status", "value": "employed"}
    )
    vis_self = json.dumps(
        {"operator": "equals", "field": "employment_status", "value": "self_employed"}
    )

    specs = [
        # 0 employment_status
        {
            "step_id": FP_STEPS[0],
            "screen_id": FP_SCREENS[0],
            "step_key": "employment_status",
            "position": 7,
            "title": "What is your employment status?",
            "description": "We need this information for regulatory purposes.",
            "visibility_rule_json": None,
            "screen_key": "employment_status_form",
            "screen_title": "Employment status",
            "screen_subtitle": "We need this information for regulatory purposes.",
            "cfg": _meta(
                "employment_status",
                "We need this information for regulatory purposes.",
                True,
            ),
            "components": [
                (
                    "select",
                    "employment_status",
                    "employment_status",
                    {
                        "label": "Employment status",
                        "required": True,
                        "options": json.loads(_emp_options()),
                    },
                ),
            ],
        },
        # 1 work_details
        {
            "step_id": FP_STEPS[1],
            "screen_id": FP_SCREENS[1],
            "step_key": "work_details",
            "position": 8,
            "title": "Where do you work?",
            "description": "Tell us about your current professional activity.",
            "visibility_rule_json": vis_work,
            "screen_key": "work_details_form",
            "screen_title": "Where do you work?",
            "screen_subtitle": "Tell us about your current professional activity.",
            "cfg": _meta(
                "work_details",
                "Tell us about your current professional activity.",
                True,
            ),
            "components": [
                (
                    "text_input",
                    "job_title",
                    "job_title",
                    {"label": "Job title", "placeholder": "Job title", "required": True},
                ),
                (
                    "text_input",
                    "employer_name_employed",
                    "employer_name",
                    {
                        "label": "Employer name",
                        "placeholder": "Employer name",
                        "required": True,
                    },
                    vis_emp,
                ),
                (
                    "text_input",
                    "employer_name_self",
                    "employer_name",
                    {
                        "label": "Business / trading name (optional)",
                        "placeholder": "Enter if applicable",
                        "required": False,
                    },
                    vis_self,
                ),
                (
                    "select",
                    "work_sector",
                    "work_sector",
                    {
                        "label": "Sector",
                        "required": True,
                        "options": json.loads(_sector_options()),
                    },
                ),
            ],
        },
        # 2 annual_income
        {
            "step_id": FP_STEPS[2],
            "screen_id": FP_SCREENS[2],
            "step_key": "annual_income",
            "position": 9,
            "title": "What is your annual income?",
            "description": "We are required to ask for this information for regulatory purposes.",
            "visibility_rule_json": None,
            "screen_key": "annual_income_form",
            "screen_title": "Annual income",
            "screen_subtitle": "We are required to ask for this information for regulatory purposes.",
            "cfg": _meta(
                "annual_income",
                "We are required to ask for this information for regulatory purposes.",
                True,
            ),
            "components": [
                (
                    "select",
                    "annual_income_range",
                    "annual_income_range",
                    {
                        "label": "Annual income range",
                        "required": True,
                        "options": json.loads(_income_options()),
                    },
                ),
            ],
        },
        # 3 net_worth
        {
            "step_id": FP_STEPS[3],
            "screen_id": FP_SCREENS[3],
            "step_key": "net_worth",
            "position": 10,
            "title": "What is your estimated net worth?",
            "description": "This includes your savings, investments and other assets.",
            "visibility_rule_json": None,
            "screen_key": "net_worth_form",
            "screen_title": "Net worth",
            "screen_subtitle": "This includes your savings, investments and other assets.",
            "cfg": _meta(
                "net_worth",
                "This includes your savings, investments and other assets.",
                True,
            ),
            "components": [
                (
                    "select",
                    "net_worth_range",
                    "net_worth_range",
                    {
                        "label": "Estimated net worth",
                        "required": True,
                        "options": json.loads(_net_worth_options()),
                    },
                ),
            ],
        },
        # 4 source_of_wealth
        {
            "step_id": FP_STEPS[4],
            "screen_id": FP_SCREENS[4],
            "step_key": "source_of_wealth",
            "position": 11,
            "title": "What is the source of your wealth?",
            "description": "Select all that apply.",
            "visibility_rule_json": None,
            "screen_key": "source_of_wealth_form",
            "screen_title": "Source of wealth",
            "screen_subtitle": "Select all that apply.",
            "cfg": _meta("source_of_wealth", "Select all that apply.", True),
            "components": [
                (
                    "multi_select",
                    "source_of_wealth",
                    "source_of_wealth",
                    {
                        "label": "Sources",
                        "required": True,
                        "options": json.loads(_sow_options()),
                    },
                ),
            ],
        },
        # 5 financial_acknowledgements + modal signal
        {
            "step_id": FP_STEPS[5],
            "screen_id": FP_SCREENS[5],
            "step_key": "financial_acknowledgements",
            "position": 12,
            "title": "Acknowledgements",
            "description": "Please confirm the following statements.",
            "visibility_rule_json": None,
            "screen_key": "financial_acknowledgements_form",
            "screen_title": "Acknowledgements",
            "screen_subtitle": "Please confirm the following statements.",
            "cfg": json.dumps(
                {
                    "step_metadata": {
                        "step_key": "financial_acknowledgements",
                        "module": "financial_profile",
                        "description": "Please confirm the following statements.",
                        "required": True,
                    },
                    "show_success_modal_on_complete": True,
                    "success_modal": {
                        "title": "Profile updated successfully",
                        "description": "Your financial profile has been recorded.",
                        "primary_label": "Continue",
                    },
                }
            ),
            "components": [
                (
                    "checkbox",
                    "info_true_and_accurate",
                    "info_true_and_accurate",
                    {
                        "label": "I confirm that the information provided is true and accurate",
                        "required": True,
                    },
                ),
                (
                    "checkbox",
                    "compliance_usage_ack",
                    "compliance_usage_ack",
                    {
                        "label": "I accept that my information may be used for compliance",
                        "required": True,
                    },
                ),
                (
                    "checkbox",
                    "not_us_person",
                    "not_us_person",
                    {
                        "label": "I am not a US person for tax purposes",
                        "required": True,
                    },
                ),
            ],
        },
    ]

    for spec in specs:
        vis = spec["visibility_rule_json"]
        if vis is None:
            conn.execute(
                text(
                    """
                    INSERT INTO public.registration_flow_steps
                    (id, flow_id, step_key, title, description, position,
                     is_optional, is_blocking, visibility_rule_json, created_at, updated_at)
                    VALUES
                    (CAST(:id AS uuid), CAST(:fid AS uuid), :step_key, :title, :description, :position,
                     false, true, NULL, CAST(:now AS timestamptz), CAST(:now AS timestamptz))
                    """
                ),
                {
                    "id": spec["step_id"],
                    "fid": FLOW_V3_ID,
                    "step_key": spec["step_key"],
                    "title": spec["title"],
                    "description": spec["description"],
                    "position": spec["position"],
                    "now": now,
                },
            )
        else:
            conn.execute(
                text(
                    """
                    INSERT INTO public.registration_flow_steps
                    (id, flow_id, step_key, title, description, position,
                     is_optional, is_blocking, visibility_rule_json, created_at, updated_at)
                    VALUES
                    (CAST(:id AS uuid), CAST(:fid AS uuid), :step_key, :title, :description, :position,
                     false, true, CAST(:vis AS jsonb), CAST(:now AS timestamptz), CAST(:now AS timestamptz))
                    """
                ),
                {
                    "id": spec["step_id"],
                    "fid": FLOW_V3_ID,
                    "step_key": spec["step_key"],
                    "title": spec["title"],
                    "description": spec["description"],
                    "position": spec["position"],
                    "vis": vis,
                    "now": now,
                },
            )

        conn.execute(
            text(
                """
                INSERT INTO public.registration_step_screens
                (id, step_id, screen_key, title, subtitle, position, layout_type,
                 screen_type, config_json, created_at, updated_at)
                VALUES
                (CAST(:id AS uuid), CAST(:sid AS uuid), :screen_key, :title, :subtitle, 0, 'form',
                 'form', CAST(:cfg AS jsonb), CAST(:now AS timestamptz), CAST(:now AS timestamptz))
                """
            ),
            {
                "id": spec["screen_id"],
                "sid": spec["step_id"],
                "screen_key": spec["screen_key"],
                "title": spec["screen_title"],
                "subtitle": spec["screen_subtitle"],
                "cfg": spec["cfg"],
                "now": now,
            },
        )

        for pos, comp in enumerate(spec["components"]):
            if len(comp) == 5:
                ctype, ckey, slug, props, cvis = comp
            else:
                ctype, ckey, slug, props = comp
                cvis = None
            cid = _uuid()
            if cvis is None:
                conn.execute(
                    text(
                        """
                        INSERT INTO public.registration_screen_components
                        (id, screen_id, component_type, component_key, position,
                         props_json, binding_slug, visibility_rule_json, created_at, updated_at)
                        VALUES
                        (CAST(:id AS uuid), CAST(:scr AS uuid), :ctype, :ckey, :pos,
                         CAST(:props AS jsonb), :slug, NULL,
                         CAST(:now AS timestamptz), CAST(:now AS timestamptz))
                        """
                    ),
                    {
                        "id": cid,
                        "scr": spec["screen_id"],
                        "ctype": ctype,
                        "ckey": ckey,
                        "pos": pos,
                        "props": json.dumps(props),
                        "slug": slug,
                        "now": now,
                    },
                )
            else:
                conn.execute(
                    text(
                        """
                        INSERT INTO public.registration_screen_components
                        (id, screen_id, component_type, component_key, position,
                         props_json, binding_slug, visibility_rule_json, created_at, updated_at)
                        VALUES
                        (CAST(:id AS uuid), CAST(:scr AS uuid), :ctype, :ckey, :pos,
                         CAST(:props AS jsonb), :slug, CAST(:cvis AS jsonb),
                         CAST(:now AS timestamptz), CAST(:now AS timestamptz))
                        """
                    ),
                    {
                        "id": cid,
                        "scr": spec["screen_id"],
                        "ctype": ctype,
                        "ckey": ckey,
                        "pos": pos,
                        "props": json.dumps(props),
                        "slug": slug,
                        "cvis": cvis,
                        "now": now,
                    },
                )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text("DELETE FROM public.registration_flows WHERE id = CAST(:id AS uuid)"),
        {"id": FLOW_V3_ID},
    )
    conn.execute(
        text(
            """
            UPDATE public.registration_flows
            SET status = 'active', updated_at = now()
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {"id": FLOW_V2_ID},
    )
