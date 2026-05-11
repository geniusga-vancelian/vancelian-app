"""Émission embed ``invest_confirmation_draft`` — partagé produit + agent action.

Réutilisable pour achat crypto (montant connu), bundles, offres exclusives :
même payload JSON, variation via ``intent_kind`` + ``compact``.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Optional
from urllib.parse import quote
from uuid import UUID

from services.assistance.action_drafts_repo import create_action_draft
from services.assistance.agents.tools.contracts import ToolContext

logger = logging.getLogger(__name__)


def _money_fmt(val: float, ccy: str) -> str:
    c = (ccy or "EUR").upper().strip()
    if c in {"EUR", "EURO"}:
        return f"{val:,.2f} €".replace(",", " ")
    if c in {"USD", "DOLLAR"}:
        return f"${val:,.2f}"
    return f"{val:,.8f} {c}".replace(",", " ")


def _build_confirm_deep_link(
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


def append_invest_confirmation_embed(
    ctx: ToolContext,
    *,
    target_kind: str,
    target_id: str,
    amount: float,
    amount_currency: str,
    account_key: str,
    source_label: str,
    destination_label: str,
    headline: Optional[str] = None,
    confirm_label: Optional[str] = None,
    cancel_label: Optional[str] = None,
    disclaimer: Optional[str] = None,
    intent_kind: str = "invest",
    compact: bool = False,
    extra_payload: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Crée un ``action_draft``, pousse l'embed sur ``ctx``.

    Retour : ``{"ok": bool, "error"?: str, "action_draft_id"?: str, "embed"?: dict}``
    (``embed`` inclus pour tests ; le runtime lit ``ctx.embeds_to_emit``).
    """
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
    pl: dict[str, Any] = {
        "target_kind": tk,
        "target_id": str(target_id).strip(),
        "stage": "confirmation",
        "amount": amt_f,
        "amount_currency": ccy_u,
        "account_key": str(account_key).strip(),
        "intent_kind": str(intent_kind).strip()[:48] or "invest",
        "compact": bool(compact),
    }
    # Phase 3 : pas de fusion libre — chaque clé doit être dans le schéma métier
    # (``action_draft_payload_schemas``). Étendre `_ALLOWED_EXTRA_KEYS` si besoin.
    _ALLOWED_EXTRA_KEYS: frozenset[str] = frozenset()
    if extra_payload and isinstance(extra_payload, dict):
        for k, v in extra_payload.items():
            if k in _ALLOWED_EXTRA_KEYS and v is not None:
                pl[k] = v

    try:
        draft = create_action_draft(
            ctx.db,
            conversation_id=conv_uid,
            client_id=cid,
            action_type=action_type,
            payload=pl,
        )
        draft_id = str(draft.id)
    except Exception:  # noqa: BLE001
        logger.exception(
            "invest_confirmation_emit.draft_failed conv=%s",
            ctx.conversation_id,
        )
        return {"ok": False, "error": "draft_persist_failed"}

    hero = _money_fmt(amt_f, ccy_u)
    confirm_link = _build_confirm_deep_link(
        target_kind=tk,
        target_id=target_id,
        account_key=account_key,
        amount=amt_f,
        amount_currency=ccy_u,
        action_draft_id=draft_id,
    )

    headline_f = headline or (
        "Confirmer ton investissement" if not compact else "Récap avant validation"
    )
    disc = disclaimer or (
        "Récapitulatif indicatif — le détail définitif (frais, taux) est "
        "recalculé sur l'écran suivant."
    )

    embed: dict[str, Any] = {
        "type": "invest_confirmation_draft",
        "action_draft_id": draft_id,
        "target_kind": tk,
        "target_id": str(target_id).strip(),
        "intent_kind": pl["intent_kind"],
        "presentation": "compact_card" if compact else "standard",
        "compact": compact,
        "headline": headline_f,
        "hero_amount": hero,
        "source_line": str(source_label).strip(),
        "destination_line": str(destination_label).strip(),
        "disclaimer": disc,
        "confirm_deep_link": confirm_link,
        "confirm_label": confirm_label or "Confirmer",
        "cancel_label": cancel_label or "Annuler",
    }
    ctx.embeds_to_emit.append(embed)

    return {"ok": True, "action_draft_id": draft_id, "embed": embed}


__all__ = [
    "append_invest_confirmation_embed",
    "_money_fmt",
    "_build_confirm_deep_link",
]
