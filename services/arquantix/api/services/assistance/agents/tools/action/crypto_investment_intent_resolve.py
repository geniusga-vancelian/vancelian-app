"""Tool ``crypto_investment_intent_resolve`` — IDs + soldes (backend, sans LLM)."""

from __future__ import annotations

import copy
import logging
from typing import Any, Optional

from uuid import UUID

from services.portfolio_engine.clients.models import Client as PeClient

from services.assistance.action_drafts_repo import (
    get_latest_active_draft_row,
    persist_action_draft_business_update,
)
from services.assistance.agents.tools.action.crypto_investment_intent_logic import (
    build_confirmation_summary_fr,
    clarification_backend_options_from_source_items,
    clarification_reason_for_source_errors,
    collect_invest_source_items,
    instrument_resolved_id,
    items_for_source_account_clarification,
    match_source_account,
    resolve_market_instrument_for_intent,
)
from services.assistance.agents.tools.contracts import ToolContext, ToolSpec
from services.test_clients.service import TestClientService

logger = logging.getLogger(__name__)


def _clarification_source_block(
    *,
    src_status: str,
    src_errs: list[str],
    items: list[dict[str, Any]],
) -> dict[str, Any]:
    if src_status == "ambiguous":
        sub = items_for_source_account_clarification(errors=src_errs, items=items)
        opts = clarification_backend_options_from_source_items(items, restrict_to=sub)
        return {
            "clarification": True,
            "clarification_reason": clarification_reason_for_source_errors(src_errs),
            "clarification_options_count": len(opts),
            "clarification_options": opts,
        }
    if (
        src_status == "failed"
        and "source_account_option_id_inconnu" in src_errs
    ):
        opts = clarification_backend_options_from_source_items(items)
        return {
            "clarification": True,
            "clarification_reason": "invalid_option_id",
            "clarification_options_count": len(opts),
            "clarification_options": opts,
        }
    return {}


_SPEC_SVC = TestClientService()


def _client_row(db, client_id: UUID) -> Optional[PeClient]:
    return db.get(PeClient, client_id)


_ALLOWED_CI_INTENT_ORIGINS: frozenset[str] = frozenset(
    {
        "chat_free_text",
        "product_page_cta",
        "portfolio_recommendation",
        "advisor_handoff",
        "push_notification",
    },
)


def _preserve_crypto_intent_draft_origin(raw: Any) -> str:
    s = str(raw or "").strip().lower()
    return s if s in _ALLOWED_CI_INTENT_ORIGINS else "chat_free_text"


