"""i18n helper for the Registration Flow Engine.

Supports both plain strings and localized JSON objects:
  - "First Name"                       → returns "First Name"
  - {"en": "First Name", "fr": "Prénom"} → returns value for requested lang

Fallback chain: requested lang → default_lang → "en" → first available → raw value.
"""
from __future__ import annotations

from typing import Any, Optional


def resolve_localized(
    value: Any,
    lang: str = "en",
    default_lang: str = "en",
) -> str:
    """Resolve a potentially localized value to a string.

    Works with both plain strings (backward compat) and {lang: text} dicts.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if lang in value:
            return str(value[lang])
        if default_lang in value:
            return str(value[default_lang])
        if "en" in value:
            return str(value["en"])
        if value:
            return str(next(iter(value.values())))
        return ""
    return str(value)


def resolve_localized_props(
    props: dict,
    lang: str = "en",
    default_lang: str = "en",
) -> dict:
    """Resolve all localizable fields in a props dict.

    Returns a new dict with localized string values for known text fields,
    preserving all other fields unchanged.
    """
    if not props:
        return {}

    result = dict(props)
    for key in ("label", "placeholder", "text", "content", "description", "link_label"):
        if key in result:
            result[key] = resolve_localized(result[key], lang, default_lang)

    if "items" in result and isinstance(result["items"], list):
        result["items"] = [
            resolve_localized(item, lang, default_lang) if isinstance(item, (str, dict)) else item
            for item in result["items"]
        ]

    if "options" in result and isinstance(result["options"], list):
        result["options"] = [
            {
                **opt,
                "label": resolve_localized(opt.get("label", ""), lang, default_lang),
            }
            if isinstance(opt, dict) else opt
            for opt in result["options"]
        ]

    return result
