"""EU v4 — e-mail collecté à l’auth : mobile + SMS KYC à la place de l’e-mail dans le module fondation.

- Masque ``email_form`` / ``email_otp_optional_form`` si ``email`` déjà dans le contexte.
- Insère ``mobile_phone_form`` + ``phone_verification_sms`` après ``home_address_form``.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
from sqlalchemy import text

revision = "157"
down_revision = "156"
branch_labels = None
depends_on = None

FLOW_V4_ID = "a4b5c6d7-e8f9-40a1-b2c3-d4e5f6a7b8c9"
STEP_IDENTITY_FOUNDATION = "a4010001-0001-4001-8001-000000000001"

SCREEN_MOBILE_PHONE = "b5700001-0001-4001-8001-000000000001"
SCREEN_PHONE_SMS = "b5700002-0002-4002-8002-000000000002"
COMP_MOBILE_PHONE = "b5700003-0003-4003-8003-000000000003"

EMAIL_HIDE_RULE = '{"operator": "not_exists", "field": "email"}'


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upgrade() -> None:
    conn = op.get_bind()
    now = _now()

    row = conn.execute(
        text(
            "SELECT id::text FROM public.registration_flows "
            "WHERE id = CAST(:id AS uuid) AND status = 'active'"
        ),
        {"id": FLOW_V4_ID},
    ).fetchone()
    if not row:
        return

    conn.execute(
        text(
            """
            UPDATE public.registration_step_screens sc
            SET visibility_rule_json = CAST(:rule AS jsonb)
            FROM public.registration_flow_steps st
            WHERE sc.step_id = st.id
              AND st.flow_id = CAST(:fid AS uuid)
              AND st.id = CAST(:sid AS uuid)
              AND sc.screen_key IN ('email_form', 'email_otp_optional_form')
            """
        ),
        {
            "rule": EMAIL_HIDE_RULE,
            "fid": FLOW_V4_ID,
            "sid": STEP_IDENTITY_FOUNDATION,
        },
    )

    conn.execute(
        text(
            """
            UPDATE public.registration_step_screens sc
            SET position = sc.position + 2
            FROM public.registration_flow_steps st
            WHERE sc.step_id = st.id
              AND st.flow_id = CAST(:fid AS uuid)
              AND st.id = CAST(:sid AS uuid)
              AND sc.position >= 4
            """
        ),
        {"fid": FLOW_V4_ID, "sid": STEP_IDENTITY_FOUNDATION},
    )

    conn.execute(
        text(
            """
            INSERT INTO public.registration_step_screens
            (id, step_id, screen_key, title, subtitle, position, layout_type,
             screen_type, interaction_type, interaction_config_json,
             title_i18n, subtitle_i18n, created_at, updated_at)
            VALUES
            (CAST(:id1 AS uuid), CAST(:sid AS uuid), 'mobile_phone_form',
             'Mobile number', 'Your mobile phone number.',
             4, 'default', 'form', NULL, NULL,
             '{"fr": "Numéro de mobile", "en": "Mobile number"}'::jsonb,
             '{"fr": "Votre numéro de téléphone mobile.", "en": "Your mobile phone number."}'::jsonb,
             CAST(:now AS timestamptz), CAST(:now AS timestamptz)),
            (CAST(:id2 AS uuid), CAST(:sid AS uuid), 'phone_verification_sms',
             'Confirm mobile', 'We will send you a verification code by SMS.',
             5, 'default', 'interaction', 'phone_verification_sms',
             CAST(:ix_cfg AS jsonb),
             '{"fr": "Confirmer le mobile", "en": "Confirm mobile"}'::jsonb,
             '{"fr": "Nous vous enverrons un code de vérification par SMS.",
               "en": "We will send you a verification code by SMS."}'::jsonb,
             CAST(:now AS timestamptz), CAST(:now AS timestamptz))
            """
        ),
        {
            "id1": SCREEN_MOBILE_PHONE,
            "id2": SCREEN_PHONE_SMS,
            "sid": STEP_IDENTITY_FOUNDATION,
            "now": now,
            "ix_cfg": (
                '{"source_field_slug": "phone_number", '
                '"verified_flag_slug": "phone_verified", '
                '"purpose": "verify_phone"}'
            ),
        },
    )

    conn.execute(
        text(
            """
            INSERT INTO public.registration_screen_components
            (id, screen_id, component_type, component_key, position, props_json,
             binding_slug, created_at, updated_at)
            VALUES
            (CAST(:cid AS uuid), CAST(:scr AS uuid), 'phone_input', 'mobile_phone',
             0,
             CAST(:props AS jsonb),
             'phone_number',
             CAST(:now AS timestamptz), CAST(:now AS timestamptz))
            """
        ),
        {
            "cid": COMP_MOBILE_PHONE,
            "scr": SCREEN_MOBILE_PHONE,
            "now": now,
            "props": (
                '{"label": "Mobile number", "placeholder": "+33 6 12 34 56 78", '
                '"required": true, "label_i18n": {"fr": "Numéro de mobile", "en": "Mobile number"}}'
            ),
        },
    )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text(
            "DELETE FROM public.registration_screen_components "
            "WHERE screen_id = CAST(:scr AS uuid)"
        ),
        {"scr": SCREEN_MOBILE_PHONE},
    )
    conn.execute(
        text(
            "DELETE FROM public.registration_step_screens "
            "WHERE id IN (CAST(:id1 AS uuid), CAST(:id2 AS uuid))"
        ),
        {"id1": SCREEN_MOBILE_PHONE, "id2": SCREEN_PHONE_SMS},
    )
    conn.execute(
        text(
            """
            UPDATE public.registration_step_screens sc
            SET position = sc.position - 2,
                visibility_rule_json = NULL
            FROM public.registration_flow_steps st
            WHERE sc.step_id = st.id
              AND st.flow_id = CAST(:fid AS uuid)
              AND st.id = CAST(:sid AS uuid)
              AND sc.position >= 6
            """
        ),
        {"fid": FLOW_V4_ID, "sid": STEP_IDENTITY_FOUNDATION},
    )
