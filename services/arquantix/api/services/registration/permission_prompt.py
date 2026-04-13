"""Permission prompt screens (Face ID, push notifications) — registration runtime + admin."""
from __future__ import annotations

from typing import Any, Dict, Optional

from database import RegistrationStepScreen

from .interaction_templates import validate_interaction_screen_admin

PERMISSION_KIND_FACE_ID = "face_id"
PERMISSION_KIND_PUSH_NOTIFICATIONS = "push_notifications"
VALID_PERMISSION_KINDS = frozenset(
    {PERMISSION_KIND_FACE_ID, PERMISSION_KIND_PUSH_NOTIFICATIONS},
)


def parse_permission_prompt_config(screen: RegistrationStepScreen) -> Dict[str, Any]:
    raw = screen.config_json or {}
    if not isinstance(raw, dict):
        raw = {}
    return {
        "permission_kind": str(raw.get("permission_kind") or "").strip(),
        "decision_slug": str(raw.get("decision_slug") or "").strip(),
        "secondary_button_label": str(raw.get("secondary_button_label") or "").strip(),
    }


def validate_permission_prompt_admin(*, config_json: Optional[Dict[str, Any]]) -> None:
    cfg = config_json if isinstance(config_json, dict) else {}
    kind = str(cfg.get("permission_kind") or "").strip()
    if kind not in VALID_PERMISSION_KINDS:
        raise ValueError(
            "config_json.permission_kind must be "
            f"'{PERMISSION_KIND_FACE_ID}' or '{PERMISSION_KIND_PUSH_NOTIFICATIONS}'",
        )
    slug = str(cfg.get("decision_slug") or "").strip()
    if not slug:
        raise ValueError("config_json.decision_slug is required for permission_prompt screens")


def validate_screen_for_admin(
    *,
    screen_type: str,
    interaction_type: Optional[str],
    interaction_config_json: Optional[Dict[str, Any]],
    config_json: Optional[Dict[str, Any]],
) -> None:
    """Validate screen payload for POST/PATCH registration admin (form | interaction | permission_prompt)."""
    st = (screen_type or "form").strip() or "form"
    if st == "permission_prompt":
        if interaction_type and str(interaction_type).strip():
            raise ValueError("interaction_type must be empty when screen_type is permission_prompt")
        if interaction_config_json and isinstance(interaction_config_json, dict) and interaction_config_json:
            raise ValueError(
                "interaction_config_json must be empty when screen_type is permission_prompt",
            )
        validate_permission_prompt_admin(config_json=config_json)
        return
    validate_interaction_screen_admin(
        screen_type=st,
        interaction_type=interaction_type,
        interaction_config_json=interaction_config_json,
    )


def list_permission_prompt_templates_for_api() -> list:
    """Presets for admin builder (mirrors interaction-templates pattern)."""
    return [
        {
            "template_key": "face_id_activation",
            "display_name": "Face ID — activer la connexion",
            "description": "Écran pleine largeur type iOS : héros Face ID, titre, texte, Activer / Pas maintenant.",
            "permission_kind": PERMISSION_KIND_FACE_ID,
            "default_title": "Log in\nwith a single look",
            "default_subtitle": "Use Face ID to quickly log in\nto your account",
            "default_button_label": "Enable Face ID",
            "default_config": {
                "permission_kind": PERMISSION_KIND_FACE_ID,
                "decision_slug": "face_id_enabled",
                "secondary_button_label": "Not Now",
            },
        },
        {
            "template_key": "push_notifications_activation",
            "display_name": "Notifications push",
            "description": "Demande d’autorisation notifications (icône / image via config côté app).",
            "permission_kind": PERMISSION_KIND_PUSH_NOTIFICATIONS,
            "default_title": "Restez informé",
            "default_subtitle": "Autorisez les notifications pour les alertes importantes sur votre compte.",
            "default_button_label": "Activer les notifications",
            "default_config": {
                "permission_kind": PERMISSION_KIND_PUSH_NOTIFICATIONS,
                "decision_slug": "push_notifications_enabled",
                "secondary_button_label": "Pas maintenant",
            },
        },
    ]
