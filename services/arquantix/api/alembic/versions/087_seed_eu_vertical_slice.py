"""Seed EU Vertical Slice — clean 3-step registration flow.

Creates a focused EU flow for end-to-end testing:
  - Step 1: Personal Info (4 components, blocking)
  - Step 2: Residency (3 components, blocking)
  - Step 3: Consent (3 components, non-blocking)

This replaces the generic 085 EU seed for the vertical slice test.
It inserts into a separate jurisdiction code (EU_VS) so as not to
conflict with existing seeded data.

Revision ID: 087
Revises: 086
"""
import json
import uuid
from datetime import datetime, timezone

from alembic import op
from sqlalchemy import text

revision = "087"
down_revision = "086"
branch_labels = None
depends_on = None


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc).isoformat()


JURISDICTION_ID = _uuid()
FLOW_ID = _uuid()

STEP_1_ID = _uuid()
STEP_2_ID = _uuid()
STEP_3_ID = _uuid()

SCREEN_1_ID = _uuid()
SCREEN_2_ID = _uuid()
SCREEN_3_ID = _uuid()


def upgrade() -> None:
    conn = op.get_bind()
    now = _now()

    # ── Jurisdiction ───────────────────────────────────────────
    conn.execute(text(
        "INSERT INTO public.registration_jurisdictions "
        "(id, code, name, entity_name, default_language, is_active, created_at, updated_at) "
        "VALUES (:id, 'EU_VS', 'European Union (Vertical Slice)', "
        "'Vancelian Europe SAS', 'en', true, :now, :now)"
    ), {"id": JURISDICTION_ID, "now": now})

    # ── Flow ───────────────────────────────────────────────────
    conn.execute(text(
        "INSERT INTO public.registration_flows "
        "(id, jurisdiction_id, name, version, status, entrypoint_type, "
        "published_at, published_by, created_at, updated_at) "
        "VALUES (:id, :jid, 'EU Individual Registration v1', 1, 'active', "
        "'individual', :now, 'system', :now, :now)"
    ), {"id": FLOW_ID, "jid": JURISDICTION_ID, "now": now})

    # ── Step 1: Personal Info (blocking) ───────────────────────
    conn.execute(text(
        "INSERT INTO public.registration_flow_steps "
        "(id, flow_id, step_key, title, description, position, is_optional, is_blocking, created_at, updated_at) "
        "VALUES (:id, :fid, 'personal_info', 'Personal Information', "
        "'Tell us about yourself', 0, false, true, :now, :now)"
    ), {"id": STEP_1_ID, "fid": FLOW_ID, "now": now})

    conn.execute(text(
        "INSERT INTO public.registration_step_screens "
        "(id, step_id, screen_key, title, subtitle, position, layout_type, created_at, updated_at) "
        "VALUES (:id, :sid, 'personal_info_form', 'Your Information', "
        "'Please fill in your personal details', 0, 'form', :now, :now)"
    ), {"id": SCREEN_1_ID, "sid": STEP_1_ID, "now": now})

    _insert_components(conn, SCREEN_1_ID, [
        ("text_input", "first_name", "first_name", {
            "label": "First Name", "placeholder": "Enter your first name", "required": True,
        }),
        ("text_input", "last_name", "last_name", {
            "label": "Last Name", "placeholder": "Enter your last name", "required": True,
        }),
        ("text_input", "email", "email", {
            "label": "Email", "placeholder": "you@example.com",
            "required": True, "keyboard_type": "email",
        }),
        ("phone_input", "phone_number", "phone_number", {
            "label": "Phone Number", "required": True, "policy_scope": "phone",
        }),
    ], now)

    # ── Step 2: Residency (blocking) ───────────────────────────
    conn.execute(text(
        "INSERT INTO public.registration_flow_steps "
        "(id, flow_id, step_key, title, description, position, is_optional, is_blocking, created_at, updated_at) "
        "VALUES (:id, :fid, 'residency', 'Residency', "
        "'Where do you live?', 1, false, true, :now, :now)"
    ), {"id": STEP_2_ID, "fid": FLOW_ID, "now": now})

    conn.execute(text(
        "INSERT INTO public.registration_step_screens "
        "(id, step_id, screen_key, title, subtitle, position, layout_type, created_at, updated_at) "
        "VALUES (:id, :sid, 'residency_form', 'Your Residency', "
        "'Tell us about your location', 0, 'form', :now, :now)"
    ), {"id": SCREEN_2_ID, "sid": STEP_2_ID, "now": now})

    _insert_components(conn, SCREEN_2_ID, [
        ("country_picker", "country_of_residence", "country_of_residence", {
            "label": "Country of Residence", "required": True, "policy_scope": "residence",
        }),
        ("country_picker", "nationality", "nationality", {
            "label": "Nationality", "required": True, "policy_scope": "nationality",
        }),
        ("date_picker", "date_of_birth", "date_of_birth", {
            "label": "Date of Birth", "required": True,
        }),
    ], now)

    # ── Step 3: Consent (non-blocking) ─────────────────────────
    conn.execute(text(
        "INSERT INTO public.registration_flow_steps "
        "(id, flow_id, step_key, title, description, position, is_optional, is_blocking, created_at, updated_at) "
        "VALUES (:id, :fid, 'consent', 'Consent', "
        "'Review and accept terms', 2, false, false, :now, :now)"
    ), {"id": STEP_3_ID, "fid": FLOW_ID, "now": now})

    conn.execute(text(
        "INSERT INTO public.registration_step_screens "
        "(id, step_id, screen_key, title, subtitle, position, layout_type, created_at, updated_at) "
        "VALUES (:id, :sid, 'consent_form', 'Terms & Conditions', "
        "'Please review and accept', 0, 'form', :now, :now)"
    ), {"id": SCREEN_3_ID, "sid": STEP_3_ID, "now": now})

    _insert_components(conn, SCREEN_3_ID, [
        ("legal_content", "terms_text", None, {
            "label": "Terms Notice",
            "text": "Please review and accept the terms before continuing.",
        }),
        ("checkbox", "terms_and_conditions", "terms_and_conditions", {
            "label": "I accept the Terms and Conditions", "required": True,
        }),
        ("checkbox", "privacy_policy", "privacy_policy", {
            "label": "I accept the Privacy Policy", "required": True,
        }),
    ], now)


