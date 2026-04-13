"""EU registration flow v2 — alignement sur le parcours produit (sans mobile / SMS / passcode).

- Archive le flux EU actif v1 (sessions existantes restent verrouillées sur flow_id).
- Insère un nouveau flux ``version=2`` ``active`` pour la juridiction EU / ``individual``.

Steps (ordre produit) :
  1. identity — first_name, last_name
  2. date_of_birth — date_of_birth
  3. residence_country — country_of_residence (policy_scope residence)
  4. home_address — address_step (Places / recherche)
  5. contact_email — email
  6. email_verification_optional — OTP email optionnel (écran form, aucun champ requis ; step non bloquant)
  7. terms — consentements

Revision ID: 121
Revises: 120
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from alembic import op
from sqlalchemy import text

revision = "121"
down_revision = "120"
branch_labels = None
depends_on = None


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# IDs fixes pour downgrade déterministe
FLOW_V2_ID = "c8a4f0e1-6b2d-4c91-9f3e-1a2b3c4d5e6f"

STEP_IDS = [
    "a1000001-0001-4001-8001-000000000001",  # identity
    "a1000001-0001-4001-8001-000000000002",  # date_of_birth
    "a1000001-0001-4001-8001-000000000003",  # residence_country
    "a1000001-0001-4001-8001-000000000004",  # home_address
    "a1000001-0001-4001-8001-000000000005",  # contact_email
    "a1000001-0001-4001-8001-000000000006",  # email_verification_optional
    "a1000001-0001-4001-8001-000000000007",  # terms
]

SCREEN_IDS = [
    "b2000002-0002-4002-8002-000000000001",
    "b2000002-0002-4002-8002-000000000002",
    "b2000002-0002-4002-8002-000000000003",
    "b2000002-0002-4002-8002-000000000004",
    "b2000002-0002-4002-8002-000000000005",
    "b2000002-0002-4002-8002-000000000006",
    "b2000002-0002-4002-8002-000000000007",
]


def _screen_meta(step_key: str, description: str, required: bool) -> str:
    return json.dumps(
        {
            "step_metadata": {
                "step_key": step_key,
                "description": description,
                "required": required,
            }
        }
    )


def upgrade() -> None:
    conn = op.get_bind()
    now = _now()

    row = conn.execute(
        text(
            """
            SELECT f.id::text
            FROM public.registration_flows f
            JOIN public.registration_jurisdictions j ON j.id = f.jurisdiction_id
            WHERE j.code = 'EU'
              AND f.entrypoint_type = 'individual'
              AND f.status = 'active'
            ORDER BY f.version DESC
            LIMIT 1
            """
        )
    ).fetchone()
    if not row:
        raise RuntimeError(
            "121_eu_registration_flow_v2: aucun flux EU individual actif trouvé "
            "(attendu: seed 085 ou équivalent)."
        )

    conn.execute(
        text(
            """
            UPDATE public.registration_flows f
            SET status = 'archived', updated_at = CAST(:now AS timestamptz)
            FROM public.registration_jurisdictions j
            WHERE f.jurisdiction_id = j.id
              AND j.code = 'EU'
              AND f.entrypoint_type = 'individual'
              AND f.status = 'active'
            """
        ),
        {"now": now},
    )

    jid = conn.execute(
        text(
            "SELECT id::text FROM public.registration_jurisdictions WHERE code = 'EU' LIMIT 1"
        )
    ).scalar()
    if not jid:
        raise RuntimeError("121: jurisdiction EU absente")

    conn.execute(
        text(
            """
            INSERT INTO public.registration_flows
            (id, jurisdiction_id, name, version, status, entrypoint_type,
             published_at, published_by, created_at, updated_at)
            VALUES
            (CAST(:id AS uuid), CAST(:jid AS uuid),
             'EU Individual Onboarding v2', 2, 'active', 'individual',
             CAST(:now AS timestamptz), 'system', CAST(:now AS timestamptz), CAST(:now AS timestamptz))
            """
        ),
        {"id": FLOW_V2_ID, "jid": jid, "now": now},
    )

    steps_spec = [
        {
            "id": STEP_IDS[0],
            "step_key": "identity",
            "title": "Your name",
            "description": "Legal first and last name as on your ID.",
            "position": 0,
            "is_optional": False,
            "is_blocking": True,
            "screen_key": "identity_form",
            "screen_title": "Identity",
            "screen_subtitle": "Enter your first and last name.",
            "meta_req": True,
            "components": [
                (
                    "text_input",
                    "first_name",
                    "first_name",
                    {
                        "label": "First name",
                        "placeholder": "First name",
                        "required": True,
                    },
                ),
                (
                    "text_input",
                    "last_name",
                    "last_name",
                    {
                        "label": "Last name",
                        "placeholder": "Last name",
                        "required": True,
                    },
                ),
            ],
        },
        {
            "id": STEP_IDS[1],
            "step_key": "date_of_birth",
            "title": "Date of birth",
            "description": "You must be eligible to open an account in your jurisdiction.",
            "position": 1,
            "is_optional": False,
            "is_blocking": True,
            "screen_key": "dob_form",
            "screen_title": "Date of birth",
            "screen_subtitle": "We use this to verify eligibility.",
            "meta_req": True,
            "components": [
                (
                    "date_picker",
                    "date_of_birth",
                    "date_of_birth",
                    {"label": "Date of birth", "required": True},
                ),
            ],
        },
        {
            "id": STEP_IDS[2],
            "step_key": "residence_country",
            "title": "Country of residence",
            "description": "Usually pre-filled from your phone country code; you can change it.",
            "position": 2,
            "is_optional": False,
            "is_blocking": True,
            "screen_key": "residence_country_form",
            "screen_title": "Country of residence",
            "screen_subtitle": "Where do you live for tax and regulatory purposes?",
            "meta_req": True,
            "components": [
                (
                    "country_picker",
                    "country_of_residence",
                    "country_of_residence",
                    {
                        "label": "Country of residence",
                        "required": True,
                        "policy_scope": "residence",
                    },
                ),
            ],
        },
        {
            "id": STEP_IDS[3],
            "step_key": "home_address",
            "title": "Home address",
            "description": "Search your address or enter it manually.",
            "position": 3,
            "is_optional": False,
            "is_blocking": True,
            "screen_key": "home_address_form",
            "screen_title": "Home address",
            "screen_subtitle": "We use your residential address for verification.",
            "meta_req": True,
            "components": [
                (
                    "address_step",
                    "home_address",
                    "address_line_1",
                    {
                        "search_enabled": True,
                        "store_place_id": True,
                        "address_line_2_optional": True,
                        "title_i18n": {
                            "en": "Home address",
                            "fr": "Adresse du domicile",
                        },
                        "search_label_i18n": {
                            "en": "Search address",
                            "fr": "Rechercher une adresse",
                        },
                    },
                ),
            ],
        },
        {
            "id": STEP_IDS[4],
            "step_key": "contact_email",
            "title": "Email",
            "description": "We will use this email for account notifications.",
            "position": 4,
            "is_optional": False,
            "is_blocking": True,
            "screen_key": "email_form",
            "screen_title": "Email",
            "screen_subtitle": "Your contact email address.",
            "meta_req": True,
            "components": [
                (
                    "text_input",
                    "email",
                    "email",
                    {
                        "label": "Email address",
                        "placeholder": "you@example.com",
                        "required": True,
                        "input_type": "email",
                    },
                ),
            ],
        },
        {
            "id": STEP_IDS[5],
            "step_key": "email_verification_optional",
            "title": "Verify email (optional)",
            "description": "You can verify your email now or skip and do it later from settings.",
            "position": 5,
            "is_optional": True,
            "is_blocking": False,
            "screen_key": "email_otp_optional_form",
            "screen_title": "Email verification",
            "screen_subtitle": "Optional — you can skip this step.",
            "meta_req": False,
            "config_extra": {"email_otp_optional": True, "skip_allowed": True},
            "components": [
                (
                    "legal_content",
                    "email_otp_intro",
                    None,
                    {
                        "text": (
                            "If you received a verification code by email, enter it below. "
                            "Otherwise you can skip this step and verify later."
                        ),
                    },
                ),
                (
                    "text_input",
                    "email_verification_code",
                    "email_verification_code",
                    {
                        "label": "Verification code (optional)",
                        "placeholder": "Enter code",
                        "required": False,
                        "input_type": "number",
                    },
                ),
                (
                    "checkbox",
                    "email_verification_skipped",
                    "email_verification_skipped",
                    {
                        "label": "Skip email verification for now",
                        "description": "You can verify from your profile later.",
                        "required": False,
                    },
                ),
            ],
        },
        {
            "id": STEP_IDS[6],
            "step_key": "terms",
            "title": "Terms & conditions",
            "description": "Review and accept the legal agreements to finish registration.",
            "position": 6,
            "is_optional": False,
            "is_blocking": True,
            "screen_key": "terms_form",
            "screen_title": "Terms & conditions",
            "screen_subtitle": "Please review and accept to continue.",
            "meta_req": True,
            "components": [
                (
                    "legal_content",
                    "terms_notice",
                    None,
                    {
                        "content": (
                            "By proceeding, you agree to our Terms of Service and Privacy Policy."
                        ),
                        "document_url": "/legal/terms",
                    },
                ),
                (
                    "checkbox",
                    "terms_accepted",
                    "terms_accepted",
                    {
                        "label": "I accept the Terms of Service and Privacy Policy",
                        "required": True,
                    },
                ),
                (
                    "checkbox",
                    "data_processing_consent",
                    "data_processing_consent",
                    {
                        "label": "I consent to the processing of my personal data",
                        "required": True,
                    },
                ),
                (
                    "checkbox",
                    "marketing_consent",
                    "marketing_consent",
                    {
                        "label": "I agree to receive marketing communications (optional)",
                        "required": False,
                    },
                ),
            ],
        },
    ]

    for i, spec in enumerate(steps_spec):
        sid = spec["id"]
        scr_id = SCREEN_IDS[i]
        cfg = _screen_meta(spec["step_key"], spec["description"], spec["meta_req"])
        extra = spec.get("config_extra")
        if extra:
            merged = json.loads(cfg)
            merged.update(extra)
            cfg = json.dumps(merged)

        conn.execute(
            text(
                """
                INSERT INTO public.registration_flow_steps
                (id, flow_id, step_key, title, description, position,
                 is_optional, is_blocking, created_at, updated_at)
                VALUES
                (CAST(:id AS uuid), CAST(:fid AS uuid), :step_key, :title, :description, :position,
                 :is_optional, :is_blocking, CAST(:now AS timestamptz), CAST(:now AS timestamptz))
                """
            ),
            {
                "id": sid,
                "fid": FLOW_V2_ID,
                "step_key": spec["step_key"],
                "title": spec["title"],
                "description": spec["description"],
                "position": spec["position"],
                "is_optional": spec["is_optional"],
                "is_blocking": spec["is_blocking"],
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
                "id": scr_id,
                "sid": sid,
                "screen_key": spec["screen_key"],
                "title": spec["screen_title"],
                "subtitle": spec["screen_subtitle"],
                "cfg": cfg,
                "now": now,
            },
        )

        for pos, comp in enumerate(spec["components"]):
            ctype, ckey, slug, props = comp
            cid = _uuid()
            conn.execute(
                text(
                    """
                    INSERT INTO public.registration_screen_components
                    (id, screen_id, component_type, component_key, position,
                     props_json, binding_slug, created_at, updated_at)
                    VALUES
                    (CAST(:id AS uuid), CAST(:scr AS uuid), :ctype, :ckey, :pos,
                     CAST(:props AS jsonb), :slug, CAST(:now AS timestamptz), CAST(:now AS timestamptz))
                    """
                ),
                {
                    "id": cid,
                    "scr": scr_id,
                    "ctype": ctype,
                    "ckey": ckey,
                    "pos": pos,
                    "props": json.dumps(props),
                    "slug": slug,
                    "now": now,
                },
            )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        text("DELETE FROM public.registration_flows WHERE id = CAST(:id AS uuid)"),
        {"id": FLOW_V2_ID},
    )
    conn.execute(
        text(
            """
            UPDATE public.registration_flows f
            SET status = 'active', updated_at = now()
            FROM public.registration_jurisdictions j
            WHERE f.jurisdiction_id = j.id
              AND j.code = 'EU'
              AND f.entrypoint_type = 'individual'
              AND f.version = 1
              AND f.status = 'archived'
            """
        )
    )