SPEC: ToolSpec = {
    "type": "function",
    "function": {
        "name": "crypto_investment_intent_resolve",
        "description": (
            "Résout ``resolved_id`` / soldes du brouillon **crypto_investment_intent** "
            "actif (MarketDataInstrument + agrégats cash/positions). **Aucun** appel "
            "LLM. À appeler après ``crypto_investment_intent_start`` lorsque les slots "
            "bruts sont complets (ou quand le client clarifie)."
        ),
        "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    "autonomy_level": "L0",
    "agent_id": "action",
}


def execute(ctx: ToolContext, **_kwargs: Any) -> dict[str, Any]:
    if not ctx.client_id:
        return {"ok": False, "error": "client_required", "flow": "crypto_investment_intent"}

    try:
        conv_uid = UUID(str(ctx.conversation_id))
        client_uid = UUID(str(ctx.client_id))
    except (ValueError, AttributeError):
        return {"ok": False, "error": "bad_uuid", "flow": "crypto_investment_intent"}

    row = get_latest_active_draft_row(
        ctx.db,
        conversation_id=conv_uid,
        action_type="crypto_investment_intent",
    )
    if row is None:
        return {"ok": False, "error": "no_active_intent_draft", "flow": "crypto_investment_intent"}

    root = dict(row.payload if isinstance(row.payload, dict) else {})
    business = {
        k: v
        for k, v in root.items()
        if k not in {"cal_contract", "_lifecycle"}
    }
    slots = copy.deepcopy(business.get("slots") if isinstance(business.get("slots"), dict) else {})
    if not isinstance(slots, dict):
        slots = {}
    for k in ("target_asset", "source_account", "amount"):
        slots.setdefault(k, {})

    errors: list[str] = []
    buy_sym_upper: Optional[str] = None

    preserved_origin = _preserve_crypto_intent_draft_origin(business.get("draft_origin"))

    ta = slots["target_asset"] if isinstance(slots["target_asset"], dict) else {}
    inst, tgt_status, tgt_errs = resolve_market_instrument_for_intent(
        ctx.db,
        raw_text=str(ta.get("raw") or ""),
        explicit_symbol=str(ta.get("symbol") or "") or None,
    )
    if tgt_status == "resolved" and inst is not None:
        ta["resolved_id"] = instrument_resolved_id(inst)
        ta["resolved_provenance"] = "backend_catalog"
        ta["label"] = (inst.name or ta.get("raw") or inst.symbol)[:256]
        ta["symbol"] = str(inst.symbol).strip().upper()
        ta["resolution_status"] = "resolved"
        if ta.get("confidence") is None:
            ta["confidence"] = 1.0
        buy_sym_upper = ta["symbol"]
    else:
        ta["resolution_status"] = "failed"
        ta["resolved_provenance"] = "unresolved"
        errors.extend(tgt_errs)
        fb = str(ta.get("symbol") or "").strip().upper()
        buy_sym_upper = fb or None

    client = _client_row(ctx.db, client_uid)
    if client is None:
        errors.append("client_not_found")

    cash: dict[str, Any] = {}
    crypto: dict[str, Any] = {}
    if client is not None:
        try:
            c = _SPEC_SVC.get_cash_data(ctx.db, client=client)
            p = _SPEC_SVC.get_crypto_positions(ctx.db, client=client)
            cash = c if isinstance(c, dict) else {}
            crypto = p if isinstance(p, dict) else {}
        except Exception:  # noqa: BLE001
            logger.exception("crypto_investment_intent_resolve.data conv=%s", ctx.conversation_id)
            errors.append("funding_data_unavailable")

    items = collect_invest_source_items(
        cash=cash,
        crypto=crypto,
        buy_symbol_upper=buy_sym_upper,
    )
    src = slots["source_account"] if isinstance(slots["source_account"], dict) else {}
    src_raw = str(src.get("raw") or "").strip() or None
    src_opt_raw = src.get("selected_option_id")
    src_opt = str(src_opt_raw).strip() if src_opt_raw else None
    src_row, src_status, src_errs = match_source_account(
        src_raw,
        items,
        selected_option_id=src_opt,
    )
    if src_status == "resolved" and src_row is not None:
        src["resolved_id"] = str(src_row.get("account_key") or "")
        src["resolved_provenance"] = "backend_funding_accounts"
        src["label"] = str(src_row.get("label") or "")[:256]
        src["resolution_status"] = "resolved"
        try:
            src["available_balance"] = float(src_row.get("balance") or 0)
        except (TypeError, ValueError):
            src["available_balance"] = None
        if src.get("confidence") is None:
            src["confidence"] = 1.0
        src.pop("selected_option_id", None)
    elif src_status == "skipped":
        src["resolution_status"] = "pending"
        errors.append("source_account_manquant")
    else:
        src["resolution_status"] = src_status
        src["resolved_provenance"] = "unresolved"
        errors.extend(src_errs)

    am = slots["amount"] if isinstance(slots["amount"], dict) else {}
    if am.get("use_all_available"):
        am["resolution_status"] = "resolved"
        am["resolved_provenance"] = "backend_validated"
        if am.get("confidence") is None:
            am["confidence"] = 0.9
    elif am.get("value") is not None:
        am["resolution_status"] = "resolved"
        am["resolved_provenance"] = "backend_validated"
        if am.get("confidence") is None:
            am["confidence"] = 0.95
    else:
        am["resolution_status"] = "pending"
        errors.append("amount_manquant")

    if (
        src_status == "resolved"
        and src_row is not None
        and am.get("value") is not None
        and not am.get("use_all_available")
    ):
        try:
            bal = float(src_row.get("balance") or 0)
            val = float(am.get("value") or 0)
            if val > bal + 1e-6:
                errors.append("montant_superieur_au_disponible_source")
        except (TypeError, ValueError):
            errors.append("montant_ou_solde_invalide")

    business_out: dict[str, Any] = {
        "intent_schema_version": str(business.get("intent_schema_version") or "1"),
        "draft_origin": preserved_origin,
        "slots": slots,
    }

    if errors:
        business_out["stage"] = "draft_ready_for_backend_validation"
        business_out["backend_validation"] = {"status": "invalid", "errors": errors}
        business_out["confirmation"] = {"status": "none", "summary": None}
        persist_action_draft_business_update(
            ctx.db,
            row=row,
            business_payload=business_out,
            lifecycle_to="collecting",
            lifecycle_reason="crypto_intent_resolver_invalid",
        )
        clar = _clarification_source_block(
            src_status=src_status,
            src_errs=src_errs,
            items=items,
        )
        return {
            "ok": False,
            "flow": "crypto_investment_intent",
            "errors": errors,
            "action_draft_id": str(row.id),
            "slots": slots,
            **clar,
        }

    summary = build_confirmation_summary_fr(slots)
    business_out["stage"] = "draft_pending_user_confirmation"
    business_out["backend_validation"] = {"status": "ok", "errors": []}
    business_out["confirmation"] = {"status": "pending", "summary": summary}

    persist_action_draft_business_update(
        ctx.db,
        row=row,
        business_payload=business_out,
        lifecycle_to="awaiting_confirmation",
        lifecycle_reason="crypto_intent_resolver_ok",
    )

    return {
        "ok": True,
        "flow": "crypto_investment_intent",
        "action_draft_id": str(row.id),
        "confirmation_summary": summary,
        "slots": slots,
    }


__all__ = ["SPEC", "execute"]
