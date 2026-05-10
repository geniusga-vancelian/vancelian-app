"""Helpers embed ``action_widget`` + persistance draft (audit)."""

from __future__ import annotations

import logging
from typing import Any, Optional
from urllib.parse import quote
from uuid import UUID

from services.assistance.action_drafts_repo import create_action_draft
from services.assistance.agents.tools.contracts import ToolContext

logger = logging.getLogger(__name__)


def append_action_widget(
    ctx: ToolContext,
    *,
    widget_kind: str,
    title: str,
    actions: list[dict[str, str]],
    disclaimer: str,
    action_type: str,
    payload: dict[str, Any],
) -> Optional[str]:
    """Crée un draft, ajoute embed `action_widget` à ctx. Retourne draft_id."""
    cid = ctx.client_id
    if not cid:
        logger.info("action_widget.skip_no_client widget_kind=%s", widget_kind)
        return None

    try:
        client_uuid = UUID(str(cid))
        conv_uuid = UUID(str(ctx.conversation_id))
    except (ValueError, TypeError):
        return None

    draft = create_action_draft(
        ctx.db,
        conversation_id=conv_uuid,
        client_id=client_uuid,
        action_type=action_type,
        payload={**payload, "widget_kind": widget_kind},
    )
    draft_id = str(draft.id)

    embed: dict[str, Any] = {
        "type": "action_widget",
        "widget_kind": widget_kind,
        "title": title,
        "actions": [],
        "disclaimer": disclaimer,
        "action_draft_id": draft_id,
    }
    sanitized: list[dict[str, str]] = []
    for row in actions:
        if not isinstance(row, dict):
            continue
        kind = str(row.get("kind") or "").strip()
        label = str(row.get("label") or "").strip()
        dl = str(row.get("deep_link") or "").strip()
        if not kind or not label or not dl:
            continue
        sanitized.append(
            {"kind": kind, "label": label, "deep_link": dl},
        )

    for it in sanitized:
        dl = it["deep_link"]
        sep_eff = "&" if "?" in dl else "?"
        it["deep_link"] = f"{dl}{sep_eff}action_draft_id={quote(draft_id, safe='')}"
    embed["actions"] = sanitized

    ctx.embeds_to_emit.append(embed)
    return draft_id


__all__ = ["append_action_widget"]
