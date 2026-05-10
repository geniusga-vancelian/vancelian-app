"""Tool ``deposit_present_channels`` — guide dépôt (virement / carte / crypto)."""

from __future__ import annotations

import logging
from typing import Any

from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.assistance.agents.tools.shared.action_cta_catalog import build_action

from ._widget import append_action_widget

logger = logging.getLogger(__name__)

SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "deposit_present_channels",
        "description": (
            "Présente des boutons conformes aux écrans de dépôt Vancelian "
            "(virement SEPA, carte, crypto incoming). À appeler lorsque "
            "le client veut **déposer des fonds**. Aucune exécution : "
            "navigation native uniquement après tap."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "include_generic_modal": {
                    "type": "boolean",
                    "description": (
                        "True (défaut) : ajouter l'entrée « Tous les modes » "
                        "qui ouvre la même modale de choix que l'accueil app."
                    ),
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
    include_generic_modal: bool = True,
    **_kwargs: Any,
) -> dict[str, Any]:
    rows: list[dict[str, str]] = []
    for kind in ("deposit_virement", "deposit_carte", "deposit_crypto"):
        ba = build_action(kind)
        if ba:
            rows.append(
                {
                    "kind": ba["kind"],
                    "label": ba["label"],
                    "deep_link": ba["deep_link"],
                },
            )

    if include_generic_modal:
        ba = build_action("deposit_funds")
        if ba:
            rows.append(
                {
                    "kind": ba["kind"],
                    "label": "Voir tous les modes",
                    "deep_link": ba["deep_link"],
                },
            )

    if not rows:
        return {"ok": False, "error": "deposit_channels_unconfigured"}

    draft_id = append_action_widget(
        ctx,
        widget_kind="deposit_channel_picker",
        title="Comment souhaites-tu déposer ?",
        actions=rows,
        disclaimer=(
            "Tu seras guidé dans l'app sécurisée ; aucun paiement depuis le chat."
        ),
        action_type="deposit_guide",
        payload={"channels": [r["kind"] for r in rows]},
    )
    if draft_id is None:
        return {
            "ok": False,
            "error": "client_required",
            "hint": (
                "Le client doit être connecté avec un client_id pour afficher "
                "les boutons de dépôt."
            ),
        }
    logger.info(
        "deposit_present_channels.embed conv=%s draft=%s rows=%s",
        ctx.conversation_id,
        draft_id,
        len(rows),
    )
    return {
        "ok": True,
        "action_draft_id": draft_id,
        "channels": [r["kind"] for r in rows],
        "message": (
            "Carte d'actions affichée : le client peut choisir son mode "
            "de dépôt."
        ),
    }
