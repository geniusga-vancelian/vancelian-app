"""EU registration flow v4 — steps = modules, screens = UI.

- Ajoute ``visibility_rule_json`` sur ``registration_step_screens`` (règles par écran).
- Duplique le flux v3 → v4 sans modifier v3.
- Regroupe 7 écrans fondation sous ``identity_foundation``, 6 écrans financial sous ``financial_profile``.
- Ajoute ``investor_profile`` (placeholder, 0 écran).
- Supprime uniquement les anciens steps « 1 écran » du flux v4.
- Archive v3, active v4.

Revision ID: 124
Revises: 123
"""
from __future__ import annotations

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text
from sqlalchemy.dialects.postgresql import JSONB

revision = "124"
down_revision = "123"
branch_labels = None
depends_on = None

FLOW_V3_ID = "f1e2d3c4-b5a6-4789-9abc-def012345678"
FLOW_V4_ID = "a4b5c6d7-e8f9-40a1-b2c3-d4e5f6a7b8c9"

STEP_IDENTITY_FOUNDATION = "a4010001-0001-4001-8001-000000000001"
STEP_FINANCIAL_PROFILE = "a4010001-0001-4001-8001-000000000002"
STEP_INVESTOR_PROFILE = "a4010001-0001-4001-8001-000000000003"

# Ordre des écrans dans chaque module (step_key v3 → screen_key)
FOUNDATION = [
    ("identity", "identity_form"),
    ("date_of_birth", "dob_form"),
    ("residence_country", "residence_country_form"),
    ("home_address", "home_address_form"),
    ("contact_email", "email_form"),
    ("email_verification_optional", "email_otp_optional_form"),
    ("terms", "terms_form"),
]

# Ordre logique des écrans (step financial_profile). Après migration 125 :
# work_sector_form est inséré entre employment_status_form et work_details_form.
FINANCIAL = [
    ("employment_status", "employment_status_form"),
    ("work_details", "work_details_form"),
    ("annual_income", "annual_income_form"),
    ("net_worth", "net_worth_form"),
    ("source_of_wealth", "source_of_wealth_form"),
    ("financial_acknowledgements", "financial_acknowledgements_form"),
]

