"""EU registration flow v2 — polish microcopy + i18n (en/fr) sans changer la structure.

Met à jour titres, sous-titres, descriptions, props des composants et métadonnées d’écran
pour le flux ``c8a4f0e1-6b2d-4c91-9f3e-1a2b3c4d5e6f`` (v2).

Revision ID: 122
Revises: 121
"""
from __future__ import annotations

import json

from alembic import op
from sqlalchemy import text

revision = "122"
down_revision = "121"
branch_labels = None
depends_on = None

FLOW_V2_ID = "c8a4f0e1-6b2d-4c91-9f3e-1a2b3c4d5e6f"


def upgrade() -> None:
    conn = op.get_bind()

    # --- Steps : title, description + title_i18n / description_i18n ---
    step_rows = [
        (
            "identity",
            "Your legal name",
            "Use the spelling shown on your passport or national ID.",
            {
                "en": "Your legal name",
                "fr": "Votre nom légal",
            },
            {
                "en": "Use the spelling shown on your passport or national ID.",
                "fr": "Indiquez l’orthographe figurant sur votre pièce d’identité.",
            },
        ),
        (
            "date_of_birth",
            "Date of birth",
            "We only use this to confirm you meet the age requirements.",
            {"en": "Date of birth", "fr": "Date de naissance"},
            {
                "en": "We only use this to confirm you meet the age requirements.",
                "fr": "Nous en avons besoin pour vérifier que vous remplissez les conditions d’âge.",
            },
        ),
        (
            "residence_country",
            "Country of residence",
            "We may pre-fill this from your phone country — change it if needed.",
            {"en": "Country of residence", "fr": "Pays de résidence"},
            {
                "en": "We may pre-fill this from your phone country — change it if needed.",
                "fr": "Nous pouvons préremplir ce champ depuis l’indicatif téléphonique — modifiez-le si besoin.",
            },
        ),
        (
            "home_address",
            "Residential address",
            "Search for your address or enter it manually — whichever you prefer.",
            {"en": "Residential address", "fr": "Adresse de résidence"},
            {
                "en": "Search for your address or enter it manually — whichever you prefer.",
                "fr": "Recherchez votre adresse ou saisissez-la manuellement.",
            },
        ),
        (
            "contact_email",
            "Email",
            "For security alerts, statements, and important account updates.",
            {"en": "Email", "fr": "E-mail"},
            {
                "en": "For security alerts, statements, and important account updates.",
                "fr": "Pour les alertes de sécurité, les relevés et les messages importants liés au compte.",
            },
        ),
        (
            "email_verification_optional",
            "Verify your email",
            "Optional — verify now with a code, or finish later from your profile.",
            {"en": "Verify your email", "fr": "Vérifier votre e-mail"},
            {
                "en": "Optional — verify now with a code, or finish later from your profile.",
                "fr": "Facultatif — vérifiez maintenant avec un code, ou plus tard depuis votre profil.",
            },
        ),
        (
            "terms",
            "Agreements",
            "A quick read before you continue — then you’re in.",
            {"en": "Agreements", "fr": "Conditions"},
            {
                "en": "A quick read before you continue — then you’re in.",
                "fr": "Quelques confirmations avant de continuer.",
            },
        ),
    ]
    for sk, title, desc, ti18n, di18n in step_rows:
        conn.execute(
            text(
                """
                UPDATE public.registration_flow_steps
                SET title = :title,
                    description = :description,
                    title_i18n = CAST(:ti18n AS jsonb),
                    description_i18n = CAST(:di18n AS jsonb),
                    updated_at = now()
                WHERE flow_id = CAST(:fid AS uuid) AND step_key = :sk
                """
            ),
            {
                "title": title,
                "description": desc,
                "ti18n": json.dumps(ti18n),
                "di18n": json.dumps(di18n),
                "fid": FLOW_V2_ID,
                "sk": sk,
            },
        )

    # --- Screens : title, subtitle, title_i18n, subtitle_i18n, config_json.step_metadata ---
    screen_rows = [
        (
            "identity_form",
            "Your legal name",
            "We’ll match this to your ID when we verify your profile.",
            {"en": "Your legal name", "fr": "Votre nom légal"},
            {
                "en": "We’ll match this to your ID when we verify your profile.",
                "fr": "Nous le comparerons à votre pièce d’identité lors de la vérification.",
            },
            {
                "step_key": "identity",
                "description": {
                    "en": "Use the spelling shown on your passport or national ID.",
                    "fr": "Indiquez l’orthographe figurant sur votre pièce d’identité.",
                },
                "required": True,
            },
        ),
        (
            "dob_form",
            "Date of birth",
            "Used for eligibility only — we don’t use it for anything else.",
            {"en": "Date of birth", "fr": "Date de naissance"},
            {
                "en": "Used for eligibility only — we don’t use it for anything else.",
                "fr": "Uniquement pour vérifier votre éligibilité — rien d’autre.",
            },
            {
                "step_key": "date_of_birth",
                "description": {
                    "en": "We only use this to confirm you meet the age requirements.",
                    "fr": "Nous en avons besoin pour vérifier que vous remplissez les conditions d’âge.",
                },
                "required": True,
            },
        ),
        (
            "residence_country_form",
            "Where you live",
            "This is your main country of residence for tax and regulatory purposes.",
            {"en": "Where you live", "fr": "Lieu de résidence"},
            {
                "en": "This is your main country of residence for tax and regulatory purposes.",
                "fr": "Votre pays de résidence principal à des fins fiscales et réglementaires.",
            },
            {
                "step_key": "residence_country",
                "description": {
                    "en": "We may pre-fill this from your phone country — change it if needed.",
                    "fr": "Nous pouvons préremplir ce champ depuis l’indicatif téléphonique — modifiez-le si besoin.",
                },
                "required": True,
            },
        ),
        (
            "home_address_form",
            "Home address",
            "Start typing to search, or enter your address line by line.",
            {"en": "Home address", "fr": "Adresse du domicile"},
            {
                "en": "Start typing to search, or enter your address line by line.",
                "fr": "Commencez à saisir pour rechercher, ou renseignez l’adresse ligne par ligne.",
            },
            {
                "step_key": "home_address",
                "description": {
                    "en": "Search for your address or enter it manually — whichever you prefer.",
                    "fr": "Recherchez votre adresse ou saisissez-la manuellement.",
                },
                "required": True,
            },
        ),
        (
            "email_form",
            "Contact email",
            "We’ll use this for sign-in notices and important messages about your account.",
            {"en": "Contact email", "fr": "E-mail de contact"},
            {
                "en": "We’ll use this for sign-in notices and important messages about your account.",
                "fr": "Pour les notifications de connexion et les messages importants sur votre compte.",
            },
            {
                "step_key": "contact_email",
                "description": {
                    "en": "For security alerts, statements, and important account updates.",
                    "fr": "Pour les alertes de sécurité, les relevés et les messages importants liés au compte.",
                },
                "required": True,
            },
        ),
        (
            "email_otp_optional_form",
            "Email verification",
            "You can enter a code now, or skip and verify anytime in settings.",
            {"en": "Email verification", "fr": "Vérification de l’e-mail"},
            {
                "en": "You can enter a code now, or skip and verify anytime in settings.",
                "fr": "Saisissez un code maintenant, ou ignorez cette étape et vérifiez plus tard dans les réglages.",
            },
            {
                "step_key": "email_verification_optional",
                "description": {
                    "en": "Optional — verify now with a code, or finish later from your profile.",
                    "fr": "Facultatif — vérifiez maintenant avec un code, ou plus tard depuis votre profil.",
                },
                "required": False,
            },
        ),
        (
            "terms_form",
            "Review and confirm",
            "Please read and accept to open your account.",
            {"en": "Review and confirm", "fr": "Lire et confirmer"},
            {
                "en": "Please read and accept to open your account.",
                "fr": "Merci de lire et d’accepter pour ouvrir votre compte.",
            },
            {
                "step_key": "terms",
                "description": {
                    "en": "A quick read before you continue — then you’re in.",
                    "fr": "Quelques confirmations avant de continuer.",
                },
                "required": True,
            },
        ),
    ]

    for screen_key, stitle, ssub, sti18n, ssi18n, meta in screen_rows:
        cfg = {
            "step_metadata": meta,
            "email_otp_optional": screen_key == "email_otp_optional_form",
            "skip_allowed": screen_key == "email_otp_optional_form",
        }
        conn.execute(
            text(
                """
                UPDATE public.registration_step_screens s
                SET title = :stitle,
                    subtitle = :ssub,
                    title_i18n = CAST(:sti18n AS jsonb),
                    subtitle_i18n = CAST(:ssi18n AS jsonb),
                    config_json = CAST(:cfg AS jsonb),
                    updated_at = now()
                FROM public.registration_flow_steps st
                WHERE s.step_id = st.id
                  AND st.flow_id = CAST(:fid AS uuid)
                  AND s.screen_key = :screen_key
                """
            ),
            {
                "stitle": stitle,
                "ssub": ssub,
                "sti18n": json.dumps(sti18n),
                "ssi18n": json.dumps(ssi18n),
                "cfg": json.dumps(cfg),
                "fid": FLOW_V2_ID,
                "screen_key": screen_key,
            },
        )

    # --- Components : props_json (localized label / placeholder / text / content / description) ---
    comp_updates = [
        (
            "identity_form",
            "first_name",
            {
                "label": {"en": "First name", "fr": "Prénom"},
                "placeholder": {"en": "Alex", "fr": "Camille"},
                "required": True,
            },
        ),
        (
            "identity_form",
            "last_name",
            {
                "label": {"en": "Last name", "fr": "Nom"},
                "placeholder": {"en": "Dupont", "fr": "Martin"},
                "required": True,
            },
        ),
        (
            "dob_form",
            "date_of_birth",
            {
                "label": {"en": "Date of birth", "fr": "Date de naissance"},
                "required": True,
            },
        ),
        (
            "residence_country_form",
            "country_of_residence",
            {
                "label": {"en": "Country of residence", "fr": "Pays de résidence"},
                "required": True,
                "policy_scope": "residence",
            },
        ),
        (
            "home_address_form",
            "home_address",
            {
                "search_enabled": True,
                "store_place_id": True,
                "address_line_2_optional": True,
                "title_i18n": {
                    "en": "Home address",
                    "fr": "Adresse du domicile",
                },
                "search_label_i18n": {
                    "en": "Search for your address",
                    "fr": "Rechercher une adresse",
                },
            },
        ),
        (
            "email_form",
            "email",
            {
                "label": {"en": "Email address", "fr": "Adresse e-mail"},
                "placeholder": {"en": "you@example.com", "fr": "vous@exemple.com"},
                "required": True,
                "input_type": "email",
            },
        ),
        (
            "email_otp_optional_form",
            "email_otp_intro",
            {
                "text": {
                    "en": (
                        "If you’ve received a verification email, enter the code below. "
                        "Otherwise you can continue — verification stays available in your profile whenever you’re ready."
                    ),
                    "fr": (
                        "Si vous avez reçu un e-mail de vérification, saisissez le code ci-dessous. "
                        "Sinon vous pouvez continuer — la vérification reste accessible depuis votre profil quand vous le souhaitez."
                    ),
                },
            },
        ),
        (
            "email_otp_optional_form",
            "email_verification_code",
            {
                "label": {"en": "Verification code", "fr": "Code de vérification"},
                "placeholder": {"en": "6-digit code", "fr": "Code à 6 chiffres"},
                "required": False,
                "input_type": "number",
            },
        ),
        (
            "email_otp_optional_form",
            "email_verification_skipped",
            {
                "label": {"en": "I’ll verify my email later", "fr": "Je vérifierai mon e-mail plus tard"},
                "description": {
                    "en": "You can complete verification anytime from settings.",
                    "fr": "Vous pourrez finaliser la vérification à tout moment dans les réglages.",
                },
                "required": False,
            },
        ),
        (
            "terms_form",
            "terms_notice",
            {
                "content": {
                    "en": (
                        "By continuing, you acknowledge our Terms of Service and Privacy Policy, "
                        "which describe how we protect and use your information."
                    ),
                    "fr": (
                        "En continuant, vous prenez connaissance de nos Conditions d’utilisation et de notre Politique de confidentialité, "
                        "qui décrivent comment nous protégeons et utilisons vos informations."
                    ),
                },
                "document_url": "/legal/terms",
            },
        ),
        (
            "terms_form",
            "terms_accepted",
            {
                "label": {
                    "en": "I have read and accept the Terms of Service and Privacy Policy",
                    "fr": "J’ai lu et j’accepte les Conditions d’utilisation et la Politique de confidentialité",
                },
                "required": True,
            },
        ),
        (
            "terms_form",
            "data_processing_consent",
            {
                "label": {
                    "en": "I agree to the processing of my personal data as described in the Privacy Policy",
                    "fr": "J’accepte le traitement de mes données personnelles tel que décrit dans la Politique de confidentialité",
                },
                "required": True,
            },
        ),
        (
            "terms_form",
            "marketing_consent",
            {
                "label": {
                    "en": "Send me occasional product updates and news (optional)",
                    "fr": "M’envoyer ponctuellement des nouveautés produit et actualités (facultatif)",
                },
                "required": False,
            },
        ),
    ]

    for screen_key, ckey, props in comp_updates:
        conn.execute(
            text(
                """
                UPDATE public.registration_screen_components c
                SET props_json = CAST(:props AS jsonb),
                    updated_at = now()
                FROM public.registration_step_screens s
                JOIN public.registration_flow_steps st ON s.step_id = st.id
                WHERE c.screen_id = s.id
                  AND st.flow_id = CAST(:fid AS uuid)
                  AND s.screen_key = :screen_key
                  AND c.component_key = :ckey
                """
            ),
            {
                "props": json.dumps(props),
                "fid": FLOW_V2_ID,
                "screen_key": screen_key,
                "ckey": ckey,
            },
        )


