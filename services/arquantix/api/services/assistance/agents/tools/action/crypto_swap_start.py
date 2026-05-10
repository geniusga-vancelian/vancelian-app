"""Tool ``crypto_swap_start`` — guide échange crypto (deep-link liste marchés)."""

from __future__ import annotations

import logging
from typing import Any, Optional

from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.assistance.agents.tools.shared.action_cta_catalog import build_action

from ._widget import append_action_widget

logger = logging.getLogger(__name__)

SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "crypto_swap_start",
        "description": (
            "Quand le client veut **échanger / swapper** deux cryptos sans "
            "contexte prérempli dans le chat — propose ouverture de la "
            "liste marchés où il peut sélectionner l'actif puis utiliser "
            "le flux Échanger de l'app."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "from_symbol": {
                    "type": "string",
                    "description": "Optionnel — actif vendu/exchange depuis (BTC, ETH).",
                },
                "to_symbol": {
                    "type": "string",
                    "description": "Optionnel — actif obtenu (USDT, BTC, …).",
                },
            },
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "action",
}


def execute(
    ctx: ToolContext,
    *,
    from_symbol: Optional[str] = None,
    to_symbol: Optional[str] = None,
    **_kwargs: Any,
) -> dict[str, Any]:
    ba = build_action("markets_crypto")
    actions: list[dict[str, str]] = []
    if ba:
        actions.append(
            {
                "kind": ba["kind"],
                "label": ba["label"],
                "deep_link": ba["deep_link"],
            },
        )
    else:
        return {"ok": False, "error": "markets_cta_unconfigured"}

    subtitle_parts: list[str] = []
    if from_symbol and to_symbol:
        subtitle_parts.append(
            f"Paire envisagée {from_symbol.strip().upper()} → "
            f"{to_symbol.strip().upper()} (indicatif — à confirmer dans l'app)."
        )

    disclaimer = (
        " ".join(subtitle_parts)
        + " Échange depuis l'espace Wallet / marchés sécurisé — rien depuis le chat."
    ).strip()

    draft_id = append_action_widget(
        ctx,
        widget_kind="crypto_swap_guide",
        title="Échanger des cryptos",
        actions=actions,
        disclaimer=disclaimer or (
            "Sélectionne un actif dans l'application puis utilise "
            "l'action Échanger — aucune conversion depuis cette conversation."
        ),
        action_type="crypto_swap_guide",
        payload={
            "from_symbol": (from_symbol or "").strip().upper() or None,
            "to_symbol": (to_symbol or "").strip().upper() or None,
        },
    )
    if draft_id is None:
        return {"ok": False, "error": "client_required"}
    logger.info(
        "crypto_swap_start conv=%s draft=%s", ctx.conversation_id, draft_id
    )
    return {
        "ok": True,
        "action_draft_id": draft_id,
        "hint": (
            "Indique aussi en texte qu'un swap multi-étapes se pilote depuis "
            "l'application (passcode / session trading requis)."
        ),
    }
