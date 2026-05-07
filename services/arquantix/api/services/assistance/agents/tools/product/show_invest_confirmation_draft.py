"""Tool ``show_invest_confirmation_draft`` récap visuel type page
Confirmation (montant + source) avec boutons **Confirmer** / **Annuler**.
Le bouton Confirmer ouvre le flux natif avec montant prérempli via
deep-link (pas d'exécution serveur depuis l'assistant en Phase 1).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import quote

from uuid import UUID

from services.assistance.action_drafts_repo import create_action_draft
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec

logger = logging.getLogger(__name__)


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
                    "description": "Clé renvoyée par show_invest_source_accounts (ex. fiat, crypto:USDC).",
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


def _money_fmt(val: float, ccy: str) -> str:
    c = (ccy or "EUR").upper().strip()
    if c in {"EUR", "EURO"}:
        return f"{val:,.2f} €".replace(",", " ")
    if c in {"USD", "DOLLAR"}:
        return f"${val:,.2f}"
    return f"{val:,.8f} {c}".replace(",", " ")


def _build_confirm_link(
    *,
    target_kind: str,
    target_id: str,
    account_key: str,
    amount: float,
    amount_currency: str,
    action_draft_id: str,
) -> Optional[str]:
    ak = quote(account_key, safe="")
    ccy = quote(amount_currency.strip(), safe="")
    amt = quote(f"{amount:.8f}".rstrip("0").rstrip("."), safe="")
    did = quote(action_draft_id, safe="")
    if target_kind == "bundle":
        bid = quote(str(target_id).strip(), safe="")
        return (
            f"vancelian://app/invest/bundle_amount?bundle_id={bid}&account_key={ak}"
            f"&amount={amt}&ccy={ccy}&action_draft_id={did}"
        )
    if target_kind == "crypto_buy":
        sym = quote(str(target_id).strip().upper(), safe="")
        return (
            f"vancelian://app/invest/crypto_buy_amount?symbol={sym}&account_key={ak}"
            f"&amount={amt}&ccy={ccy}&action_draft_id={did}"
        )
    return None


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
    tk = (target_kind or "").strip().lower()
    if tk not in {"crypto_buy", "bundle"}:
        return {"ok": False, "error": "invalid_target"}

    if not ctx.client_id or not ctx.conversation_id:
        return {"ok": False, "error": "context_required"}

    try:
        cid = UUID(str(ctx.client_id))
        conv_uid = UUID(str(ctx.conversation_id))
    except (ValueError, AttributeError):
        return {"ok": False, "error": "invalid_context"}

    try:
        amt_dec = Decimal(str(amount))
    except Exception:  # noqa: BLE001
        return {"ok": False, "error": "invalid_amount"}
    if amt_dec <= 0:
        return {"ok": False, "error": "amount_must_be_positive"}

    ccy_u = (amount_currency or "EUR").strip().upper()
    try:
        amt_f = float(amt_dec)
    except Exception:  # noqa: BLE001
        amt_f = float(amount)

    action_type = "bundle_invest" if tk == "bundle" else "crypto_buy"
    try:
        draft = create_action_draft(
            ctx.db,
            conversation_id=conv_uid,
            client_id=cid,
            action_type=action_type,
            payload={
                "target_kind": tk,
                "target_id": str(target_id).strip(),
                "stage": "confirmation",
                "amount": amt_f,
                "amount_currency": ccy_u,
                "account_key": str(account_key).strip(),
            },
        )
        draft_id = str(draft.id)
    except Exception:  # noqa: BLE001
        logger.exception(
            "show_invest_confirmation_draft.action_draft_failed conv=%s",
            ctx.conversation_id,
        )
        return {"ok": False, "error": "draft_persist_failed"}

    hero = _money_fmt(amt_f, ccy_u)
    confirm_link = _build_confirm_link(
        target_kind=tk,
        target_id=target_id,
        account_key=account_key,
        amount=amt_f,
        amount_currency=ccy_u,
        action_draft_id=draft_id,
    )

    embed: dict[str, Any] = {
        "type": "invest_confirmation_draft",
        "action_draft_id": draft_id,
        "target_kind": tk,
        "target_id": str(target_id).strip(),
        "headline": "Confirmer ton investissement",
        "hero_amount": hero,
        "source_line": str(source_label).strip(),
        "destination_line": str(destination_label).strip(),
        "disclaimer": (
            "Récapitulatif indicatif — le détail définitif (frais, taux) est "
            "recalculé sur l'écran suivant."
        ),
        "confirm_deep_link": confirm_link,
        "confirm_label": "Confirmer",
        "cancel_label": "Annuler",
    }
    ctx.embeds_to_emit.append(embed)

    return {
        "ok": True,
        "action_draft_id": draft_id,
        "message": (
            "Encart de confirmation affiché — rappelle que l'exécution se fait "
            "dans l'app après validation native."
        ),
    }


__all__ = ["SPEC", "execute"]
