"""Seed registration flows for EU and UAE jurisdictions.

Creates:
  - 2 jurisdictions (EU, UAE)
  - 2 active flows (one per jurisdiction, individual)
  - 5 steps per flow (basic_info, residence, professional, risk_screening, consent)
  - 1 screen per step with appropriate components

Revision ID: 085
Revises: 084
"""
import uuid
from datetime import datetime, timezone

from alembic import op
from sqlalchemy import text

revision = "085"
down_revision = "084"
branch_labels = None
depends_on = None


def _uuid():
    return str(uuid.uuid4())


def _now():
    return datetime.now(timezone.utc).isoformat()


# Pre-generate IDs for referential integrity
EU_J = _uuid()
UAE_J = _uuid()
EU_FLOW = _uuid()
UAE_FLOW = _uuid()


def _build_flow_data(jurisdiction_id, flow_id, jurisdiction_code):
    """Build steps → screens → components for one flow."""
    now = _now()
    steps = []
    screens = []
    components = []

    step_defs = [
        {
            "key": "basic_info", "title": "Personal Information", "pos": 0,
            "screen_key": "basic_info_form", "screen_title": "Tell us about yourself",
            "components": [
                ("section_title", "section_heading", None, {"label": "Personal Details"}, None),
                ("text_input", "first_name", "first_name", {"label": "First name", "placeholder": "Enter your first name", "required": True}, {"type": "required"}),
                ("text_input", "last_name", "last_name", {"label": "Last name", "placeholder": "Enter your last name", "required": True}, {"type": "required"}),
                ("text_input", "email", "email", {"label": "Email address", "placeholder": "you@example.com", "required": True, "keyboard_type": "email"}, {"type": "email"}),
                ("phone_input", "phone", "phone_number", {"label": "Phone number", "required": True, "policy_scope": "phone"}, {"type": "required"}),
                ("date_picker", "dob", "date_of_birth", {"label": "Date of birth", "required": True}, {"type": "required"}),
            ],
        },
        {
            "key": "residence", "title": "Residence", "pos": 1,
            "screen_key": "residence_form", "screen_title": "Where do you live?",
            "components": [
                ("country_picker", "country", "country_of_residence", {"label": "Country of residence", "required": True, "policy_scope": "residence"}, {"type": "required"}),
                ("text_input", "city", "city", {"label": "City", "required": True}, {"type": "required"}),
                ("text_input", "address", "address_line_1", {"label": "Address", "required": True}, {"type": "required"}),
                ("text_input", "postal_code", "postal_code", {"label": "Postal code", "required": True}, {"type": "required"}),
                ("country_picker", "nationality", "nationality", {"label": "Nationality", "required": True, "policy_scope": "nationality"}, {"type": "required"}),
            ],
        },
        {
            "key": "professional", "title": "Professional Profile", "pos": 2,
            "screen_key": "professional_form", "screen_title": "Your professional background",
            "components": [
                ("select", "employment", "employment_status", {
                    "label": "Employment status", "required": True,
                    "options": [
                        {"value": "employed", "label": "Employed"},
                        {"value": "self_employed", "label": "Self-employed"},
                        {"value": "student", "label": "Student"},
                        {"value": "retired", "label": "Retired"},
                        {"value": "unemployed", "label": "Unemployed"},
                    ]
                }, {"type": "required"}),
                ("text_input", "employer", "employer_name", {"label": "Employer name", "placeholder": "Company name"}, None),
                ("select", "income_range", "annual_income_range", {
                    "label": "Annual income range", "required": True,
                    "options": [
                        {"value": "under_25k", "label": "Under €25,000"},
                        {"value": "25k_50k", "label": "€25,000 – €50,000"},
                        {"value": "50k_100k", "label": "€50,000 – €100,000"},
                        {"value": "100k_250k", "label": "€100,000 – €250,000"},
                        {"value": "over_250k", "label": "Over €250,000"},
                    ]
                }, {"type": "required"}),
                ("select", "source_of_funds", "source_of_funds", {
                    "label": "Source of funds", "required": True,
                    "options": [
                        {"value": "salary", "label": "Salary"},
                        {"value": "business", "label": "Business income"},
                        {"value": "investments", "label": "Investment returns"},
                        {"value": "inheritance", "label": "Inheritance"},
                        {"value": "savings", "label": "Savings"},
                        {"value": "other", "label": "Other"},
                    ]
                }, {"type": "required"}),
            ],
        },
        {
            "key": "risk_screening", "title": "Risk Profile", "pos": 3,
            "screen_key": "risk_form", "screen_title": "Investment experience",
            "components": [
                ("select", "investment_experience", "investment_experience", {
                    "label": "Investment experience", "required": True,
                    "options": [
                        {"value": "none", "label": "No experience"},
                        {"value": "basic", "label": "Basic (< 2 years)"},
                        {"value": "intermediate", "label": "Intermediate (2-5 years)"},
                        {"value": "advanced", "label": "Advanced (> 5 years)"},
                    ]
                }, {"type": "required"}),
                ("multi_select", "asset_classes", "known_asset_classes", {
                    "label": "Asset classes you have invested in",
                    "options": [
                        {"value": "stocks", "label": "Stocks"},
                        {"value": "bonds", "label": "Bonds"},
                        {"value": "crypto", "label": "Cryptocurrency"},
                        {"value": "real_estate", "label": "Real estate"},
                        {"value": "commodities", "label": "Commodities"},
                    ]
                }, None),
                ("select", "risk_tolerance", "risk_tolerance", {
                    "label": "Risk tolerance", "required": True,
                    "options": [
                        {"value": "conservative", "label": "Conservative"},
                        {"value": "moderate", "label": "Moderate"},
                        {"value": "aggressive", "label": "Aggressive"},
                    ]
                }, {"type": "required"}),
            ],
        },
        {
            "key": "consent", "title": "Consent & Agreement", "pos": 4,
            "screen_key": "consent_form", "screen_title": "Legal agreements",
            "components": [
                ("legal_content", "terms_content", None, {
                    "content": "By proceeding, you agree to our Terms of Service and Privacy Policy.",
                    "document_url": "/legal/terms",
                }, None),
                ("checkbox", "terms_accepted", "terms_accepted", {
                    "label": "I accept the Terms of Service and Privacy Policy", "required": True
                }, {"type": "required"}),
                ("checkbox", "data_consent", "data_processing_consent", {
                    "label": "I consent to the processing of my personal data", "required": True
                }, {"type": "required"}),
                ("checkbox", "marketing_consent", "marketing_consent", {
                    "label": "I agree to receive marketing communications (optional)"
                }, None),
            ],
        },
    ]

    for step_def in step_defs:
        step_id = _uuid()
        screen_id = _uuid()

        steps.append({
            "id": step_id,
            "flow_id": flow_id,
            "step_key": step_def["key"],
            "title": step_def["title"],
            "position": step_def["pos"],
            "is_optional": False,
        })

        screens.append({
            "id": screen_id,
            "step_id": step_id,
            "screen_key": step_def["screen_key"],
            "title": step_def["screen_title"],
            "position": 0,
            "layout_type": "form",
        })

        for pos, (ctype, ckey, slug, props, validation) in enumerate(step_def["components"]):
            # employer_name conditional on employment_status == employed
            vis = None
            if ckey == "employer":
                vis = {"field": "employment_status", "operator": "equals", "value": "employed"}

            components.append({
                "id": _uuid(),
                "screen_id": screen_id,
                "component_type": ctype,
                "component_key": ckey,
                "position": pos,
                "props_json": props,
                "binding_slug": slug,
                "visibility_rule_json": vis,
                "validation_rule_json": validation,
            })

    return steps, screens, components