def downgrade() -> None:
    """Restore previous English-only copy from migration 121 (approximation)."""
    conn = op.get_bind()
    # Minimal downgrade: reset to 121 English strings via embedded snapshot.
    # Steps
    conn.execute(
        text(
            """
            UPDATE public.registration_flow_steps
            SET title = CASE step_key
                WHEN 'identity' THEN 'Your name'
                WHEN 'date_of_birth' THEN 'Date of birth'
                WHEN 'residence_country' THEN 'Country of residence'
                WHEN 'home_address' THEN 'Home address'
                WHEN 'contact_email' THEN 'Email'
                WHEN 'email_verification_optional' THEN 'Verify email (optional)'
                WHEN 'terms' THEN 'Terms & conditions'
                ELSE title END,
                description = CASE step_key
                WHEN 'identity' THEN 'Legal first and last name as on your ID.'
                WHEN 'date_of_birth' THEN 'You must be eligible to open an account in your jurisdiction.'
                WHEN 'residence_country' THEN 'Usually pre-filled from your phone country code; you can change it.'
                WHEN 'home_address' THEN 'Search your address or enter it manually.'
                WHEN 'contact_email' THEN 'We will use this email for account notifications.'
                WHEN 'email_verification_optional' THEN 'You can verify your email now or skip and do it later from settings.'
                WHEN 'terms' THEN 'Review and accept the legal agreements to finish registration.'
                ELSE description END,
                title_i18n = NULL,
                description_i18n = NULL,
                updated_at = now()
            WHERE flow_id = CAST(:fid AS uuid)
            """
        ),
        {"fid": FLOW_V2_ID},
    )

    conn.execute(
        text(
            """
            UPDATE public.registration_step_screens s
            SET title = CASE s.screen_key
                WHEN 'identity_form' THEN 'Identity'
                WHEN 'dob_form' THEN 'Date of birth'
                WHEN 'residence_country_form' THEN 'Country of residence'
                WHEN 'home_address_form' THEN 'Home address'
                WHEN 'email_form' THEN 'Email'
                WHEN 'email_otp_optional_form' THEN 'Email verification'
                WHEN 'terms_form' THEN 'Terms & conditions'
                ELSE s.title END,
                subtitle = CASE s.screen_key
                WHEN 'identity_form' THEN 'Enter your first and last name.'
                WHEN 'dob_form' THEN 'We use this to verify eligibility.'
                WHEN 'residence_country_form' THEN 'Where do you live for tax and regulatory purposes?'
                WHEN 'home_address_form' THEN 'We use your residential address for verification.'
                WHEN 'email_form' THEN 'Your contact email address.'
                WHEN 'email_otp_optional_form' THEN 'Optional — you can skip this step.'
                WHEN 'terms_form' THEN 'Please review and accept to continue.'
                ELSE s.subtitle END,
                title_i18n = NULL,
                subtitle_i18n = NULL,
                updated_at = now()
            FROM public.registration_flow_steps st
            WHERE s.step_id = st.id AND st.flow_id = CAST(:fid AS uuid)
            """
        ),
        {"fid": FLOW_V2_ID},
    )

    # Restore config_json step_metadata English strings (single-language)
    meta_by_screen = {
        "identity_form": ("identity", "Legal first and last name as on your ID.", True),
        "dob_form": ("date_of_birth", "You must be eligible to open an account in your jurisdiction.", True),
        "residence_country_form": (
            "residence_country",
            "Usually pre-filled from your phone country code; you can change it.",
            True,
        ),
        "home_address_form": ("home_address", "Search your address or enter it manually.", True),
        "email_form": ("contact_email", "We will use this email for account notifications.", True),
        "email_otp_optional_form": (
            "email_verification_optional",
            "You can verify your email now or skip and do it later from settings.",
            False,
        ),
        "terms_form": ("terms", "Review and accept the legal agreements to finish registration.", True),
    }
    for sk, (mkey, mdesc, mreq) in meta_by_screen.items():
        cfg = {
            "step_metadata": {"step_key": mkey, "description": mdesc, "required": mreq},
            "email_otp_optional": sk == "email_otp_optional_form",
            "skip_allowed": sk == "email_otp_optional_form",
        }
        conn.execute(
            text(
                """
                UPDATE public.registration_step_screens s
                SET config_json = CAST(:cfg AS jsonb),
                    updated_at = now()
                FROM public.registration_flow_steps st
                WHERE s.step_id = st.id
                  AND st.flow_id = CAST(:fid AS uuid)
                  AND s.screen_key = :screen_key
                """
            ),
            {"cfg": json.dumps(cfg), "fid": FLOW_V2_ID, "screen_key": sk},
        )
