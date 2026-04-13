"""Explicit ``policy_scope`` for registration submit routing (no slug-based inference).

Resolution order (strict, documented):

- ``phone_input`` → always ``phone`` (props ``policy_scope`` ≠ phone is logged and ignored).
- Otherwise: ``props_json.policy_scope`` → ``field_definition.policy_scope`` (if loaded)
  → ``country_picker`` default ``residence`` → ``none``.
- Nationality flows **must** set ``policy_scope: nationality`` on the component props
  or on ``field_definitions.policy_scope``.

Known scopes: ``phone``, ``residence``, ``nationality``, ``none``.
"""
from __future__ import annotations

import logging
from typing import Any, FrozenSet, Optional

logger = logging.getLogger(__name__)

VALID_POLICY_SCOPES: FrozenSet[str] = frozenset(
    {"phone", "residence", "nationality", "none"}
)


def _normalized_scope(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().lower()
    return s if s in VALID_POLICY_SCOPES else None


def resolve_policy_scope(comp: Any) -> str:
    """Return policy scope for submit-time validation routing."""
    ctype = (getattr(comp, "component_type", None) or "").strip()

    if ctype == "phone_input":
        props = getattr(comp, "props_json", None) or {}
        explicit = _normalized_scope(props.get("policy_scope"))
        if explicit is not None and explicit != "phone":
            logger.warning(
                "registration_policy_scope: phone_input with policy_scope=%r ignored; forcing phone",
                explicit,
            )
        return "phone"

    props = getattr(comp, "props_json", None) or {}
    explicit = _normalized_scope(props.get("policy_scope"))
    if explicit is not None:
        return explicit

    fd = getattr(comp, "field_definition", None)
    if fd is not None:
        fd_scope = _normalized_scope(getattr(fd, "policy_scope", None))
        if fd_scope is not None:
            return fd_scope

    if ctype == "country_picker":
        return "residence"

    return "none"
