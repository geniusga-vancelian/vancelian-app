"""Tool ``show_invest_confirmation_draft`` récap visuel type page
Confirmation (montant + source) avec boutons **Confirmer** / **Annuler**.
Le bouton Confirmer ouvre le flux natif avec montant prérempli via
deep-link (pas d'exécution serveur depuis l'assistant en Phase 1).
"""

from __future__ import annotations

from typing import Any

from services.assistance.agents.tools.contracts import ToolContext, ToolSpec

from services.assistance.agents.tools.product.invest_confirmation_emit import (
    append_invest_confirmation_embed,
)

SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "show_invest_confirmation_draft",
        "description": (
            "Affiche un encart de CONFIRMATION d'investissement (brouillon) : "
            "montant, source d'approvisionnement, destination (crypto / bundle). "
            "Les boutons Confirmer / Annuler sont natifs ; Confirmer ouvre le "
            "flux transactionnel existant côté app — le LLM ne doit jamais "
            "prétendre que l'ordre est exécuté. À utiliser quand montant et "
            "compte source sont déjà connus de la conversation."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "target_kind": {
                    "type": "string",
                    "enum": ["crypto_buy", "bundle"],
                },
                "target_id": {
                    "type": "string",
                    "description": "Symbol crypto ou UUID bundle.",
                },
                "amount": {
                    "type": "number",
                    "description": "Montant à investir (> 0) dans amount_currency.",
                },
                "amount_currency": {
                    "type": "string",
                    "description": "Devise du montant (EUR, USD, ou actif crypto si source crypto).",
                },
                "account_key": {
                    "type": "string",
                    "description": (
                        "Clé renvoyée par show_invest_source_accounts (ex. fiat, crypto:USDC)."
                    ),
                },
                "source_label": {
                    "type": "string",
                    "description": "Libellé court du compte source affiché au client.",
                },
                "destination_label": {
                    "type": "string",
                    "description": "Libellé de la cible (ex. nom du bundle).",
                },
            },
            "required": [
                "target_kind",
                "target_id",
                "amount",
                "amount_currency",
                "account_key",
                "source_label",
                "destination_label",
            ],
            "additionalProperties": False,
        },
    },
    "autonomy_level": "L0",
    "agent_id": "product",
}


def execute(
    ctx: ToolContext,
    *,
    target_kind: str,
    target_id: str,
    amount: float,
    amount_currency: str,
    account_key: str,
    source_label: str,
    destination_label: str,
    **_kwargs: Any,
) -> dict[str, Any]:
    ik = (
        "bundle_invest"
        if (target_kind or "").strip().lower() == "bundle"
        else "crypto_buy"
    )
    res = append_invest_confirmation_embed(
        ctx,
        target_kind=target_kind,
        target_id=target_id,
        amount=amount,
        amount_currency=amount_currency,
        account_key=account_key,
        source_label=source_label,
        destination_label=destination_label,
        intent_kind=ik,
        compact=False,
    )
    if not res.get("ok"):
        return {
            "ok": False,
            "error": res.get("error", "confirmation_failed"),
        }
    draft_id = res.get("action_draft_id")
    return {
        "ok": True,
        "action_draft_id": draft_id,
        "message": (
            "Encart de confirmation affiché — rappelle que l'exécution se fait "
            "dans l'app après validation native."
        ),
    }


__all__ = ["SPEC", "execute"]