def upgrade() -> None:
    conn = op.get_bind()
    now = _now()

    # Jurisdictions
    conn.execute(text(
        "INSERT INTO public.registration_jurisdictions (id, code, name, entity_name, default_language, is_active, created_at, updated_at) "
        "VALUES (:id, :code, :name, :entity, :lang, true, :now, :now)"
    ), {"id": EU_J, "code": "EU", "name": "European Union", "entity": "Vancelian Europe SAS", "lang": "en", "now": now})

    conn.execute(text(
        "INSERT INTO public.registration_jurisdictions (id, code, name, entity_name, default_language, is_active, created_at, updated_at) "
        "VALUES (:id, :code, :name, :entity, :lang, true, :now, :now)"
    ), {"id": UAE_J, "code": "UAE", "name": "United Arab Emirates", "entity": "Vancelian DMCC", "lang": "en", "now": now})

    # Flows
    for j_id, f_id, name in [(EU_J, EU_FLOW, "EU Individual Onboarding v1"), (UAE_J, UAE_FLOW, "UAE Individual Onboarding v1")]:
        conn.execute(text(
            "INSERT INTO public.registration_flows (id, jurisdiction_id, name, version, status, entrypoint_type, published_at, published_by, created_at, updated_at) "
            "VALUES (:id, :jid, :name, 1, 'active', 'individual', :now, 'system', :now, :now)"
        ), {"id": f_id, "jid": j_id, "name": name, "now": now})

    # Steps, screens, components for each flow
    for j_id, f_id, code in [(EU_J, EU_FLOW, "EU"), (UAE_J, UAE_FLOW, "UAE")]:
        steps, screens, components = _build_flow_data(j_id, f_id, code)

        for s in steps:
            conn.execute(text(
                "INSERT INTO public.registration_flow_steps (id, flow_id, step_key, title, position, is_optional, created_at, updated_at) "
                "VALUES (:id, :flow_id, :step_key, :title, :position, :is_optional, :now, :now)"
            ), {**s, "now": now})

        for sc in screens:
            conn.execute(text(
                "INSERT INTO public.registration_step_screens (id, step_id, screen_key, title, position, layout_type, created_at, updated_at) "
                "VALUES (:id, :step_id, :screen_key, :title, :position, :layout_type, :now, :now)"
            ), {**sc, "now": now})

        for c in components:
            import json
            conn.execute(text(
                "INSERT INTO public.registration_screen_components "
                "(id, screen_id, component_type, component_key, position, props_json, binding_slug, visibility_rule_json, validation_rule_json, created_at, updated_at) "
                "VALUES (:id, :screen_id, :component_type, :component_key, :position, "
                "cast(:props_json as jsonb), :binding_slug, cast(:visibility_rule_json as jsonb), cast(:validation_rule_json as jsonb), :now, :now)"
            ), {
                **c,
                "props_json": json.dumps(c["props_json"]) if c["props_json"] else None,
                "visibility_rule_json": json.dumps(c["visibility_rule_json"]) if c["visibility_rule_json"] else None,
                "validation_rule_json": json.dumps(c["validation_rule_json"]) if c["validation_rule_json"] else None,
                "now": now,
            })


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(text("DELETE FROM public.registration_screen_components"))
    conn.execute(text("DELETE FROM public.registration_step_screens"))
    conn.execute(text("DELETE FROM public.registration_flow_steps"))
    conn.execute(text("DELETE FROM public.registration_flows"))
    conn.execute(text("DELETE FROM public.registration_jurisdictions"))
