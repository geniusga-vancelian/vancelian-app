"""Registry of admin-facing interaction screen templates (business presets).

Runtime continues to use screen_type, interaction_type, interaction_config_json only.
Templates are the source of truth for builder defaults and optional inference of
``interaction_template_key`` in admin API responses (no DB column required).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# Template keys are stable API identifiers for admin / future persistence.
TEMPLATE_CONFIRMATION_CODE_SMS = "confirmation_code_sms"
TEMPLATE_CONFIRMATION_CODE_EMAIL = "confirmation_code_email"

_RAW_TEMPLATES: List[Dict[str, Any]] = [
    {
        "template_key": TEMPLATE_CONFIRMATION_CODE_SMS,
        "display_name": "Confirmation code (SMS)",
        "description": "Verify a phone number by sending a 6-digit SMS code.",
        "interaction_type": "phone_verification_sms",
        "default_title": "Confirm your mobile number",
        "default_subtitle": "Enter the 6-digit code sent to your phone",
        "default_button_label": "Continue",
        "default_interaction_config": {
            "source_field_slug": "phone_number",
            "verified_flag_slug": "phone_verified",
            "purpose": "verify_phone",
        },
        "required_config_fields": [
            "source_field_slug",
            "verified_flag_slug",
            "purpose",
        ],
        "selectable": True,
    },
    {
        "template_key": TEMPLATE_CONFIRMATION_CODE_EMAIL,
        "display_name": "Confirmation code (email)",
        "description": "Verify an email address with a one-time code (runtime support planned).",
        "interaction_type": "email_verification_otp",
        "default_title": "Confirm your email",
        "default_subtitle": "Enter the code we sent to your inbox",
        "default_button_label": "Continue",
        "default_interaction_config": {
            "source_field_slug": "email",
            "verified_flag_slug": "email_verified",
            "purpose": "verify_email",
        },
        "required_config_fields": [
            "source_field_slug",
            "verified_flag_slug",
            "purpose",
        ],
        "selectable": False,
    },
]

_BY_KEY = {t["template_key"]: t for t in _RAW_TEMPLATES}


def list_interaction_templates_for_api() -> List[Dict[str, Any]]:
    """Return all templates for GET /admin/registration/interaction-templates.

    Use ``selectable`` to grey out or hide presets not yet wired to runtime.
    """
    out: List[Dict[str, Any]] = []
    for t in _RAW_TEMPLATES:
        out.append(
            {
                "template_key": t["template_key"],
                "display_name": t["display_name"],
                "description": t["description"],
                "interaction_type": t["interaction_type"],
                "default_title": t["default_title"],
                "default_subtitle": t["default_subtitle"],
                "default_button_label": t.get("default_button_label") or "Continue",
                "default_interaction_config": dict(t["default_interaction_config"]),
                "required_config_fields": list(t["required_config_fields"]),
                "selectable": bool(t.get("selectable", True)),
            }
        )
    return out


def get_template(template_key: str) -> Optional[Dict[str, Any]]:
    return _BY_KEY.get(template_key)


def _nonempty_str(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def infer_interaction_template_key(
    *,
    screen_type: Optional[str],
    interaction_type: Optional[str],
    interaction_config_json: Optional[Dict[str, Any]],
) -> Optional[str]:
    """Best-effort match for admin display; legacy screens without stored key still infer."""
    if (screen_type or "").strip() != "interaction":
        return None
    it = (interaction_type or "").strip()
    if not it:
        return None
    cfg = interaction_config_json if isinstance(interaction_config_json, dict) else {}
    for t in _RAW_TEMPLATES:
        if t["interaction_type"] != it:
            continue
        req = t["required_config_fields"]
        if not all(_nonempty_str(cfg.get(k)) for k in req):
            continue
        return str(t["template_key"])
    return None


def infer_interaction_template_display_name(
    *,
    screen_type: Optional[str],
    interaction_type: Optional[str],
    interaction_config_json: Optional[Dict[str, Any]],
) -> Optional[str]:
    key = infer_interaction_template_key(
        screen_type=screen_type,
        interaction_type=interaction_type,
        interaction_config_json=interaction_config_json,
    )
    if not key:
        return None
    t = _BY_KEY.get(key)
    return str(t["display_name"]) if t else None


def validate_interaction_screen_admin(
    *,
    screen_type: str,
    interaction_type: Optional[str],
    interaction_config_json: Optional[Dict[str, Any]],
) -> None:
    """Raise ValueError with human-readable message if invalid (maps to HTTP 422)."""
    st = (screen_type or "form").strip() or "form"
    if st == "form":
        if interaction_type is not None and str(interaction_type).strip():
            raise ValueError("interaction_type must be empty when screen_type is form")
        if interaction_config_json is not None and interaction_config_json != {}:
            # allow None or empty dict only
            if isinstance(interaction_config_json, dict) and interaction_config_json:
                raise ValueError("interaction_config_json must be empty when screen_type is form")
        return

    if st != "interaction":
        raise ValueError("screen_type must be 'form' or 'interaction'")

    it = (interaction_type or "").strip()
    if not it:
        raise ValueError("interaction_type is required when screen_type is interaction")

    cfg = interaction_config_json
    if not cfg or not isinstance(cfg, dict):
        raise ValueError("interaction_config_json is required when screen_type is interaction")

    if it == "phone_verification_sms":
        for key in ("source_field_slug", "verified_flag_slug", "purpose"):
            if not _nonempty_str(cfg.get(key)):
                raise ValueError(
                    f"interaction_config_json.{key} is required for phone_verification_sms",
                )
        return

    raise ValueError(
        f"Unsupported interaction_type for registration admin: {it!r}. "
        "Only phone_verification_sms is supported by the runtime today.",
    )