OLD_STEP_KEYS = [s[0] for s in FOUNDATION] + [s[0] for s in FINANCIAL]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upgrade() -> None:
    op.add_column(
        "registration_step_screens",
        sa.Column("visibility_rule_json", JSONB(astext_type=sa.Text()), nullable=True),
        schema="public",
    )

    conn = op.get_bind()
    now = _now()

    row = conn.execute(
        text("SELECT id::text FROM public.registration_flows WHERE id = CAST(:id AS uuid)"),
        {"id": FLOW_V3_ID},
    ).fetchone()
    if not row:
        raise RuntimeError("124: flux EU v3 introuvable (f1e2d3c4-…).")

    jid = conn.execute(
        text(
            "SELECT jurisdiction_id::text FROM public.registration_flows "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": FLOW_V3_ID},
    ).scalar()

    # Archive v3 (sessions existantes inchangées)
    conn.execute(
        text(
            """
            UPDATE public.registration_flows
            SET status = 'archived', updated_at = CAST(:now AS timestamptz)
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {"id": FLOW_V3_ID, "now": now},
    )

    # Flux v4
    conn.execute(
        text(
            """
            INSERT INTO public.registration_flows
            (id, jurisdiction_id, name, version, status, entrypoint_type,
             published_at, published_by, created_at, updated_at)
            VALUES
            (CAST(:id AS uuid), CAST(:jid AS uuid),
             'EU Individual Onboarding v4', 4, 'active', 'individual',
             CAST(:now AS timestamptz), 'system',
             CAST(:now AS timestamptz), CAST(:now AS timestamptz))
            """
        ),
        {"id": FLOW_V4_ID, "jid": jid, "now": now},
    )

    # Clone v3 → v4 (steps, screens, components)
    conn.execute(
        text(
            """
            INSERT INTO public.registration_flow_steps
            (id, flow_id, step_key, title, description, position,
             is_optional, is_blocking, visibility_rule_json, title_i18n, description_i18n,
             completion_rule_json, created_at, updated_at)
            SELECT
              gen_random_uuid(),
              CAST(:v4 AS uuid),
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
            WHERE flow_id = CAST(:v3 AS uuid)
            """
        ),
        {"v3": FLOW_V3_ID, "v4": FLOW_V4_ID, "now": now},
    )

    conn.execute(
        text(
            """
            INSERT INTO public.registration_step_screens
            (id, step_id, screen_key, title, subtitle, position, layout_type,
             screen_type, interaction_type, config_json, title_i18n, subtitle_i18n,
             button_label, button_label_i18n, visibility_rule_json, created_at, updated_at)
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
              NULL,
              CAST(:now AS timestamptz),
              CAST(:now AS timestamptz)
            FROM public.registration_step_screens ovs
            JOIN public.registration_flow_steps os
              ON ovs.step_id = os.id AND os.flow_id = CAST(:v3 AS uuid)
            JOIN public.registration_flow_steps ns
              ON ns.step_key = os.step_key AND ns.flow_id = CAST(:v4 AS uuid)
            """
        ),
        {"v3": FLOW_V3_ID, "v4": FLOW_V4_ID, "now": now},
    )

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
              ON os.step_id = ost.id AND ost.flow_id = CAST(:v3 AS uuid)
            JOIN public.registration_flow_steps nst
              ON nst.step_key = ost.step_key AND nst.flow_id = CAST(:v4 AS uuid)
            JOIN public.registration_step_screens ns
              ON ns.step_id = nst.id AND ns.screen_key = os.screen_key
            """
        ),
        {"v3": FLOW_V3_ID, "v4": FLOW_V4_ID, "now": now},
    )

    # Copier la règle step work_details → écran work_details_form (avant fusion steps)
    conn.execute(
        text(
            """
            UPDATE public.registration_step_screens ss
            SET visibility_rule_json = st.visibility_rule_json
            FROM public.registration_flow_steps st
            WHERE ss.step_id = st.id
              AND st.flow_id = CAST(:v4 AS uuid)
              AND st.step_key = 'work_details'
              AND ss.screen_key = 'work_details_form'
              AND st.visibility_rule_json IS NOT NULL
            """
        ),
        {"v4": FLOW_V4_ID},
    )

    # Nouveaux steps modules (IDs fixes)
    conn.execute(
        text(
            """
            INSERT INTO public.registration_flow_steps
            (id, flow_id, step_key, title, description, position,
             is_optional, is_blocking, visibility_rule_json, created_at, updated_at)
            VALUES
            (CAST(:id1 AS uuid), CAST(:fid AS uuid),
             'identity_foundation',
             'Identity & onboarding',
             'Verify your identity and accept the agreements.',
             0, false, true, NULL, CAST(:now AS timestamptz), CAST(:now AS timestamptz)),
            (CAST(:id2 AS uuid), CAST(:fid AS uuid),
             'financial_profile',
             'Financial profile',
             'Wealth and employment information.',
             1, true, false, NULL, CAST(:now AS timestamptz), CAST(:now AS timestamptz)),
            (CAST(:id3 AS uuid), CAST(:fid AS uuid),
             'investor_profile',
             'Investor profile',
             'Coming soon.',
             2, true, false, NULL, CAST(:now AS timestamptz), CAST(:now AS timestamptz))
            """
        ),
        {
            "id1": STEP_IDENTITY_FOUNDATION,
            "id2": STEP_FINANCIAL_PROFILE,
            "id3": STEP_INVESTOR_PROFILE,
            "fid": FLOW_V4_ID,
            "now": now,
        },
    )

    # Rattacher les écrans aux modules + position
    for pos, (_sk, screen_key) in enumerate(FOUNDATION):
        conn.execute(
            text(
                """
                UPDATE public.registration_step_screens sc
                SET step_id = CAST(:new_sid AS uuid), position = :pos
                FROM public.registration_flow_steps st
                WHERE sc.step_id = st.id
                  AND st.flow_id = CAST(:fid AS uuid)
                  AND st.step_key = :old_step_key
                  AND sc.screen_key = :screen_key
                """
            ),
            {
                "new_sid": STEP_IDENTITY_FOUNDATION,
                "pos": pos,
                "fid": FLOW_V4_ID,
                "old_step_key": _sk,
                "screen_key": screen_key,
            },
        )

    for pos, (_sk, screen_key) in enumerate(FINANCIAL):
        conn.execute(
            text(
                """
                UPDATE public.registration_step_screens sc
                SET step_id = CAST(:new_sid AS uuid), position = :pos
                FROM public.registration_flow_steps st
                WHERE sc.step_id = st.id
                  AND st.flow_id = CAST(:fid AS uuid)
                  AND st.step_key = :old_step_key
                  AND sc.screen_key = :screen_key
                """
            ),
            {
                "new_sid": STEP_FINANCIAL_PROFILE,
                "pos": pos,
                "fid": FLOW_V4_ID,
                "old_step_key": _sk,
                "screen_key": screen_key,
            },
        )

    # Supprimer les anciens steps v4 (1 écran chacun), devenus orphelins
    in_keys = ",".join(f"'{k}'" for k in OLD_STEP_KEYS)
    conn.execute(
        text(
            f"""
            DELETE FROM public.registration_flow_steps
            WHERE flow_id = CAST(:fid AS uuid)
              AND step_key IN ({in_keys})
            """
        ),
        {"fid": FLOW_V4_ID},
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text("DELETE FROM public.registration_flows WHERE id = CAST(:id AS uuid)"),
        {"id": FLOW_V4_ID},
    )
    conn.execute(
        text(
            """
            UPDATE public.registration_flows
            SET status = 'active', updated_at = now()
            WHERE id = CAST(:id AS uuid)
            """
        ),
        {"id": FLOW_V3_ID},
    )
    op.drop_column("registration_step_screens", "visibility_rule_json", schema="public")