def _insert_components(conn, screen_id, components, now):
    for pos, (ctype, ckey, slug, props) in enumerate(components):
        conn.execute(text(
            "INSERT INTO public.registration_screen_components "
            "(id, screen_id, component_type, component_key, position, "
            "props_json, binding_slug, created_at, updated_at) "
            "VALUES (:id, :sid, :ctype, :ckey, :pos, "
            "cast(:props as jsonb), :slug, :now, :now)"
        ), {
            "id": _uuid(), "sid": screen_id,
            "ctype": ctype, "ckey": ckey, "pos": pos,
            "props": json.dumps(props), "slug": slug,
            "now": now,
        })


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text(
        "DELETE FROM public.registration_screen_components WHERE screen_id IN "
        f"('{SCREEN_1_ID}', '{SCREEN_2_ID}', '{SCREEN_3_ID}')"
    ))
    conn.execute(text(
        "DELETE FROM public.registration_step_screens WHERE id IN "
        f"('{SCREEN_1_ID}', '{SCREEN_2_ID}', '{SCREEN_3_ID}')"
    ))
    conn.execute(text(
        "DELETE FROM public.registration_flow_steps WHERE flow_id = :fid"
    ), {"fid": FLOW_ID})
    conn.execute(text(
        "DELETE FROM public.registration_flows WHERE id = :fid"
    ), {"fid": FLOW_ID})
    conn.execute(text(
        "DELETE FROM public.registration_jurisdictions WHERE id = :jid"
    ), {"jid": JURISDICTION_ID})
