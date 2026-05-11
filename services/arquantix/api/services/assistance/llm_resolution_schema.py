"""Contrat strict — signal de résolution conversationnel émis par un LLM (Phase 6).

Le modèle produit **uniquement** ce schéma (JSON). Aucun ``should_*`` : le backend les
déduit via ``resolution_type``.
"""

from __future__ import annotations

import json
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError

LLMResolutionType = Literal[
    "same_action_continuation",
    "new_action_detected",
    "cancel_requested",
    "off_topic",
    "ambiguous",
    "no_active_action",
]


class LLMConversationResolutionSignal(BaseModel):
    """Signal validé strictement ``extra=forbid`` — aucune clé inconnue."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    resolution_type: LLMResolutionType
    confidence: float = Field(ge=0.0, le=1.0)
    target_action_type: Optional[str] = Field(default=None, max_length=80)
    reason: str = Field(default="", max_length=768)
    extracted_entities: dict[str, Any] = Field(default_factory=dict)


def strip_llm_json_fences(text: str) -> str:
    """Retire un wrapper Markdown type ```json ... ``` sans interprétation métier."""
    t = text.strip()
    if not t.startswith("```"):
        return t
    lines = t.splitlines()
    if not lines:
        return ""
    i = 0
    if lines[0].strip().startswith("```"):
        i += 1
    out: list[str] = []
    while i < len(lines):
        if lines[i].strip().startswith("```"):
            break
        out.append(lines[i])
        i += 1
    return "\n".join(out).strip()


def parse_llm_resolution_json_any(
    payload: Any,
) -> tuple[Optional[LLMConversationResolutionSignal], list[str]]:
    """Parse + valide depuis ``dict`` (déjà JSON-décodé) ou échoue."""
    errs: list[str] = []
    if not isinstance(payload, dict):
        return None, ["payload_not_json_object"]
    try:
        sig = LLMConversationResolutionSignal.model_validate(payload)
    except ValidationError as exc:
        errs = [str(x) for x in exc.errors()][:32]
        return None, errs
    return sig, []


def parse_llm_resolution_json_string(
    raw: str,
) -> tuple[Optional[LLMConversationResolutionSignal], list[str]]:
    """Parse depuis texte brut (JSON uniquement ou bloc ```json)."""
    if not isinstance(raw, str) or not raw.strip():
        return None, ["empty_raw_output"]

    stripped = strip_llm_json_fences(raw)
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        return None, [f"json_decode_error:{exc}"]

    if not isinstance(data, dict):
        return None, ["root_not_object"]

    return parse_llm_resolution_json_any(data)


__all__ = [
    "LLMConversationResolutionSignal",
    "LLMResolutionType",
    "parse_llm_resolution_json_any",
    "parse_llm_resolution_json_string",
    "strip_llm_json_fences",
]
