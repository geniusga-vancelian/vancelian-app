"""Tool ``bundle_invest_start`` — flux bundle CAL (liste comptes source)."""

from __future__ import annotations

import logging
from typing import Any

from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.assistance.agents.tools.product import show_invest_source_accounts

logger = logging.getLogger(__name__)

SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "bundle_invest_start",
        "description": (
            "Démarre l'investissement dans un crypto bundle depuis "
            "l'assistant — affiche les comptes source autorisés (entry "
            "assets) comme le flux CAL existant."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "bundle_id": {
                    "type": "string",
                    "description": (
                        "UUID du produit bundle (`pe_product_definitions.id`)."
                    ),
                },
            },
            "required": ["bundle_id"],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "action",
}


def execute(
    ctx: ToolContext,
    *,
    bundle_id: str,
    **_kwargs: Any,
) -> dict[str, Any]:
    out = show_invest_source_accounts.execute(
        ctx,
        target_kind="bundle",
        target_id=(bundle_id or "").strip(),
    )
    logger.info(
        "bundle_invest_start passthrough conv=%s ok=%s",
        ctx.conversation_id,
        bool(out.get("ok")),
    )
    return {**out, "flow": "bundle_invest"}
